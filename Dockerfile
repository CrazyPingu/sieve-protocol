FROM python:3.10-alpine

WORKDIR /src
ADD src /src
ADD requirements.txt .

RUN pip install -r requirements.txt

ENV BUFFER_SIZE=8192

CMD ["python", "./main.py"]