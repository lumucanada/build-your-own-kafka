"""后台管理"""

import csv
import io
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, session
from werkzeug.security import generate_password_hash, check_password_hash
from modules.database import get_db
from modules.auth import login_required, get_current_user

admin_bp = Blueprint('admin', __name__)


def ok(data=None, **kwargs):
    return jsonify({"ok": True, "data": data, **kwargs})


def fail(message, code=400):
    return jsonify({"ok": False, "message": message}), code


# ============================================================
# 页面
# ============================================================

@admin_bp.route('/admin')
@login_required
def admin_page():
    user = get_current_user()
    return render_template('admin.html', user=user)


# ============================================================
# API
# ============================================================

@admin_bp.route('/api/stats')
@login_required
def api_stats():
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) as n FROM tasks").fetchone()["n"]
        done = conn.execute("SELECT COUNT(*) as n FROM tasks WHERE completed=1").fetchone()["n"]
    return ok({
        "total": total,
        "done": done,
        "pending": total - done,
        "completion_rate": f"{round(done/total*100, 1)}%" if total > 0 else "0%"
    })


@admin_bp.route('/api/tasks/batch-delete', methods=['POST'])
@login_required
def batch_delete():
    data = request.json or {}
    filter_type = data.get("filter", "completed")

    with get_db() as conn:
        if filter_type == "all":
            cur = conn.execute("DELETE FROM tasks")
        else:
            cur = conn.execute("DELETE FROM tasks WHERE completed=1")
        conn.commit()
        deleted = cur.rowcount

    return ok({"deleted": deleted})


@admin_bp.route('/api/tasks/export')
@login_required
def export_csv():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "任务内容", "完成状态", "创建时间"])
    for r in rows:
        writer.writerow([r["id"], r["task"], "已完成" if r["completed"] else "未完成", r["created_at"]])

    csv_content = output.getvalue()
    output.close()

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    return csv_content, 200, {
        "Content-Type": "text/csv; charset=utf-8-sig",
        "Content-Disposition": f"attachment; filename=tasks_{ts}.csv"
    }


@admin_bp.route('/api/change-password', methods=['POST'])
@login_required
def change_password():
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
