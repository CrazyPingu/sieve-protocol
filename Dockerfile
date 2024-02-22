FROM python:3.10-alpine

WORKDIR /src
ADD src /src
ADD requirements.txt .

RUN pip install -r requirements.txt

ENV N_PROCESSES=7
ENV BUFFER_SIZE=2048

CMD ["python", "./main.py"]