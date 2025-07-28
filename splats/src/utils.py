import logging
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import UploadFile


def copy_upload_file_to_disk(file: UploadFile, output_dir: Path):
    """Copies an UploadFile to disk.

    UploadFile is a "spooled" file which is: A file stored in memory up to a maximum size limit,
    and after passing this limit it will be stored on disk. This utility function is for use
    when you need to reliably guarantee that a physical file is stored on disk for
    downstream processing.

    https://fastapi.tiangolo.com/tutorial/request-files/#file-parameters-with-uploadfile
    """

    with open(output_dir, "wb+") as f:
        shutil.copyfileobj(file.file, f)  # type: ignore


def run_command(cmd: str, verbose=False) -> Optional[str]:
    """Runs a command and returns the output.

    Args:
        cmd: Command to run.
        verbose: If True, logs the output of the command.
    Returns:
        The output of the command if return_output is True, otherwise None.
    """
    out = subprocess.run(
        cmd, capture_output=not verbose, shell=True, check=False, text=True
    )
    if out.returncode != 0:
        logging.error(out.stderr)
    if out.stdout is not None:
        return out.stdout
    return out


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
