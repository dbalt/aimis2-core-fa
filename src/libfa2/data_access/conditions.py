"""
Модуль для представления SQL-условий фильтрации (WHERE-clause).

Обеспечивает иерархическую систему классов для условий с возможностью
комбинирования (AND/OR) и оптимизации (редукции).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Union


# Тип для значений фильтра
FilterValue = Union[Any, List[Any]]


class ConditionBase(ABC):
    """Абстрактный базовый класс для всех типов условий."""

    @abstractmethod
    def to_dict(self) -> Dict[str, FilterValue]:
        """Сериализует условие в словарь."""

    @property
    @abstractmethod
    def columns(self) -> List[str]:
        """Возвращает список имён столбцов, используемых в условии."""

    @abstractmethod
    def get_filter_for_column(self, column_name: str) -> FilterValue:
        """Возвращает значение(я) фильтрации для указанного столбца."""


class ConditionSet(ConditionBase):
    """
    Типизированный контейнер для фильтрации по столбцам таблицы.

    По смыслу — Dict[str, Any|List[Any]], где:
    - ключ — имя столбца
    - значение — одно значение или список значений для фильтрации

    SQL-семантика:
    {"name": ["foo", "bar"], "part_id": 1}
    → WHERE 1=1 AND name IN ('foo', 'bar') AND part_id = 1
    """

    def __init__(self, data: Dict[str, FilterValue] | None = None):
        """
        Инициализирует ConditionSet.

        Args:
            data: Словарь условий {имя_столбца: значение/список_значений}
        """
        self._data: Dict[str, FilterValue] = data.copy() if data else {}

    @property
    def columns(self) -> List[str]:
        """Возвращает список имён столбцов в ConditionSet."""
        return list(self._data.keys())

    def get_filter_for_column(self, column_name: str) -> FilterValue:
        """
        Возвращает значение(я) фильтрации для указанного столбца.

        Args:
            column_name: Имя столбца

        Returns:
            Значение или список значений для фильтрации

        Raises:
            KeyError: Если столбец не найден в ConditionSet
        """
        if column_name not in self._data:
            raise KeyError(f"Column '{column_name}' not found in ConditionSet")
        return self._data[column_name]

    def set_filter(self, column_name: str, value: FilterValue) -> None:
        """
        Устанавливает фильтр для указанного столбца.

        Args:
            column_name: Имя столбца
            value: Значение или список значений для фильтрации
        """
        self._data[column_name] = value

    def remove_filter(self, column_name: str) -> bool:
        """
        Удаляет фильтр для указанного столбца.

        Args:
            column_name: Имя столбца

        Returns:
            True если фильтр был удалён, False если столбец не найден
        """
        if column_name in self._data:
            del self._data[column_name]
            return True
        return False

    def has_column(self, column_name: str) -> bool:
        """Проверяет наличие столбца в ConditionSet."""
        return column_name in self._data

    def to_dict(self) -> Dict[str, FilterValue]:
        """Сериализует в словарь."""
        return self._data.copy()

    @classmethod
    def from_dict(cls, data: Dict[str, FilterValue]) -> "ConditionSet":
        """
        Фабричный метод создания из словаря.

        Args:
            data: Словарь условий

        Returns:
            Экземпляр ConditionSet
        """
        return cls(data)

    def copy(self) -> "ConditionSet":
        """Возвращает копию ConditionSet."""
        return ConditionSet(self._data.copy())

    def __repr__(self) -> str:
        return f"ConditionSet({self._data})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ConditionSet):
            return False
        return self._data == other._data


class _ConditionContainer(ConditionBase):
    """
    Базовый класс для контейнеров условий (ConditionOr/ConditionAnd).

    Хранит список условий типа ConditionBase.
    """

    def __init__(self, conditions: List[ConditionBase] | None = None):
        """
        Инициализирует контейнер условий.

        Args:
            conditions: Список условий ConditionBase
        """
        self._conditions: List[ConditionBase] = conditions.copy() if conditions else []

    def add(self, condition: ConditionBase) -> None:
        """
        Добавляет условие в контейнер.

        Args:
            condition: Условие для добавления
        """
        self._conditions.append(condition)

    def remove(self, index: int) -> ConditionBase:
        """
        Удаляет условие по индексу.

        Args:
            index: Индекс условия

        Returns:
            Удалённое условие

        Raises:
            IndexError: Если индекс вне диапазона
        """
        return self._conditions.pop(index)

    def get(self, index: int) -> ConditionBase:
        """
        Возвращает условие по индексу.

        Args:
            index: Индекс условия

        Returns:
            Условие ConditionBase

        Raises:
            IndexError: Если индекс вне диапазона
        """
        return self._conditions[index]

    @property
    def conditions(self) -> List[ConditionBase]:
        """Возвращает список условий."""
        return self._conditions.copy()

    @property
    def count(self) -> int:
        """Возвращает количество условий."""
        return len(self._conditions)

    def to_dict(self) -> Dict[str, FilterValue]:
        """
        Сериализует в словарь.

        Для контейнеров это сложная операция, требующая объединения всех условий.
        Базовая реализация возвращает пустой словарь.
        """
        return {}

    @property
    def columns(self) -> List[str]:
        """
        Возвращает список всех уникальных столбцов из всех вложенных условий.
        """
        result: List[str] = []
        seen: set[str] = set()
        for condition in self._conditions:
            for col in condition.columns:
                if col not in seen:
                    seen.add(col)
                    result.append(col)
        return result

    def get_filter_for_column(self, column_name: str) -> FilterValue:
        """
        Возвращает значение(я) фильтрации для указанного столбца.

        Для контейнеров это возвращает значение из первого условия,
        содержащего этот столбец.

        Raises:
            KeyError: Если столбец не найден ни в одном условии
        """
        for condition in self._conditions:
            try:
                return condition.get_filter_for_column(column_name)
            except KeyError:
                continue
        raise KeyError(f"Column '{column_name}' not found in any condition")

    def copy(self) -> "_ConditionContainer":
        """Возвращает копию контейнера."""
        # Создаём экземпляр подкласса
        instance = self.__class__()
        instance._conditions = [c.copy() for c in self._conditions]
        return instance

    def __repr__(self) -> str:
        op = "OR" if isinstance(self, ConditionOr) else "AND"
        return f"{op}({self._conditions})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _ConditionContainer):
            return False
        return self._conditions == other._conditions


class ConditionOr(_ConditionContainer):
    """
    Контейнер для условий, объединённых оператором OR (логическое ИЛИ).

    SQL-семантика:
    ConditionOr([ConditionSet({"name": "foo"}), ConditionSet({"name": "bar"})])
    → WHERE 1=1 AND (name = 'foo' OR name = 'bar')
    """


class ConditionAnd(_ConditionContainer):
    """
    Контейнер для условий, объединённых оператором AND (логическое И).

    SQL-семантика:
    ConditionAnd([ConditionSet({"name": "foo"}), ConditionSet({"part_id": 1})])
    → WHERE 1=1 AND (name = 'foo' AND part_id = 1)
    """


def _normalize_value(value: FilterValue) -> List[Any]:
    """
    Нормализует значение фильтра к списку.

    Args:
        value: Значение или список значений

    Returns:
        Список значений
    """
    if isinstance(value, list):
        return value.copy()
    return [value]


def _denormalize_value(values: List[Any]) -> FilterValue:
    """
    Денормализует список значений в оптимальное представление.

    Если список состоит из одного элемента, возвращает этот элемент.
    Иначе возвращает список.

    Args:
        values: Список значений

    Returns:
        Значение или список значений
    """
    if len(values) == 1:
        return values[0]
    return values


def _intersect_values(
    value1: FilterValue, value2: FilterValue, column_name: str
) -> FilterValue:
    """
    Вычисляет пересечение значений двух фильтров.

    Args:
        value1: Первое значение или список значений
        value2: Второе значение или список значений
        column_name: Имя столбца (для сообщения об ошибке)

    Returns:
        Пересечение значений

    Raises:
        ValueError: Если пересечение пусто
    """
    list1 = _normalize_value(value1)
    list2 = _normalize_value(value2)
    intersection = [v for v in list1 if v in list2]

    if not intersection:
        raise ValueError(
            f"Conflicting conditions for column '{column_name}': "
            f"no common values in {list1} and {list2}"
        )

    return _denormalize_value(intersection)


def _union_values(value1: FilterValue, value2: FilterValue) -> FilterValue:
    """
    Вычисляет объединение значений двух фильтров.

    Args:
        value1: Первое значение или список значений
        value2: Второе значение или список значений

    Returns:
        Объединение значений (уникальные)
    """
    list1 = _normalize_value(value1)
    list2 = _normalize_value(value2)

    # Объединяем с сохранением уникальности
    seen: set[Any] = set()
    result: List[Any] = []

    for v in list1 + list2:
        if v not in seen:
            seen.add(v)
            result.append(v)

    return _denormalize_value(result)


def _has_same_columns(set1: ConditionSet, set2: ConditionSet) -> bool:
    """
    Проверяет, имеют ли два ConditionSet одинаковый набор столбцов.

    Args:
        set1: Первый ConditionSet
        set2: Второй ConditionSet

    Returns:
        True если наборы столбцов совпадают, иначе False
    """
    return set(set1.columns) == set(set2.columns)


def _reduce_condition_and_condition_set(
    and_condition: ConditionAnd,
) -> ConditionBase:
    """
    Пытается редуцировать ConditionAnd в ConditionSet.

    Правило: ConditionAnd(ConditionSet1, ConditionSet2) → ConditionSet
    При пересечении имён столбцов — берётся пересечение значений.

    Args:
        and_condition: ConditionAnd для редукции

    Returns:
        Редуцированное условие

    Raises:
        ValueError: Если есть противоречивые условия (пустое пересечение)
    """
    conditions = and_condition.conditions

    if len(conditions) != 2:
        return and_condition

    cond1, cond2 = conditions

    if not (isinstance(cond1, ConditionSet) and isinstance(cond2, ConditionSet)):
        return and_condition

    # Объединяем оба ConditionSet
    result_data: Dict[str, FilterValue] = {}

    # Копируем все столбцы из первого ConditionSet
    for col in cond1.columns:
        result_data[col] = cond1.get_filter_for_column(col)

    # Добавляем столбцы из второго ConditionSet
    for col in cond2.columns:
        value2 = cond2.get_filter_for_column(col)
        if col in result_data:
            # Пересечение значений
            result_data[col] = _intersect_values(result_data[col], value2, col)
        else:
            result_data[col] = value2

    return ConditionSet(result_data)


def _reduce_condition_or_condition_set(
    or_condition: ConditionOr,
) -> ConditionBase:
    """
    Пытается редуцировать ConditionOr в ConditionSet.

    Правило: ConditionOr(ConditionSet1, ConditionSet2) → ConditionSet
    Условие: оба ConditionSet имеют одинаковый набор столбцов.
    Для каждого столбца берётся объединение значений.

    Args:
        or_condition: ConditionOr для редукции

    Returns:
        Редуцированное условие или исходный, если редукция невозможна
    """
    conditions = or_condition.conditions

    if len(conditions) != 2:
        return or_condition

    cond1, cond2 = conditions

    if not (isinstance(cond1, ConditionSet) and isinstance(cond2, ConditionSet)):
        return or_condition

    # Проверяем совпадение наборов столбцов
    if not _has_same_columns(cond1, cond2):
        return or_condition

    # Объединяем значения
    result_data: Dict[str, FilterValue] = {}

    for col in cond1.columns:
        value1 = cond1.get_filter_for_column(col)
        value2 = cond2.get_filter_for_column(col)
        result_data[col] = _union_values(value1, value2)

    return ConditionSet(result_data)


def _iterative_reduce(container: _ConditionContainer) -> ConditionBase:
    """
    Итеративно редуцирует ConditionOr или ConditionAnd.

    Пытается редуцировать каждую пару условий. После успешной редукции
    начинает процесс сначала. Останавливается, когда попытались каждую
    пару и редукций не было.

    Args:
        container: ConditionOr или ConditionAnd для редукции

    Returns:
        Редуцированное условие
    """
    while True:
        conditions = container.conditions
        n = len(conditions)

        if n < 2:
            break

        reduced = False
        for i in range(n):
            for j in range(i + 1, n):
                # Создаём временный контейнер из пары
                if isinstance(container, ConditionOr):
                    temp = ConditionOr([conditions[i], conditions[j]])
                    reduced_pair = _reduce_condition_or_condition_set(temp)
                else:  # ConditionAnd
                    temp = ConditionAnd([conditions[i], conditions[j]])
                    reduced_pair = _reduce_condition_and_condition_set(temp)

                # Если редуцировалось в ConditionSet, заменяем пару
                if isinstance(reduced_pair, ConditionSet):
                    # Создаём новый список без i и j, добавляем результат
                    new_conditions: List[ConditionBase] = []
                    for k in range(n):
                        if k != i and k != j:
                            new_conditions.append(conditions[k])
                    new_conditions.append(reduced_pair)

                    # Обновляем контейнер
                    if isinstance(container, ConditionOr):
                        container._conditions = new_conditions
                    else:
                        container._conditions = new_conditions

                    reduced = True
                    break  # Выходим из внутреннего цикла

            if reduced:
                break  # Выходим из внешнего цикла и начинаем заново

        if not reduced:
            break  # Редукций не было, завершаем

    # Если остался один элемент ConditionSet, возвращаем его
    if container.count == 1 and isinstance(container.get(0), ConditionSet):
        return container.get(0)

    return container


def _reduce_recursively(condition: ConditionBase) -> ConditionBase:
    """
    Рекурсивно редуцирует условие снизу вверх.

    Сначала редуцирует вложенные контейнеры, затем внешние.

    Args:
        condition: Условие для редукции

    Returns:
        Редуцированное условие
    """
    # Если это контейнер, сначала редуцируем все вложенные условия
    if isinstance(condition, _ConditionContainer):
        # Рекурсивно редуцируем каждое вложенное условие
        new_conditions: List[ConditionBase] = []
        for i in range(condition.count):
            reduced_child = _reduce_recursively(condition.get(i))
            new_conditions.append(reduced_child)

        # Создаём новый контейнер с редуцированными детьми
        if isinstance(condition, ConditionOr):
            container = ConditionOr(new_conditions)
        else:
            container = ConditionAnd(new_conditions)

        # Пытаемся итеративно редуцировать этот контейнер
        return _iterative_reduce(container)

    # ConditionSet не редуцируется
    return condition


def reduce_condition(condition: ConditionBase) -> ConditionBase:
    """
    Оптимизирует (редуцирует) структуру условий.

    Возвращает условие в максимально упрощённой форме.
    Редукция происходит рекурсивно снизу вверх.

    Args:
        condition: Исходное условие

    Returns:
        Редуцированное условие

    Raises:
        ValueError: При конфликте условий в ConditionAnd
    """
    return _reduce_recursively(condition)


def get_where_clause_part(condition: ConditionBase) -> tuple[str, Dict[str, Any]]:
    """
    Формирует часть условия WHERE на основе переданного ConditionBase.

    Генерирует SQL-подвыражение для WHERE-клаузы и словарь параметров.
    Для списков используется оператор IN, для одиночных значений - =.

    Args:
        condition: Условие для генерации WHERE-клаузы

    Returns:
        Кортеж из (where_clause_sql, params_dict)

    Examples:
        >>> cs = ConditionSet({"name": ["foo", "bar"], "part_id": 1})
        >>> sql, params = get_where_clause_part(cs)
        >>> sql
        "t.name in %(name)s and t.part_id = %(part_id)s"
        >>> params
        {"name": ("foo", "bar"), "part_id": 1}

        >>> cor = ConditionOr([
        ...     ConditionSet({"name": "foo", "part_id": 1}),
        ...     ConditionSet({"name": "bar", "part_id": 2})
        ... ])
        >>> sql, params = get_where_clause_part(cor)
        >>> sql
        "(t.name = %(name_0)s and t.part_id = %(part_id_0)s or t.name = %(name_1)s and t.part_id = %(part_id_1)s)"
    """
    return _get_where_clause_part_recursive(condition, {})


def _get_where_clause_part_recursive(
    condition: ConditionBase,
    counter: Dict[str, int]
) -> tuple[str, Dict[str, Any]]:
    """
    Рекурсивно генерирует WHERE-клаузу с учетом уникальности имен параметров.

    Args:
        condition: Условие для генерации
        counter: Счетчик для уникальных имен параметров

    Returns:
        Кортеж из (where_clause_sql, params_dict)
    """
    if isinstance(condition, ConditionSet):
        return _condition_set_to_where(condition, counter)
    elif isinstance(condition, ConditionOr):
        return _condition_container_to_where(condition, "or", counter)
    elif isinstance(condition, ConditionAnd):
        return _condition_container_to_where(condition, "and", counter)
    else:
        raise ValueError(f"Unknown condition type: {type(condition)}")


def _condition_set_to_where(
    condition_set: ConditionSet,
    counter: Dict[str, int]
) -> tuple[str, Dict[str, Any]]:
    """
    Преобразует ConditionSet в WHERE-клаузу.

    Args:
        condition_set: ConditionSet для преобразования
        counter: Счетчик для уникальных имен параметров

    Returns:
        Кортеж из (where_clause_sql, params_dict)
    """
    parts = []
    params: Dict[str, Any] = {}

    for column in condition_set.columns:
        value = condition_set.get_filter_for_column(column)
        param_name = _get_unique_param_name(column, counter)

        if isinstance(value, list):
            # Используем IN для списков
            parts.append(f"t.{column} in %({param_name})s")
            params[param_name] = tuple(value)
        else:
            # Используем = для одиночных значений
            parts.append(f"t.{column} = %({param_name})s")
            params[param_name] = value

    return " and ".join(parts), params


def _condition_container_to_where(
    container: _ConditionContainer,
    operator: str,
    counter: Dict[str, int]
) -> tuple[str, Dict[str, Any]]:
    """
    Преобразует ConditionOr или ConditionAnd в WHERE-клаузу.

    Args:
        container: ConditionOr или ConditionAnd
        operator: "or" или "and"
        counter: Счетчик для уникальных имен параметров

    Returns:
        Кортеж из (where_clause_sql, params_dict)
    """
    parts = []
    params: Dict[str, Any] = {}

    for i in range(container.count):
        sub_condition = container.get(i)
        sub_sql, sub_params = _get_where_clause_part_recursive(sub_condition, counter)
        if sub_sql:
            parts.append(f"({sub_sql})")
            params.update(sub_params)

    if not parts:
        return "", {}

    return f" {operator} ".join(parts), params


def _get_unique_param_name(base_name: str, counter: Dict[str, int]) -> str:
    """
    Генерирует уникальное имя параметра на основе базового имени.

    Всегда добавляет суффикс с номером, начиная с 0, для каждого использования имени.
    Это гарантирует уникальность всех параметров в запросе.

    Args:
        base_name: Базовое имя параметра
        counter: Счетчик использования имен

    Returns:
        Уникальное имя параметра с суффиксом

    Examples:
        >>> counter = {}
        >>> _get_unique_param_name("name", counter)
        'name_0'
        >>> _get_unique_param_name("name", counter)
        'name_1'
        >>> _get_unique_param_name("status", counter)
        'status_0'
    """
    if base_name not in counter:
        counter[base_name] = 0
    else:
        counter[base_name] += 1

    return f"{base_name}_{counter[base_name]}"
