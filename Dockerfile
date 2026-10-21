FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv/ncet-verifyflow
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng ca-certificates && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home --uid 10001 docflow
COPY . .
RUN mkdir -p /var/data/ncet-uploads && chown -R docflow:docflow /srv/ncet-verifyflow /var/data/ncet-uploads
USER docflow
EXPOSE 10000
CMD ["python", "-m", "app.serve"]
