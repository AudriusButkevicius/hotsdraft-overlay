from dataclasses import dataclass, astuple, field
from enum import Enum
from typing import List, Optional, Any, Tuple

from PyQt5.QtCore import QPoint, QRect


class Region(Enum):
    ALLY_PICKS = 0
    ENEMY_PICKS = 1
    ALLY_BANS = 2
    ENEMY_BANS = 3


@dataclass
class Hero:
    name: str
    id: Optional[int]


@dataclass
class Point:
    x: int
    y: int

    @property
    def tuple(self) -> Tuple[int, int]:
        return astuple(self)

    @property
    def qpoint(self) -> QPoint:
        return QPoint(self.x, self.y)


@dataclass
class Rect:
    top_left: Point
    bottom_right: Point

    @property
    def ratio(self) -> float:
        return (self.bottom_right.x - self.top_left.x) / (self.bottom_right.y - self.top_left.y)

    @property
    def qrect(self):
        return QRect(self.top_left.qpoint, self.bottom_right.qpoint)

    @property
    def tuple(self) -> Tuple[int, int, int, int]:
        return self.top_left.tuple + self.bottom_right.tuple


@dataclass
class DraftHero(Hero):
    locked: bool
    bounding_box: Rect
    region: Region


@dataclass
class DraftState:
    map: str
    ally_picks: List[DraftHero] = field(default_factory=list)
    enemy_picks: List[DraftHero] = field(default_factory=list)

    ally_bans: List[DraftHero] = field(default_factory=list)
    enemy_bans: List[DraftHero] = field(default_factory=list)

    @property
    def bans(self) -> List[DraftHero]:
        return self.enemy_bans + self.ally_bans

    @property
    def locked_ally_picks(self) -> List[DraftHero]:
        return [pick for pick in self.ally_picks if pick.locked]

    @property
    def all_heroes(self) -> List[DraftHero]:
        return self.ally_picks + self.enemy_picks + self.ally_bans + self.enemy_bans


@dataclass
class Features:
    key_points: Any
    descriptors: Any


@dataclass
class Portrait:
    hero: Hero
    image: Any
    features: Features


@dataclass
class Trait:
    score: int
    message: str


@dataclass
class Suggestion:
    hero: Hero
    score: int
    traits: List[Trait]


@dataclass
class ImageCut:
    image: Any
    region: Region
    offset: Point


@dataclass
class Annotation:
    draft_state: DraftState
    pick_suggestions: List[Suggestion]
    ban_suggestions: List[Suggestion]
    unlocked_pick_suggestions: List[Suggestion]
    unlocked_ban_suggestions: List[Suggestion]
