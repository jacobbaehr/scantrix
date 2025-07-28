import logging
from pathlib import Path

from src.utils import run_command

LOGGER = logging.getLogger(__name__)


def run_brush(colmap_dir: Path, output_dir: Path, filename: str):
    cmd = "brush_app --sh-degree 2 " f"{colmap_dir} --export-path {output_dir} --export-name {filename}.ply " "--export-every 30000"
    LOGGER.info("Running brush with command: %s", cmd)
    run_command(cmd, verbose=True)
