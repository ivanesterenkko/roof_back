FROM python:3.12

ENV PYTHONUNBUFFERED=1

RUN mkdir /auto_app

WORKDIR /auto_app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

RUN chmod a+x /auto_app/docker/*.sh

CMD ["gunicorn", "main:app", "--workers", "1", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind=0.0.0.0:8001"]