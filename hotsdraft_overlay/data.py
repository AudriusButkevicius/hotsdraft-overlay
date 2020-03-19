import json
import tempfile
from typing import List, Optional

import cv2

from hotsdraft_overlay import utils
from hotsdraft_overlay.models import Portrait, Hero


class DataProvider(object):
    __known_missing_heroes = ['deathwing']

    def __init__(self):
        self.__portraits = []
        self.__map_to_id = {}
        self.__hero_name_to_hero = {}
        self.__id_to_hero = {}
        self.__word_file = None
        self.__populate_id_data()
        self.__populate_portraits()
        self.__populate_word_file()
        self.__validate()

    def get_hero_by_id(self, hero_id) -> Optional[Hero]:
        return self.__id_to_hero.get(hero_id)

    def get_hero_by_name(self, name) -> Optional[Hero]:
        return self.__hero_name_to_hero.get(name)

    def get_portraits(self) -> List[Portrait]:
        return self.__portraits

    def get_word_file(self) -> str:
        return self.__word_file

    def get_map_names(self) -> List[str]:
        return list(self.__map_to_id.keys())

    def get_map_id(self, map_name) -> Optional[int]:
        return self.__map_to_id.get(map_name)

    def __populate_portraits(self):
        portraits_directory = utils.get_root() / "portraits"
        for path_item in portraits_directory.iterdir():
            path = path_item.absolute().as_posix()

            # Load portrait
            image = cv2.imread(path)

            features = utils.extract_features(image)

            hero_name = path_item.stem.replace('.png', '').lower()

            hero = self.get_hero_by_name(hero_name)
            if not hero:
                hero = Hero(hero_name, None)

            portrait = Portrait(hero, image, features)

            self.__portraits.append(portrait)

    def __populate_word_file(self):
        words = set()
        for map_name in self.__map_to_id:
            words.update(map_name.split())

        name = tempfile.mktemp()
        with open(name, "w") as fd:
            fd.writelines(words)
        self.__word_file = name

    def __populate_id_data(self):
        # Copy dropdown options html from hotsdraft.com, run:
        # cat ids | sed 's/.*value="\([[:digit:]]*\)".*>\(.*\)<.*/"\L\2": \1,/g'
        #
        # For heroes add:  sed "s/'//g;s/-//g;s/\.//g"

        data_file = utils.get_root() / "data.json"
        with data_file.open() as fd:
            data = json.load(fd)
            self.__map_to_id = data['maps']
            for hero_name, hero_id in data['heroes'].items():
                hero = Hero(hero_name, hero_id)
                self.__hero_name_to_hero[hero_name] = hero
                self.__id_to_hero[hero_id] = hero

    def __validate(self):
        portrait_names = set(portrait.hero.name for portrait in self.__portraits)
        data_names = set(self.__hero_name_to_hero)

        for name in portrait_names - data_names:
            if name not in self.__known_missing_heroes:
                raise RuntimeError("Missing id for: " + name)

        for name in data_names - portrait_names:
            if name not in self.__known_missing_heroes:
                raise RuntimeError("Missing id for: " + name)
