from typing import List

import requests

from hotsdraft_overlay.data import DataProvider
from hotsdraft_overlay.models import Suggestion, Hero, Trait


class Suggester(object):
    def __init__(self, data_provider: DataProvider):
        self.__data_provider = data_provider

    def get_draft_suggestions(self, map_name: str, allies: List[Hero], enemies: List[Hero], bans: List[Hero]) -> \
            List[Suggestion]:

        map_id = self.__data_provider.get_map_id(map_name) or 0

        payload = {
            "map": map_id,
            "banned[]": [hero.id for hero in bans],
            "allies[]": [hero.id for hero in allies],
            "enemies[]": [hero.id for hero in enemies],
            "league": 0
        }

        return self.__get_suggestions_for_payload(payload)

    def get_ban_suggestions(self, map_name: str, allies: List[Hero], enemies: List[Hero], bans: List[Hero]) -> \
            List[Suggestion]:

        map_id = self.__data_provider.get_map_id(map_name)

        payload = {
            "map": map_id,
            "banned[]": [hero.id for hero in bans],
            # Inverse for bans
            "allies[]": [hero.id for hero in enemies],
            "enemies[]": [hero.id for hero in allies],
            "league": 0,
            "banlist": 1
        }

        return self.__get_suggestions_for_payload(payload)

    def __get_suggestions_for_payload(self, payload) -> List[Suggestion]:
        response = requests.post("https://hotsdraft.com/draft/list/", data=payload)
        suggestions = []
        for result in response.json()['scores']:
            suggestions.append(self.__process_result(result))
        suggestions.sort(key=lambda x: x.score, reverse=True)
        return suggestions

    def __process_result(self, result) -> Suggestion:
        hero_id = result['id']
        hero = self.__data_provider.get_hero_by_id(hero_id)

        traits = []
        if 'messages' in result:
            messages = result['messages']
            messages = messages.replace("""<i class="fas fa-plus-circle"></i>""", "+")
            messages = messages.replace("""<i class="fas fa-minus-circle"></i>""", "-")
            messages = messages.replace("""<br/>""", "\n")
            messages = messages.replace("""<span class="bonus">""", "")
            messages = messages.replace("""<span class="malus">""", "")
            messages = messages.replace("""<span class="hero">""", "")
            messages = messages.replace("""</span>""", "")

            for message in messages.split('\n'):
                score, message = message.split(" ", 1)
                score = score.count('+') - score.count("-")
                message = message.strip().replace("  ", " ")
                message = message[0].upper() + message[1:]
                traits.append(Trait(score, message))

            traits.sort(key=lambda x: abs(x.score), reverse=True)

        return Suggestion(hero, result['score'], traits)
