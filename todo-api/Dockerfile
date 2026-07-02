# ---- 构建阶段 ----
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- 运行阶段 ----
FROM python:3.11-slim
WORKDIR /app

# 从 builder 复制已安装的依赖
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# 复制源码
COPY . .

# 数据持久化
VOLUME ["/app/data"]
ENV TODO_DATABASE=/app/data/todo.db

# 暴露端口
EXPOSE 5000

# 生产环境用 gunicorn 启动
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "60", "app:app"]
