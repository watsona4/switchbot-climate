FROM python:3.13

USER 0

ENV TZ="America/New_York"
RUN cp /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

COPY README.md .
COPY pyproject.toml .
COPY switchbot_climate switchbot_climate

RUN python -m pip install .

CMD ["python", "-m", "switchbot_climate", "-c", "/data/config.yaml"]
