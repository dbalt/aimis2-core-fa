"""
Тесты модуля условий для доступа к данным.

Покрывают все классы и функции reduce_condition, get_where_clause_part.
"""

import pytest

from libfa2.data_access.conditions import (
    ConditionBase,
    ConditionSet,
    ConditionOr,
    ConditionAnd,
    reduce_condition,
    get_where_clause_part,
)


class TestConditionSet:
    """Тесты класса ConditionSet."""

    def test_init_empty(self):
        """Тест создания пустого ConditionSet."""
        cs = ConditionSet()
        assert cs.columns == []
        assert cs.to_dict() == {}

    def test_init_with_data(self):
        """Тест создания ConditionSet с данными."""
        cs = ConditionSet({"name": "foo", "part_id": 1})
        assert cs.columns == ["name", "part_id"]
        assert cs.to_dict() == {"name": "foo", "part_id": 1}

    def test_columns(self):
        """Тест свойства columns."""
        cs = ConditionSet({"name": ["foo", "bar"], "part_id": 1, "status": "active"})
        assert set(cs.columns) == {"name", "part_id", "status"}

    def test_get_filter_for_column_single_value(self):
        """Тест получения фильтра для столбца с одиночным значением."""
        cs = ConditionSet({"name": "foo", "part_id": 1})
        assert cs.get_filter_for_column("name") == "foo"
        assert cs.get_filter_for_column("part_id") == 1

    def test_get_filter_for_column_list_value(self):
        """Тест получения фильтра для столбца со списком значений."""
        cs = ConditionSet({"name": ["foo", "bar", "baz"]})
        assert cs.get_filter_for_column("name") == ["foo", "bar", "baz"]

    def test_get_filter_for_column_not_found(self):
        """Тест получения фильтра для несуществующего столбца."""
        cs = ConditionSet({"name": "foo"})
        with pytest.raises(KeyError, match="Column 'status' not found"):
            cs.get_filter_for_column("status")

    def test_set_filter_new_column(self):
        """Тест установки фильтра для нового столбца."""
        cs = ConditionSet()
        cs.set_filter("name", "foo")
        assert cs.columns == ["name"]
        assert cs.get_filter_for_column("name") == "foo"

    def test_set_filter_existing_column(self):
        """Тест установки фильтра для существующего столбца."""
        cs = ConditionSet({"name": "foo"})
        cs.set_filter("name", "bar")
        assert cs.get_filter_for_column("name") == "bar"

    def test_remove_filter(self):
        """Тест удаления фильтра."""
        cs = ConditionSet({"name": "foo", "part_id": 1})
        assert cs.remove_filter("name") is True
        assert cs.columns == ["part_id"]
        assert cs.has_column("name") is False

    def test_remove_filter_not_found(self):
        """Тест удаления несуществующего фильтра."""
        cs = ConditionSet({"name": "foo"})
        assert cs.remove_filter("status") is False

    def test_has_column(self):
        """Тест проверки наличия столбца."""
        cs = ConditionSet({"name": "foo", "part_id": 1})
        assert cs.has_column("name") is True
        assert cs.has_column("status") is False

    def test_to_dict(self):
        """Тест сериализации в словарь."""
        cs = ConditionSet({"name": "foo", "part_id": 1})
        data = cs.to_dict()
        assert data == {"name": "foo", "part_id": 1}
        # Проверяем, что возвращается копия
        data["new_col"] = "value"
        assert cs.to_dict() == {"name": "foo", "part_id": 1}

    def test_from_dict(self):
        """Тест фабричного метода from_dict."""
        data = {"name": "foo", "part_id": 1}
        cs = ConditionSet.from_dict(data)
        assert cs.to_dict() == data

    def test_copy(self):
        """Тест копирования ConditionSet."""
        cs1 = ConditionSet({"name": "foo", "part_id": 1})
        cs2 = cs1.copy()
        assert cs1.to_dict() == cs2.to_dict()
        cs2.set_filter("name", "bar")
        assert cs1.get_filter_for_column("name") == "foo"
        assert cs2.get_filter_for_column("name") == "bar"

    def test_repr(self):
        """Тест строкового представления."""
        cs = ConditionSet({"name": "foo", "part_id": 1})
        assert repr(cs) == "ConditionSet({'name': 'foo', 'part_id': 1})"

    def test_eq(self):
        """Тест сравнения на равенство."""
        cs1 = ConditionSet({"name": "foo", "part_id": 1})
        cs2 = ConditionSet({"name": "foo", "part_id": 1})
        cs3 = ConditionSet({"name": "bar"})
        assert cs1 == cs2
        assert cs1 != cs3
        assert cs1 != "not a ConditionSet"


class TestConditionOr:
    """Тесты класса ConditionOr."""

    def test_init_empty(self):
        """Тест создания пустого ConditionOr."""
        cor = ConditionOr()
        assert cor.count == 0
        assert cor.conditions == []

    def test_init_with_conditions(self):
        """Тест создания ConditionOr с условиями."""
        cs1 = ConditionSet({"name": "foo"})
        cs2 = ConditionSet({"name": "bar"})
        cor = ConditionOr([cs1, cs2])
        assert cor.count == 2

    def test_add(self):
        """Тест добавления условия."""
        cor = ConditionOr()
        cs = ConditionSet({"name": "foo"})
        cor.add(cs)
        assert cor.count == 1
        assert isinstance(cor.get(0), ConditionSet)

    def test_remove(self):
        """Тест удаления условия."""
        cs1 = ConditionSet({"name": "foo"})
        cs2 = ConditionSet({"name": "bar"})
        cor = ConditionOr([cs1, cs2])
        removed = cor.remove(0)
        assert removed == cs1
        assert cor.count == 1

    def test_get(self):
        """Тест получения условия."""
        cs1 = ConditionSet({"name": "foo"})
        cs2 = ConditionSet({"name": "bar"})
        cor = ConditionOr([cs1, cs2])
        assert cor.get(0) == cs1
        assert cor.get(1) == cs2

    def test_conditions_property(self):
        """Тест свойства conditions."""
        cs1 = ConditionSet({"name": "foo"})
        cs2 = ConditionSet({"name": "bar"})
        cor = ConditionOr([cs1, cs2])
        conditions = cor.conditions
        assert conditions == [cs1, cs2]
        # Проверяем, что возвращается копия
        conditions.append(ConditionSet({}))
        assert cor.count == 2

    def test_count(self):
        """Тест свойства count."""
        cor = ConditionOr()
        assert cor.count == 0
        cor.add(ConditionSet({}))
        cor.add(ConditionSet({}))
        assert cor.count == 2

    def test_columns(self):
        """Тест свойства columns."""
        cs1 = ConditionSet({"name": "foo", "part_id": 1})
        cs2 = ConditionSet({"name": "bar", "status": "active"})
        cor = ConditionOr([cs1, cs2])
        columns = cor.columns
        assert set(columns) == {"name", "part_id", "status"}

    def test_get_filter_for_column(self):
        """Тест получения фильтра по столбцу."""
        cs1 = ConditionSet({"name": "foo", "part_id": 1})
        cs2 = ConditionSet({"name": "bar", "status": "active"})
        cor = ConditionOr([cs1, cs2])
        assert cor.get_filter_for_column("name") == "foo"
        assert cor.get_filter_for_column("part_id") == 1

    def test_get_filter_for_column_not_found(self):
        """Тест получения фильтра для несуществующего столбца."""
        cor = ConditionOr([ConditionSet({"name": "foo"})])
        with pytest.raises(KeyError, match="Column 'status' not found"):
            cor.get_filter_for_column("status")

    def test_copy(self):
        """Тест копирования ConditionOr."""
        cs1 = ConditionSet({"name": "foo"})
        cs2 = ConditionSet({"name": "bar"})
        cor1 = ConditionOr([cs1, cs2])
        cor2 = cor1.copy()
        assert cor1.count == cor2.count
        cor2.remove(0)
        assert cor1.count == 2
        assert cor2.count == 1

    def test_repr(self):
        """Тест строкового представления."""
        cs1 = ConditionSet({"name": "foo"})
        cs2 = ConditionSet({"name": "bar"})
        cor = ConditionOr([cs1, cs2])
        assert "OR(" in repr(cor)


class TestConditionAnd:
    """Тесты класса ConditionAnd."""

    def test_init_empty(self):
        """Тест создания пустого ConditionAnd."""
        cand = ConditionAnd()
        assert cand.count == 0
        assert cand.conditions == []

    def test_init_with_conditions(self):
        """Тест создания ConditionAnd с условиями."""
        cs1 = ConditionSet({"name": "foo"})
        cs2 = ConditionSet({"part_id": 1})
        cand = ConditionAnd([cs1, cs2])
        assert cand.count == 2

    def test_add(self):
        """Тест добавления условия."""
        cand = ConditionAnd()
        cs = ConditionSet({"name": "foo"})
        cand.add(cs)
        assert cand.count == 1

    def test_columns(self):
        """Тест свойства columns."""
        cs1 = ConditionSet({"name": "foo", "part_id": 1})
        cs2 = ConditionSet({"name": "bar", "status": "active"})
        cand = ConditionAnd([cs1, cs2])
        columns = cand.columns
        assert set(columns) == {"name", "part_id", "status"}

    def test_repr(self):
        """Тест строкового представления."""
        cs1 = ConditionSet({"name": "foo"})
        cs2 = ConditionSet({"name": "bar"})
        cand = ConditionAnd([cs1, cs2])
        assert "AND(" in repr(cand)


class TestReduceCondition:
    """Тесты функции reduce_condition."""

    def test_reduce_condition_set(self):
        """Тест редукции одиночного ConditionSet (без изменений)."""
        cs = ConditionSet({"name": "foo", "part_id": 1})
        result = reduce_condition(cs)
        assert result == cs
        assert isinstance(result, ConditionSet)

    def test_reduce_condition_and_two_sets_success(self):
        """Тест успешной редукции ConditionAnd с двумя ConditionSet.

        Вход:
        ConditionAnd([
            ConditionSet({"name": ["foo", "bar", "baz"], "part_id": 1}),
            ConditionSet({"name": ["bar", "baz"], "status": "active"})
        ])

        Ожидаемый результат:
        ConditionSet({
            "name": ["bar", "baz"],
            "part_id": 1,
            "status": "active"
        })
        """
        input_condition = ConditionAnd([
            ConditionSet({"name": ["foo", "bar", "baz"], "part_id": 1}),
            ConditionSet({"name": ["bar", "baz"], "status": "active"})
        ])

        result = reduce_condition(input_condition)

        assert isinstance(result, ConditionSet)
        assert set(result.columns) == {"name", "part_id", "status"}
        assert result.get_filter_for_column("name") == ["bar", "baz"]
        assert result.get_filter_for_column("part_id") == 1
        assert result.get_filter_for_column("status") == "active"

    def test_reduce_condition_and_two_sets_error(self):
        """Тест ошибки при редукции ConditionAnd с пустым пересечением.

        Вход:
        ConditionAnd([
            ConditionSet({"name": ["foo", "bar"]}),
            ConditionSet({"name": ["baz", "qux"]})
        ])

        Ожидается: ValueError
        """
        input_condition = ConditionAnd([
            ConditionSet({"name": ["foo", "bar"]}),
            ConditionSet({"name": ["baz", "qux"]})
        ])

        with pytest.raises(ValueError, match="Conflicting conditions"):
            reduce_condition(input_condition)

    def test_reduce_condition_and_single_value(self):
        """Тест редукции ConditionAnd с одиночными значениями."""
        input_condition = ConditionAnd([
            ConditionSet({"name": ["foo", "bar", "baz"]}),
            ConditionSet({"name": "bar", "status": "active"})
        ])

        result = reduce_condition(input_condition)

        assert isinstance(result, ConditionSet)
        assert result.get_filter_for_column("name") == "bar"

    def test_reduce_condition_or_two_sets_success(self):
        """Тест успешной редукции ConditionOr с двумя ConditionSet.

        Вход:
        ConditionOr([
            ConditionSet({"name": ["foo", "bar"], "part_id": 1}),
            ConditionSet({"name": ["baz"], "part_id": 1})
        ])

        Ожидаемый результат:
        ConditionSet({
            "name": ["foo", "bar", "baz"],
            "part_id": 1
        })
        """
        input_condition = ConditionOr([
            ConditionSet({"name": ["foo", "bar"], "part_id": 1}),
            ConditionSet({"name": ["baz"], "part_id": 1})
        ])

        result = reduce_condition(input_condition)

        assert isinstance(result, ConditionSet)
        assert set(result.columns) == {"name", "part_id"}
        assert result.get_filter_for_column("name") == ["foo", "bar", "baz"]
        assert result.get_filter_for_column("part_id") == 1

    def test_reduce_condition_or_two_sets_fail(self):
        """Тест неудачной редукции ConditionOr (разные столбцы).

        Вход:
        ConditionOr([
            ConditionSet({"name": ["foo", "bar"], "part_id": 1}),
            ConditionSet({"name": ["baz"], "status": "active"})
        ])

        Ожидаемый результат: ConditionOr возвращается без изменений
        """
        input_condition = ConditionOr([
            ConditionSet({"name": ["foo", "bar"], "part_id": 1}),
            ConditionSet({"name": ["baz"], "status": "active"})
        ])

        result = reduce_condition(input_condition)

        # Редукция невозможна, возвращаем исходный контейнер
        assert isinstance(result, ConditionOr)
        assert result.count == 2

    def test_reduce_nested_and_or(self):
        """Тест редукции вложенной структуры ConditionAnd(ConditionOr(...)).

        Вход:
        ConditionAnd([
            ConditionSet({"name": "foo"}),
            ConditionOr([
                ConditionSet({"status": "active"}),
                ConditionSet({"status": "pending"})
            ])
        ])

        Ожидаемый результат:
        ConditionSet({
            "name": "foo",
            "status": ["active", "pending"]
        })
        """
        input_condition = ConditionAnd([
            ConditionSet({"name": "foo"}),
            ConditionOr([
                ConditionSet({"status": "active"}),
                ConditionSet({"status": "pending"})
            ])
        ])

        result = reduce_condition(input_condition)

        assert isinstance(result, ConditionSet)
        assert set(result.columns) == {"name", "status"}
        assert result.get_filter_for_column("name") == "foo"
        assert result.get_filter_for_column("status") == ["active", "pending"]

    def test_reduce_condition_and_three_sets(self):
        """Тест итеративной редукции ConditionAnd с тремя элементами.

        Вход:
        ConditionAnd([
            ConditionSet({"name": ["foo", "bar", "baz"]}),
            ConditionSet({"name": ["bar", "baz"]}),
            ConditionSet({"part_id": 1})
        ])

        Ожидаемый результат:
        ConditionSet({
            "name": ["bar", "baz"],
            "part_id": 1
        })
        """
        input_condition = ConditionAnd([
            ConditionSet({"name": ["foo", "bar", "baz"]}),
            ConditionSet({"name": ["bar", "baz"]}),
            ConditionSet({"part_id": 1})
        ])

        result = reduce_condition(input_condition)

        assert isinstance(result, ConditionSet)
        assert set(result.columns) == {"name", "part_id"}
        assert result.get_filter_for_column("name") == ["bar", "baz"]
        assert result.get_filter_for_column("part_id") == 1

    def test_reduce_condition_or_three_sets(self):
        """Тест итеративной редукции ConditionOr с тремя элементами.

        Вход:
        ConditionOr([
            ConditionSet({"name": ["foo"], "status": "active"}),
            ConditionSet({"name": ["bar"], "status": "active"}),
            ConditionSet({"name": ["baz"], "status": "active"})
        ])

        Ожидаемый результат:
        ConditionSet({
            "name": ["foo", "bar", "baz"],  # порядок не важен
            "status": "active"
        })
        """
        input_condition = ConditionOr([
            ConditionSet({"name": ["foo"], "status": "active"}),
            ConditionSet({"name": ["bar"], "status": "active"}),
            ConditionSet({"name": ["baz"], "status": "active"})
        ])

        result = reduce_condition(input_condition)

        assert isinstance(result, ConditionSet)
        assert set(result.columns) == {"name", "status"}
        # Используем set для проверки, так как порядок значений не важен
        assert set(result.get_filter_for_column("name")) == {"foo", "bar", "baz"}
        assert result.get_filter_for_column("status") == "active"

    def test_reduce_condition_or_partial_reduction(self):
        """Тест частичной редукции ConditionOr с остановкой.

        Вход:
        ConditionOr([
            ConditionSet({"name": ["foo"], "status": "active"}),
            ConditionSet({"name": ["bar"], "status": "active"}),
            ConditionSet({"name": ["baz"], "part_id": 1})
        ])

        Ожидаемый результат:
        ConditionOr с двумя ConditionSet, где одна содержит объединение двух первых
        """
        input_condition = ConditionOr([
            ConditionSet({"name": ["foo"], "status": "active"}),
            ConditionSet({"name": ["bar"], "status": "active"}),
            ConditionSet({"name": ["baz"], "part_id": 1})
        ])

        result = reduce_condition(input_condition)

        assert isinstance(result, ConditionOr)
        assert result.count == 2

        # Находим редуцированный ConditionSet (оба столбца: name и status)
        # и оставшийся ConditionSet (столбцы: name и part_id)
        has_reduced = False
        has_original = False

        for i in range(2):
            cond = result.get(i)
            assert isinstance(cond, ConditionSet)
            columns = set(cond.columns)

            if columns == {"name", "status"}:
                # Редуцированный ConditionSet
                assert set(cond.get_filter_for_column("name")) == {"foo", "bar"}
                assert cond.get_filter_for_column("status") == "active"
                has_reduced = True
            elif columns == {"name", "part_id"}:
                # Оставшийся ConditionSet
                assert cond.get_filter_for_column("name") == ["baz"]
                assert cond.get_filter_for_column("part_id") == 1
                has_original = True

        assert has_reduced, "Should have a reduced ConditionSet with 'name' and 'status'"
        assert has_original, "Should have an original ConditionSet with 'name' and 'part_id'"

    def test_reduce_recursive_complex(self):
        """Тест рекурсивной редукции сложной структуры.

        Вход:
        ConditionAnd([
            ConditionOr([
                ConditionSet({"name": ["foo"], "status": "active"}),
                ConditionSet({"name": ["bar"], "status": "active"})
            ]),
            ConditionOr([
                ConditionSet({"name": ["baz"], "part_id": 1}),
                ConditionSet({"name": ["qux"], "part_id": 1})
            ]),
            ConditionSet({"region": "Moscow"})
        ])

        Ожидается: ValueError (конфликт при пересечении)
        """
        input_condition = ConditionAnd([
            ConditionOr([
                ConditionSet({"name": ["foo"], "status": "active"}),
                ConditionSet({"name": ["bar"], "status": "active"})
            ]),
            ConditionOr([
                ConditionSet({"name": ["baz"], "part_id": 1}),
                ConditionSet({"name": ["qux"], "part_id": 1})
            ]),
            ConditionSet({"region": "Moscow"})
        ])

        with pytest.raises(ValueError, match="Conflicting conditions"):
            reduce_condition(input_condition)

    def test_reduce_nested_successful(self):
        """Тест успешной редукции сложной вложенной структуры."""
        input_condition = ConditionAnd([
            ConditionOr([
                ConditionSet({"name": ["foo"], "status": "active"}),
                ConditionSet({"name": ["bar"], "status": "active"})
            ]),
            ConditionOr([
                ConditionSet({"name": ["foo"], "part_id": 1}),
                ConditionSet({"name": ["bar"], "part_id": 2})
            ]),
            ConditionSet({"region": "Moscow"})
        ])

        result = reduce_condition(input_condition)

        # Первый ConditionOr: {"name": ["foo", "bar"], "status": "active"}
        # Второй ConditionOr: {"name": ["foo", "bar"], "part_id": [1, 2]}
        # ConditionAnd: пересечение по name (common), объединение остального
        # name: ["foo", "bar"] (пересечение)
        # status: "active"
        # part_id: [1, 2]
        # region: "Moscow"
        assert isinstance(result, ConditionSet)
        assert set(result.columns) == {"name", "status", "part_id", "region"}

    def test_reduce_deeply_nested(self):
        """Тест редукции глубоко вложенной структуры."""
        input_condition = ConditionAnd([
            ConditionOr([
                ConditionSet({"a": 1}),
                ConditionSet({"a": 2})
            ]),
            ConditionOr([
                ConditionSet({"b": 3}),
                ConditionSet({"b": 4})
            ]),
            ConditionSet({"c": 5})
        ])

        result = reduce_condition(input_condition)

        assert isinstance(result, ConditionSet)
        assert set(result.columns) == {"a", "b", "c"}
        assert result.get_filter_for_column("a") == [1, 2]
        assert result.get_filter_for_column("b") == [3, 4]
        assert result.get_filter_for_column("c") == 5

    def test_reduce_condition_and_single_element(self):
        """Тест ConditionAnd с одним элементом (возвращает элемент как есть)."""
        cs = ConditionSet({"name": "foo"})
        input_condition = ConditionAnd([cs])
        result = reduce_condition(input_condition)
        assert result == cs

    def test_reduce_condition_or_single_element(self):
        """Тест ConditionOr с одним элементом (возвращает элемент как есть)."""
        cs = ConditionSet({"name": "foo"})
        input_condition = ConditionOr([cs])
        result = reduce_condition(input_condition)
        assert result == cs

    def test_reduce_preserves_original(self):
        """Тест того, что reduce_condition не модифицирует исходное условие."""
        cs1 = ConditionSet({"name": "foo", "part_id": 1})
        cs2 = ConditionSet({"name": "bar", "status": "active"})
        input_condition = ConditionOr([cs1, cs2])

        original_data = input_condition.to_dict()
        result = reduce_condition(input_condition)

        # Исходное условие не изменилось
        assert input_condition.to_dict() == original_data

    def test_reduce_union_single_value_to_list(self):
        """Тест того, что объединение одиночных значений даёт список."""
        input_condition = ConditionOr([
            ConditionSet({"name": "foo", "status": "active"}),
            ConditionSet({"name": "bar", "status": "active"})
        ])

        result = reduce_condition(input_condition)

        assert isinstance(result, ConditionSet)
        assert result.get_filter_for_column("name") == ["foo", "bar"]

    def test_reduce_union_list_to_single(self):
        """Тест того, что список из одного элемента редуцируется в одиночное значение."""
        input_condition = ConditionOr([
            ConditionSet({"name": ["foo"], "status": "active"}),
            ConditionSet({"name": ["foo"], "status": "active"})
        ])

        result = reduce_condition(input_condition)

        assert isinstance(result, ConditionSet)
        assert result.get_filter_for_column("name") == "foo"

    def test_reduce_complex_tree(self):
        """Тест редукции сложного дерева условий."""
        # Structure:
        # AND(
        #   OR(A, B),
        #   OR(C, D),
        #   E
        # )
        # where A, B, C, D, E are ConditionSets

        input_condition = ConditionAnd([
            ConditionOr([
                ConditionSet({"x": 1, "y": 2}),
                ConditionSet({"x": 2, "y": 2})
            ]),
            ConditionOr([
                ConditionSet({"x": 1, "z": 3}),
                ConditionSet({"x": 2, "z": 3})
            ]),
            ConditionSet({"w": 4})
        ])

        result = reduce_condition(input_condition)

        # Должен редуцироваться в ConditionSet
        assert isinstance(result, ConditionSet)
        assert set(result.columns) == {"x", "y", "z", "w"}
        assert result.get_filter_for_column("x") == [1, 2]
        assert result.get_filter_for_column("y") == 2
        assert result.get_filter_for_column("z") == 3
        assert result.get_filter_for_column("w") == 4


class TestGetWhereClausePart:
    """Тесты функции get_where_clause_part."""

    def test_condition_set_single_values(self):
        """Тест ConditionSet с одиночными значениями."""
        cs = ConditionSet({"name": "foo", "part_id": 1, "status": "active"})
        where_sql, params = get_where_clause_part(cs)

        assert "t.name = %(name_0)s" in where_sql
        assert "t.part_id = %(part_id_0)s" in where_sql
        assert "t.status = %(status_0)s" in where_sql
        assert " and " in where_sql

        assert params == {"name_0": "foo", "part_id_0": 1, "status_0": "active"}

    def test_condition_set_list_values(self):
        """Тест ConditionSet со списком значений."""
        cs = ConditionSet({"name": ["foo", "bar", "baz"], "part_id": 1})
        where_sql, params = get_where_clause_part(cs)

        assert "t.name in %(name_0)s" in where_sql
        assert "t.part_id = %(part_id_0)s" in where_sql

        assert params["name_0"] == ("foo", "bar", "baz")
        assert params["part_id_0"] == 1

    def test_condition_set_empty(self):
        """Тест пустого ConditionSet."""
        cs = ConditionSet()
        where_sql, params = get_where_clause_part(cs)

        assert where_sql == ""
        assert params == {}

    def test_condition_or_two_sets(self):
        """Тест ConditionOr с двумя ConditionSet."""
        cor = ConditionOr([
            ConditionSet({"name": "foo", "part_id": 1}),
            ConditionSet({"name": "bar", "part_id": 2})
        ])
        where_sql, params = get_where_clause_part(cor)

        assert " or " in where_sql.lower()
        assert "(t.name = %(name_0)s and t.part_id = %(part_id_0)s)" in where_sql
        assert "(t.name = %(name_1)s and t.part_id = %(part_id_1)s)" in where_sql

        assert params == {
            "name_0": "foo",
            "part_id_0": 1,
            "name_1": "bar",
            "part_id_1": 2
        }

    def test_condition_and_two_sets(self):
        """Тест ConditionAnd с двумя ConditionSet."""
        cand = ConditionAnd([
            ConditionSet({"name": "foo"}),
            ConditionSet({"part_id": 1})
        ])
        where_sql, params = get_where_clause_part(cand)

        assert " and " in where_sql.lower()
        assert "(t.name = %(name_0)s)" in where_sql
        assert "(t.part_id = %(part_id_0)s)" in where_sql

        assert params == {"name_0": "foo", "part_id_0": 1}

    def test_condition_or_with_lists(self):
        """Тест ConditionOr со списками значений."""
        cor = ConditionOr([
            ConditionSet({"name": ["foo", "bar"], "status": "active"}),
            ConditionSet({"name": "baz", "status": "pending"})
        ])
        where_sql, params = get_where_clause_part(cor)

        assert " or " in where_sql.lower()
        assert "t.name in %(name_0)s" in where_sql
        assert "t.name = %(name_1)s" in where_sql

        assert params["name_0"] == ("foo", "bar")
        assert params["name_1"] == "baz"
        assert params["status_0"] == "active"
        assert params["status_1"] == "pending"

    def test_condition_and_with_lists(self):
        """Тест ConditionAnd со списками значений."""
        cand = ConditionAnd([
            ConditionSet({"name": ["foo", "bar"]}),
            ConditionSet({"status": ["active", "pending"]})
        ])
        where_sql, params = get_where_clause_part(cand)

        assert " and " in where_sql.lower()
        assert "t.name in %(name_0)s" in where_sql
        assert "t.status in %(status_0)s" in where_sql

        assert params["name_0"] == ("foo", "bar")
        assert params["status_0"] == ("active", "pending")

    def test_nested_condition_or_in_and(self):
        """Тест вложенной структуры ConditionAnd(ConditionOr(...))."""
        cand = ConditionAnd([
            ConditionOr([
                ConditionSet({"status": "active"}),
                ConditionSet({"status": "pending"})
            ]),
            ConditionSet({"name": "foo"})
        ])
        where_sql, params = get_where_clause_part(cand)

        assert " and " in where_sql.lower()
        assert " or " in where_sql.lower()
        # Вложенный OR с одинаковыми столбцами
        assert "((t.status = %(status_0)s) or (t.status = %(status_1)s))" in where_sql
        assert "(t.name = %(name_0)s)" in where_sql

        assert params["status_0"] == "active"
        assert params["status_1"] == "pending"
        assert params["name_0"] == "foo"

    def test_nested_condition_and_in_or(self):
        """Тест вложенной структуры ConditionOr(ConditionAnd(...))."""
        cor = ConditionOr([
            ConditionAnd([
                ConditionSet({"name": "foo"}),
                ConditionSet({"status": "active"})
            ]),
            ConditionAnd([
                ConditionSet({"name": "bar"}),
                ConditionSet({"status": "pending"})
            ])
        ])
        where_sql, params = get_where_clause_part(cor)

        assert " or " in where_sql.lower()
        assert " and " in where_sql.lower()

        assert params == {
            "name_0": "foo",
            "status_0": "active",
            "name_1": "bar",
            "status_1": "pending"
        }

    def test_deeply_nested_conditions(self):
        """Тест глубоко вложенной структуры."""
        cand = ConditionAnd([
            ConditionOr([
                ConditionSet({"x": 1}),
                ConditionSet({"x": 2})
            ]),
            ConditionOr([
                ConditionSet({"y": 3}),
                ConditionSet({"y": 4})
            ]),
            ConditionSet({"z": 5})
        ])
        where_sql, params = get_where_clause_part(cand)

        assert " and " in where_sql.lower()
        assert " or " in where_sql.lower()
        assert params == {
            "x_0": 1,
            "x_1": 2,
            "y_0": 3,
            "y_1": 4,
            "z_0": 5
        }

    def test_unique_param_names_for_same_columns(self):
        """Тест уникальности имен параметров для одинаковых столбцов."""
        cor = ConditionOr([
            ConditionSet({"name": "foo", "status": "active"}),
            ConditionSet({"name": "bar", "status": "active"}),
            ConditionSet({"name": "baz", "status": "active"})
        ])
        where_sql, params = get_where_clause_part(cor)

        # Проверяем, что параметры имеют уникальные имена
        param_names = list(params.keys())
        assert len(param_names) == len(set(param_names))

        # Проверяем, что в SQL используются правильные имена параметров
        assert "%(name_0)s" in where_sql
        assert "%(name_1)s" in where_sql
        assert "%(name_2)s" in where_sql
        assert "%(status_0)s" in where_sql
        assert "%(status_1)s" in where_sql
        assert "%(status_2)s" in where_sql

    def test_mixed_single_and_list_values(self):
        """Тест смешанных одиночных и списочных значений."""
        cs = ConditionSet({
            "name": ["foo", "bar"],
            "part_id": 1,
            "status": ["active", "pending"],
            "region": "Moscow"
        })
        where_sql, params = get_where_clause_part(cs)

        assert "t.name in %(name_0)s" in where_sql
        assert "t.part_id = %(part_id_0)s" in where_sql
        assert "t.status in %(status_0)s" in where_sql
        assert "t.region = %(region_0)s" in where_sql

        assert params["name_0"] == ("foo", "bar")
        assert params["part_id_0"] == 1
        assert params["status_0"] == ("active", "pending")
        assert params["region_0"] == "Moscow"

    def test_condition_or_empty(self):
        """Тест пустого ConditionOr."""
        cor = ConditionOr()
        where_sql, params = get_where_clause_part(cor)

        assert where_sql == ""
        assert params == {}

    def test_condition_and_empty(self):
        """Тест пустого ConditionAnd."""
        cand = ConditionAnd()
        where_sql, params = get_where_clause_part(cand)

        assert where_sql == ""
        assert params == {}
