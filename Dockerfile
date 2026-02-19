FROM python:3.14-slim


RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential gcc g++ make pkg-config ca-certificates git curl libssl-dev libffi-dev libbz2-dev libreadline-dev libsqlite3-dev zlib1g-dev liblzma-dev libncurses5-dev libncursesw5-dev \ 
 && rm -rf /var/lib/apt/lists/*
    

WORKDIR /app

COPY . .
RUN pip install --no-cache-dir -r requirements.txt
RUN git clone https://github.com/PEERS21/Common-python.git /app/common
RUN pip install --no-cache-dir -r common/requirements.txt \
 && pip uninstall -y redis || true \
 && pip install --no-cache-dir "redis==7.2.0"

RUN apt-get remove -y --purge gcc g++ make pkg-config git curl \
 && apt-get autoremove -y 

CMD ["python", "bot.py"]