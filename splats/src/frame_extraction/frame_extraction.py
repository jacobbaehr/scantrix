import logging
import math
import os
import re
import shutil
from pathlib import Path

import cv2

from src.frame_extraction.ImageSelector import ImageSelector
from src.frame_extraction.mask import save_mask
from src.utils import run_command

LOGGER = logging.getLogger(__name__)


def extract_frames(
    video_path: os.PathLike, output_dir: os.PathLike, interval: int = 60
):
    os.makedirs(output_dir, exist_ok=True)
    cap = cv2.VideoCapture(str(video_path))
    frame_idx = 0
    saved_idx = 0

    fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"fps: {fps}")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % interval == 0:
            frame_path = os.path.join(output_dir, f"{saved_idx:06}.jpg")
            cv2.imwrite(frame_path, frame)
            saved_idx += 1
        frame_idx += 1

    cap.release()


def get_num_frames_in_video(video: Path) -> int:
    """Returns the number of frames in a video.

    Args:
        video: Path to a video.

    Returns:
        The number of frames in a video.
    """
    cmd = f'ffprobe -v error -select_streams v:0 -count_packets \
            -show_entries stream=nb_read_packets -of csv=p=0 "{video}"'
    output = run_command(cmd)
    assert output is not None
    number_match = re.search(r"\d+", output)
    assert number_match is not None
    return int(number_match[0])


def extract_frames_ffmpeg(video_path: Path, output_dir: Path) -> Path | None:
    num_frames = get_num_frames_in_video(video_path)
    if num_frames == 0:
        LOGGER.error(f"Video has no frames: {video_path}")
    LOGGER.info("Number of frames in video:", num_frames)

    num_frames_target = 300  # supposedly a good target num of frames

    num_downscales = 0 # 3
    ffmpeg_cmd = f'ffmpeg -i "{video_path}"'

    crop_cmd = ""

    downscale_chains = [
        f"[t{i}]scale=iw/{2 ** i}:ih/{2 ** i}[out{i}]"
        for i in range(num_downscales + 1)
    ]
    downscale_dirs = [
        Path(str(output_dir) + (f"_{2 ** i}" if i > 0 else ""))
        for i in range(num_downscales + 1)
    ]
    downscale_paths = [
        downscale_dirs[i] / "frame_%05d.png" for i in range(num_downscales + 1)
    ]

    for dir in downscale_dirs:
        dir.mkdir(parents=True, exist_ok=True)

    downscale_chain = (
        f"split={num_downscales + 1}"
        + "".join([f"[t{i}]" for i in range(num_downscales + 1)])
        + ";"
        + ";".join(downscale_chains)
    )

    ffmpeg_cmd += " -vsync vfr"

    # Evenly distribute frame selection
    spacing = num_frames // num_frames_target
    if spacing > 1:
        LOGGER.info(
            f"Extracting {math.ceil(num_frames / spacing)} frames in evenly spaced intervals"
        )
        select_cmd = f"thumbnail={spacing},setpts=N/TB,"
    else:
        LOGGER.error("Can't satisfy requested number of frames. Extracting all frames.")
        ffmpeg_cmd += " -pix_fmt bgr8"
        select_cmd = ""

    downscale_cmd = (
        f' -filter_complex "{select_cmd}{crop_cmd}{downscale_chain}"'
        + "".join(
            [
                f' -map "[out{i}]" "{downscale_paths[i]}"'
                for i in range(num_downscales + 1)
            ]
        )
    )

    ffmpeg_cmd += downscale_cmd

    run_command(ffmpeg_cmd, verbose=True)

    percent_radius_crop: float = 1.0

    # Create mask
    mask_path = save_mask(
        image_dir=output_dir,
        num_downscales=num_downscales,
        crop_factor=(0.0, 0.0, 0.0, 0.0),
        percent_radius=percent_radius_crop,
    )
    if mask_path is not None:
        LOGGER.info(f"Saved mask to {mask_path}")

    return mask_path


def filter_images(
    input_images_dir: os.PathLike,
    target_percentage: int,
    group_count: int = 1,
    scalar: int = 1,
    output_images_dir: os.PathLike | None = None,
):
    """Filters images based on blurriness, exposure, and scene change.

    Sharpness selection based on Laplacian Variance."""
    images = [
        os.path.join(input_images_dir, img) for img in os.listdir(input_images_dir)
    ]
    images.sort()
    total_images = len(images)
    target_count = int(total_images * (target_percentage / 100))
    selector = ImageSelector(images)
    selected_images = selector.filter_sharpest_images(target_count, group_count, scalar)

    if (
        output_images_dir
        and os.path.isdir(input_images_dir)
        and os.path.normcase(os.path.abspath(os.path.normpath(input_images_dir)))
        != os.path.normcase(os.path.abspath(os.path.normpath(output_images_dir)))
    ):
        for img in selected_images:
            new_location = os.path.join(output_images_dir, os.path.basename(img))
            shutil.copy2(img, new_location)
    else:
        for img in images:
            if img not in selected_images:
                os.remove(img)

    LOGGER.info(f"Retained {len(selected_images)} sharpest images.")
