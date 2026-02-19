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


RUN python - <<'PY'
import importlib, sys
r = importlib.import_module('redis')
print('redis ok:', r.__version__, r.__file__)
import redis.exceptions as exc
print('DataError present:', hasattr(exc, 'DataError'), 'exceptions file:', getattr(exc, "__file__", None))
PY


CMD ["python", "bot.py"]