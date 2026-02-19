FROM python:3.14-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends git ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .
RUN pip install --no-cache-dir -r requirements.txt
RUN git clone https://github.com/PEERS21/Common-python.git /app/common
RUN pip install --no-cache-dir -r common/requirements.txt

CMD ["python", "bot.py"]