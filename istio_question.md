# Ошибка `400 DPE,SLR http1.codec_error` в логах istio на ingress

> Вопрос: что означает ошибка `400 DPE,SLR http1.codec_error` в логах istio на ingress?

## Коротко

Клиент (то, что подключается к ingress-gateway — downstream) прислал байты, которые Envoy **не смог разобрать как валидный HTTP/1.1**. HTTP-кодек упал с ошибкой ещё до маршрутизации, и Envoy вернул `400 Bad Request`. Это не ошибка бэкенда — запрос «умер» на самом входе в сетку.

## Расшифровка полей лога

В стандартном формате лога Istio после `%RESPONSE_CODE%` идёт `%RESPONSE_FLAGS%`, а затем `%RESPONSE_CODE_DETAILS%`. Так что `400 DPE,SLR http1.codec_error` разбирается так:

| Токен | Что значит |
|---|---|
| `400` | HTTP Bad Request |
| `DPE` | **D**ownstream **P**rotocol **E**rror — ошибка протокола со стороны клиента. Запрос от клиента не соответствует ожидаемому протоколу |
| `http1.codec_error` | Конкретная причина: сбой произошёл **внутри HTTP/1-кодека** (http_parser не смог распарсить request-line/заголовки) |
| `SLR` | ⚠️ **Не является стандартным флагом Envoy.** Полный валидный список флагов из `envoy/config/accesslog/v3/accesslog.proto` (`ResponseFlagFilter.flags`): `LH, UH, UT, LR, UR, UF, UC, UO, NR, DI, FI, RL, UAEX, RLSE, DC, URX, SI, IH, DPE, UMSDR, RFCF, NFCF, DT, UPE, NC, OM, DF, DO, DR, UDO`. `SLR` там **нет**. Скорее всего это либо опечатка/ошибка чтения (ближе всего `LR` — local reset, или `SI` — stream idle timeout), либо нестандартный/кастомный токен формата лога. Смысл инцидента задаёт именно `DPE + http1.codec_error`. |

## Типичные причины именно на ingress

1. **HTTPS отправляют на plaintext HTTP-порт** (и наоборот). Самый частый кейс: клиент стучится `https://host` (TLS ClientHello) на порт gateway, объявленный как `HTTP`, — Envoy пытается разобрать байты TLS-рукопожатия как HTTP и падает. В доках Istio это прямо описано как «400 DPE».
2. **Не-HTTP трафик на HTTP-порт**: сканеры, health-check-зонды LB, сырое TCP, бинарный протокол.
3. **HTTP/2 (h2c) или WebSocket-preflight на порту, ожидающем HTTP/1.1**, либо рассинхрон ALPN.
4. **Малформированный запрос**: нелегальные символы в request-line/заголовках, превышение лимитов, разорванный/chunked запрос.
5. **LB перед Istio**: если балансировщик терминирует TLS, но не передаёт SNI/пересоздаёт соединение криво — реальные клиенты получают 400, хотя health-checkи проходят.
6. **Несоответствие имени/протокола порта** в `Service`/`Gateway` (`http` vs `https` vs `tcp-...`) — ломает protocol-sniffing.

## Что делать

1. Посмотреть полную строку лога целиком: `%DOWNSTREAM_REMOTE_ADDRESS%`, `%REQUESTED_SERVER_NAME%` (SNI), `%REQ(USER-AGENT)%`, `BYTES_RECEIVED`. Часто сразу видно «пришёл TLS на http-порт» (SNI/host + User-Agent сканера) или пустой мусорный запрос.
2. Проверить порт `Gateway`/`Service` — какой `protocol` объявлен и что реально шлёт клиент (`http://` vs `https://`). На ingress: `kubectl get gateway -o yaml` + `istioctl proxy-config listener <ingress-pod> -n istio-system`.
3. Воспроизвести руками: `curl -v http://<ingress-ip>:<https-port>/...` vs `https://` — увидеть `wrong version number` / `400`.
4. Если источником являются пробы/сканеры/LB — это часто **неопасный шум** (зонды по IP), и его можно отфильтровать в логах; но если это реальные клиенты — чинить схему TLS/протокола.

## Источники

- [Istio — Traffic Management Problems (раздел про `400 DPE`)](https://istio.io/latest/docs/ops/common-problems/network-issues/)
- [Envoy — Response Code Details (`http1.codec_error`)](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_conn_man/response_code_details)
- [Envoy — Access logging (`%RESPONSE_FLAGS%`)](https://www.envoyproxy.io/docs/envoy/latest/configuration/observability/access_log/usage)
- [Envoy — `accesslog.proto` (исходный список флагов `ResponseFlagFilter.flags`)](https://github.com/envoyproxy/envoy/blob/main/api/envoy/config/accesslog/v3/accesslog.proto)
- [F5 K000133163 — istio-proxy logs show "400 DPE http1.codec_error"](https://my.f5.com/manage/s/article/K000133163)
- [Tetrate — When Protocols Clash: Debugging a Broken Gateway](https://tetrate.io/blog/when-protocols-clash-debugging-a-broken-gateway-in-a-service-mesh)
