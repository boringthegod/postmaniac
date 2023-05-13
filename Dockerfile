FROM python:3-alpine

RUN pip install postmaniac

WORKDIR /output

ENTRYPOINT [ "postmaniac"]

VOLUME [ "/output" ]