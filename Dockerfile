FROM python:3.12

ENV PYTHONUNBUFFERED=1

RUN mkdir /auto_app

WORKDIR /auto_app

COPY requirements.txt .

RUN pip install -r requirements.txt

RUN apt-get update && apt-get install -y netcat-openbsd

COPY . .

RUN chmod a+x /auto_app/docker/*.sh

CMD ["bash", "/auto_app/docker/app.sh"]