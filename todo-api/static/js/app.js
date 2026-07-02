/* ============================================================
   Todo App — Frontend Logic
   ============================================================ */

// ---- 状态 ----
let currentFilter = 'all';

// ---- DOM 引用 ----
const addInput  = document.getElementById('addInput');
const addBtn    = document.getElementById('addBtn');
const taskList  = document.getElementById('taskList');
const emptyEl   = document.getElementById('emptyState');
const totalEl   = document.getElementById('totalCount');
const pendingEl = document.getElementById('pendingCount');
const navLinks  = document.querySelectorAll('.sidebar-nav a');
const filterTitle = document.getElementById('filterTitle');

// ---- 工具 ----
function api(url, opts = {}) {
    return fetch(url, opts).then(res => {
        if (res.status === 401) { window.location.href = '/login'; throw new Error('unauth'); }
        return res.json();
    });
}

function escapeHtml(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}

function toast(msg) {
    const el = document.getElementById('toast');
    el.textContent = msg;
    el.classList.add('show');
    clearTimeout(el._tid);
    el._tid = setTimeout(() => el.classList.remove('show'), 2000);
}

function fmtTime(dt) {
    if (!dt) return '';
    // dt is like "2024-07-01 14:30:00"
    const m = dt.match(/(\d{4})-(\d{2})-(\d{2})/);
    if (!m) return dt;
    const now = new Date();
    const d = new Date(+m[1], +m[2] - 1, +m[3]);
    const diff = Math.floor((now - d) / 86400000);
    if (diff === 0) return '今天';
    if (diff === 1) return '昨天';
    if (diff < 7)  return `${diff}天前`;
    return `${m[2]}/${m[3]}`;
}

// ---- 加载列表 ----
async function loadTasks() {
    try {
        const json = await api(`/list?filter=${currentFilter}`);
        const tasks = json.data || [];

        taskList.innerHTML = '';

        if (tasks.length === 0) {
            emptyEl.style.display = 'block';
        } else {
            emptyEl.style.display = 'none';
            tasks.forEach(t => renderTask(t));
        }

        // 加载统计
        const statsJson = await api('/api/stats');
        const s = statsJson.data;
        totalEl.textContent = s.total;
        pendingEl.textContent = s.pending;
    } catch (err) {
        if (err.message !== 'unauth') toast('加载失败');
    }
}

// ---- 渲染单条 ----
function renderTask(t) {
    const li = document.createElement('li');
    li.className = 'task-item';
    li.id = 'task-' + t.id;
    li.innerHTML = `
        <div class="task-check ${t.completed ? 'done' : ''}" onclick="toggleTask(${t.id}, ${t.completed})"></div>
        <span class="task-text ${t.completed ? 'done' : ''}" ondblclick="startEdit(${t.id}, this)">${escapeHtml(t.task)}</span>
        <span class="task-time">${fmtTime(t.created_at)}</span>
        <span class="task-actions">
            <button title="编辑" onclick="startEdit(${t.id}, this.parentElement.parentElement.querySelector('.task-text'))">✎</button>
            <button class="del" title="删除" onclick="deleteTask(${t.id})">✕</button>
        </span>
    `;
    taskList.appendChild(li);
}

// ---- 添加 ----
async function addTask() {
    const text = addInput.value.trim();
    if (!text) return;

    try {
        const json = await api('/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task: text })
        });
        if (!json.ok) return toast(json.message);

        addInput.value = '';
        addInput.focus();
        await loadTasks();
    } catch (err) {
        toast('添加失败');
    }
}

// ---- 完成/撤销 ----
async function toggleTask(id, completed) {
    const url = completed ? '/undo' : '/done';
    try {
        await api(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id })
        });
        await loadTasks();
    } catch (err) {
        toast('操作失败');
    }
}

// ---- 删除 ----
async function deleteTask(id) {
    try {
        const json = await api('/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id })
        });
        if (!json.ok) return toast(json.message);
        await loadTasks();
    } catch (err) {
        toast('删除失败');
    }
}

// ---- 内联编辑 ----
function startEdit(id, spanEl) {
    if (spanEl.querySelector('input')) return; // 已在编辑中

    const oldText = spanEl.textContent.trim();
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'task-edit-input';
    input.value = oldText;

    spanEl.replaceWith(input);
    input.focus();
    input.select();

    const finish = async () => {
        const newText = input.value.trim();
        if (!newText || newText === oldText) {
            // 恢复
            input.replaceWith(spanEl);
            return;
        }
        try {
            const json = await api('/edit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id, task: newText })
            });
            if (json.ok) {
                spanEl.textContent = newText;
            }
        } catch (_) {
            toast('编辑失败');
        }
        input.replaceWith(spanEl);
    };

    input.addEventListener('blur', finish);
    input.addEventListener('keydown', e => {
        if (e.key === 'Enter') { input.blur(); }
        if (e.key === 'Escape') { input.value = oldText; input.blur(); }
    });
}

// ---- 侧边栏切换 ----
navLinks.forEach(a => {
    a.addEventListener('click', e => {
        e.preventDefault();
        navLinks.forEach(n => n.classList.remove('active'));
        a.classList.add('active');
        currentFilter = a.dataset.filter;
        filterTitle.textContent = a.textContent.trim().replace(/\d/g, '').trim();
        loadTasks();
    });
});

// ---- 回车添加 ----
addInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') addTask();
});

// ---- 启动 ----
loadTasks();
