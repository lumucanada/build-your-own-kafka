"""任务 CRUD + 页面"""

from flask import Blueprint, request, jsonify, render_template
from modules.database import get_db
from modules.auth import login_required

tasks_bp = Blueprint('tasks', __name__)


# ============================================================
# 工具
# ============================================================

def ok(data=None, **kwargs):
    return jsonify({"ok": True, "data": data, **kwargs})


def fail(message, code=400):
    return jsonify({"ok": False, "message": message}), code


def row_to_dict(r):
    return {"id": r["id"], "task": r["task"], "completed": r["completed"], "created_at": r["created_at"]}


# ============================================================
# 页面
# ============================================================

@tasks_bp.route('/')
@login_required
def home():
    return render_template('index.html')


# ============================================================
# CRUD API
# ============================================================

@tasks_bp.route('/add', methods=['POST'])
@login_required
def add_task():
    data = request.json
    if not data:
        return fail("请求体不能为空")
    task = (data.get("task") or "").strip()
    if not task:
        return fail("任务内容不能为空")
    if len(task) > 500:
        return fail("任务内容过长，最多500字")

    with get_db() as conn:
        cur = conn.execute("INSERT INTO tasks (task) VALUES (?)", (task,))
        conn.commit()
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (cur.lastrowid,)).fetchone()

    return jsonify({"ok": True, "data": row_to_dict(row)})


@tasks_bp.route('/list', methods=['GET'])
@login_required
def list_tasks():
    filter_type = request.args.get("filter", "all")  # all | pending | completed

    with get_db() as conn:
        if filter_type == "completed":
            rows = conn.execute("SELECT * FROM tasks WHERE completed=1 ORDER BY id DESC").fetchall()
        elif filter_type == "pending":
            rows = conn.execute("SELECT * FROM tasks WHERE completed=0 ORDER BY id DESC").fetchall()
        else:
            rows = conn.execute("SELECT * FROM tasks ORDER BY id DESC").fetchall()

    return jsonify({"ok": True, "data": [row_to_dict(r) for r in rows]})


@tasks_bp.route('/delete', methods=['POST'])
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


@tasks_bp.route('/done', methods=['POST'])
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


@tasks_bp.route('/undo', methods=['POST'])
@login_required
def undo_task():
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


@tasks_bp.route('/edit', methods=['POST'])
@login_required
def edit_task():
    """编辑任务内容"""
    data = request.json
    if not data:
        return fail("请求体不能为空")
    task_id = data.get("id")
    new_text = (data.get("task") or "").strip()

    if task_id is None:
        return fail("缺少 id 参数")
    if not new_text:
        return fail("任务内容不能为空")
    if len(new_text) > 500:
        return fail("任务内容过长，最多500字")

    with get_db() as conn:
        cur = conn.execute("UPDATE tasks SET task=? WHERE id=?", (new_text, task_id))
        conn.commit()
        if cur.rowcount == 0:
            return fail("任务不存在", code=404)

    return jsonify({"ok": True, "data": {"id": task_id, "task": new_text}})
