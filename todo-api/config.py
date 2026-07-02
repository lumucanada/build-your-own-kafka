"""全局配置"""

import os
import sys

# ---- 路径适配 (PyInstaller / 开发) ----
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE = os.environ.get("TODO_DATABASE", os.path.join(BASE_DIR, "todo.db"))
SECRET_KEY = os.environ.get("TODO_SECRET", "change-me-to-a-random-secret-2024")
HOST = os.environ.get("TODO_HOST", "0.0.0.0")
PORT = int(os.environ.get("TODO_PORT", "5000"))
DEBUG = os.environ.get("TODO_DEBUG", "false").lower() == "true"

# 默认管理员
DEFAULT_USERNAME = os.environ.get("TODO_ADMIN_USER", "admin")
DEFAULT_PASSWORD = os.environ.get("TODO_ADMIN_PASS", "admin123")
