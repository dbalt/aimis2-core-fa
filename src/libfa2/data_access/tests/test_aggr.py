"""
Тесты модуля DataAccess для агрегированных SQL-запросов.
"""

import pytest

# Импорт с обработкой отсутствия SDK
try:
    from libfa2.data_access.aggr import DataAccessDataGate
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
        class MockKeyDbClient:
            pass

        data_access = DataAccessDataGate(MockKeyDbClient())

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
        assert "t.rep_dt = %(rep_dt_0)s" in sql
        assert "t.kpi_name = %(kpi_name_0)s" in sql
        assert "t.tb_name in %(tb_name_0)s" in sql

        # Проверяем параметры
        assert params["rep_dt_0"] == "2026-02-28"
        assert params["kpi_name_0"] == "Чистая прибыль"
        assert params["tb_name_0"] == ("Уральский банк", "Байкальский банк")

    def test_build_query_with_condition_or(self):
        """Тест построения запроса с ConditionOr (разные столбцы — не редуцируется)."""
        class MockKeyDbClient:
            pass

        data_access = DataAccessDataGate(MockKeyDbClient())

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

        # ConditionOr с одинаковыми столбцами редуцируется в ConditionSet
        assert "where 1=1" in sql.lower()
        assert "t.name in %(name_0)s" in sql
        assert "t.part_id in %(part_id_0)s" in sql

        # Проверяем параметры
        assert params["name_0"] == ("foo", "bar")
        assert params["part_id_0"] == (1, 2)

    def test_build_query_with_condition_and(self):
        """Тест построения запроса с ConditionAnd."""
        class MockKeyDbClient:
            pass

        data_access = DataAccessDataGate(MockKeyDbClient())

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
        assert "t.name = %(name_0)s" in sql
        assert "t.status = %(status_0)s" in sql

        # Проверяем параметры
        assert params["name_0"] == "foo"
        assert params["status_0"] == "active"

    def test_build_query_empty_condition_set(self):
        """Тест построения запроса с пустым ConditionSet."""
        class MockKeyDbClient:
            pass

        data_access = DataAccessDataGate(MockKeyDbClient())

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

        data_access = DataAccessDataGate(MockKeyDbClient())

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
        assert "t.region = %(region_0)s" in sql
        assert params["region_0"] == "Moscow"

    def test_build_query_nested_conditions(self):
        """Тест построения запроса с вложенными условиями."""
        class MockKeyDbClient:
            pass

        data_access = DataAccessDataGate(MockKeyDbClient())

        # ConditionOr с одинаковым столбцом status редуцируется в IN
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

        # Проверяем вложенные условия (ConditionOr редуцируется в IN)
        assert "where 1=1" in sql.lower()
        assert "t.status in %(status_0)s" in sql
        assert "t.region = %(region_0)s" in sql

        # Проверяем параметры
        assert "active" in params["status_0"]
        assert "pending" in params["status_0"]
        assert params["region_0"] == "Moscow"

    def test_build_query_reduced_conditions(self):
        """Тест того, что условия редуцируются перед построением запроса."""
        class MockKeyDbClient:
            pass

        data_access = DataAccessDataGate(MockKeyDbClient())

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

        # Проверяем параметры — status объединен в список/кортеж
        assert "status_0" in params
        assert "region_0" in params
        assert "active" in params["status_0"]
        assert "pending" in params["status_0"]
        assert params["region_0"] == "Moscow"

    def test_build_query_with_list_in_condition_set(self):
        """Тест построения запроса с IN-условием."""
        class MockKeyDbClient:
            pass

        data_access = DataAccessDataGate(MockKeyDbClient())

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
        assert "t.id in %(id_0)s" in sql
        assert "t.category in %(category_0)s" in sql

        # Проверяем, что значения преобразованы в кортежи
        assert isinstance(params["id_0"], tuple)
        assert params["id_0"] == (1, 2, 3, 4, 5)
        assert isinstance(params["category_0"], tuple)
        assert params["category_0"] == ("A", "B")

    def test_build_query_sql_format(self):
        """Тест форматирования SQL-запроса."""
        class MockKeyDbClient:
            pass

        data_access = DataAccessDataGate(MockKeyDbClient())

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

        # GROUP BY присутствует
        assert "group by" in sql.lower()

        # Проверяем, что FROM есть
        from_line = [line for line in lines if "from" in line.lower()]
        assert len(from_line) == 1
        assert "schema.table_name t" in from_line[0]
