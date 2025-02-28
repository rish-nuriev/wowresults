import random
from tournaments.models import Match


WIN_WORDS = (
    "победил",
    "одолел",
    "переиграл",
    "справился c",
    "разобрался с",
    "сломил сопротивление",
    "превзошел",
    "сразил",
    "осилил",
    "поборол",
    "обыграл",
)

LOSE_WORDS = (
    "проиграл",
    "уступил",
    "потерпел поражение от",
)

SUPER_WIN_WORDS = (
    "разгромил",
    "разнес",
    "уничтожил",
    "с легкостью разобрался с",
    "разбил",
    "разорвал",
    "смял оборону",
    "сокрушил",
    "раскатал",
)

SUPER_LOSE_WORDS = (
    "был разгромлен",
    "был уничтожен",
    "был унижен",
)

DRAW_WORDS = (
    "сыграли вничью",
    "не выявили победителя",
    "разошлись миром",
)


def gen_match_text(team1, team2, result, goals1, goals2):
    if result == Match.ResultVals.WIN:
        if goals1 - goals2 > 2:
            text = f"ФК {team1} {SUPER_WIN_WORDS[random.randint(0, len(SUPER_WIN_WORDS)-1)]} ФК {team2}. "
        else:
            text = (
                f"ФК {team1} {WIN_WORDS[random.randint(0, len(WIN_WORDS)-1)]} ФК {team2}. "
            )
    elif result == Match.ResultVals.LOSE:
        if goals2 - goals1 > 2:
            text = f"ФК {team1} {SUPER_LOSE_WORDS[random.randint(0, len(SUPER_LOSE_WORDS)-1)]} ФК {team2}. "
        else:
            text = f"ФК {team1} {LOSE_WORDS[random.randint(0, len(LOSE_WORDS)-1)]} ФК {team2}. "
    else:
        text = (
            f"ФК {team1} и ФК {team2} {DRAW_WORDS[random.randint(0, len(DRAW_WORDS)-1)]}. "
        )
    return text


def translit_to_eng(s: str) -> str:
    d = {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "yo",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "h",
        "ц": "c",
        "ч": "ch",
        "ш": "sh",
        "щ": "shch",
        "ь": "",
        "ы": "y",
        "ъ": "",
        "э": "r",
        "ю": "yu",
        "я": "ya",
    }

    return "".join(map(lambda x: d[x] if d.get(x, False) else x, s.lower()))