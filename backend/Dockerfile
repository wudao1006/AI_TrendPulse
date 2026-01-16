# 使用官方 Python 轻量级镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Playwright 路径
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# 安装系统依赖 (用于构建 Python 包和 Playwright)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 安装 Playwright 浏览器 (仅 Chromium)
RUN playwright install --with-deps chromium

# 复制项目代码
COPY . .

# 暴露端口
EXPOSE 8000

# 默认启动命令 (会被 docker-compose 覆盖)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
