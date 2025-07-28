import logging

import cv2
import numpy as np

"""Inspired by https://github.com/SharkWipf/nerf_dataset_preprocessing_helper/blob/main/ImageSelector.py"""


LOGGER = logging.getLogger(__name__)

FEATURE_MOTION_SCORE_THRESHOLD = 10


class ImageSelector:
    def __init__(self, images):
        self.images = images
        self.image_fm = self._compute_sharpness_values()

    def _compute_sharpness_values(self):
        LOGGER.info("Calculating image sharpness...")
        scores_array = []
        for i, img_path in enumerate(self.images):
            print(f"calculating img score for {img_path}")
            img = cv2.imread(img_path)
            if img is None:
                continue
            else:
                scores = {
                    "sharpness": self.variance_of_laplacian(
                        cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    ),
                    "exposure": "",
                    "feature_motion_score": (
                        self.feature_motion_score(cv2.imread(self.images[i - 1]), img)
                        if i > 0
                        else 0
                    ),
                    "img_path": img_path,
                }
                print(scores)
                if scores["feature_motion_score"] <= 0.2:
                    continue
                scores_array.append(scores)
        return scores_array

    @staticmethod
    def variance_of_laplacian(image):
        return cv2.Laplacian(image, cv2.CV_64F).var()

    @staticmethod
    def feature_motion_score(prev_image, image):
        feature = cv2.SIFT_create()
        kp1, des1 = feature.detectAndCompute(prev_image, None)
        kp2, des2 = feature.detectAndCompute(image, None)

        if des1 is None or des2 is None:
            return 0

        bf = cv2.BFMatcher(cv2.NORM_L2)
        matches = bf.match(des1, des2)

        if len(matches) < 8:
            return 0

        # Compute average keypoint motion
        motions = []
        for m in matches:
            pt1 = kp1[m.queryIdx].pt
            pt2 = kp2[m.trainIdx].pt
            dist = np.linalg.norm(np.array(pt1) - np.array(pt2))
            motions.append(dist)

        raw_motion_score = np.median(motions)

        h1, w1 = prev_image.shape[:2]
        h2, w2 = image.shape[:2]
        max_dim = max(w1, h1, w2, h2)
        normalized_motion_score = raw_motion_score / max_dim

        return normalized_motion_score

    @staticmethod
    def distribute_evenly(total, num_of_groups):
        ideal_per_group = total / num_of_groups
        accumulated_error = 0.0
        distribution = [0] * num_of_groups

        for i in range(num_of_groups):
            distribution[i] = int(ideal_per_group)
            accumulated_error += ideal_per_group - distribution[i]

            while accumulated_error >= 1.0:
                distribution[i] += 1
                accumulated_error -= 1.0

        return distribution, ideal_per_group

    def filter_sharpest_images(self, target_count, group_count=None, scalar=1):
        if scalar is None:
            scalar = 1
        if group_count is None:
            group_count = target_count // (2 ** (scalar - 1))
            group_count = max(1, group_count)

        split = len(self.images) / target_count
        ratio = target_count / len(self.images)
        formatted_ratio = "{:.1%}".format(ratio)
        LOGGER.info(
            f"Requested {target_count} out of {len(self.images)} images ({formatted_ratio}, 1 in {split:.1f})."
        )

        group_sizes, ideal_total_images_per_group = self.distribute_evenly(
            len(self.images), group_count
        )
        images_per_group_list, ideal_selected_images_per_group = self.distribute_evenly(
            target_count, group_count
        )

        LOGGER.info(
            f"Selecting {target_count} image{'s' if target_count != 1 else ''} across {group_count} group{'s' if group_count != 1 else ''}, "
            f"with total ~{ideal_total_images_per_group:.1f} image{'s' if ideal_total_images_per_group != 1 else ''} per group and selecting "
            f"~{ideal_selected_images_per_group:.1f} image{'s' if ideal_selected_images_per_group != 1 else ''} per group (scalar {scalar})."
        )

        images_per_group_list, _ = self.distribute_evenly(target_count, group_count)

        selected_images = []
        offset_index = 0
        for idx, size in enumerate(group_sizes):
            end_idx = offset_index + size
            group = sorted(
                self.image_fm[offset_index:end_idx],
                key=lambda x: (x["sharpness"], x["feature_motion_score"]),
                reverse=True,
            )
            """
            # Sort by multiple keys
print("\nSort by age (ascending) then by name (descending):")
print(sorted(people, key=lambda x: (x['age'], x['name']), reverse=True))
            """
            selected_images.extend(
                [img["img_path"] for img in group[: images_per_group_list[idx]]]
            )
            offset_index = end_idx

        return selected_images
