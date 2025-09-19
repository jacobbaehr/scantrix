from pathlib import Path

from fastapi import FastAPI, Request, HTTPException, Header, Response, status
import os
import re
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import aiofiles

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 👈 Change this to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

VIDEO_PATH = Path(os.getenv("VIDEO_PATH"))
SPLAT_STORAGE_DIR = Path(os.getenv("SPLAT_STORAGE_DIR", "splat_storage"))
SPLAT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
CHUNK_SIZE = 1024 * 1024  # 1 MiB per chunk

# 1) Allow an override so you can set FRONTEND_DIST in prod (e.g. Docker)
landing_page_dist = os.getenv("LANDING_PAGE_FRONTEND_DIST")
if landing_page_dist:
    LANDING_PAGE_DIST = Path(landing_page_dist)
else:
    # 2) Fallback: locate it relative to this file in source checkout
    #    └── project/
    #        ├─ src/ark/main.py    <- this file
    #        └─ src/scantrix-api-web/dist/
    LANDING_PAGE_DIST = Path(__file__).parent.parent.parent.parent / "scantrix-api-web" / "dist"

print(LANDING_PAGE_DIST)

# sanity‐check
if not LANDING_PAGE_DIST.exists():
    raise RuntimeError(f"Could not find frontend dist folder at {LANDING_PAGE_DIST!r}")

app.mount(
    "/landing_page",
    StaticFiles(directory=LANDING_PAGE_DIST),
    name="landing page",
)

demo_app_dist = os.getenv("DEMO_APP_FRONTEND_DIST")
if demo_app_dist:
    DEMO_APP_DIST = Path(demo_app_dist)
else:
    # 2) Fallback: locate it relative to this file in source checkout
    #    └── project/
    #        ├─ src/ark/main.py    <- this file
    #        └─ src/scantrix-ui-web/dist/
    DEMO_APP_DIST = Path(__file__).parent.parent.parent.parent / "scantrix-ui-web" / "dist"

print(DEMO_APP_DIST)

# sanity‐check
if not DEMO_APP_DIST.exists():
    raise RuntimeError(f"Could not find frontend dist folder at {DEMO_APP_DIST!r}")

app.mount(
    "/demo_app",
    StaticFiles(directory=DEMO_APP_DIST),
    name="demo app",
)

@app.get("/", response_class=HTMLResponse)
async def serve_spa():
    return FileResponse(LANDING_PAGE_DIST / "index.html")

@app.get("/demo", response_class=HTMLResponse)
async def serve_spa_demo():
    return FileResponse(DEMO_APP_DIST / "index.html")


def get_file_size(path: str) -> int:
    return os.stat(path).st_size

def iter_file(path: str, start: int = 0, end: int = None):
    """Yield file bytes from start to end (inclusive)."""
    with open(path, "rb") as f:
        f.seek(start)
        bytes_to_read = (end - start + 1) if end is not None else None
        while True:
            chunk = f.read(CHUNK_SIZE if bytes_to_read is None else min(CHUNK_SIZE, bytes_to_read))
            if not chunk:
                break
            yield chunk
            if bytes_to_read is not None:
                bytes_to_read -= len(chunk)
                if bytes_to_read <= 0:
                    break

@app.get("/video")
async def stream_video(range: str = Header(None)):
    file_size = get_file_size(VIDEO_PATH)

    if range is None:
        # No Range header: client wants the whole file
        return StreamingResponse(
            iter_file(VIDEO_PATH),
            media_type="video/mp4",
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(file_size),
            },
        )

    # Parse Range header: e.g. "bytes=0-1023"
    m = re.match(r"bytes=(\d*)-(\d*)", range)
    if not m:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Range header")

    start_str, end_str = m.groups()
    start = int(start_str) if start_str else 0
    end = int(end_str) if end_str else file_size - 1
    if start >= file_size or end >= file_size or start > end:
        # Unsatisfiable range
        raise HTTPException(status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE)

    chunk_size = end - start + 1

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(chunk_size),
    }

    return StreamingResponse(
        iter_file(VIDEO_PATH, start, end),
        status_code=status.HTTP_206_PARTIAL_CONTENT,
        media_type="video/mp4",
        headers=headers,
    )


async def file_chunk_generator(
    path: Path,
    chunk_size: int = 1024 * 1024,  # 1 MB per chunk,
    start: int = 0,
    end: int = None
):
    """
    Async generator that reads a slice [start,end] of the file in CHUNK_SIZE pieces.
    """
    file_size = path.stat().st_size
    end = end if end is not None else file_size - 1
    bytes_to_read = end - start + 1

    async with aiofiles.open(path, "rb") as f:
        await f.seek(start)
        while bytes_to_read > 0:
            read_size = min(chunk_size, bytes_to_read)
            data = await f.read(read_size)
            if not data:
                break
            bytes_to_read -= len(data)
            yield data


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
