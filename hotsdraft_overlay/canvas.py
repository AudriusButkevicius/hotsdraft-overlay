import ctypes
import logging
import os
import os.path
from typing import Optional, Any, List

import cv2
import numpy as np
from PyQt5.Qt import Qt
from PyQt5.QtCore import QPoint, QTimer
from PyQt5.QtGui import QImage, QPainter
from PyQt5.QtWidgets import QMainWindow, QDesktopWidget
from desktopmagic.screengrab_win32 import getRectAsImage
from win32gui import GetWindowText, GetForegroundWindow, GetClientRect, ClientToScreen, FindWindow

from hotsdraft_overlay.models import Rect, Point
from hotsdraft_overlay.painting import PaintCommand


class BaseCanvas(QMainWindow):
    def __init__(self):
        ctypes.windll.user32.SetProcessDPIAware()
        super().__init__()
        self.__paint_commands = []
        self.init()
        self.showMaximized()
        self.activateWindow()

    def init(self):
        raise NotImplemented()

    def capture(self):
        raise NotImplemented()

    def execute_paint_commands(self, paint_commands: List[PaintCommand]):
        self.__paint_commands = paint_commands
        self.repaint()

    def clear_paint_commands(self):
        self.__paint_commands = []
        self.repaint()

    def paintEvent(self, e):
        painter = QPainter(self)
        for command in self.__paint_commands:
            painter.save()
            command.paint(painter)
            painter.restore()
        super().paintEvent(e)


class WindowCanvas(BaseCanvas):
    def __init__(self, window_name):
        super().__init__()
        self.__window_name = window_name
        self.__last_rect = None

    def init(self):
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setWindowFlag(Qt.Tool)

    def capture(self) -> Optional[Any]:
        hwnd = GetForegroundWindow()
        if hwnd:
            if GetWindowText(hwnd) == self.__window_name:
                rect = self.__get_handle_rect(hwnd)
                self.__maybe_align(rect)
                screen_shot = getRectAsImage(rect.tuple)
                return cv2.cvtColor(np.array(screen_shot), cv2.COLOR_RGB2BGR)
        return None

    def paintEvent(self, e):
        self.__align_to_target_window()
        super().paintEvent(e)

    def __align_to_target_window(self):
        hwnd = FindWindow(0, self.__window_name)
        if hwnd:
            rect = self.__get_handle_rect(hwnd)
            self.__maybe_align(rect)

    def __maybe_align(self, rect: Rect):
        if rect == self.__last_rect:
            return

        self.__last_rect = rect
        # Run in UI thread
        QTimer.singleShot(0, self.__adjust_geometry)

    def __adjust_geometry(self):
        logging.debug("Moving overlay to %s" % self.__last_rect)
        self.setGeometry(self.__last_rect.qrect)
        self.updateGeometry()

    @staticmethod
    def __get_handle_rect(hwnd) -> Rect:
        # Get the size of the rectangle
        x, y, x1, y1 = GetClientRect(hwnd)
        # Get the position of the rectangle top corner on screen.
        x, y = ClientToScreen(hwnd, (x, y))
        # Move the bottom right corner by the offset
        x1 += x
        y1 += y
        return Rect(Point(x, y), Point(x1, y1))


class ScreenshotCanvas(BaseCanvas):
    def __init__(self, directory):
        self.__desktop_size = QDesktopWidget().screenGeometry().size()
        super().__init__()
        self.__screenshots = [
            os.path.join(directory, file)
            for file in os.listdir(directory)
            if os.path.isfile(os.path.join(directory, file))
        ]
        self.__current_image = None

    def init(self):
        self.setWindowTitle("Screenshot preview")
        self.setBaseSize(self.__desktop_size)

    def capture(self) -> Optional[Any]:
        if not self.__screenshots:
            self.__current_image = None
            self.__set_title("No more images left")
        else:
            path = self.__screenshots.pop(0)
            logging.debug("Providing screenshot %s", path)
            self.__set_title("Preview %s" % path)
            cv_image = cv2.imread(path)

            img_h, img_w = cv_image.shape[:2]
            window_h, window_w = self.size().height(), self.size().width()

            biggest_ratio = max(float(img_h) / window_h, float(img_w) / window_w)
            if biggest_ratio > 1:
                cv_image = cv2.resize(cv_image, None, fx=1.0 / biggest_ratio, fy=1.0 / biggest_ratio,
                                      interpolation=cv2.INTER_AREA)

            self.__current_image = cv_image
            self.repaint()

        return self.__current_image

    def __set_title(self, title):
        # Needs to run on UI thread
        QTimer.singleShot(0, lambda t=title: self.setWindowTitle(t))

    def paintEvent(self, e):
        if self.__current_image is not None:
            img = self.__current_image
            painter = QPainter(self)
            qimg = QImage(img, img.shape[1], img.shape[0], img.shape[1] * 3, QImage.Format_RGB888).rgbSwapped()
            painter.drawImage(QPoint(0, 0), qimg)
        super().paintEvent(e)
