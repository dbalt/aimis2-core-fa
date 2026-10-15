"""Тесты configs.fa2026.json — файловый конфиг сервиса.

Проверяют:
1. Файл парсится как корректный JSON
2. Блок `summarize` удалён — источник precompute-конфига перенесён
   в SQL-конфиг (`#sqlconf.core_fa_settings.summarize.precompute`);
   деградация к дефолту при отсутствии sqlconf-строки покрыта
   `validate_precompute_cfg(None)` в tests/test_precompute_config.py
"""

from __future__ import annotations

import json
import os

import pytest

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONF_PATH = os.path.join(_PROJECT_ROOT, 'configs.fa2026.json')


@pytest.fixture(scope='module')
def conf() -> dict:
    with open(CONF_PATH, encoding='utf-8') as f:
        return json.load(f)


def test_conf_file_exists():
    assert os.path.isfile(CONF_PATH), f'Ожидался файл конфига: {CONF_PATH}'


def test_conf_is_valid_json(conf):
    assert isinstance(conf, dict)


def test_summarize_key_removed(conf):
    """Файловый ключ больше не источник precompute-конфига."""
    assert 'summarize' not in conf


def test_remaining_keys_intact(conf):
    """Остальные секции файлового конфига не затронуты переносом."""
    assert set(conf) == {'tables', 'models', 'gigachat_cert_source', 'navi_settings'}
