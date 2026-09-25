FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml ./
COPY qaf ./qaf
COPY config ./config
RUN pip install --no-cache-dir .

ENV QAF_PROMETHEUS_URL=http://prometheus:9090
EXPOSE 8000
ENTRYPOINT ["qaf", "--config", "/app/config/qaf.yaml"]
CMD ["serve", "--port", "8000", "--interval", "15"]
