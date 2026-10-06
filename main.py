from fastapi import FastAPI, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Template
import psycopg2
from datetime import datetime

app = FastAPI(title="Lotto ERP Cloud Web")

# ⚠️ อย่าลืมเปลี่ยน [YOUR-PASSWORD] เป็นรหัสผ่านฐานข้อมูล Supabase ของคุณ
DB_URI = "postgresql://postgres.mpyswshlrxwpirzdexrn:Clublifekorat3888@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres"

def connect_db():
    return psycopg2.connect(DB_URI)

# หน้าจอ Login
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Lotto ERP Cloud</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-dark text-light d-flex align-items-center justify-content-center" style="height: 100vh;">
    <div class="card bg-secondary p-4 shadow" style="width: 350px;">
        <h3 class="text-center text-warning mb-4">☁️ Lotto ERP Cloud</h3>
        {% if error %}
            <div class="alert alert-danger py-2 text-center">{{ error }}</div>
        {% endif %}
        <form method="POST" action="/login">
            <div class="mb-3">
                <label class="form-label">ชื่อผู้ใช้งาน (Username)</label>
                <input type="text" name="username" class="form-control" required autofocus>
            </div>
            <div class="mb-3">
                <label class="form-label">รหัสผ่าน (Password)</label>
                <input type="password" name="password" class="form-control" required>
            </div>
            <button type="submit" class="btn btn-warning w-100 fw-bold">เข้าสู่ระบบ</button>
        </form>
    </div>
</body>
</html>
"""

# หน้าจอบันทึกโพย
BUY_TEMPLATE = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>บันทึกโพย - Lotto ERP</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <nav class="navbar navbar-dark bg-dark px-3">
        <span class="navbar-brand mb-0 h1">🛒 บันทึกโพย | ผู้ใช้: {{ username }}</span>
        <a href="/logout" class="btn btn-outline-danger btn-sm">ออกจากระบบ</a>
    </nav>

    <div class="container my-4">
        <div class="card shadow p-4 mb-4">
            <form method="POST" action="/submit-buy">
                <input type="hidden" name="user" value="{{ username }}">
                <div class="mb-3">
                    <label class="form-label fw-bold">เลือกลูกค้า / สายงาน:</label>
                    <select name="customer_info" class="form-select" required>
                        {% for c in customers %}
                            <option value="{{ c[0] }}|{{ c[1] }}|{{ c[2] }}">{{ c[1] }} ({{ c[2] }})</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="mb-3">
                    <label class="form-label fw-bold">คีย์รายการ (เช่น 123=100*100, 456=50):</label>
                    <input type="text" name="raw_input" class="form-control form-control-lg" placeholder="พิมพ์เลขและราคา..." required>
                    <div class="form-text text-danger">*ห้ามใส่ลูกน้ำในยอดเงิน เช่น 1000 ห้ามพิมพ์ 1,000</div>
                </div>
                <button type="submit" class="btn btn-success btn-lg w-100 fw-bold">📥 บันทึกลงรายการร่าง</button>
            </form>
        </div>

        <div class="card shadow p-4">
            <h4 class="text-primary mb-3">📋 รายการร่าง (รอยืนยัน)</h4>
            <table class="table table-striped table-bordered text-center">
                <thead class="table-dark">
                    <tr>
                        <th>เลข</th>
                        <th>บน</th>
                        <th>ล่าง</th>
                        <th>ประเภท</th>
                    </tr>
                </thead>
                <tbody>
                    {% for d in drafts %}
                    <tr>
                        <td>{{ d[1] }}</td>
                        <td>{{ d[2] if d[2] > 0 else '-' }}</td>
                        <td>{{ d[3] if d[3] > 0 else '-' }}</td>
                        <td>{{ d[4] }}</td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="4" class="text-muted">ยังไม่มีรายการในร่าง</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def index():
    return RedirectResponse(url="/login")

@app.get("/login", response_class=HTMLResponse)
def login_page(error: str = None):
    return Template(LOGIN_TEMPLATE).render(error=error)

@app.post("/login")
def login_action(username: str = Form(...), password: str = Form(...)):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("SELECT role FROM Users WHERE username=%s AND password=%s", (username, password))
        res = c.fetchone()
        conn.close()
        if res:
            return RedirectResponse(url=f"/buy?user={username}", status_code=status.HTTP_303_SEE_OTHER)
        else:
            return Template(LOGIN_TEMPLATE).render(error="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง!")
    except Exception as e:
        return Template(LOGIN_TEMPLATE).render(error=f"เกิดข้อผิดพลาด: {str(e)}")

@app.get("/buy", response_class=HTMLResponse)
def buy_page(user: str):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("SELECT id, name, 'Customer' FROM Customers WHERE owner_username=%s", (user,))
        custs = c.fetchall()
        c.execute("SELECT id, username, 'User' FROM Users WHERE parent_user=%s", (user,))
        agents = c.fetchall()
        all_targets = custs + agents
        
        c.execute("SELECT id, num, amt_teng, amt_tod, type FROM TempDraft WHERE username=%s", (user,))
        drafts = c.fetchall()
        conn.close()

        return Template(BUY_TEMPLATE).render(username=user, customers=all_targets, drafts=drafts)
    except Exception as e:
        return f"System Error: {str(e)}"

@app.post("/submit-buy")
def submit_buy(user: str = Form(...), customer_info: str = Form(...), raw_input: str = Form(...)):
    parts = customer_info.split('|')
    c_id, c_name, c_type = parts[0], parts[1], parts[2]
    
    raw_input = raw_input.strip().upper().replace(' ', '').replace('X', '*').replace('+', '*').replace('/', '*')
    blocks = raw_input.split(',')
    
    try:
        conn = connect_db()
        c = conn.cursor()
        hold_nums = []
        for block in blocks:
            if not block: continue
            if '=' in block:
                num_str, amt_str = block.split('=')[0].strip(), block.split('=')[1].strip()
                if num_str: hold_nums.append(num_str)
                if '*' in amt_str:
                    ap = amt_str.split('*')
                    top, bot = float(ap[0] or 0), float(ap[1] or 0)
                else:
                    top, bot = float(amt_str or 0), 0.0
                
                for n in hold_nums:
                    if len(n) == 3:
                        if top > 0: c.execute("INSERT INTO TempDraft (username, customer_id, customer_type, num, amt_teng, type) VALUES (%s,%s,%s,%s,%s,%s)", (user, c_id, c_type, n, top, "3ตัวตรง"))
                        if bot > 0: c.execute("INSERT INTO TempDraft (username, customer_id, customer_type, num, amt_tod, type) VALUES (%s,%s,%s,%s,%s,%s)", (user, c_id, c_type, n, bot, "3ตัวโต๊ด"))
                    elif len(n) == 2:
                        if top > 0: c.execute("INSERT INTO TempDraft (username, customer_id, customer_type, num, amt_teng, type) VALUES (%s,%s,%s,%s,%s,%s)", (user, c_id, c_type, n, top, "2ตัวบน"))
                        if bot > 0: c.execute("INSERT INTO TempDraft (username, customer_id, customer_type, num, amt_tod, type) VALUES (%s,%s,%s,%s,%s,%s)", (user, c_id, c_type, n, bot, "2ตัวล่าง"))
                hold_nums = []
            else:
                hold_nums.append(block.strip())
        conn.commit()
        conn.close()
    except Exception as e:
        print("Error:", e)

    return RedirectResponse(url=f"/buy?user={user}", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/logout")
def logout():
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)