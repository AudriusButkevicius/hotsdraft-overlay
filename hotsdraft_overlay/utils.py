import logging
import pathlib
import sys
from typing import Optional

import cv2

from hotsdraft_overlay.models import Point, Features, Rect

FEATURE_EXTRACTOR = cv2.xfeatures2d.SIFT_create()
MATCHER = cv2.BFMatcher()


def extract_features(image) -> Features:
    key_points, descriptors = FEATURE_EXTRACTOR.detectAndCompute(
        cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), None
    )
    return Features(key_points, descriptors)


def match_features(query: Features, train: Features):
    return MATCHER.knnMatch(query.descriptors, train.descriptors, k=2)


def crop_to_rect(image, rect: Rect):
    return image[
           rect.top_left.y:rect.bottom_right.y,
           rect.top_left.x:rect.bottom_right.x
           ]


def resize(image, width: Optional[int] = None, height: Optional[int] = None, inter=cv2.INTER_AREA):
    # initialize the dimensions of the image to be resized and
    # grab the image size
    dim = None
    (h, w) = image.shape[:2]

    # if both the width and height are None, then return the
    # original image
    if width is None and height is None:
        return image

    # check to see if the width is None
    if width is None:
        # calculate the ratio of the height and construct the
        # dimensions
        r = height / float(h)
        dim = (int(w * r), height)

    # otherwise, the height is None
    else:
        # calculate the ratio of the width and construct the
        # dimensions
        r = width / float(w)
        dim = (width, int(h * r))

    # resize the image
    resized = cv2.resize(image, dim, interpolation=inter)

    # return the resized image
    return resized


def add_offset_to_point(point: Point, offset: Point) -> Point:
    return Point(point.x + offset.x, point.y + offset.y)


def get_channel_variance(image, color_scheme=None):
    if color_scheme:
        image = cv2.cvtColor(image, color_scheme)
    image_channels = cv2.split(image)
    channel_variance = []
    for channel in image_channels:
        mean = channel.mean()
        difference = channel - mean
        channel_variance.append((difference ** 2).mean())
    return channel_variance


def monkey_patch_exception_hook():
    import sys

    real_hook = sys.excepthook

    def monkey_patched_exception_hook(exception_type, value, traceback):
        logging.error("Got exception %s: %s\nTraceback:\n%s" % (exception_type, value, traceback))
        return real_hook(exception_type, value, traceback)

    sys.excepthook = monkey_patched_exception_hook


def get_root():
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        return pathlib.Path(sys._MEIPASS).absolute()
    except Exception:
        return pathlib.Path(__file__).parent.absolute()
