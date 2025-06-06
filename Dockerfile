FROM python:3.12.3-slim-bullseye

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV FLASK_APP=start.py
ENV FLASK_ENV=production

RUN echo "Acquire::Retries \"5\";" > /etc/apt/apt.conf.d/80-retries && \
    echo "Acquire::http::Timeout \"30\";" >> /etc/apt/apt.conf.d/80-retries && \
    apt-get update --fix-missing || apt-get update

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p static/uploads && \
    chmod 755 static/uploads && \
    chown -R 1000:1000 static/uploads

USER 1000

EXPOSE 5000

ENTRYPOINT ["python", "start.py"]