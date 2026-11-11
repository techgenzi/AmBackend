FROM python:3-alpine

RUN apk update && apk add gcc libc-dev make git libffi-dev openssl-dev python3-dev libxml2-dev libxslt-dev

RUN adduser -D api
USER api
WORKDIR /home/api

ENV PATH="/home/api/.local/bin:${PATH}"

COPY --chown=api:api requirements.txt .
RUN pip install -r requirements.txt
RUN pip3 install git+https://${GITHUB_TOKEN}@github.com/ekalaiv/IpssApiUtils.git --upgrade
RUN pip install sentry-sdk --upgrade

COPY --chown=api:api . .