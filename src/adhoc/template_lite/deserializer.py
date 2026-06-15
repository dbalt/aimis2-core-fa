"""
Функции десериализации упрощённого шаблона сценария (template lite) из JSON.

Основная точка входа — :func:`get_from_template_lite_json`, читающая JSON-файл
сценария обхода данных и возвращающая объект :class:`TemplateLite`.
"""

import json
from pathlib import Path
from typing import Union

from .template import TemplateLite

#: Тип источника данных: путь к файлу, JSON-строка или уже разобранный dict.
TemplateLiteSource = Union[str, "Path", dict]


def get_from_template_lite_json(source: TemplateLiteSource) -> TemplateLite:
    """
    Десериализовать упрощённый шаблон сценария обхода данных из JSON.

    Функция является основной точкой входа для разбора «lite»-сценариев,
    сформированных утилитой по составлению сценария обхода данных для
    факторного анализа.

    Источник ``source`` может быть задан одним из трёх способов:

    1. **Путь к файлу** (``str`` или :class:`pathlib.Path`), указывающий на
       JSON-файл сценария — основной вариант использования
       («из этого json файла»)::

           from libfa2.adhoc.template_lite import get_from_template_lite_json
           tpl = get_from_template_lite_json("src/tmp/template_lite/чкд+_тб_business_lite.json")

    2. **JSON-строка** с содержимым сценария. JSON-контент (строка, которая
       после отсечения пробелов начинается с ``{`` или ``[``) разбирается
       напрямую, без обращения к файловой системе::

           tpl = get_from_template_lite_json('{"metricName": "X", "nodes": [...]}')

    3. **Уже разобранный ``dict``** — удобен, когда JSON уже прочитан
       вызывающим кодом::

           tpl = get_from_template_lite_json({"metricName": "X", "nodes": [...]})

    Различение «путь к файлу» и «JSON-контент» для строкового источника
    выполняется по первому непробельному символу: ``{``/``[`` — JSON,
    иначе — путь. Это надёжнее проверки существования файла: длинная
    JSON-строка вызовет ``OSError`` при вызове ``Path(...).is_file()``.

    Args:
        source: Путь к JSON-файлу, JSON-строка либо dict со сценарием.

    Returns:
        Объект :class:`TemplateLite`, заполненный узлами сценария.

    Raises:
        TypeError: если ``source`` имеет неподдерживаемый тип.
        FileNotFoundError: если передан путь к несуществующему файлу.
        json.JSONDecodeError: если JSON-контент не удалось разобрать.
        ValueError: при ошибке структуры данных сценария.

    Example:
        >>> tpl = get_from_template_lite_json("src/tmp/template_lite/чкд+_тб_business_lite.json")
        >>> tpl.metric_name
        'ЧКД+ ТБ'
        >>> tpl.count_nodes()
        33
    """
    # Уже разобранный словарь — используем напрямую.
    if isinstance(source, dict):
        return TemplateLite.from_dict(source)

    # Путь к файлу или JSON-строка.
    if isinstance(source, (str, Path)):
        text = source if isinstance(source, str) else str(source)

        # JSON-контент всегда начинается с '{' или '['. Файловые пути реально
        # не начинаются с этих символов, поэтому это надёжный способ отличить
        # содержимое JSON от пути без обращения к файловой системе (вызов
        # is_file() на длинной JSON-строке выбрасывает OSError).
        if text.lstrip().startswith(("{", "[")):
            data = json.loads(text)
        else:
            path = Path(text)
            with path.open(encoding="utf-8") as fh:
                data = json.load(fh)

        return TemplateLite.from_dict(data)

    raise TypeError(
        f"source должен быть str, pathlib.Path или dict, "
        f"получен {type(source).__name__}"
    )
