from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import csv
import io
import os
import sys
import webbrowser
import threading
from contextlib import contextmanager
from functools import wraps
from datetime import datetime

# ---- PyInstaller 打包适配 ----
if getattr(sys, 'frozen', False):
    # 打包后的 EXE 运行时
    BASE_DIR = os.path.dirname(sys.executable)
    TEMPLATE_DIR = os.path.join(sys._MEIPASS, 'templates')
else:
    # 开发环境
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')

app = Flask(__name__, template_folder=TEMPLATE_DIR)
app.secret_key = os.environ.get("TODO_SECRET", "change-me-to-a-random-secret-2024")
DATABASE = os.path.join(BASE_DIR, "todo.db")

# ============================================================
# 数据库工具
# ============================================================

@contextmanager
def get_db():
    """上下文管理器，自动关闭连接"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """初始化所有数据库表"""
    with get_db() as conn:
        # 任务表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT NOT NULL,
                completed INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        # 用户表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'admin',
                created_at TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        conn.commit()

def seed_admin():
    """如果没有管理员用户，创建一个默认的"""
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM users WHERE role='admin'").fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                ("admin", generate_password_hash("admin123"))
            )
            conn.commit()
            print("[OK] 默认管理员创建成功: admin / admin123")
        else:
            print("[OK] 管理员账号已存在，跳过创建")

# 启动时初始化
init_db()
seed_admin()

# ============================================================
# 认证工具
# ============================================================

def login_required(f):
    """登录拦截装饰器 — 页面路由重定向登录页，API路由返回401 JSON"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            # 判断是否是 API 请求（以 /api/ 开头 或 方法是 POST 且接受 JSON）
            if request.path.startswith("/api/") or request.content_type == "application/json":
                return jsonify({"ok": False, "message": "请先登录"}), 401
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated

def get_current_user():
    """获取当前登录用户信息"""
    uid = session.get("user_id")
    if not uid:
        return None
    with get_db() as conn:
        return conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()

# ============================================================
# 统一响应
# ============================================================

def ok(data=None, **kwargs):
    return jsonify({"ok": True, "data": data, **kwargs})

def fail(message, code=400):
    return jsonify({"ok": False, "message": message}), code

# ============================================================
# 认证页面与接口
# ============================================================

@app.route('/login')
def login_page():
    """登录页面"""
    if "user_id" in session:
        return redirect(url_for("home"))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    """登录接口"""
    data = request.json
    if not data:
        return fail("请求体不能为空")

    username = (data.get("username") or "").strip()
    password = (data.get("password") or "")

    if not username or not password:
        return fail("用户名和密码不能为空")

    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()

    if not user or not check_password_hash(user["password_hash"], password):
        return fail("用户名或密码错误", code=401)

    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["role"] = user["role"]

    return ok({
        "id": user["id"],
        "username": user["username"],
        "role": user["role"]
    })

@app.route('/logout')
def logout():
    """退出登录"""
    session.clear()
    return redirect(url_for("login_page"))

# ============================================================
# 页面路由（需要登录）
# ============================================================

@app.route('/')
@login_required
def home():
    """主页面 — Todo 列表"""
    return render_template('index.html')

@app.route('/admin')
@login_required
def admin_page():
    """后台管理页面"""
    user = get_current_user()
    return render_template('admin.html', user=user)

# ============================================================
# Todo API（需要登录）
# ============================================================

@app.route('/add', methods=['POST'])
@login_required
def add_task():
    data = request.json
    if not data:
        return fail("请求体不能为空")
    task = (data.get("task") or "").strip()
    if not task:
        return fail("任务内容不能为空")
    if len(task) > 200:
        return fail("任务内容过长，最多200字")

    with get_db() as conn:
        cur = conn.execute("INSERT INTO tasks (task) VALUES (?)", (task,))
        conn.commit()
        new_id = cur.lastrowid
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (new_id,)).fetchone()

    return jsonify({
        "ok": True,
        "data": {"id": row["id"], "task": row["task"], "completed": row["completed"], "created_at": row["created_at"]}
    })

@app.route('/list', methods=['GET'])
@login_required
def list_tasks():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM tasks ORDER BY id DESC").fetchall()

    tasks = [{"id": r["id"], "task": r["task"], "completed": r["completed"], "created_at": r["created_at"]} for r in rows]
    return jsonify({"ok": True, "data": tasks})

@app.route('/delete', methods=['POST'])
@login_required
def delete_task():
    data = request.json
    if not data:
        return fail("请求体不能为空")
    task_id = data.get("id")
    if task_id is None:
        return fail("缺少 id 参数")

    with get_db() as conn:
        cur = conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        conn.commit()
        if cur.rowcount == 0:
            return fail("任务不存在", code=404)

    return jsonify({"ok": True, "data": {"id": task_id}})

@app.route('/done', methods=['POST'])
@login_required
def done_task():
    data = request.json
    if not data:
        return fail("请求体不能为空")
    task_id = data.get("id")
    if task_id is None:
        return fail("缺少 id 参数")

    with get_db() as conn:
        cur = conn.execute("UPDATE tasks SET completed=1 WHERE id=?", (task_id,))
        conn.commit()
        if cur.rowcount == 0:
            return fail("任务不存在", code=404)

    return jsonify({"ok": True, "data": {"id": task_id}})

@app.route('/undo', methods=['POST'])
@login_required
def undo_task():
    """取消完成"""
    data = request.json
    if not data:
        return fail("请求体不能为空")
    task_id = data.get("id")
    if task_id is None:
        return fail("缺少 id 参数")

    with get_db() as conn:
        cur = conn.execute("UPDATE tasks SET completed=0 WHERE id=?", (task_id,))
        conn.commit()
        if cur.rowcount == 0:
            return fail("任务不存在", code=404)

    return jsonify({"ok": True, "data": {"id": task_id}})

# ============================================================
# 管理后台 API
# ============================================================

@app.route('/api/stats')
@login_required
def api_stats():
    """统计数据"""
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) as n FROM tasks").fetchone()["n"]
        done = conn.execute("SELECT COUNT(*) as n FROM tasks WHERE completed=1").fetchone()["n"]
        pending = total - done
    return ok({
        "total": total,
        "done": done,
        "pending": pending,
        "completion_rate": f"{round(done/total*100, 1)}%" if total > 0 else "0%"
    })

@app.route('/api/tasks/batch-delete', methods=['POST'])
@login_required
def batch_delete():
    """批量删除已完成的任务"""
    data = request.json or {}
    filter_type = data.get("filter", "completed")  # "completed" | "all"

    with get_db() as conn:
        if filter_type == "all":
            cur = conn.execute("DELETE FROM tasks")
        else:
            cur = conn.execute("DELETE FROM tasks WHERE completed=1")
        conn.commit()
        deleted = cur.rowcount

    return ok({"deleted": deleted})

@app.route('/api/tasks/export')
@login_required
def export_csv():
    """导出任务为 CSV"""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "任务内容", "完成状态", "创建时间"])
    for r in rows:
        status = "已完成" if r["completed"] else "未完成"
        writer.writerow([r["id"], r["task"], status, r["created_at"]])

    csv_content = output.getvalue()
    output.close()

    return csv_content, 200, {
        "Content-Type": "text/csv; charset=utf-8-sig",
        "Content-Disposition": f"attachment; filename=tasks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    }

@app.route('/api/change-password', methods=['POST'])
@login_required
def change_password():
    """修改密码"""
    data = request.json
    if not data:
        return fail("请求体不能为空")

    old_pw = data.get("old_password", "")
    new_pw = data.get("new_password", "")

    if not old_pw or not new_pw:
        return fail("旧密码和新密码不能为空")
    if len(new_pw) < 6:
        return fail("新密码至少6位")

    user = get_current_user()
    if not check_password_hash(user["password_hash"], old_pw):
        return fail("旧密码错误", code=401)

    with get_db() as conn:
        conn.execute(
            "UPDATE users SET password_hash=? WHERE id=?",
            (generate_password_hash(new_pw), session["user_id"])
        )
        conn.commit()

    return ok(message="密码修改成功")

# ============================================================
# 启动
# ============================================================

if __name__ == '__main__':
    is_frozen = getattr(sys, 'frozen', False)

    def open_browser():
        webbrowser.open('http://127.0.0.1:5000')

    if is_frozen:
        # 打包后延迟打开浏览器（等服务器启动完毕）
        threading.Timer(1.0, open_browser).start()

    print("=" * 50)
    print("  📝 Todo App 已启动！")
    print("  浏览器打开 → http://127.0.0.1:5000")
    print("  默认账号   → admin / admin123")
    print("  按 Ctrl+C 可停止服务")
    print("=" * 50)

    app.run(debug=not is_frozen, host='127.0.0.1', port=5000)
