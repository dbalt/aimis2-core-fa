"""
Тесты модуля DataAccess для агрегированных SQL-запросов.
"""

import pytest

# Импорт с обработкой отсутствия SDK
try:
    from libfa2.data_access.aggr import DataAccess
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False

from libfa2.data_access.conditions import (
    ConditionSet,
    ConditionOr,
    ConditionAnd,
)


@pytest.mark.skipif(not SDK_AVAILABLE, reason="SDK not available")
class TestBuildQuery:
    """Тесты метода _build_query."""

    def test_build_query_simple_condition_set(self):
        """Тест построения запроса с простым ConditionSet."""
        # Создаем mock для KeyDbClient
        class MockKeyDbClient:
            pass

        data_access = DataAccess(MockKeyDbClient())

        conditions = ConditionSet({
            "rep_dt": "2026-02-28",
            "kpi_name": "Чистая прибыль",
            "tb_name": ["Уральский банк", "Байкальский банк"]
        })

        sql, params = data_access._build_query(
            source="missa_bidr.t_aimis_fa__metrics_bsp",
            grp_by_columns=["gosb_name"],
            aggr_columns=["plan", "fact"],
            conditions=conditions
        )

        # Проверяем SQL структуру
        assert "select" in sql.lower()
        assert "from missa_bidr.t_aimis_fa__metrics_bsp t" in sql.lower()
        assert "group by" in sql.lower()
        assert "t.gosb_name" in sql
        assert "sum(t.plan) as plan" in sql
        assert "sum(t.fact) as fact" in sql

        # Проверяем WHERE clause
        assert "where 1=1" in sql.lower()
        assert "and" in sql.lower()
        assert "t.rep_dt = %(rep_dt)s" in sql
        assert "t.kpi_name = %(kpi_name)s" in sql
        assert "t.tb_name in %(tb_name)s" in sql

        # Проверяем параметры
        assert params["rep_dt"] == "2026-02-28"
        assert params["kpi_name"] == "Чистая прибыль"
        assert params["tb_name"] == ("Уральский банк", "Байкальский банк")

    def test_build_query_with_condition_or(self):
        """Тест построения запроса с ConditionOr."""
        class MockKeyDbClient:
            pass

        data_access = DataAccess(MockKeyDbClient())

        conditions = ConditionOr([
            ConditionSet({"name": "foo", "part_id": 1}),
            ConditionSet({"name": "bar", "part_id": 2})
        ])

        sql, params = data_access._build_query(
            source="test_table",
            grp_by_columns=["category"],
            aggr_columns=["value"],
            conditions=conditions
        )

        # Проверяем WHERE clause с OR
        assert "where 1=1" in sql.lower()
        assert " or " in sql.lower()
        assert "(t.name = %(name_0)s and t.part_id = %(part_id_0)s)" in sql
        assert "(t.name = %(name_1)s and t.part_id = %(part_id_1)s)" in sql

        # Проверяем параметры
        assert params["name_0"] == "foo"
        assert params["part_id_0"] == 1
        assert params["name_1"] == "bar"
        assert params["part_id_1"] == 2

    def test_build_query_with_condition_and(self):
        """Тест построения запроса с ConditionAnd."""
        class MockKeyDbClient:
            pass

        data_access = DataAccess(MockKeyDbClient())

        conditions = ConditionAnd([
            ConditionSet({"name": "foo"}),
            ConditionSet({"status": "active"})
        ])

        sql, params = data_access._build_query(
            source="test_table",
            grp_by_columns=["category"],
            aggr_columns=["value"],
            conditions=conditions
        )

        # Проверяем WHERE clause с AND
        assert "where 1=1" in sql.lower()
        assert " and " in sql.lower()
        assert "(t.name = %(name)s)" in sql
        assert "(t.status = %(status)s)" in sql

        # Проверяем параметры
        assert params["name"] == "foo"
        assert params["status"] == "active"

    def test_build_query_empty_condition_set(self):
        """Тест построения запроса с пустым ConditionSet."""
        class MockKeyDbClient:
            pass

        data_access = DataAccess(MockKeyDbClient())

        conditions = ConditionSet()

        sql, params = data_access._build_query(
            source="test_table",
            grp_by_columns=["category"],
            aggr_columns=["value"],
            conditions=conditions
        )

        # Проверяем отсутствие WHERE clause
        assert "where" not in sql.lower()
        assert params == {}

    def test_build_query_multiple_group_by(self):
        """Тест построения запроса с несколькими столбцами группировки."""
        class MockKeyDbClient:
            pass

        data_access = DataAccess(MockKeyDbClient())

        conditions = ConditionSet({"region": "Moscow"})

        sql, params = data_access._build_query(
            source="test_table",
            grp_by_columns=["region", "category", "product"],
            aggr_columns=["revenue", "profit"],
            conditions=conditions
        )

        # Проверяем SELECT clause
        assert "t.region" in sql
        assert "t.category" in sql
        assert "t.product" in sql
        assert "sum(t.revenue) as revenue" in sql
        assert "sum(t.profit) as profit" in sql

        # Проверяем GROUP BY clause
        group_by_section = sql[sql.index("group by"):]
        assert "t.region" in group_by_section
        assert "t.category" in group_by_section
        assert "t.product" in group_by_section

        # Проверяем WHERE clause
        assert "t.region = %(region)s" in sql
        assert params["region"] == "Moscow"

    def test_build_query_nested_conditions(self):
        """Тест построения запроса с вложенными условиями."""
        class MockKeyDbClient:
            pass

        data_access = DataAccess(MockKeyDbClient())

        conditions = ConditionAnd([
            ConditionOr([
                ConditionSet({"status": "active"}),
                ConditionSet({"status": "pending"})
            ]),
            ConditionSet({"region": "Moscow"})
        ])

        sql, params = data_access._build_query(
            source="test_table",
            grp_by_columns=["category"],
            aggr_columns=["value"],
            conditions=conditions
        )

        # Проверяем вложенные условия
        assert "where 1=1" in sql.lower()
        assert " and " in sql.lower()
        assert " or " in sql.lower()
        assert "(t.status = %(status_0)s or t.status = %(status_1)s)" in sql
        assert "(t.region = %(region)s)" in sql

        # Проверяем параметры
        assert params["status_0"] == "active"
        assert params["status_1"] == "pending"
        assert params["region"] == "Moscow"

    def test_build_query_reduced_conditions(self):
        """Тест того, что условия редуцируются перед построением запроса."""
        class MockKeyDbClient:
            pass

        data_access = DataAccess(MockKeyDbClient())

        # Создаем условие, которое может быть редуцировано
        # ConditionOr с одинаковыми столбцами редуцируется в ConditionSet
        conditions = ConditionOr([
            ConditionSet({"status": "active", "region": "Moscow"}),
            ConditionSet({"status": "pending", "region": "Moscow"})
        ])

        sql, params = data_access._build_query(
            source="test_table",
            grp_by_columns=["category"],
            aggr_columns=["value"],
            conditions=conditions
        )

        # После редукции ConditionOr с одинаковыми столбцами превращается в ConditionSet
        # с объединенными значениями для status и общим значением для region
        assert "where 1=1" in sql.lower()
        assert " and " in sql.lower()
        # Редуцированное условие не должно содержать OR
        assert " or " not in sql.lower()

        # Проверяем параметры
        # status должен быть списком ["active", "pending"]
        assert "active" in params["status"] if isinstance(params["status"], (list, tuple)) else params["status"] == "active"
        assert "pending" in params["status"] if isinstance(params["status"], (list, tuple)) else False
        assert params["region"] == "Moscow"

    def test_build_query_with_list_in_condition_set(self):
        """Тест построения запроса с IN-условием."""
        class MockKeyDbClient:
            pass

        data_access = DataAccess(MockKeyDbClient())

        conditions = ConditionSet({
            "id": [1, 2, 3, 4, 5],
            "category": ["A", "B"]
        })

        sql, params = data_access._build_query(
            source="test_table",
            grp_by_columns=["status"],
            aggr_columns=["count"],
            conditions=conditions
        )

        # Проверяем IN операторы
        assert "t.id in %(id)s" in sql
        assert "t.category in %(category)s" in sql

        # Проверяем, что значения преобразованы в кортежи
        assert isinstance(params["id"], tuple)
        assert params["id"] == (1, 2, 3, 4, 5)
        assert isinstance(params["category"], tuple)
        assert params["category"] == ("A", "B")

    def test_build_query_sql_format(self):
        """Тест форматирования SQL-запроса."""
        class MockKeyDbClient:
            pass

        data_access = DataAccess(MockKeyDbClient())

        conditions = ConditionSet({"name": "test"})

        sql, params = data_access._build_query(
            source="schema.table_name",
            grp_by_columns=["col1"],
            aggr_columns=["col2"],
            conditions=conditions
        )

        # Проверяем базовую структуру SQL
        lines = sql.strip().split("\n")

        # Первая строка - SELECT
        assert lines[0].strip().lower().startswith("select")

        # Последняя строка - GROUP BY
        assert lines[-1].strip().lower().startswith("group by")

        # Проверяем, что FROM есть
        from_line = [line for line in lines if "from" in line.lower()]
        assert len(from_line) == 1
        assert "schema.table_name t" in from_line[0]
