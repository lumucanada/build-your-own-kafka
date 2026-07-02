"""认证: 登录 / 登出 / 装饰器"""

from functools import wraps
from flask import Blueprint, request, jsonify, redirect, url_for, session
from werkzeug.security import check_password_hash
from modules.database import get_db

auth_bp = Blueprint('auth', __name__)


# ============================================================
# 登录拦截装饰器
# ============================================================

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/") or request.content_type == "application/json":
                return jsonify({"ok": False, "message": "请先登录"}), 401
            return redirect(url_for("auth.login_page"))
        return f(*args, **kwargs)
    return decorated


def get_current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    with get_db() as conn:
        return conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()


# ============================================================
# 路由
# ============================================================

@auth_bp.route('/login')
def login_page():
    if "user_id" in session:
        return redirect(url_for("tasks.home"))
    from flask import render_template
    return render_template('login.html')


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    if not data:
        return jsonify({"ok": False, "message": "请求体不能为空"}), 400

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"ok": False, "message": "用户名和密码不能为空"}), 400

    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()

    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"ok": False, "message": "用户名或密码错误"}), 401

    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["role"] = user["role"]

    return jsonify({
        "ok": True,
        "data": {"id": user["id"], "username": user["username"], "role": user["role"]}
    })


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("auth.login_page"))
