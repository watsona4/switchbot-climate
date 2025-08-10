FROM python:3.13-alpine AS builder

WORKDIR /app

COPY README.md pyproject.toml ./
COPY switchbot_climate switchbot_climate

RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels .

FROM python:3.13-alpine

WORKDIR /app

RUN apk update && apk add --no-cache mosquitto-clients

COPY --from=builder /app/wheels /wheels

RUN pip install --no-cache --break-system-packages /wheels/*

USER 0

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
  CMD python -m switchbot_climate -c /data/config.yaml --check-heartbeat || exit 1

LABEL org.opencontainers.image.source=https://github.com/watsona4/switchbot_climate

CMD ["python", "-m", "switchbot_climate", "-c", "/data/config.yaml"]
