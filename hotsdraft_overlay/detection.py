import logging
import os.path
from typing import Optional, List, Any, Tuple

import cv2
import numpy as np
import pytesseract
from rapidfuzz import fuzz

from hotsdraft_overlay import utils
from hotsdraft_overlay.data import DataProvider
from hotsdraft_overlay.models import DraftState, Point, ImageCut, Region, Rect, Features, Portrait, DraftHero


class Detector(object):
    __tessaract_cmd = "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

    def __init__(self, data_provider: DataProvider):
        self.__data_provider = data_provider

        self.__init_tessaract()

    def __init_tessaract(self):
        if not os.path.exists(self.__tessaract_cmd):
            raise RuntimeError("Could not find tesseract in " + self.__tessaract_cmd)
        pytesseract.pytesseract.tesseract_cmd = self.__tessaract_cmd

    def get_draft_state(self, image, show_cuts=False, allow_resize=False) -> Optional[DraftState]:
        # Resize the image if it's large
        if allow_resize and image.shape[0] > 1080:
            logging.debug("Resizing image")
            image = utils.resize(image, height=1080)

        cuts = self.__get_image_cuts(image)

        if show_cuts:
            for i, cut in enumerate(cuts):
                cv2.imshow(cut.region.name + " " + str(i), cut.image)
                cv2.waitKey(0)

        # Get the map we're playing, if we can't get that, we're probably not in draft.
        game_map = self.__get_map(image) or None
        logging.debug("Got map %s", game_map)

        best_score = 0
        best_map_name = None
        if game_map:
            for map_name in self.__data_provider.get_map_names():
                score = fuzz.partial_ratio(map_name, game_map)
                logging.debug("Got %d score for %s", score, map_name)
                if score > best_score:
                    best_score = score
                    best_map_name = map_name

            if best_score < 75:
                logging.debug("Best score %d < 50, clearing map %s", best_score, best_map_name)
                best_map_name = None

        state = DraftState(best_map_name)

        for cut in cuts:
            cut_features = utils.extract_features(cut.image)
            if not cut_features.key_points:
                logging.debug("Cut %s produced no key points" % cut)
                continue

            best_score = 0
            best_match = None

            for portrait in self.__data_provider.get_portraits():
                try:
                    all_matches = utils.match_features(portrait.features, cut_features)

                    # Apply ratio test
                    good_matches = []
                    score = 0
                    for m, n in all_matches:
                        if m.distance < 0.7 * n.distance:
                            good_matches.append(m)
                            score += m.distance ** 2 + n.distance ** 2

                    if len(good_matches) < 10:
                        logging.debug("Skipping %s as got %d matches", portrait.hero.name, len(good_matches))
                        continue

                    if score < best_score:
                        logging.debug("Skipping %s as got %.2f score vs current best %.2f", portrait.hero.name, score,
                                      best_score)
                        continue

                    bounding_box = self.__get_bounding_box(portrait, cut_features, good_matches)
                    if not bounding_box:
                        logging.debug("Failed to compute bounding box for %s, skipping", portrait.hero.name)
                        continue

                    # Some false matches are sometimes produced with a bounding box that is stretched.
                    # We expect the matches have a sensible height to width ratio.
                    bounding_box_ratio = bounding_box.ratio
                    if bounding_box_ratio > 1.2:
                        logging.debug("Skipping %s as got high bounding box ratio %.2f", portrait.hero.name,
                                      bounding_box_ratio)
                        continue

                    locked = True
                    if cut.region == Region.ALLY_PICKS:
                        bounding_box_image = utils.crop_to_rect(cut.image, bounding_box)
                        locked = self.__get_locked_status(portrait.image, bounding_box_image)

                    bounding_box_with_offset = Rect(
                        utils.add_offset_to_point(bounding_box.top_left, cut.offset),
                        utils.add_offset_to_point(bounding_box.bottom_right, cut.offset),
                    )

                    best_match = DraftHero(portrait.hero.name, portrait.hero.id, locked, bounding_box_with_offset,
                                           cut.region)
                    best_score = score
                    logging.debug("%s is the current best match with score %.2f", portrait.hero.name, score)
                except Exception as e:
                    logging.exception("Exception while processing %s" % portrait.hero.name)

            if best_match is not None:
                if cut.region == Region.ALLY_PICKS:
                    state.ally_picks.append(best_match)
                elif cut.region == Region.ENEMY_PICKS:
                    state.enemy_picks.append(best_match)
                elif cut.region == Region.ALLY_BANS:
                    state.ally_bans.append(best_match)
                elif cut.region == Region.ENEMY_BANS:
                    state.enemy_bans.append(best_match)
                else:
                    raise RuntimeError("Unhandled cut region")

        # Sort by x or y, which roughly translates into slot order.
        state.ally_picks.sort(key=lambda pick: pick.bounding_box.top_left.y)
        state.enemy_picks.sort(key=lambda pick: pick.bounding_box.top_left.y)
        state.ally_bans.sort(key=lambda pick: pick.bounding_box.top_left.x)
        state.enemy_bans.sort(key=lambda pick: pick.bounding_box.top_left.x)

        return state

    def __get_map(self, image) -> Optional[str]:
        h, w = image.shape[:2]
        ratio = 3
        cropped = image[0:int(h / 25), int(w / ratio):int((ratio - 1) * w / ratio)]
        lab = cv2.cvtColor(cropped, cv2.COLOR_BGR2LAB)
        # Remove color channels, just use luminosity
        luminosity = cv2.split(lab)[0]
        config = "--psm 7"
        word_file = self.__data_provider.get_word_file()
        if word_file:
            config += " --user-words " + word_file
        return pytesseract.image_to_string(luminosity, config=config)

    @staticmethod
    def __get_bounding_box(portrait: Portrait, cut_features: Features, matches: List[Any]) -> Optional[Rect]:
        src_pts = np.float32([portrait.features.key_points[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([cut_features.key_points[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)

        matrix, _ = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        if matrix is None:
            return None

        h, w, d = portrait.image.shape
        pts = np.float32([[0, 0], [0, h - 1], [w - 1, h - 1], [w - 1, 0]]).reshape(-1, 1, 2)
        dst = cv2.perspectiveTransform(pts, matrix)

        top_left = Point(
            max(int(min(point[0][0] for point in dst)), 0),
            max(int(min(point[0][1] for point in dst)), 0)
        )
        bottom_right = Point(
            max(int(max(point[0][0] for point in dst)), 0),
            max(int(max(point[0][1] for point in dst)), 0)
        )

        return Rect(top_left, bottom_right)

    @staticmethod
    def __get_image_cuts(image) -> List[ImageCut]:
        h, w = image.shape[:2]

        cuts = []
        # These offsets adjust x axis based on the height of the image, as it seems the UI elements are either
        # left or right aligned in case of wide screen monitors.
        ally_picks_offset = Point(0, int(h * 0.06))
        ally_picks = image[ally_picks_offset.y:int(h * 0.85), ally_picks_offset.x:int(h / 3.6)]

        cuts.extend(
            Detector.__get_pick_portrait_slices(
                ally_picks, ally_picks_offset, (0.47, 0.97), (0.14, 0.65), Region.ALLY_PICKS
            )
        )

        enemy_picks_offset = Point(int(w - (h / 3.6)), int(h * 0.06))
        enemy_picks = image[enemy_picks_offset.y:int(h * 0.85), enemy_picks_offset.x:w]
        cuts.extend(
            Detector.__get_pick_portrait_slices(
                enemy_picks, enemy_picks_offset, (0.03, 0.54), (0.34, 0.87), Region.ENEMY_PICKS
            )
        )

        ally_bans_offset = Point(int(h / 4), int(h / 100))
        ally_bans = image[ally_bans_offset.y:int(h / 10), ally_bans_offset.x:int(2.05 * h / 4)]
        cuts.extend(
            Detector.__get_ban_portrait_slices(ally_bans, ally_bans_offset, Region.ALLY_BANS)
        )

        enemy_bans_offset = Point(w - int(2.05 * h / 4), int(h / 100))
        enemy_bans = image[enemy_bans_offset.y:int(h / 10), enemy_bans_offset.x:w - int(h / 4)]
        cuts.extend(
            Detector.__get_ban_portrait_slices(enemy_bans, enemy_bans_offset, Region.ENEMY_BANS)
        )

        return cuts

    @staticmethod
    def __get_pick_portrait_slices(base_image: Any, base_offset: Point,
                                   odd_multiplier: Tuple[float, float], even_multiplier: Tuple[float, float],
                                   region: Region) -> List[ImageCut]:
        cuts = []
        h, w = base_image.shape[:2]
        for idx in range(5):
            # Portraits alternate
            if idx % 2 == 1:
                w_start = int(w * odd_multiplier[0])
                w_end = int(w * odd_multiplier[1])
            else:
                w_start = int(w * even_multiplier[0])
                w_end = int(w * even_multiplier[1])
            portrait_cut_offset = Point(w_start, int(h / 5 * idx))
            portrait_cut = base_image[portrait_cut_offset.y:int(h / 5 * (idx + 1)), portrait_cut_offset.x:w_end]
            current_portrait_offset = utils.add_offset_to_point(base_offset, portrait_cut_offset)
            cuts.append(ImageCut(portrait_cut, region, current_portrait_offset))
        return cuts

    @staticmethod
    def __get_ban_portrait_slices(base_image: Any, base_offset: Point, region: Region):
        cuts = []
        h, w = base_image.shape[:2]
        for idx in range(3):
            portrait_cut_offset = Point(int(w / 3 * idx), 0)
            portrait_cut = base_image[portrait_cut_offset.y:h, portrait_cut_offset.x:int(w / 3 * (idx + 1))]
            current_portrait_offset = utils.add_offset_to_point(base_offset, portrait_cut_offset)
            cuts.append(ImageCut(portrait_cut, region, current_portrait_offset))
        return cuts

    @staticmethod
    def __get_locked_status(portrait_image, draft_image):
        if draft_image.shape[0] > portrait_image.shape[0]:
            draft_image = utils.resize(draft_image, height=portrait_image.shape[0])
        else:
            portrait_image = utils.resize(portrait_image, height=draft_image.shape[0])

        # Remove the frames and what not, by cutting a smaller square out of the image, stripping 25% of each side.
        h, w = draft_image.shape[:2]
        ratio = 4
        crop_bounding_box = Rect(
            Point(int(w / ratio), int(h / ratio)),
            Point(int((ratio - 1) * w / ratio), int((ratio - 1) * h / ratio))
        )

        draft_image_cropped = utils.crop_to_rect(draft_image, crop_bounding_box)
        portrait_image_cropped = utils.crop_to_rect(portrait_image, crop_bounding_box)

        if min(*(draft_image_cropped.shape[:2] + portrait_image_cropped.shape[:2])) > 0:
            draft_image_channel_variance = utils.get_channel_variance(draft_image_cropped, cv2.COLOR_BGR2YCrCb)
            portrait_channel_variance = utils.get_channel_variance(portrait_image_cropped, cv2.COLOR_BGR2YCrCb)

            luminosity_ratio = (portrait_channel_variance[0] / draft_image_channel_variance[0])
            chromatic_ratio = (
                    ((portrait_channel_variance[1] / draft_image_channel_variance[1]) +
                     (portrait_channel_variance[2] / draft_image_channel_variance[2])) / 2
            )
            # Not used for now
            _ = chromatic_ratio
            return luminosity_ratio < 2.5
        return False
