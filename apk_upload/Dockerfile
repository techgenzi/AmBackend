FROM python:3.10-alpine

RUN apk update && apk add git

RUN adduser -D api
USER api
WORKDIR /home/api

ENV PATH="/home/api/.local/bin:${PATH}"

COPY --chown=api:api requirements.txt .
RUN pip install -r requirements.txt
RUN pip install    git+https://${GITHUB_TOKEN}@github.com/ekalaiv/IpssApiUtils.git --upgrade
RUN pip install sentry-sdk --upgrade
RUN pip install blinker
RUN pip3 install boto3
RUN pip3 install botocore

COPY --chown=api:api . .