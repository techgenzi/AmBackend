FROM python:3.10-slim-buster

RUN apt-get update && apt-get install git -y

RUN useradd -ms /bin/bash api
USER api
WORKDIR /home/api

ENV PATH="/home/api/.local/bin:${PATH}"

COPY --chown=api:api requirements.txt .
RUN pip install -r requirements.txt
RUN pip install git+https://${GITHUB_TOKEN}@github.com/ekalaiv/IpssApiUtils.git@ipss/prod --upgrade
RUN pip install boto3

COPY --chown=api:api . .
