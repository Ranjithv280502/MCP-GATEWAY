FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gnupg && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p data/workspace data/audit data/embeddings

ENV MCP_GATEWAY_ROOT=/app
ENV PYTHONPATH=/app

EXPOSE 8080
CMD ["python", "-m", "gateway.main"]
