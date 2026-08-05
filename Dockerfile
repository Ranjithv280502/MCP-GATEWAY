FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
ENV MCP_GATEWAY_ROOT=/app
ENV PYTHONPATH=/app

EXPOSE 8080
CMD ["python", "-m", "gateway.main"]
