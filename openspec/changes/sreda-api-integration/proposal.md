# Proposal: Интеграция API платформы «Среда» для загрузки метаданных ФА

## Why

Методанные факторного анализа (иерархия показателей, фильтры запросов, drill-down алгоритмы)
загружаются из БД напрямую, но в новой конфигурации платформы «Среда» (IFT) все метаданные
экспонируются через REST API с mTLS-аутентификацией. Текущий подход не поддерживает
автоматическую загрузку метаданных из API, что требует ручного перевода в JSON-формат
и блокирует автоматизацию развёртывания сценариев ФА.

## What Changes

1. **Новый пакет `sreda_api/`** — HTTP-клиент для API платформы «Среда» с mTLS, cookie SID,
   рекурсивным обходом иерархии, получением drill-step алгоритмов.
2. **Новый пакет `sreda_models/`** — dataclass-модели для данных из API: `AnalytStep`,
   `DrillStepComponent`, `QueryFilterDetail` с методами сериализации/десериализации.
   Отдельный модуль `enum_mapper.py` — маппинг строковых значений API → enum-классы проекта.
3. **Новый пакет `sreda_transform/`** — конвертер `SredaToDeviationCalcConverter` для
   трансформации API-ответов в существующую структуру `DeviationCalcMetadata`.
4. **Модификация `hier_metadata/metric_node.py`** — добавление полей `analyt_steps` и
   `api_uuid` для сохранения шагов аналитического разложения и UUID узла из Среды.

**Не входит в текущую итерацию:**
- Обратная конвертация (`reverse()`) — DeviationCalcMetadata → API JSON
- Вынесение GUID в env-переменные
- `raw_api_tree` в DeviationCalcMetadata
- README и внешняя документация

## Capabilities

### New Capabilities

- `sreda-api-client`: mTLS HTTP-клиент для платформы «Среда» с поддержкой guide_id,
  табличных частей, рекурсивного обхода иерархии и drill-step алгоритмов.
- `sreda-api-models`: dataclass-модели для сериализации/десериализации данных из API Среды
  (AnalytStep, DrillStepComponent, QueryFilterDetail) + модуль маппинга enum-значений.
- `sreda-api-transform`: конвертер API → DeviationCalcMetadata с поддержкой drill-down
  из табличной части `t_aimis_fa__analyt_drill_steps__components`.

### Modified Capabilities

- `metric-node`: добавление опциональных полей `analyt_steps: List[AnalytStep]` и
  `api_uuid: str | None` в `MetricNode` для хранения шагов аналитического разложения
  и UUID узла из API Среды.

## Impact

| Файл | Тип | Описание |
|------|-----|----------|
| `libfa2/sreda_api/__init__.py` | **Новый** | Пакет API-клиента |
| `libfa2/sreda_api/client.py` | **Новый** | SredaAPIClient (mTLS, fetch_guide, tree) |
| `libfa2/sreda_api/exceptions.py` | **Новый** | Исключения API |
| `libfa2/sreda_models/__init__.py` | **Новый** | Пакет моделей |
| `libfa2/sreda_models/enum_mapper.py` | **Новый** | Маппинг строковых enum-значений API → enum-классы |
| `libfa2/sreda_models/analyt_step.py` | **Новый** | AnalytStep dataclass |
| `libfa2/sreda_models/drill_step_component.py` | **Новый** | DrillStepComponent dataclass |
| `libfa2/sreda_models/query_filter.py` | **Новый** | QueryFilterDetail dataclass |
| `libfa2/sreda_transform/__init__.py` | **Новый** | Пакет конвертеров |
| `libfa2/sreda_transform/to_metadata.py` | **Новый** | SredaToDeviationCalcConverter |
| `libfa2/hier_metadata/metric_node.py` | **Модификация** | + `analyt_steps` + `api_uuid` |

**Всего:** 10 новых файлов + 1 изменённый ≈ ~850 строк кода.
