import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from queue import Queue

import keyboard
from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import QApplication

from hotsdraft_overlay import layout, utils
from hotsdraft_overlay.canvas import WindowCanvas, BaseCanvas
from hotsdraft_overlay.data import DataProvider
from hotsdraft_overlay.detection import Detector
from hotsdraft_overlay.models import Annotation, Point
from hotsdraft_overlay.suggest import Suggester

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s]: %(message)s')


class Runner(QThread):
    def __init__(self, parent, canvas: BaseCanvas):
        super().__init__(parent)
        self.canvas = canvas

    def run(self):
        # run_in_layout_build_mode(canvas)
        data_provider = DataProvider()
        detector = Detector(data_provider)
        suggester = Suggester(data_provider)
        layouts = [
            layout.LabelLayout(),
            layout.DraftSuggestionLayout()
        ]
        thread_pool = ThreadPoolExecutor(4)

        keyboard_queue = Queue(100)
        keyboard.add_hotkey("F8", lambda *a, **k: keyboard_queue.put("F8"))
        keyboard.add_hotkey("F7", lambda *a, **k: keyboard_queue.put("F7"))

        visible = False

        logging.info("Press F8 to show/hide overlay, F7 to refresh while it's visible")

        while True:
            key_pressed = keyboard_queue.get()
            if key_pressed == "F8" and visible:
                canvas.clear_paint_commands()
                visible = False
                logging.info("Hiding overlay")
                continue

            if key_pressed == "F7" and not visible:
                logging.info("Cannot refresh when overlay not visible")
                continue

            # Supposedly something should become visible, if something fails
            # F8 will be queued up which will make it invisible.
            visible = True

            # It's either a refresh with F7 or a show with F8
            try:
                canvas_image = canvas.capture()
                if canvas_image is None:
                    logging.info("Could not capture image")
                    keyboard_queue.put("F8")
                    continue
                logging.info("Captured image, processing")
                draft_state = detector.get_draft_state(canvas_image)
                logging.info("Processed image")

                if not draft_state:
                    logging.info("Could not determine the draft")
                    keyboard_queue.put("F8")
                    continue

                pick_suggestions_future = thread_pool.submit(lambda: suggester.get_draft_suggestions(
                    draft_state.map,
                    draft_state.locked_ally_picks,
                    draft_state.enemy_picks,
                    draft_state.bans
                ))
                unlocked_pick_suggestions_future = thread_pool.submit(lambda: suggester.get_draft_suggestions(
                    draft_state.map,
                    draft_state.ally_picks,
                    draft_state.enemy_picks,
                    draft_state.bans
                ))
                ban_suggestions_future = thread_pool.submit(lambda: suggester.get_ban_suggestions(
                    draft_state.map,
                    draft_state.locked_ally_picks,
                    draft_state.enemy_picks,
                    draft_state.bans
                ))
                unlocked_ban_suggestions_future = thread_pool.submit(lambda: suggester.get_ban_suggestions(
                    draft_state.map,
                    draft_state.ally_picks,
                    draft_state.enemy_picks,
                    draft_state.bans
                ))
                logging.info("Submitted suggestion requests")
                pick_suggestions = pick_suggestions_future.result()
                unlocked_pick_suggestions = unlocked_pick_suggestions_future.result()
                ban_suggestions = ban_suggestions_future.result()
                unlocked_ban_suggestions = unlocked_ban_suggestions_future.result()
                logging.info("Suggestions retrieved")

                annotation = Annotation(draft_state, pick_suggestions, ban_suggestions, unlocked_pick_suggestions,
                                        unlocked_ban_suggestions)

                size = Point(canvas_image.shape[1], canvas_image.shape[0])
                paint_commands = []
                for current_layout in layouts:
                    paint_commands.extend(
                        current_layout.get_paint_commands(size, annotation)
                    )
                logging.info("Generated overlay")
                canvas.execute_paint_commands(paint_commands)
            except Exception as e:
                logging.exception("Failed to run: %s", e)


def run_in_layout_build_mode(canvas):
    data_provider = DataProvider()
    detector = Detector(data_provider)
    suggester = Suggester(data_provider)
    thread_pool = ThreadPoolExecutor(4)

    canvas_image = canvas.capture()
    draft_state = detector.get_draft_state(canvas_image)

    pick_suggestions_future = thread_pool.submit(lambda: suggester.get_draft_suggestions(
        draft_state.map,
        draft_state.locked_ally_picks,
        draft_state.enemy_picks,
        draft_state.bans
    ))
    unlocked_pick_suggestions_future = thread_pool.submit(lambda: suggester.get_draft_suggestions(
        draft_state.map,
        draft_state.ally_picks,
        draft_state.enemy_picks,
        draft_state.bans
    ))
    ban_suggestions_future = thread_pool.submit(lambda: suggester.get_ban_suggestions(
        draft_state.map,
        draft_state.locked_ally_picks,
        draft_state.enemy_picks,
        draft_state.bans
    ))
    unlocked_ban_suggestions_future = thread_pool.submit(lambda: suggester.get_ban_suggestions(
        draft_state.map,
        draft_state.ally_picks,
        draft_state.enemy_picks,
        draft_state.bans
    ))
    logging.info("Submitted suggestion requests")
    pick_suggestions = pick_suggestions_future.result()
    unlocked_pick_suggestions = unlocked_pick_suggestions_future.result()
    ban_suggestions = ban_suggestions_future.result()
    unlocked_ban_suggestions = unlocked_ban_suggestions_future.result()
    logging.info("Suggestions retrieved")

    annotation = Annotation(draft_state, pick_suggestions, ban_suggestions, unlocked_pick_suggestions,
                            unlocked_ban_suggestions)

    size = Point(canvas_image.shape[1], canvas_image.shape[0])

    import importlib

    while True:
        try:
            canvas.clear_paint_commands()
            importlib.reload(layout)
            layouts = [
                layout.DraftSuggestionLayout(),
                layout.LabelLayout()
            ]

            paint_commands = []
            for current_layout in layouts:
                paint_commands.extend(
                    current_layout.get_paint_commands(size, annotation)
                )
            canvas.execute_paint_commands(paint_commands)
        except Exception as e:
            logging.exception("Exception")

        keyboard.wait('F8')
        logging.info("Rerender")


if __name__ == "__main__":
    utils.monkey_patch_exception_hook()
    app = QApplication(sys.argv)
    canvas = WindowCanvas("Heroes of the Storm")

    runner = Runner(app, canvas)
    runner.start()

    sys.exit(app.exec())
