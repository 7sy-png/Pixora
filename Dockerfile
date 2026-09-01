FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    QT_QPA_PLATFORM=offscreen

WORKDIR /app

RUN apt-get update \
    && apt-get install --yes --no-install-recommends libegl1 libgl1 libxkbcommon0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --requirement requirements.txt

COPY app ./app
COPY tests ./tests
COPY main.py ./

CMD ["python", "-m", "pytest", "-q", "-W", "error"]
