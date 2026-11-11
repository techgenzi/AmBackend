FROM python:3.10-slim-buster

RUN apt-get update && apt-get install git curl -y

RUN useradd -ms /bin/bash api
USER api
WORKDIR /home/api

ENV PATH="/home/api/.local/bin:${PATH}"

COPY --chown=api:api requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install git+https://${GITHUB_TOKEN}@github.com/ekalaiv/IpssApiUtils.git --upgrade || true
RUN pip install sentry-sdk gunicorn --upgrade

COPY --chown=api:api . .


EXPOSE 5015

CMD ["gunicorn", "--bind", "0.0.0.0:5015", "--workers", "3", "--timeout", "180", "wsgi:app"]
