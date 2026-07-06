"""Todo App — 入口"""
#hhahaahha
import os
import sys
import webbrowser
import threading
from flask import Flask
from config import SECRET_KEY, HOST, PORT, BASE_DIR

# ---- PyInstaller 模板路径适配 ----
if getattr(sys, 'frozen', False):
    template_dir = os.path.join(sys._MEIPASS, 'templates')
    static_dir = os.path.join(sys._MEIPASS, 'static')
else:
    template_dir = os.path.join(BASE_DIR, 'templates')
    static_dir = os.path.join(BASE_DIR, 'static')

# ---- 创建应用 ----
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.secret_key = SECRET_KEY

# ---- 注册模块 ----
from modules.database import init_db, seed_admin
from modules.auth import auth_bp
from modules.tasks import tasks_bp
from modules.admin import admin_bp

app.register_blueprint(auth_bp)
app.register_blueprint(tasks_bp)
app.register_blueprint(admin_bp)

init_db()
seed_admin()

# ---- 启动 ----
if __name__ == '__main__':
    is_frozen = getattr(sys, 'frozen', False)

    if is_frozen:
        threading.Timer(1.0, lambda: webbrowser.open(f'http://127.0.0.1:{PORT}')).start()

    print("=" * 50)
    print(f"  📝 Todo App 已启动 → http://127.0.0.1:{PORT}")
    print(f"  默认账号: admin / admin123")
    print("=" * 50)

    app.run(debug=not is_frozen, host=HOST, port=PORT)
