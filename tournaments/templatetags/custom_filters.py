from django import template
from django.template.defaultfilters import stringfilter

from transliterate import translit, base


class CustomLanguagePack(base.TranslitLanguagePack):
    language_code = "cstm"
    language_name = "CustomRU"
    mapping = (
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZóšćéíčãě",
        "абкдефгхижклмнопкрстуввчизАБКДЕФГХИЖКЛМНОПКРСТУВВЧИЗошчэичае",
    )
    pre_processor_mapping = {
        "ch": "ч",
        "CH": "Ч",
        "Ch": "Ч",
        "sh": "ш",
        "SH": "Ш",
        "sc": "с",
        "SC": "С",
        "kh": "х",
        "KH": "Х",
        "Kh": "Х",
        "yu": "ю",
        "YU": "Ю",
        "ts": "ц",
        "TS": "Ц",
        "Ts": "Ц",
        "ya": "я",
        "YA": "Я",
        "Ya": "Я",
        "ye": "е",
        "YE": "Е",
        "Ye": "Е",
        "je": "ье",
        "ji": "ьи",
        "zh": "ж",
        "ZH": "Ж",
        "Zh": "Ж",
    }


base.registry.register(CustomLanguagePack)

register = template.Library()


@register.filter
@stringfilter
def get_cnt(value, arg=""):
    return value.count(arg)


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def translite_player(name):
    if name.endswith("yi"):
        name = name[:-2] + "ый"
    if name.endswith("iy"):
        name = name[:-2] + "ий"
    if name.endswith("y"):
        name = name[:-1] + "ый"
    elif name.endswith("ic"):
        name = name[:-2] + "ич"
    elif name.startswith("He"):
        name = "Э" + name[2:]
    elif name.startswith("Y."):
        name = "И." + name[2:]
    elif name == "G. Bijl":
        name = "Бэйл"
    elif name == "L. Đorđević":
        name = "Джорджевич"

    return translit(name, "cstm")


@register.filter
def apply_events_rules(points, event):
    if event['operation'] == 'R':
        points -= event['value']
    elif event['operation'] == 'A':
        points += event['value']
    return points
