FROM python:3.13-alpine AS builder

WORKDIR /app

COPY README.md pyproject.toml .
COPY switchbot_climate switchbot_climate

RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels .

FROM python:3.13-alpine

WORKDIR /app

COPY --from=builder /app/wheels /wheels

RUN pip install --no-cache --break-system-packages /wheels/*

USER 0

LABEL org.opencontainers.image.source=https://github.com/watsona4/switchbot_climate

CMD ["python", "-m", "switchbot_climate", "-c", "/data/config.yaml"]
