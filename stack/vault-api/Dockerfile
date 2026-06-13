FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY . /app

RUN if [ -f requirements.txt ]; then \
      pip install --no-cache-dir -r requirements.txt; \
    fi

RUN if [ ! -f main.py ]; then \
      printf 'from fastapi import FastAPI\napp = FastAPI(title="Hermes Vault API")\n' > main.py; \
    fi

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090"]