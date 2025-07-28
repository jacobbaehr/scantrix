import logging
import mimetypes
import os
from typing import Dict

from fastapi import HTTPException, status, UploadFile

LOGGER = logging.getLogger(__name__)

VIDEO_MIMETYPES = {
    "video/mp4",
    "video/webm",
    "video/quicktime",
    "video/x-msvideo",
    "video/x-flv",
    "video/x-ms-wmv",
}
MAX_VIDEO_SIZE_BYTES = 5 * 1000 * 1024 * 1024  # 5GB
# Allowed image MIME types and file extensions
IMAGE_MIMETYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/bmp",
    "image/tiff",
    "image/webp",
}
ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}

# (Optional) enforce a per-image size limit, e.g. 50 MB
MAX_IMAGE_SIZE_BYTES = 50 * 1024 * 1024


def validate_upload_file(file: UploadFile) -> UploadFile:
    errors: Dict[str, str] = {}

    if file.content_type not in VIDEO_MIMETYPES:
        errors["content_type"] = f"Expected video file, got {file.content_type}"

    mimetype, _ = mimetypes.guess_type(file.filename)
    if file.content_type != mimetype:
        errors["content_type_mismatch"] = (
            f"Header content type mismatch, expected {file.content_type}, got {mimetype}"
        )

    _, ext = os.path.splitext(file.filename)
    if ext not in [".mp4", ".MP4", ".webm", ".MOV", ".mov", ".avi", ".flv", ".wmv"]:
        errors["extension"] = f"Unsupported video format: {ext}"

    if file.size > MAX_VIDEO_SIZE_BYTES:
        errors["size"] = (
            f"File too large. Maximum size is {MAX_VIDEO_SIZE_BYTES} bytes. Got {file.size} bytes"
        )

    if errors:
        LOGGER.error(errors)
        raise HTTPException(
            status_code=400,
            detail="Invalid video file",
            headers={"X-Error-Detail": str(errors)},
        )

    return file


def validate_image_file(file: UploadFile) -> UploadFile:
    """
    Ensure an UploadFile is a supported image type, has a matching extension,
    and (optionally) is under the size limit.
    """
    errors: Dict[str, str] = {}

    # 1) content_type must be an image
    if file.content_type not in IMAGE_MIMETYPES:
        errors["content_type"] = f"Expected image file, got {file.content_type}"

    # 2) extension must match a known image format
    _, ext = os.path.splitext(file.filename)
    if ext.lower() not in ALLOWED_IMAGE_EXTS:
        errors["extension"] = f"Unsupported image format: {ext}"

    # 3) header/content-type vs. filename guess
    guessed_type, _ = mimetypes.guess_type(file.filename)
    if guessed_type and guessed_type != file.content_type:
        errors["mimetype_mismatch"] = (
            f"Filename suggests {guessed_type}, but header is {file.content_type}"
        )

    # 4) optional size check (if your UploadFile has .size)
    size = getattr(file, "size", None)
    if size is not None and size > MAX_IMAGE_SIZE_BYTES:
        errors["size"] = (
            f"Image too large: max {MAX_IMAGE_SIZE_BYTES} bytes, got {size}"
        )

    if errors:
        LOGGER.error("Image validation failed: %s", errors)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file",
            headers={"X-Error-Detail": str(errors)},
        )

    return file

