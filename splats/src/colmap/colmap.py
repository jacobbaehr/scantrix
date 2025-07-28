import logging
import os
import subprocess
from pathlib import Path
from typing import Literal, Optional

from src.utils import run_command

LOGGER = logging.getLogger(__name__)


def _run_colmap(
    image_dir: Path,
    colmap_dir: Path,
    camera_model: str,
    camera_mask_path: Optional[Path] = None,
    gpu: bool = True,
    verbose: bool = False,
    matching_method: Literal["vocab_tree", "exhaustive", "sequential"] = "vocab_tree",
    refine_intrinsics: bool = True,
    colmap_cmd: str = "colmap",
) -> None:
    """Runs COLMAP on the images.

    Args:
        image_dir: Path to the directory containing the images.
        colmap_dir: Path to the output directory.
        camera_model: Camera model to use.
        camera_mask_path: Path to the camera mask.
        gpu: If True, use GPU.
        verbose: If True, logs the output of the command.
        matching_method: Matching method to use.
        refine_intrinsics: If True, refine intrinsics.
        colmap_cmd: Path to the COLMAP executable.
    """

    colmap_database_path = colmap_dir / "database.db"
    colmap_database_path.unlink(missing_ok=True)

    # Feature extraction
    feature_extractor_cmd = [
        f"{colmap_cmd} feature_extractor",
        f"--database_path {colmap_dir / 'database.db'}",
        f"--image_path {image_dir}",
        "--ImageReader.single_camera 1",
        f"--ImageReader.camera_model {camera_model}",
        f"--SiftExtraction.use_gpu {int(gpu)}",
    ]
    if camera_mask_path is not None:
        feature_extractor_cmd.append(
            f"--ImageReader.camera_mask_path {camera_mask_path}"
        )
    feature_extractor_cmd = " ".join(feature_extractor_cmd)

    run_command(feature_extractor_cmd, verbose=verbose)

    LOGGER.info("Done extracting COLMAP features.")

    # Feature matching
    feature_matcher_cmd = [
        f"{colmap_cmd} {matching_method}_matcher",
        f"--database_path {colmap_dir / 'database.db'}",
        f"--SiftMatching.use_gpu {int(gpu)}",
    ]
    vocab_tree_path = Path("src/colmap/vocab_tree.fbow")
    if matching_method == "vocab_tree":
        feature_matcher_cmd.append(
            f'--VocabTreeMatching.vocab_tree_path "{vocab_tree_path}"'
        )
    feature_matcher_cmd = " ".join(feature_matcher_cmd)
    run_command(feature_matcher_cmd, verbose=verbose)
    LOGGER.info("Done matching COLMAP features.")

    # Bundle adjustment
    sparse_dir = colmap_dir / "sparse"
    sparse_dir.mkdir(parents=True, exist_ok=True)
    mapper_cmd = [
        f"{colmap_cmd} mapper",
        f"--database_path {colmap_dir / 'database.db'}",
        f"--image_path {image_dir}",
        f"--output_path {sparse_dir}",
    ]
    mapper_cmd.append("--Mapper.ba_global_function_tolerance=1e-6")

    mapper_cmd = " ".join(mapper_cmd)

    LOGGER.info("Running COLMAP bundle adjustment...")
    run_command(mapper_cmd, verbose=verbose)
    LOGGER.info("Done COLMAP bundle adjustment.")

    if refine_intrinsics:
        bundle_adjuster_cmd = [
            f"{colmap_cmd} bundle_adjuster",
            f"--input_path {sparse_dir}/0",
            f"--output_path {sparse_dir}/0",
            "--BundleAdjustment.refine_principal_point 1",
        ]
        run_command(" ".join(bundle_adjuster_cmd), verbose=verbose)
        LOGGER.info("Done refining intrinsics.")


def run_colmap(images_dir: Path, colmap_dir: Path, mask_path: Optional[Path] = None):
    """
    Args:
        mask_path: Path to the camera mask. Defaults to None.
    """

    matching_method = "vocab_tree"  # got from nerfstudio

    _run_colmap(
        image_dir=images_dir,
        colmap_dir=colmap_dir,
        camera_model="OPENCV",
        camera_mask_path=mask_path,
        gpu=True,
        verbose=True,
        matching_method=matching_method,
        refine_intrinsics=True,
        colmap_cmd="colmap",
    )
