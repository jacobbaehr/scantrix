import io
import logging
import os
import zipfile

import requests
import uuid
from pathlib import Path
from typing import Annotated, Optional, List

from fastapi import Depends, FastAPI, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from src.brush import run_brush
from src.colmap.colmap import run_colmap
from src.dependencies import validate_upload_file
from src.frame_extraction.frame_extraction import extract_frames_ffmpeg
from src.utils import copy_upload_file_to_disk, file_chunk_generator

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 👈 Change this to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# read from env (with fallback)
SPLAT_STORAGE_DIR = Path(os.getenv("SPLAT_STORAGE_DIR", "splat_storage"))
SPLAT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

LOGGER = logging.getLogger(__name__)


@app.post("/splats")
def create_splat(
    video: Annotated[Optional[UploadFile], "One video file"] = None,
    images_archive: Annotated[Optional[UploadFile], "A ZIP archive containing image files"] = None,
):
    # Mutual‐exclusion check
    if bool(video) == bool(images_archive):
        raise HTTPException(
            status_code=400,
            detail="You must provide exactly one of `video` or `images_archive`.",
        )

    request_uuid = uuid.uuid4()
    temp_dir = SPLAT_STORAGE_DIR / str(request_uuid)
    temp_dir.mkdir(parents=True)
    colmap_dir = temp_dir / "colmap"
    images_dir = colmap_dir / "images"
    colmap_dir.mkdir()
    images_dir.mkdir()

    mask_path = None
    if video:
        validate_upload_file(video)
        temp_video_path = temp_dir / video.filename
        copy_upload_file_to_disk(video, temp_video_path)
        mask_path = extract_frames_ffmpeg(temp_video_path, images_dir)
    else: # images
        name, ext = os.path.splitext(images_archive.filename or "")
        if ext.lower() != ".zip":
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported archive format: {ext}, expected .zip",
            )

        images_archive.file.seek(0)
        data = images_archive.file.read()
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                # extract only files (skip directories)
                for member in z.namelist():
                    if member.endswith("/"):
                        continue
                    # normalize the path so no one can escape images_dir
                    target = images_dir / Path(member).name
                    with z.open(member) as src, open(target, "wb") as dst:
                        dst.write(src.read())
        except zipfile.BadZipFile:
            raise HTTPException(
                status_code=400, detail="Invalid or corrupted ZIP archive"
            )

    run_colmap(images_dir, colmap_dir, mask_path)
    run_brush(colmap_dir, temp_dir, str(request_uuid))
    compress_splat_to_ksplat(request_uuid)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED, content={"uuid": str(request_uuid)}
    )


def compress_splat_to_ksplat(request_uuid):
    ksplats_url = f"http://localhost:8090/ksplats/{request_uuid}"
    try:
        resp = requests.post(ksplats_url, timeout=5.0)
        resp.raise_for_status()
        LOGGER.info(f"Successfully notified ksplats service: {ksplats_url}")
    except requests.RequestException as e:
        LOGGER.error(f"Failed to notify ksplats service at {ksplats_url}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not notify ksplats service"
        )


@app.get("/splats/{splat_uuid}")
async def read_item(splat_uuid: str):
    file_path = SPLAT_STORAGE_DIR / splat_uuid / f"{splat_uuid}.ksplat"
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    file_size = file_path.stat().st_size
    headers = {
        "Content-Length": str(file_size),
        "Accept-Ranges": "bytes",
        "Content-Disposition": f'attachment; filename="{splat_uuid}.ksplat"',
    }
    return StreamingResponse(
        file_chunk_generator(file_path),
        media_type="application/octet-stream",
        headers=headers,
    )
