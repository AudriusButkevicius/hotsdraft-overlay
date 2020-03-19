from typing import List

from PyQt5.QtCore import QPoint, QRect
from PyQt5.QtGui import QColor

from hotsdraft_overlay.models import Annotation, Point, Region
from hotsdraft_overlay.painting import PaintCommand, PaintRect, PaintText


class Layout(object):
    def get_paint_commands(self, dimensions: Point, annotation: Annotation) -> List[PaintCommand]:
        raise NotImplemented()


class DraftSuggestionLayout(Layout):
    def get_paint_commands(self, dimensions: Point, annotation: Annotation) -> List[PaintCommand]:
        paint_commands = []
        paint_commands.extend(self.__get_suggested_picks_commands(dimensions, annotation))
        paint_commands.extend(self.__get_suggested_ban_commands(dimensions, annotation))
        return paint_commands

    @staticmethod
    def __get_suggested_ban_commands(dimensions: Point, annotation: Annotation) -> List[PaintCommand]:
        paint_commands = []
        h, w = dimensions.y, dimensions.x

        h_start = h / 7
        w_start = int(w - (h / 2))
        line_size = 30

        lines = 0

        paint_commands.append(
            PaintText(
                "Suggested bans", 20, 5, QPoint(w_start, h_start + ((lines - 1.5) * line_size)),
                color=QColor(255, 255, 255)
            )
        )

        for _, suggestion in enumerate(annotation.ban_suggestions[:8]):
            msg = "%s (%d)" % (suggestion.hero.name.capitalize(), suggestion.score)
            paint_commands.append(
                PaintText(
                    msg, 15, 3, QPoint(w_start, h_start + (lines * line_size)),
                    color=QColor(255, 255, 255)
                )
            )
            lines += 1
            for trait in list(filter(lambda x: x.score > 0, suggestion.traits))[:5]:
                color_offset = (150 / 5) * (5 - abs(trait.score))
                color = QColor(color_offset, 255 - color_offset, color_offset)
                msg = ("⊕" * trait.score) + " " + trait.message

                paint_commands.append(
                    PaintText(
                        msg, 12, 3, QPoint(w_start, h_start + (lines * line_size)),
                        color=color
                    )
                )
                lines += 1
            lines += 0.5

        return paint_commands

    @staticmethod
    def __get_suggested_picks_commands(dimensions: Point, annotation: Annotation) -> List[PaintCommand]:
        paint_commands = []
        h, w = dimensions.y, dimensions.x

        h_start = h / 7
        w_start = int(h / 3.4)
        line_size = 30

        lines = 0

        paint_commands.append(
            PaintText(
                "Suggested picks", 20, 5, QPoint(w_start, h_start + ((lines - 1.5) * line_size)),
                color=QColor(255, 255, 255)
            )
        )

        for suggestion in annotation.pick_suggestions[:10]:
            paint_commands.append(
                PaintText(
                    suggestion.hero.name.capitalize(), 15, 3, QPoint(w_start, h_start + (lines * line_size)),
                    color=QColor(255, 255, 255)
                )
            )
            paint_commands.append(
                PaintText(
                    "(%d)" % suggestion.score, 15, 3, QPoint(w_start, h_start + ((lines + 1) * line_size)),
                    color=QColor(255, 255, 255)
                )
            )
            lines += 1
            for trait in suggestion.traits:
                if trait.score > 0:
                    color_offset = (150 / 5) * (5 - abs(trait.score))
                    color = QColor(color_offset, 255 - color_offset, color_offset)
                    msg = ("⊕" * trait.score) + " " + trait.message
                else:
                    color_offset = (200 / 5) * (5 - abs(trait.score))
                    color = QColor(255, color_offset, color_offset)
                    msg = ("⊖" * abs(trait.score)) + " " + trait.message

                paint_commands.append(
                    PaintText(
                        msg, 12, 3, QPoint(w_start + (w_start / 3.8), h_start + ((lines - 1) * line_size)),
                        color=color
                    )
                )
                lines += 1
            lines -= 0.5

        return paint_commands


class LabelLayout(Layout):
    def get_paint_commands(self, dimensions: Point, annotation: Annotation) -> List[PaintCommand]:
        paint_commands = []
        for draft_hero in annotation.draft_state.all_heroes:
            text = draft_hero.name.capitalize()
            if draft_hero.region == Region.ALLY_PICKS and draft_hero.locked:
                text += " [x]"

            paint_commands.append(
                PaintText(
                    text, 20, 3, QPoint(draft_hero.bounding_box.top_left.x, draft_hero.bounding_box.bottom_right.y),
                    color=QColor(0, 255, 0)
                )
            )

        if annotation.draft_state.map:
            position = QPoint(20, dimensions.y - 20)
            paint_commands.append(
                PaintText(
                    annotation.draft_state.map.capitalize(), 20, 3, position,
                    color=QColor(0, 255, 0)
                )
            )

        return paint_commands


class BoundingBoxLayout(Layout):
    def get_paint_commands(self, dimensions: Point, annotation: Annotation) -> List[PaintCommand]:
        paint_commands = []
        for draft_hero in annotation.draft_state.all_heroes:
            paint_commands.append(
                PaintRect(draft_hero.bounding_box.qrect, QColor(0, 0, 255), 2)
            )

        paint_commands.append(
            PaintRect(
                QRect(0, 0, dimensions.x, dimensions.y),
                QColor(0, 0, 255), 10
            )
        )

        return paint_commands
