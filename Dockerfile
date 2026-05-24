FROM python:3.11-slim

LABEL description="ZSXQ Daily Digest - 知识星球AI日报生成器"

# Install system deps for PDF generation (optional)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi8 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt weasyprint

COPY . .

# Create data and output dirs
RUN mkdir -p data output logs

# Schedule: run at configured time daily, default 1:00 AM
ENV RUN_HOUR=1
ENV RUN_MINUTE=0

CMD ["python3", "scheduler.py"]
