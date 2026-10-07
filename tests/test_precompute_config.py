"""Unit-тесты precompute_config — валидация и нормализация конфига предвычислений.

Проверяют:
1. Дефолт при None/пустом конфиге = всё code, пороги 0.30/0.15
2. Каждое нарушение: режим, порог, similarity, неизвестные ключи, типы
3. Мастер-нормализацию numbers=llm → llm для markers/selection/names
4. Граничные значения порогов и процентный формат pct_str
"""

from __future__ import annotations

import pytest

from src.libfa2.fa_impl.precompute_config import (
    DEFAULT_PRECOMPUTE,
    validate_precompute_cfg,
    pct_str,
)


class TestDefaults:

    def test_none_gives_default(self):
        assert validate_precompute_cfg(None) == DEFAULT_PRECOMPUTE

    def test_empty_dict_gives_default(self):
        assert validate_precompute_cfg({}) == DEFAULT_PRECOMPUTE

    def test_default_all_code(self):
        cfg = validate_precompute_cfg(None)
        assert cfg["numbers"]["mode"] == "code"
        assert cfg["markers"]["mode"] == "code"
        assert cfg["selection"]["mode"] == "code"
        assert cfg["selection"]["threshold"] == 0.30
        assert cfg["selection"]["similarity"] == 0.15
        assert cfg["names"]["allowed"] == "code"
        assert cfg["names"]["children"] == "code"

    def test_partial_config_fills_defaults(self):
        cfg = validate_precompute_cfg({"markers": {"mode": "llm"}})
        assert cfg["markers"]["mode"] == "llm"
        assert cfg["numbers"]["mode"] == "code"
        assert cfg["selection"]["threshold"] == 0.30

    def test_input_not_mutated(self):
        raw = {"selection": {"threshold": 0.5}}
        validate_precompute_cfg(raw)
        assert raw["selection"] == {"threshold": 0.5}


class TestModeValidation:

    def test_invalid_mode_rejected(self):
        with pytest.raises(ValueError, match="numbers.*'code' или 'llm'"):
            validate_precompute_cfg({"numbers": {"mode": "auto"}})

    def test_invalid_names_mode_rejected(self):
        with pytest.raises(ValueError, match=r"names\.allowed"):
            validate_precompute_cfg({"names": {"allowed": "yes"}})

    def test_valid_llm_mode_accepted(self):
        cfg = validate_precompute_cfg({"markers": {"mode": "llm"}})
        assert cfg["markers"]["mode"] == "llm"

    def test_section_not_dict_rejected(self):
        with pytest.raises(ValueError, match="numbers.*словарь"):
            validate_precompute_cfg({"numbers": "llm"})


class TestThresholdValidation:

    def test_threshold_zero_rejected(self):
        with pytest.raises(ValueError, match=r"selection\.threshold"):
            validate_precompute_cfg({"selection": {"threshold": 0}})

    def test_threshold_negative_rejected(self):
        with pytest.raises(ValueError, match=r"selection\.threshold"):
            validate_precompute_cfg({"selection": {"threshold": -0.1}})

    def test_threshold_above_one_allowed(self):
        """threshold > 1 = «значим только максимум» — легитимный конфиг."""
        cfg = validate_precompute_cfg({"selection": {"threshold": 1.5}})
        assert cfg["selection"]["threshold"] == 1.5

    def test_threshold_non_number_rejected(self):
        with pytest.raises(ValueError, match=r"selection\.threshold.*число"):
            validate_precompute_cfg({"selection": {"threshold": "30%"}})

    def test_threshold_bool_rejected(self):
        with pytest.raises(ValueError, match=r"selection\.threshold"):
            validate_precompute_cfg({"selection": {"threshold": True}})

    def test_similarity_zero_rejected(self):
        with pytest.raises(ValueError, match=r"selection\.similarity"):
            validate_precompute_cfg({"selection": {"similarity": 0}})

    def test_similarity_one_rejected(self):
        with pytest.raises(ValueError, match=r"selection\.similarity"):
            validate_precompute_cfg({"selection": {"similarity": 1.0}})

    def test_similarity_valid(self):
        cfg = validate_precompute_cfg({"selection": {"similarity": 0.99}})
        assert cfg["selection"]["similarity"] == 0.99


class TestUnknownKeys:

    def test_unknown_top_key_rejected(self):
        with pytest.raises(ValueError, match="неизвестные ключи.*\\['params'\\]"):
            validate_precompute_cfg({"params": {}})

    def test_unknown_section_key_rejected(self):
        with pytest.raises(ValueError, match="numbers.*неизвестные ключи"):
            validate_precompute_cfg({"numbers": {"mode": "code", "precision": 2}})


class TestMasterForcing:

    def test_numbers_llm_forces_all_llm(self):
        cfg = validate_precompute_cfg({
            "numbers": {"mode": "llm"},
            "markers": {"mode": "code"},
            "selection": {"mode": "code", "threshold": 0.5},
            "names": {"allowed": "code", "children": "code"},
        })
        assert cfg["numbers"]["mode"] == "llm"
        assert cfg["markers"]["mode"] == "llm"
        assert cfg["selection"]["mode"] == "llm"
        assert cfg["names"]["allowed"] == "llm"
        assert cfg["names"]["children"] == "llm"
        # пороги сохраняются — подставляются в llm-правило промпта
        assert cfg["selection"]["threshold"] == 0.5

    def test_numbers_code_keeps_explicit_llm_handls(self):
        cfg = validate_precompute_cfg({
            "numbers": {"mode": "code"},
            "markers": {"mode": "llm"},
        })
        assert cfg["markers"]["mode"] == "llm"
        assert cfg["selection"]["mode"] == "code"


class TestPctStr:

    def test_typical(self):
        assert pct_str(0.30) == "30"
        assert pct_str(0.15) == "15"
        assert pct_str(0.5) == "50"

    def test_fractional(self):
        assert pct_str(0.075) == "7,5"
        assert pct_str(1.5) == "150"
