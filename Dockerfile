FROM python:3.13

USER 0

ENV TZ="America/New_York"
RUN cp /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

RUN mkdir switchbot_climate
COPY *.py switchbot_climate

CMD ["python", "-m", "switchbot_climate", "-c", "/data/config.yaml"]
