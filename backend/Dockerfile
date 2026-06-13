FROM python:3.11-slim

WORKDIR /app

# 换清华源加速 apt（替换所有 Debian 源）
RUN sed -i "s|http://deb.debian.org/debian|http://mirrors.tuna.tsinghua.edu.cn/debian|g" /etc/apt/sources.list.d/debian.sources && \
    sed -i "s|http://security.debian.org/debian-security|http://mirrors.tuna.tsinghua.edu.cn/debian-security|g" /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo libxml2 libxslt1.1 \
    tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

COPY app/ ./app/
RUN mkdir -p /app/uploads

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000"]
