FROM python:3.10-alpine

RUN apk add --no-cache build-base libffi-dev openssl-dev

RUN mkdir /app
WORKDIR /app

RUN pip install pipenv

ADD Pipfile .
ADD Pipfile.lock .
RUN pipenv install

ADD . .

CMD [ "pipenv", "run", "python", "./main.py" ]
