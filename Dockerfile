FROM python:3.13-alpine AS builder

WORKDIR /app

COPY README.md pyproject.toml ./
COPY switchbot_climate switchbot_climate

RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels .

FROM python:3.13-alpine

WORKDIR /app

RUN apk update && apk add --no-cache mosquitto-clients

COPY --from=builder /app/wheels /wheels
COPY healthcheck.sh .

RUN pip install --no-cache --break-system-packages /wheels/*

USER 0

HEALTHCHECK --interval=15m CMD ./healthcheck.sh

LABEL org.opencontainers.image.source=https://github.com/watsona4/switchbot_climate

CMD ["python", "-m", "switchbot_climate", "-c", "/data/config.yaml"]
