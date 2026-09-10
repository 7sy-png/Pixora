FROM python:3.12-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    QT_QPA_PLATFORM=offscreen \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        libdbus-1-3 \
        libegl1 \
        libfontconfig1 \
        libgl1 \
        libglib2.0-0 \
        libxkbcommon0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
COPY requirements-distributed.txt ./
COPY requirements-dev.txt ./
RUN python -m pip install --no-cache-dir \
    --requirement requirements-dev.txt

COPY app ./app
COPY tests ./tests
COPY main.py ./
COPY pytest.ini ./
COPY README.md ./

CMD ["python", "-m", "pytest", "-q", "-W", "error"]
