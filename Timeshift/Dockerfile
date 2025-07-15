FROM python:3.11-slim-bullseye

WORKDIR /app

COPY ./requirements.txt /app

COPY . /app


RUN apt-get update

RUN apt-get install libpq-dev python3-dev --assume-yes --force-yes

RUN apt-get install pkg-config python3-dev default-libmysqlclient-dev build-essential --assume-yes --force-yes

RUN pip install --no-cache-dir --requirement /app/requirements.txt

RUN apt-get update \
    && apt-get install -y --no-install-recommends --no-install-suggests \
    build-essential default-libmysqlclient-dev \
    && pip install --no-cache-dir --upgrade pip
EXPOSE 50910

CMD ["python","predictor.py"]