FROM python:3.12

ENV PYTHONUNBUFFERED=1

RUN mkdir /auto_app

WORKDIR /auto_app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

RUN chmod a+x /auto_app/docker/*.sh

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "4"]