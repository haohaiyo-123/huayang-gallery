FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY templates/ templates/
# PORT 由平台注入（Cloady 用 3000，Render 用 10000）；默认兜底 3000
ENV PORT=3000
EXPOSE 3000
CMD ["python", "app.py"]
