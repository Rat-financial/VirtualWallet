import json
import os
import uuid
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# ==========================================
# 資料存取層 (Data Access Layer)
# ==========================================
DB_FILE = 'wallet_data.json'

def load_data():
    # 預設資料結構
    default_data = {
        "users": {
            "admin": {
                "password": "admin", 
                "name": "系統管理員", 
                "balance": 0, 
                "role": "admin",
                "user_type": True,
                "kyc_status": True, 
                "kyc_info": "Admin"
            }
        },
        "transactions": [],
        "pending_deposits": [],
        "announcements": [] 
    }

    if not os.path.exists(DB_FILE):
        save_data(default_data)
        return default_data
    
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
            # 資料結構遷移檢查
            if "announcements" not in data: data["announcements"] = []
            for u in data["users"].values():
                if "kyc_status" not in u: u["kyc_status"] = False
                if "kyc_info" not in u: u["kyc_info"] = None
            return data
        except:
            return default_data

def save_data(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ==========================================
# 業務邏輯類別
# ==========================================

class DigitalWalletSystem:
    def register_user(self, username, password, name):
        data = load_data()
        if username in data['users']:
            return False, "帳號已存在"
        
        data['users'][username] = {
            "password": password,
            "name": name,
            "balance": 0,
            "role": "user",
            "user_type": False,
            "kyc_status": False, 
            "kyc_info": None
        }
        save_data(data)
        return True, "註冊成功"

    def login(self, username, password):
        data = load_data()
        user = data['users'].get(username)
        if user and user['password'] == password:
            return user
        return None

    def request_deposit(self, username, amount):
        data = load_data()
        request_id = str(uuid.uuid4())[:8]
        deposit_req = {
            "req_id": request_id,
            "username": username,
            "amount": int(amount),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "pending"
        }
        data['pending_deposits'].append(deposit_req)
        save_data(data)
        return True

    def transfer(self, sender_username, receiver_username, amount):
        try:
            amount = int(amount)
        except ValueError:
            return False, "金額格式錯誤"

        data = load_data()
        sender = data['users'].get(sender_username)
        receiver = data['users'].get(receiver_username)

        if sender_username == receiver_username:
            return False, "無法轉帳給自己"

        if not receiver:
            return False, "接收者帳號不存在"

        if sender.get('kyc_status') is not True:
            return False, "您的帳號尚未通過 KYC 認證，無法轉帳"

        if sender['balance'] < amount:
            return False, "餘額不足"
        if amount <= 0:
            return False, "金額必須大於 0"

        sender['balance'] -= amount
        receiver['balance'] += amount

        tx_record = {
            "tx_id": str(uuid.uuid4())[:12],
            "sender": sender_username,
            "receiver": receiver_username,
            "amount": amount,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": True
        }
        data['transactions'].append(tx_record)
        save_data(data)
        return True, "轉帳成功"

    def approve_deposit(self, req_id):
        data = load_data()
        target_req = None
        for req in data['pending_deposits']:
            if req['req_id'] == req_id:
                target_req = req
                break
        
        if target_req:
            user = data['users'].get(target_req['username'])
            if user:
                user['balance'] += target_req['amount']
                data['pending_deposits'].remove(target_req)
                tx_record = {
                    "tx_id": f"DEP-{target_req['req_id']}",
                    "sender": "System(Bank)",
                    "receiver": target_req['username'],
                    "amount": target_req['amount'],
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": True
                }
                data['transactions'].append(tx_record)
                save_data(data)
                return True
        return False

    def submit_kyc(self, username, id_number):
        data = load_data()
        user = data['users'].get(username)
        if user:
            user['kyc_status'] = "pending"
            user['kyc_info'] = id_number
            save_data(data)
            return True
        return False

    def approve_kyc(self, username, action):
        data = load_data()
        user = data['users'].get(username)
        if user and user['kyc_status'] == "pending":
            if action == 'approve':
                user['kyc_status'] = True
            else:
                user['kyc_status'] = False 
                user['kyc_info'] = None
            save_data(data)
            return True
        return False

    def admin_reset_password(self, username, new_password):
        data = load_data()
        user = data['users'].get(username)
        if user:
            user['password'] = new_password
            save_data(data)
            return True
        return False

    def add_announcement(self, content):
        data = load_data()
        announcement = {
            "id": str(uuid.uuid4())[:6],
            "content": content,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        data['announcements'].insert(0, announcement)
        save_data(data)
        return True

    def delete_announcement(self, ann_id):
        """刪除指定的公告"""
        data = load_data()
        # 保留 ID 不符合的公告 (即刪除符合 ID 的)
        original_count = len(data['announcements'])
        data['announcements'] = [a for a in data['announcements'] if a['id'] != ann_id]
        
        if len(data['announcements']) < original_count:
            save_data(data)
            return True
        return False

system = DigitalWalletSystem()

# ==========================================
# 前端 HTML 模板
# ==========================================

HTML_HEADER = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>數位錢包系統</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #f8f9fa; }
        .card { box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .navbar { margin-bottom: 30px; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="#">💰 數位錢包</a>
            <div class="d-flex">
                {% if session.get('user') %}
                    <span class="navbar-text text-white me-3">你好, {{ session['user'] }}</span>
                    <a href="/logout" class="btn btn-outline-light btn-sm">登出</a>
                {% endif %}
            </div>
        </div>
    </nav>
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="alert alert-{{ category }}">{{ message }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}
"""

HTML_FOOTER = """
    </div>
</body>
</html>
"""

LOGIN_CONTENT = """
<div class="row justify-content-center">
    <div class="col-md-5">
        <div class="card">
            <div class="card-header bg-white text-center"><h4>系統登入</h4></div>
            <div class="card-body">
                <form action="/login" method="post">
                    <div class="mb-3"><label>帳號</label><input type="text" name="username" class="form-control" required></div>
                    <div class="mb-3"><label>密碼</label><input type="password" name="password" class="form-control" required></div>
                    <button type="submit" class="btn btn-primary w-100">登入</button>
                </form>
            </div>
        </div>
        <div class="card mt-3">
            <div class="card-header bg-white text-center"><h4>註冊新帳號</h4></div>
            <div class="card-body">
                <form action="/register" method="post">
                    <div class="mb-3"><label>設定帳號</label><input type="text" name="username" class="form-control" required></div>
                    <div class="mb-3"><label>設定密碼</label><input type="password" name="password" class="form-control" required></div>
                    <div class="mb-3"><label>姓名</label><input type="text" name="name" class="form-control" required></div>
                    <button type="submit" class="btn btn-success w-100">註冊</button>
                </form>
            </div>
        </div>
    </div>
</div>
"""

USER_DASHBOARD_CONTENT = """
<div class="row">
    <div class="col-12 mb-3">
        <div class="card border-info">
            <div class="card-header bg-info text-white">📢 系統公告</div>
            <ul class="list-group list-group-flush">
                {% if announcements %}
                    {% for ann in announcements[:3] %}
                        <li class="list-group-item">
                            <small class="text-muted">[{{ ann.time }}]</small> {{ ann.content }}
                        </li>
                    {% endfor %}
                {% else %}
                    <li class="list-group-item text-muted">目前沒有公告</li>
                {% endif %}
            </ul>
        </div>
    </div>

    <div class="col-md-4">
        <div class="card bg-primary text-white">
            <div class="card-body">
                <h5 class="card-title">我的錢包</h5>
                <h2 class="display-6">${{ user_info.balance }}</h2>
                <p>帳號: {{ user_info.name }}</p>
                <p>
                    KYC 認證: 
                    {% if user_info.kyc_status == True %}
                        <span class="badge bg-success">已認證 ✅</span>
                    {% elif user_info.kyc_status == 'pending' %}
                        <span class="badge bg-warning text-dark">審核中 ⏳</span>
                    {% else %}
                        <span class="badge bg-danger">未認證 ❌</span>
                    {% endif %}
                </p>
            </div>
        </div>

        {% if user_info.kyc_status == False %}
        <div class="card border-danger">
            <div class="card-header">實名認證 (KYC)</div>
            <div class="card-body">
                <form action="/submit_kyc" method="post">
                    <div class="mb-2">
                        <label>身分證字號 / 證件號碼</label>
                        <input type="text" name="id_number" class="form-control" required>
                    </div>
                    <button class="btn btn-danger w-100" type="submit">提交審核</button>
                </form>
            </div>
        </div>
        {% endif %}

        <div class="card">
            <div class="card-header">申請儲值</div>
            <div class="card-body">
                <form action="/deposit" method="post">
                    <div class="input-group mb-3">
                        <span class="input-group-text">$</span>
                        <input type="number" name="amount" class="form-control" placeholder="金額" required min="1">
                        <button class="btn btn-success" type="submit">申請</button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <div class="col-md-8">
        <div class="card">
            <div class="card-header">轉帳給他人</div>
            <div class="card-body">
                {% if user_info.kyc_status != True %}
                    <div class="alert alert-warning">⚠️ 必須通過 KYC 認證才能使用轉帳功能</div>
                {% endif %}
                <form action="/transfer" method="post" class="row g-3">
                    <div class="col-md-5"><input type="text" name="receiver" class="form-control" placeholder="接收者帳號" required></div>
                    <div class="col-md-4"><input type="number" name="amount" class="form-control" placeholder="金額" required min="1"></div>
                    <div class="col-md-3"><button type="submit" class="btn btn-warning w-100" {% if user_info.kyc_status != True %}disabled{% endif %}>轉帳</button></div>
                </form>
            </div>
        </div>

        <div class="card">
            <div class="card-header">交易紀錄</div>
            <div class="card-body">
                <table class="table table-striped">
                    <thead><tr><th>時間</th><th>類型/對象</th><th>金額</th></tr></thead>
                    <tbody>
                        {% for tx in transactions %}
                        <tr>
                            <td>{{ tx.time }}</td>
                            <td>
                                {% if tx.sender == session['user'] %}
                                    <span class="badge bg-danger">轉出</span> -> {{ tx.receiver }}
                                {% else %}
                                    <span class="badge bg-success">收到</span> <- {{ tx.sender }}
                                {% endif %}
                            </td>
                            <td class="{{ 'text-danger' if tx.sender == session['user'] else 'text-success' }}">
                                {{ '-' if tx.sender == session['user'] else '+' }}{{ tx.amount }}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>
"""

ADMIN_DASHBOARD_CONTENT = """
<div class="row">
    <div class="col-12"><h2 class="mb-4">管理員後台</h2></div>

    <div class="col-md-12 mb-4">
        <div class="card border-primary">
            <div class="card-header bg-primary text-white">📢 系統公告管理</div>
            <div class="card-body">
                <form action="/admin/announcement" method="post" class="d-flex gap-2 mb-3">
                    <input type="text" name="content" class="form-control" placeholder="輸入公告內容..." required>
                    <button type="submit" class="btn btn-primary">發送</button>
                </form>
                
                <h6>現有公告：</h6>
                <ul class="list-group">
                    {% if announcements %}
                        {% for ann in announcements %}
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            <span>
                                <small class="text-muted">[{{ ann.time }}]</small>
                                {{ ann.content }}
                            </span>
                            <a href="/admin/announcement/delete/{{ ann.id }}" class="btn btn-sm btn-outline-danger" onclick="return confirm('確定要刪除這則公告嗎？')">刪除</a>
                        </li>
                        {% endfor %}
                    {% else %}
                        <li class="list-group-item text-muted">無公告</li>
                    {% endif %}
                </ul>
            </div>
        </div>
    </div>

    <div class="col-md-6">
        <div class="card border-danger">
            <div class="card-header bg-danger text-white"><strong>待審核 KYC 申請</strong></div>
            <div class="card-body">
                {% set kyc_pending = [] %}
                {% for uid, u in all_users.items() %}
                    {% if u.kyc_status == 'pending' %}{% set _ = kyc_pending.append({'uid': uid, 'info': u.kyc_info}) %}{% endif %}
                {% endfor %}

                {% if not kyc_pending %}
                    <p class="text-muted">無待審核 KYC。</p>
                {% else %}
                    <table class="table">
                        <thead><tr><th>用戶</th><th>證件資料</th><th>操作</th></tr></thead>
                        <tbody>
                            {% for item in kyc_pending %}
                            <tr>
                                <td>{{ item.uid }}</td>
                                <td>{{ item.info }}</td>
                                <td>
                                    <a href="/admin/kyc/approve/{{ item.uid }}" class="btn btn-sm btn-success">V</a>
                                    <a href="/admin/kyc/reject/{{ item.uid }}" class="btn btn-sm btn-outline-danger">X</a>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                {% endif %}
            </div>
        </div>
    </div>

    <div class="col-md-6">
        <div class="card border-warning">
            <div class="card-header bg-warning text-dark"><strong>待審核儲值申請</strong></div>
            <div class="card-body">
                {% if not pending_deposits %}
                    <p class="text-muted">無待審核儲值。</p>
                {% else %}
                    <table class="table">
                        <thead><tr><th>用戶</th><th>金額</th><th>操作</th></tr></thead>
                        <tbody>
                            {% for req in pending_deposits %}
                            <tr>
                                <td>{{ req.username }}</td>
                                <td>${{ req.amount }}</td>
                                <td><a href="/admin/deposit/approve/{{ req.req_id }}" class="btn btn-sm btn-success">批准</a></td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                {% endif %}
            </div>
        </div>
    </div>

    <div class="col-12 mt-4">
        <div class="card border-info">
            <div class="card-header bg-info text-white"><strong>用戶管理 & 密碼重設</strong></div>
            <div class="card-body">
                <table class="table table-sm align-middle">
                    <thead><tr><th>帳號</th><th>姓名</th><th>餘額</th><th>KYC</th><th>重設密碼</th></tr></thead>
                    <tbody>
                        {% for uid, udata in all_users.items() %}
                        {% if udata.role != 'admin' %}
                        <tr>
                            <td>{{ uid }}</td>
                            <td>{{ udata.name }}</td>
                            <td>${{ udata.balance }}</td>
                            <td>
                                {% if udata.kyc_status == True %} <span class="text-success">已認證</span>
                                {% elif udata.kyc_status == 'pending' %} <span class="text-warning">審核中</span>
                                {% else %} <span class="text-danger">未認證</span> {% endif %}
                            </td>
                            <td>
                                <form action="/admin/reset_password" method="post" class="d-flex gap-1">
                                    <input type="hidden" name="target_user" value="{{ uid }}">
                                    <input type="text" name="new_password" class="form-control form-control-sm" placeholder="新密碼" style="width: 120px;" required>
                                    <button type="submit" class="btn btn-sm btn-outline-secondary">重設</button>
                                </form>
                            </td>
                        </tr>
                        {% endif %}
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>
"""

PAGE_LOGIN = HTML_HEADER + LOGIN_CONTENT + HTML_FOOTER
PAGE_USER = HTML_HEADER + USER_DASHBOARD_CONTENT + HTML_FOOTER
PAGE_ADMIN = HTML_HEADER + ADMIN_DASHBOARD_CONTENT + HTML_FOOTER

# ==========================================
# Flask 路由設定
# ==========================================

@app.route('/')
def index():
    if 'user' in session:
        return redirect('/admin') if session.get('role') == 'admin' else redirect('/dashboard')
    return render_template_string(PAGE_LOGIN)

@app.route('/login', methods=['POST'])
def login():
    user = system.login(request.form.get('username'), request.form.get('password'))
    if user:
        session['user'] = request.form.get('username')
        session['role'] = user['role']
        return redirect('/admin') if user['role'] == 'admin' else redirect('/dashboard')
    flash('帳號或密碼錯誤', 'danger')
    return redirect('/')

@app.route('/register', methods=['POST'])
def register():
    success, msg = system.register_user(request.form.get('username'), request.form.get('password'), request.form.get('name'))
    flash('註冊成功' if success else msg, 'success' if success else 'danger')
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# --- 用戶功能 ---
@app.route('/dashboard')
def dashboard():
    if 'user' not in session or session['role'] == 'admin': return redirect('/')
    data = load_data()
    user_info = data['users'].get(session['user'])
    if not user_info: session.clear(); return redirect('/')
    
    user_txs = [tx for tx in data['transactions'] if tx['sender'] == session['user'] or tx['receiver'] == session['user']]
    return render_template_string(PAGE_USER, user_info=user_info, transactions=reversed(user_txs), announcements=data['announcements'])

@app.route('/deposit', methods=['POST'])
def deposit():
    if 'user' in session: system.request_deposit(session['user'], request.form.get('amount'))
    flash('儲值申請已送出', 'info')
    return redirect('/dashboard')

@app.route('/transfer', methods=['POST'])
def transfer():
    if 'user' in session:
        success, msg = system.transfer(session['user'], request.form.get('receiver'), request.form.get('amount'))
        flash(msg, 'success' if success else 'danger')
    return redirect('/dashboard')

@app.route('/submit_kyc', methods=['POST'])
def submit_kyc():
    if 'user' in session:
        system.submit_kyc(session['user'], request.form.get('id_number'))
        flash('KYC 資料已提交，請等待審核', 'success')
    return redirect('/dashboard')

# --- 管理員功能 ---
@app.route('/admin')
def admin_panel():
    if session.get('role') != 'admin': return redirect('/')
    data = load_data()
    return render_template_string(PAGE_ADMIN, pending_deposits=data['pending_deposits'], all_users=data['users'], announcements=data['announcements'])

@app.route('/admin/deposit/approve/<req_id>')
def admin_approve_deposit(req_id):
    if session.get('role') == 'admin' and system.approve_deposit(req_id): flash('已批准儲值', 'success')
    return redirect('/admin')

@app.route('/admin/kyc/approve/<username>')
def admin_approve_kyc(username):
    if session.get('role') == 'admin':
        system.approve_kyc(username, 'approve')
        flash(f'已通過 {username} 的 KYC', 'success')
    return redirect('/admin')

@app.route('/admin/kyc/reject/<username>')
def admin_reject_kyc(username):
    if session.get('role') == 'admin':
        system.approve_kyc(username, 'reject')
        flash(f'已駁回 {username} 的 KYC', 'warning')
    return redirect('/admin')

@app.route('/admin/reset_password', methods=['POST'])
def admin_reset_password():
    if session.get('role') == 'admin':
        target = request.form.get('target_user')
        new_pw = request.form.get('new_password')
        system.admin_reset_password(target, new_pw)
        flash(f'已重設 {target} 的密碼', 'success')
    return redirect('/admin')

@app.route('/admin/announcement', methods=['POST'])
def admin_announcement():
    if session.get('role') == 'admin':
        system.add_announcement(request.form.get('content'))
        flash('公告發送成功', 'success')
    return redirect('/admin')

# 新增：刪除公告路由
@app.route('/admin/announcement/delete/<ann_id>')
def admin_delete_announcement(ann_id):
    if session.get('role') == 'admin':
        if system.delete_announcement(ann_id):
            flash('公告已刪除', 'success')
        else:
            flash('刪除失敗', 'danger')
    return redirect('/admin')

if __name__ == '__main__':
    load_data()
    print("系統啟動: http://127.0.0.1:5000")
    app.run(debug=False, port=5000)