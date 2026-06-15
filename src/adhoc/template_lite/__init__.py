"""
Модуль template_lite для разбора упрощённых шаблонов сценариев обхода данных.

Этот модуль предоставляет классы для работы с «lite»-сценариями обхода данных
факторного анализа, формируемыми вспомогательной утилитой. Сценарий описывает
дерево статей показателя (подстатьи), аналитических разрезов, а также
мультипликативных компонент (тариф + база). В дальнейшем lite-сценарий может
быть развёрнут в полноценные метаданные иерархии
(:mod:`libfa2.hier_metadata`) и аналитических разрезов
(:mod:`libfa2.analyt_struct_metadata`).

Основные классы и функции:
- TemplateLite: Контейнер шаблона сценария (имя показателя + дерево узлов)
- TemplateLiteNode: Узел дерева сценария
- NodeRole: Роль узла (подстатья / разрез / тариф / база)
- get_from_template_lite_json: Десериализация JSON-сценария в TemplateLite

Пример использования:
    >>> from libfa2.adhoc.template_lite import (
    ...     get_from_template_lite_json,
    ...     NodeRole,
    ... )
    >>> tpl = get_from_template_lite_json(
    ...     "src/tmp/template_lite/чкд+_тб_business_lite.json"
    ... )
    >>> tpl.metric_name
    'ЧКД+ ТБ'
    >>> len(tpl.get_razrez())  # количество узлов-разрезов
    2
"""

from .enums import NodeRole
from .node import TemplateLiteNode
from .template import TemplateLite
from .deserializer import get_from_template_lite_json
from .transform import transform_template_lite_to_hierarchy

__all__ = [
    "NodeRole",
    "TemplateLiteNode",
    "TemplateLite",
    "get_from_template_lite_json",
    "transform_template_lite_to_hierarchy",
]

__version__ = "1.0.0"
