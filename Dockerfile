
FROM python:3.12-slim

WORKDIR /server

COPY requirements-freeze.txt ./

RUN apt update && apt -y install git && apt clean
RUN pip install --upgrade pip && pip install -r requirements-freeze.txt

COPY dobot_server ./dobot_server
COPY pyproject.toml .
RUN pip install .
ENV PYTHONPATH=/server

CMD ["dobot-server"]