Нужно доработать модуль @src/libfa2/hier_metadata

В класс MetricNode нужно добавить поле mp_decomp_tp (multi part decomposition type)

Оно может иметь следующие значения:
- DirectBase
- DirectRate
- Integral
- AverageWeighted

соответственно нужно реализовать соответствующий enum class


Это поле обязательно только при условии, что type === MetricType.MULTI, в остальных случаях должно игнорироваться (особенно при сериализации/десериализации из/в JSON)

Нужно добавить validation для этого поля, доработать функции сериализации/десериализации и т.д. и т.п. (включая тесты, которые в tests/libfa2/hier_metadata)

Подробный отчет о проделанной работе положить в agent_stuff/reports/20_mpdecomp_glm_report.md
