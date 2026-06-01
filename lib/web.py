#!/usr/bin/env python3
"""web.py - Web UI for sing-box manager"""
import json
from .config import load_config, load_users_data, save_users_data
from .users import load_users, add_user, remove_user, get_user
from .sharing import gen_all_links, generate_subscription
from .subscription import get_token

ADMIN_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>sing-box 管理面板</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }
.container { max-width: 900px; margin: 0 auto; padding: 20px; }
.header { text-align: center; padding: 30px 0; border-bottom: 1px solid #1e293b; margin-bottom: 30px; }
.header h1 { font-size: 24px; color: #38bdf8; }
.header p { color: #94a3b8; margin-top: 8px; }
.card { background: #1e293b; border-radius: 12px; padding: 24px; margin-bottom: 20px; }
.card-title { font-size: 18px; color: #38bdf8; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
.user-list { list-style: none; }
.user-item { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background: #0f172a; border-radius: 8px; margin-bottom: 8px; }
.user-info { flex: 1; }
.user-name { font-weight: 600; color: #f1f5f9; }
.user-uuid { font-size: 12px; color: #64748b; margin-top: 4px; font-family: monospace; }
.user-links { display: flex; gap: 8px; }
.btn { padding: 8px 16px; border-radius: 6px; border: none; cursor: pointer; font-size: 13px; font-weight: 500; transition: all 0.2s; }
.btn-primary { background: #38bdf8; color: #0f172a; }
.btn-primary:hover { background: #7dd3fc; }
.btn-danger { background: #ef4444; color: white; }
.btn-danger:hover { background: #f87171; }
.btn-sm { padding: 6px 12px; font-size: 12px; }
.add-form { display: flex; gap: 12px; margin-top: 16px; }
.add-form input { flex: 1; padding: 10px 14px; border-radius: 8px; border: 1px solid #334155; background: #0f172a; color: #e2e8f0; font-size: 14px; }
.add-form input:focus { outline: none; border-color: #38bdf8; }
.toast { position: fixed; top: 20px; right: 20px; padding: 12px 20px; border-radius: 8px; background: #22c55e; color: white; font-weight: 500; opacity: 0; transition: opacity 0.3s; z-index: 1000; }
.toast.show { opacity: 1; }
.toast.error { background: #ef4444; }
.modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 999; justify-content: center; align-items: center; }
.modal.show { display: flex; }
.modal-content { background: #1e293b; padding: 24px; border-radius: 12px; max-width: 500px; width: 90%; max-height: 80vh; overflow-y: auto; }
.modal-title { font-size: 18px; margin-bottom: 16px; color: #38bdf8; }
.link-item { padding: 8px 12px; background: #0f172a; border-radius: 6px; margin-bottom: 8px; font-family: monospace; font-size: 12px; word-break: break-all; color: #94a3b8; }
.link-label { font-size: 11px; color: #64748b; margin-bottom: 4px; text-transform: uppercase; }
.empty { text-align: center; padding: 40px; color: #64748b; }
.stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 20px; }
.stat { background: #0f172a; padding: 16px; border-radius: 8px; text-align: center; }
.stat-value { font-size: 28px; font-weight: 700; color: #38bdf8; }
.stat-label { font-size: 12px; color: #64748b; margin-top: 4px; }
.copy-btn { background: none; border: none; color: #38bdf8; cursor: pointer; font-size: 14px; padding: 4px; }
.copy-btn:hover { color: #7dd3fc; }
</style>
</head>
<body>
<div id="toast" class="toast"></div>
<div id="modal" class="modal">
  <div class="modal-content">
    <div class="modal-title" id="modal-title">订阅链接</div>
    <div id="modal-body"></div>
    <div style="margin-top: 16px; text-align: right;">
      <button class="btn btn-primary" onclick="closeModal()">关闭</button>
    </div>
  </div>
</div>
<div class="container">
  <div class="header">
    <h1>⚡ sing-box 管理面板</h1>
    <p>SN团队 · 代理服务管理</p>
  </div>
  <div class="stats">
    <div class="stat">
      <div class="stat-value" id="user-count">0</div>
      <div class="stat-label">用户数</div>
    </div>
    <div class="stat">
      <div class="stat-value" id="status">-</div>
      <div class="stat-label">服务状态</div>
    </div>
    <div class="stat">
      <div class="stat-value" id="version">-</div>
      <div class="stat-label">版本</div>
    </div>
  </div>
  <div class="card">
    <div class="card-title">👥 用户管理</div>
    <ul class="user-list" id="user-list">
      <li class="empty">加载中...</li>
    </ul>
    <div class="add-form">
      <input type="text" id="new-username" placeholder="输入新用户名" onkeypress="if(event.key==='Enter')addUser()">
      <button class="btn btn-primary" onclick="addUser()">添加用户</button>
    </div>
  </div>
  <div class="card">
    <div class="card-title">ℹ️ 使用说明</div>
    <p style="color: #94a3b8; line-height: 1.8; font-size: 14px;">
      • 点击用户名可查看订阅链接<br>
      • 订阅链接支持 sing-box / Clash / 原始格式<br>
      • 删除用户不可恢复，请谨慎操作<br>
      • Token 认证保护所有 API 请求
    </p>
  </div>
</div>
<script>
const TOKEN = new URLSearchParams(window.location.search).get('token') || '';
let users = [];

function showToast(msg, isError = false) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show' + (isError ? ' error' : '');
  setTimeout(() => t.className = 'toast', 3000);
}

function closeModal() {
  document.getElementById('modal').className = 'modal';
}

async function api(path, method = 'GET', body = null) {
  const url = `/api${path}?token=${TOKEN}`;
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  if (res.status === 403) { showToast('认证失败，请检查 Token', true); return null; }
  return res.json();
}

async function loadUsers() {
  const data = await api('/users');
  if (!data) return;
  users = data.users || [];
  document.getElementById('user-count').textContent = users.length;
  renderUsers();
}

function renderUsers() {
  const list = document.getElementById('user-list');
  if (users.length === 0) {
    list.innerHTML = '<li class="empty">暂无用户</li>';
    return;
  }
  list.innerHTML = users.map(u => `
    <li class="user-item">
      <div class="user-info">
        <div class="user-name">${u.name}</div>
        <div class="user-uuid">${u.uuid}</div>
      </div>
      <div class="user-links">
        <button class="btn btn-primary btn-sm" onclick="showLinks('${u.name}')">订阅链接</button>
        <button class="btn btn-danger btn-sm" onclick="deleteUser('${u.name}')">删除</button>
      </div>
    </li>
  `).join('');
}

async function addUser() {
  const input = document.getElementById('new-username');
  const name = input.value.trim();
  if (!name) { showToast('请输入用户名', true); return; }
  const data = await api('/users', 'POST', { name });
  if (data && data.ok) {
    showToast(`用户 ${name} 已添加`);
    input.value = '';
    loadUsers();
  } else {
    showToast(data?.error || '添加失败', true);
  }
}

async function deleteUser(name) {
  if (!confirm(`确定删除用户 ${name} 吗？此操作不可恢复。`)) return;
  const data = await api(`/users/${name}`, 'DELETE');
  if (data && data.ok) {
    showToast(`用户 ${name} 已删除`);
    loadUsers();
  } else {
    showToast(data?.error || '删除失败', true);
  }
}

async function showLinks(name) {
  const data = await api(`/links/${name}`);
  if (!data || !data.links) return;
  const body = document.getElementById('modal-body');
  body.innerHTML = data.links.map(l => `
    <div style="margin-bottom: 12px;">
      <div class="link-label">${l.label}</div>
      <div class="link-item" style="display:flex; justify-content:space-between; align-items:center;">
        <span style="flex:1; overflow:hidden; text-overflow:ellipsis;">${l.link}</span>
        <button class="copy-btn" onclick="copyLink(this, '${l.link.replace(/'/g, "\\'")}')">📋</button>
      </div>
    </div>
  `).join('');
  document.getElementById('modal-title').textContent = `${name} 的订阅链接`;
  document.getElementById('modal').className = 'modal show';
}

function copyLink(btn, link) {
  navigator.clipboard.writeText(link).then(() => {
    showToast('已复制到剪贴板');
    btn.textContent = '✓';
    setTimeout(() => btn.textContent = '📋', 1500);
  });
}

async function loadStatus() {
  const data = await api('/status');
  if (data) {
    document.getElementById('status').textContent = data.running ? '运行中' : '已停止';
    document.getElementById('version').textContent = data.version || '-';
  }
}

// Init
loadUsers();
loadStatus();
setInterval(loadStatus, 30000);
</script>
</body>
</html>"""


def get_admin_page():
    """返回管理面板 HTML"""
    return ADMIN_HTML


def handle_api_request(path, token):
    """处理 API 请求，返回 (status_code, content_type, response_body)"""
    if token != get_token():
        return 403, "application/json", json.dumps({"error": "Invalid token"})

    parts = path.strip("/").split("/")
    
    # GET /api/users
    if len(parts) == 1 and parts[0] == "users":
        users = load_users()
        return 200, "application/json", json.dumps({"users": users})
    
    # POST /api/users
    if len(parts) == 1 and parts[0] == "users":
        return 200, "application/json", json.dumps({"error": "Use POST to add user"})
    
    # GET /api/links/<username>
    if len(parts) == 2 and parts[0] == "links":
        username = parts[1]
        config = load_config()
        user = get_user(username)
        if not user:
            return 404, "application/json", json.dumps({"error": "User not found"})
        links = gen_all_links(config, user)
        return 200, "application/json", json.dumps({
            "user": username,
            "links": [{"label": label, "link": link} for label, link in links]
        })
    
    # DELETE /api/users/<username>
    if len(parts) == 2 and parts[0] == "users":
        username = parts[1]
        try:
            remove_user(username)
            return 200, "application/json", json.dumps({"ok": True})
        except ValueError as e:
            return 400, "application/json", json.dumps({"error": str(e)})
    
    # GET /api/status
    if len(parts) == 1 and parts[0] == "status":
        import subprocess
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "sing-box"],
                capture_output=True, text=True, timeout=5
            )
            running = result.stdout.strip() == "active"
        except:
            running = False
        
        try:
            result = subprocess.run(
                ["/etc/s-box-sn/sing-box", "version"],
                capture_output=True, text=True, timeout=5
            )
            version = result.stdout.strip().split("\n")[0] if result.stdout else "-"
        except:
            version = "-"
        
        return 200, "application/json", json.dumps({
            "running": running,
            "version": version
        })
    
    return 404, "application/json", json.dumps({"error": "Not found"})


def handle_post_api(path, token, body):
    """处理 POST API 请求"""
    if token != get_token():
        return 403, "application/json", json.dumps({"error": "Invalid token"})
    
    parts = path.strip("/").split("/")
    
    # POST /api/users
    if len(parts) == 1 and parts[0] == "users":
        try:
            data = json.loads(body) if body else {}
            name = data.get("name", "").strip()
            if not name:
                return 400, "application/json", json.dumps({"error": "Username required"})
            user = add_user(name)
            
            # 重建配置并重启服务
            from .protocols import build_server_config
            from .config import save_sb_config
            from .service import restart
            config = load_config()
            sb = build_server_config(config, {"users": load_users()})
            save_sb_config(sb)
            restart()
            
            return 200, "application/json", json.dumps({"ok": True, "user": user})
        except ValueError as e:
            return 400, "application/json", json.dumps({"error": str(e)})
        except Exception as e:
            return 500, "application/json", json.dumps({"error": str(e)})
    
    return 404, "application/json", json.dumps({"error": "Not found"})
