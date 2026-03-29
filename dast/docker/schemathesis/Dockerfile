FROM python:3.12-slim

ARG SCHEMATHESIS_VERSION=4.14.2

RUN pip install --no-cache-dir "schemathesis==${SCHEMATHESIS_VERSION}"

ENTRYPOINT ["st"]
