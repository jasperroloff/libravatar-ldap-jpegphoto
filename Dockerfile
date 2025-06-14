# syntax=docker/dockerfile:1

FROM python:3-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .

ENV PORT 5000
ENV PYTHONUNBUFFERED 1

EXPOSE $PORT

CMD [ "python3", "server.py"]
