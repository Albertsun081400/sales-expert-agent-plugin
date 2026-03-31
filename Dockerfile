FROM python:3.11-slim

WORKDIR /app

# 安装依赖（使用腾讯云镜像源加速）
COPY requirements.txt .
RUN pip install --no-cache-dir \
    -i https://mirrors.cloud.tencent.com/pypi/simple \
    -r requirements.txt

# 复制应用代码
COPY app/ ./app/

EXPOSE 8080

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
