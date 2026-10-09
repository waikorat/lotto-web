from fastapi import FastAPI, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Template
import psycopg2
from datetime import datetime
import itertools

app = FastAPI(title="Lotto ERP Full Enterprise Cloud")

DB_URI = "postgresql://postgres.mpyswshlrxwpirzdexrn:Clublifekorat3888@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres"

def connect_db():
    return psycopg2.connect(DB_URI)

@app.on_event("startup")
def startup_db():
    try:
        conn = connect_db()
        c = conn.cursor()
        
        c.execute("""
            CREATE TABLE IF NOT EXISTS Customers (
                id SERIAL PRIMARY KEY,
                name TEXT,
                owner_username TEXT,
                discount_type INTEGER DEFAULT 1,
                disc_total NUMERIC DEFAULT 0,
                disc_3d NUMERIC DEFAULT 0,
                disc_2d NUMERIC DEFAULT 0,
                pay_3d NUMERIC DEFAULT 500,
                pay_3tod NUMERIC DEFAULT 100,
                pay_2d NUMERIC DEFAULT 70
            );
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS LotteryCampaigns (
                id SERIAL PRIMARY KEY,
                lotto_name TEXT,
                draw_date TEXT,
                status TEXT DEFAULT 'Active'
            );
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS BlockedNumbers (
                id SERIAL PRIMARY KEY,
                draw_date TEXT,
                raw_num TEXT,
                status TEXT,
                type TEXT
            );
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS TempDraft (
                id SERIAL PRIMARY KEY,
                username TEXT,
                customer_id TEXT,
                customer_type TEXT,
                num TEXT,
                amt_teng NUMERIC DEFAULT 0,
                amt_tod NUMERIC DEFAULT 0,
                type TEXT,
                payout_rate NUMERIC DEFAULT 0,
                discount NUMERIC DEFAULT 0,
                net NUMERIC DEFAULT 0,
                status TEXT DEFAULT 'ปกติ'
            );
        """)
        conn.commit()

        migrations = [
            "ALTER TABLE TempDraft ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'ปกติ';",
            "ALTER TABLE TempDraft ADD COLUMN IF NOT EXISTS amt_teng NUMERIC DEFAULT 0;",
            "ALTER TABLE TempDraft ADD COLUMN IF NOT EXISTS amt_tod NUMERIC DEFAULT 0;",
            "ALTER TABLE TempDraft ADD COLUMN IF NOT EXISTS payout_rate NUMERIC DEFAULT 0;",
            "ALTER TABLE TempDraft ADD COLUMN IF NOT EXISTS discount NUMERIC DEFAULT 0;",
            "ALTER TABLE TempDraft ADD COLUMN IF NOT EXISTS net NUMERIC DEFAULT 0;",
            "ALTER TABLE Customers ADD COLUMN IF NOT EXISTS disc_3d NUMERIC DEFAULT 0;",
            "ALTER TABLE Customers ADD COLUMN IF NOT EXISTS disc_2d NUMERIC DEFAULT 0;",
            "ALTER TABLE Customers ADD COLUMN IF NOT EXISTS disc_total NUMERIC DEFAULT 0;",
            "ALTER TABLE Users ADD COLUMN IF NOT EXISTS disc_total NUMERIC DEFAULT 0;",
            "ALTER TABLE Users ADD COLUMN IF NOT EXISTS disc_3d NUMERIC DEFAULT 0;",
            "ALTER TABLE Users ADD COLUMN IF NOT EXISTS disc_2d NUMERIC DEFAULT 0;",
            "ALTER TABLE Users ADD COLUMN IF NOT EXISTS pay_3d NUMERIC DEFAULT 500;",
            "ALTER TABLE Users ADD COLUMN IF NOT EXISTS pay_3tod NUMERIC DEFAULT 100;",
            "ALTER TABLE Users ADD COLUMN IF NOT EXISTS pay_2d NUMERIC DEFAULT 70;"
        ]
        for mig in migrations:
            try:
                c.execute(mig)
                conn.commit()
            except Exception as m_err:
                conn.rollback()
                print("Migration note:", m_err)

        c.execute("""
            CREATE TABLE IF NOT EXISTS Transactions (
                id SERIAL PRIMARY KEY,
                draw_date TEXT,
                timestamp TEXT,
                username TEXT,
                customer_id INTEGER,
                customer_name TEXT,
                customer_type TEXT,
                bill_no TEXT,
                num TEXT,
                type TEXT,
                amount NUMERIC DEFAULT 0,
                status TEXT,
                discount NUMERIC DEFAULT 0,
                net NUMERIC DEFAULT 0,
                payout_rate NUMERIC DEFAULT 0
            );
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS DrawResults (
                id SERIAL PRIMARY KEY,
                draw_date TEXT UNIQUE,
                prize_1 TEXT,
                bottom_2 TEXT
            );
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print("Startup DB Init Warning:", e)

# ================= Master Layout Template =================

LAYOUT = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lotto ERP - ระบบบริหารจัดการหวย</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { background-color: #f0f2f5; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; overflow-x: hidden; }
        .top-navbar { background-color: #1a1a1a; color: white; padding: 8px 15px; display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #ffc107; }
        .top-nav-links { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
        .top-nav-links a { background-color: #ffc107; color: #000; font-weight: bold; padding: 5px 12px; border-radius: 4px; text-decoration: none; font-size: 0.9rem; transition: 0.2s; }
        .top-nav-links a:hover { background-color: #e0a800; }
        .ticker-banner { background-color: #dc3545; color: white; text-align: center; padding: 6px; font-weight: bold; font-size: 0.95rem; }
        .main-wrapper { display: flex; min-height: calc(100vh - 100px); }
        .sidebar { width: 260px; background-color: #1a1a1a; color: white; border-right: 2px solid #ffc107; padding: 15px 10px; flex-shrink: 0; }
        .user-profile-box { background-color: #2b2b2b; border: 1px solid #ffc107; border-radius: 6px; text-align: center; padding: 12px; margin-bottom: 20px; }
        .sidebar-section-title { color: #ffc107; font-weight: bold; font-size: 0.95rem; margin-top: 15px; margin-bottom: 8px; border-bottom: 1px solid #444; padding-bottom: 4px; }
        .sidebar-menu-item { display: block; color: #fff; text-decoration: none; padding: 6px 10px; border-radius: 4px; font-size: 0.9rem; margin-bottom: 3px; }
        .sidebar-menu-item:hover { background-color: #333; color: #ffc107; }
        .content-area { flex-grow: 1; background-color: #ffffff; padding: 20px; box-shadow: inset 0 0 10px rgba(0,0,0,0.05); }
    </style>
    <script>
        function updateClock() {
            const now = new Date();
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            const seconds = String(now.getSeconds()).padStart(2, '0');
            const day = String(now.getDate()).padStart(2, '0');
            const month = String(now.getMonth() + 1).padStart(2, '0');
            const year = now.getFullYear();
            document.getElementById('live-clock').innerText = `${day}/${month}/${year} ${hours}:${minutes}:${seconds}`;
        }
        setInterval(updateClock, 1000);
        window.onload = updateClock;
    </script>
</head>
<body>
    <div class="top-navbar">
        <div class="fw-bold fs-5 text-warning">
            Lotto ERP | งวด: <span class="text-white">{{ draw_date }}</span> | User: <b>{{ username }} ({{ role }})</b>
        </div>
        <div class="top-nav-links">
            <a href="/dashboard?user={{ username }}&draw={{ draw_date }}">📊 แดชบอร์ด</a>
            <a href="/buy?user={{ username }}&draw={{ draw_date }}">🛒 บันทึกโพย</a>
            {% if role == 'Admin' %}
            <a href="/audit-all?user={{ username }}&draw={{ draw_date }}">🔍 ตรวจสอบการซื้อทั้งหมด</a>
            <a href="/results?user={{ username }}&draw={{ draw_date }}">🏆 ออกผลรางวัล</a>
            <a href="/db-inspector?user={{ username }}&draw={{ draw_date }}">🗄️ ตรวจสอบฐานข้อมูล</a>
            {% endif %}
            <a href="/password?user={{ username }}&draw={{ draw_date }}">⚙ ตั้งค่าเริ่มต้น</a>
            <a href="/customers?user={{ username }}&draw={{ draw_date }}">👥 จัดการลูกค้า</a>
        </div>
        <div class="d-flex align-items-center gap-3">
            <span id="live-clock" class="text-info fw-bold font-monospace">กำลังโหลด...</span>
            <a href="/logout" class="btn btn-danger btn-sm fw-bold px-3">🚪 ออกจากระบบ</a>
        </div>
    </div>

    <div class="ticker-banner">
        📢 แถบแจ้งข้อมูลข่าวสาร: กำลังเปิดรับแทงงวด หวยรัฐบาล งวด {{ draw_date }}
    </div>

    <div class="main-wrapper">
        <div class="sidebar">
            <div class="user-profile-box">
                <div class="text-warning fw-bold fs-5">👤 ยินดีต้อนรับ</div>
                <div class="text-white fw-bold fs-6 mt-1">{{ username }}</div>
                <div class="text-info small">({{ role }})</div>
            </div>

            <div class="sidebar-section-title">จัดการผู้ใช้</div>
            {% if role == 'Admin' %}
                <a href="/users?user={{ username }}&draw={{ draw_date }}" class="sidebar-menu-item">▶ Master</a>
                <a href="/users?user={{ username }}&draw={{ draw_date }}" class="sidebar-menu-item">▶ เอเย่นต์</a>
                <a href="/users?user={{ username }}&draw={{ draw_date }}" class="sidebar-menu-item">▶ สมาชิก</a>
            {% elif role == 'Master Agent' %}
                <a href="/users?user={{ username }}&draw={{ draw_date }}" class="sidebar-menu-item">▶ เอเย่นต์</a>
                <a href="/users?user={{ username }}&draw={{ draw_date }}" class="sidebar-menu-item">▶ สมาชิก</a>
            {% elif role == 'Agent' %}
                <a href="/users?user={{ username }}&draw={{ draw_date }}" class="sidebar-menu-item">▶ สมาชิก</a>
            {% endif %}

            <div class="sidebar-section-title">แทงหวย</div>
            <a href="/campaigns?user={{ username }}" class="sidebar-menu-item">▶ หวยรัฐบาล</a>
            <a href="/campaigns?user={{ username }}" class="sidebar-menu-item">▶ หวยลาว</a>
            <a href="/campaigns?user={{ username }}" class="sidebar-menu-item">▶ หวยหุ้น</a>
            <a href="/blocked-numbers?user={{ username }}&draw={{ draw_date }}" class="sidebar-menu-item text-warning fw-bold">🚫 จัดการเลขอั้น</a>

            <div class="sidebar-section-title">รายงานและเครื่องมือ</div>
            <a href="/results?user={{ username }}&draw={{ draw_date }}" class="sidebar-menu-item">▶ ชนะ แพ้ (รายละเอียด)</a>
            <a href="/reports?user={{ username }}&draw={{ draw_date }}" class="sidebar-menu-item">▶ เอเย่นต์</a>
            <a href="/reports?user={{ username }}&draw={{ draw_date }}" class="sidebar-menu-item">▶ สมาชิก</a>
            <a href="/audit-discount?user={{ username }}&draw={{ draw_date }}" class="sidebar-menu-item text-warning fw-bold">🔍 ตรวจสอบส่วนลดลูกค้า</a>
            {% if role == 'Admin' %}
            <a href="/db-inspector?user={{ username }}&draw={{ draw_date }}" class="sidebar-menu-item text-info fw-bold">🗄️ ตรวจสอบตารางฐานข้อมูล</a>
            {% endif %}
        </div>

        <div class="content-area">
            {% if msg %}
                <div class="alert alert-success text-center fw-bold">{{ msg }}</div>
            {% endif %}
            {% if error %}
                <div class="alert alert-danger text-center fw-bold" style="font-size: 1.1rem; border: 2px solid #dc3545;">⚠️ {{ error }}</div>
            {% endif %}
            {{ content | safe }}
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Lotto ERP Cloud</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-dark d-flex align-items-center justify-content-center" style="height: 100vh;">
    <div class="card bg-white p-4 shadow border border-warning" style="width: 380px;">
        <h3 class="text-center text-primary mb-4 fw-bold">☁ Lotto ERP Cloud</h3>
        {% if error %}
            <div class="alert alert-danger py-2 text-center">{{ error }}</div>
        {% endif %}
        <form method="POST" action="/login">
            <div class="mb-3">
                <label class="form-label fw-bold text-dark">ชื่อผู้ใช้งาน (Username)</label>
                <input type="text" name="username" class="form-control" required autofocus>
            </div>
            <div class="mb-3">
                <label class="form-label fw-bold text-dark">รหัสผ่าน (Password)</label>
                <input type="password" name="password" class="form-control" required>
            </div>
            <button type="submit" class="btn btn-warning w-100 fw-bold py-2 text-dark">เข้าสู่ระบบ</button>
        </form>
    </div>
</body>
</html>
"""

CAMPAIGN_TEMPLATE = """
<div class="container my-3" style="max-width: 800px;">
    <div class="card bg-white p-4 shadow border">
        <h2 class="text-center text-primary mb-4 fw-bold">📌 จัดการและเลือกงวดหวย</h2>
        {% if role == 'Admin' %}
        <div class="card bg-light p-3 mb-4 border border-primary">
            <h5 class="text-primary mb-3 fw-bold">➕ เปิดงวดหวยใหม่ (Admin)</h5>
            <form method="POST" action="/create-campaign">
                <input type="hidden" name="user" value="{{ username }}">
                <div class="mb-2">
                    <label class="form-label fw-bold text-dark">ชื่อหวย:</label>
                    <input type="text" name="lotto_name" class="form-control" placeholder="เช่น หวยรัฐบาล, หวยลาว" required>
                </div>
                <div class="mb-3">
                    <label class="form-label fw-bold text-dark">งวดวันที่:</label>
                    <input type="text" name="draw_date" class="form-control" placeholder="เช่น 16 ตุลาคม 2026" required>
                </div>
                <button type="submit" class="btn btn-primary w-100 fw-bold">เปิดงวดใหม่</button>
            </form>
        </div>
        {% endif %}
        <h5 class="text-dark mb-3 fw-bold">รายการงวดหวยทั้งหมด</h5>
        <div class="list-group">
            {% for camp in campaigns %}
                <div class="list-group-item list-group-item-light py-3 mb-2 d-flex justify-content-between align-items-center border">
                    <div>
                        <a href="/buy?user={{ username }}&draw={{ camp[0] }} งวด {{ camp[1] }}" class="text-primary text-decoration-none fs-5 fw-bold">
                            🎯 {{ camp[0] }} งวดวันที่ {{ camp[1] }}
                        </a>
                        <div class="small text-muted mt-1">สถานะ: <span class="badge {% if camp[2] == 'Active' %}bg-success{% else %}bg-danger{% endif %}">{{ camp[2] }}</span></div>
                    </div>
                    {% if role == 'Admin' %}
                    <div>
                        <a href="/toggle-campaign?id={{ camp[3] }}&user={{ username }}" class="btn btn-outline-dark btn-sm fw-bold">สลับเปิด/ปิด</a>
                    </div>
                    {% endif %}
                </div>
            {% else %}
                <div class="text-center text-muted py-4">ยังไม่มีงวดหวยในฐานข้อมูล</div>
            {% endfor %}
        </div>
    </div>
</div>
"""

BLOCKED_TEMPLATE = """
<div class="row">
    <div class="col-md-5 mb-4">
        <div class="card shadow p-4">
            {% if edit_blocked %}
                <h4 class="text-warning mb-3 fw-bold">✏️ แก้ไขเลขอั้นประจำงวด</h4>
                <form method="POST" action="/update-blocked">
                    <input type="hidden" name="user" value="{{ username }}">
                    <input type="hidden" name="draw" value="{{ draw_date }}">
                    <input type="hidden" name="blocked_id" value="{{ edit_blocked[0] }}">
                    <div class="mb-3">
                        <label class="form-label fw-bold text-dark">หมายเลขเลขอั้น:</label>
                        <input type="text" name="raw_num" class="form-control" value="{{ edit_blocked[2] }}" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label fw-bold text-dark">สถานะเลขอั้น:</label>
                        <select name="status" class="form-select">
                            <option value="ปิดรับ" {% if edit_blocked[3] == 'ปิดรับ' %}selected{% endif %}>ปิดรับ (ห้ามแทง)</option>
                            <option value="จ่ายครึ่ง" {% if edit_blocked[3] == 'จ่ายครึ่ง' %}selected{% endif %}>จ่ายครึ่ง (เลขอั้นจ่าย 50%)</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label fw-bold text-dark">ประเภท:</label>
                        <select name="type" class="form-select">
                            <option value="3ตัว" {% if edit_blocked[4] == '3ตัว' %}selected{% endif %}>3 ตัว</option>
                            <option value="2ตัว" {% if edit_blocked[4] == '2ตัว' %}selected{% endif %}>2 ตัว</option>
                        </select>
                    </div>
                    <button type="submit" class="btn btn-warning w-100 fw-bold py-2 mb-2">💾 บันทึกการแก้ไข</button>
                    <a href="/blocked-numbers?user={{ username }}&draw={{ draw_date }}" class="btn btn-outline-secondary w-100 fw-bold">ยกเลิก</a>
                </form>
            {% else %}
                <h4 class="text-danger mb-3 fw-bold">🚫 จัดการและนำเข้าเลขอั้นประจำงวด</h4>
                <form method="POST" action="/save-blocked">
                    <input type="hidden" name="user" value="{{ username }}">
                    <input type="hidden" name="draw" value="{{ draw_date }}">
                    <div class="mb-3">
                        <label class="form-label fw-bold text-dark">ข้อมูลดิบเลขอั้น (รองรับคั่นด้วยจุลภาคหรือขึ้นบรรทัดใหม่):</label>
                        <textarea name="raw_input" class="form-control" rows="4" placeholder="เช่น 123, 45, 789" required autofocus></textarea>
                    </div>
                    <div class="mb-3">
                        <label class="form-label fw-bold text-dark">สถานะเลขอั้น:</label>
                        <select name="status" class="form-select">
                            <option value="ปิดรับ">ปิดรับ (ห้ามแทง)</option>
                            <option value="จ่ายครึ่ง">จ่ายครึ่ง (เลขอั้นจ่าย 50% ทุกกลับ/ตัวกลับ)</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label fw-bold text-dark">ประเภท:</label>
                        <select name="type" class="form-select">
                            <option value="3ตัว">3 ตัว (สลับตำแหน่งอัตโนมัติ)</option>
                            <option value="2ตัว">2 ตัว (สลับตำแหน่งอัตโนมัติ)</option>
                        </select>
                    </div>
                    <button type="submit" class="btn btn-danger w-100 fw-bold py-2">💾 ประมวลผลและบันทึกเลขอั้น</button>
                </form>
            {% endif %}
        </div>
    </div>
    <div class="col-md-7">
        <div class="card shadow p-4">
            <h4 class="text-primary mb-3 fw-bold">📋 รายการเลขอั้นงวด: {{ draw_date }}</h4>
            <div class="table-responsive">
                <table class="table table-striped table-bordered text-center align-middle">
                    <thead class="table-dark">
                        <tr><th>ID</th><th>ข้อมูลดิบ (Raw Num)</th><th>สถานะ</th><th>ประเภท</th><th>จัดการแบบเบ็ดเสร็จ</th></tr>
                    </thead>
                    <tbody>
                        {% for b in blocked_list %}
                        <tr>
                            <td>{{ b[0] }}</td>
                            <td><b class="text-danger fs-5">{{ b[2] }}</b></td>
                            <td><span class="badge {% if b[3] == 'ปิดรับ' %}bg-danger{% else %}bg-warning text-dark{% endif %}">{{ b[3] }}</span></td>
                            <td>{{ b[4] }}</td>
                            <td>
                                <a href="/blocked-numbers?user={{ username }}&draw={{ draw_date }}&edit_id={{ b[0] }}" class="btn btn-warning btn-sm fw-bold">✏️ แก้ไข</a>
                                <a href="/delete-blocked?id={{ b[0] }}&user={{ username }}&draw={{ draw_date }}" class="btn btn-outline-danger btn-sm fw-bold" onclick="return confirm('ยืนยันการลบเลขอั้นนี้?')">🗑️ ลบ</a>
                            </td>
                        </tr>
                        {% else %}
                        <tr><td colspan="5" class="text-muted py-3">ยังไม่มีเลขอั้นในงวดนี้</td></tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>
"""

BUY_CONTENT = """
<div class="row">
    <div class="col-lg-8">
        <div class="card shadow p-4 mb-4">
            <form id="custForm" method="POST" action="/submit-buy">
                <input type="hidden" name="user" value="{{ username }}">
                <input type="hidden" name="draw" value="{{ draw_date }}">
                <div class="mb-3">
                    <label class="form-label fw-bold text-dark">เลือกลูกค้า / สายงาน:</label>
                    <select name="customer_info" id="customerSelect" class="form-select form-select-lg" onchange="document.getElementById('custForm').submit()">
                        {% for c in customers %}
                            <option value="{{ c[0] }}|{{ c[1] }}|{{ c[2] }}" {% if selected_target_raw and selected_target_raw == c[0]|string ~ '|' ~ c[1] ~ '|' ~ c[2] %}selected{% endif %}>{{ c[1] }} ({{ c[2] }})</option>
                        {% endfor %}
                    </select>
                </div>
            </form>

            <form method="POST" action="/add-draft">
                <input type="hidden" name="user" value="{{ username }}">
                <input type="hidden" name="draw" value="{{ draw_date }}">
                <input type="hidden" name="customer_info" id="hiddenCustomerInfo" value="{{ selected_target_raw }}">
                <div class="mb-3">
                    <label class="form-label fw-bold text-dark">คีย์รายการ (เช่น 123=100*100, 456=50 หรือ 12,34=50):</label>
                    <input type="text" name="raw_input" class="form-control form-control-lg" placeholder="พิมพ์เลขและราคา..." required autofocus>
                    <div class="form-text text-danger">*ห้ามใส่ลูกน้ำในยอดเงิน เช่น 1000 ห้ามพิมพ์ 1,000 | อัตราจ่ายห้ามเป็น 0 โดยเด็ดขาด</div>
                </div>
                <button type="submit" class="btn btn-success btn-lg w-100 fw-bold">📥 บันทึกลงรายการร่าง</button>
            </form>
        </div>

        <script>
            document.getElementById('customerSelect').addEventListener('change', function() {
                document.getElementById('hiddenCustomerInfo').value = this.value;
            });
        </script>

        <div class="card shadow p-4 mb-4">
            <h4 class="text-primary mb-3 fw-bold">📋 1. รายการร่าง (รอยืนยันโพย)</h4>
            <div class="table-responsive">
                <table class="table table-striped table-bordered text-center align-middle">
                    <thead class="table-dark">
                        <tr><th>เลข</th><th>ประเภท</th><th>ยอดซื้อ</th><th>อัตราจ่ายประจำตัว</th><th>ส่วนลด (%)</th><th>ยอดสุทธิ</th><th>สถานะอั้น</th></tr>
                    </thead>
                    <tbody>
                        {% for d in drafts %}
                        <tr>
                            <td><b>{{ d[1] }}</b></td>
                            <td>{{ d[4] }}</td>
                            <td>{{ "{:,.2f}".format(d[2] | float) }}</td>
                            <td><span class="badge bg-success">{{ d[5] }}</span></td>
                            <td>{{ d[6] }}%</td>
                            <td>{{ "{:,.2f}".format(d[7] | float) }}</td>
                            <td><span class="badge bg-danger">{{ d[3] }}</span></td>
                        </tr>
                        {% else %}
                        <tr><td colspan="7" class="text-muted">ยังไม่มีรายการในร่าง</td></tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>

            {% if drafts %}
            <div class="card bg-light p-3 mb-3 border">
                <div class="row text-center fw-bold text-dark">
                    <div class="col">ยอดซื้อรวม: ฿{{ "{:,.2f}".format(draft_totals.sum_amt) }}</div>
                    <div class="col text-danger">ส่วนลดรวม: ฿{{ "{:,.2f}".format(draft_totals.sum_disc) }}</div>
                    <div class="col text-primary">ยอดสุทธิที่ต้องชำระ: ฿{{ "{:,.2f}".format(draft_totals.sum_net) }}</div>
                </div>
            </div>
            <form method="POST" action="/confirm-bill">
                <input type="hidden" name="user" value="{{ username }}">
                <input type="hidden" name="draw" value="{{ draw_date }}">
                <input type="hidden" name="customer_info" value="{{ selected_target_raw }}">
                <button type="submit" class="btn btn-primary btn-lg w-100 fw-bold">✅ ยืนยันโพยและบันทึกบิลเข้าระบบ</button>
            </form>
            {% endif %}
        </div>
    </div>

    <div class="col-lg-4">
        <div class="card shadow p-3 bg-white mb-4 border">
            <h5 class="text-danger fw-bold mb-3">🚫 ข้อมูลดิบเลขอั้น (งวดปัจจุบัน)</h5>
            <label class="fw-bold text-dark mb-1">เลขอั้นปิดรับ:</label>
            <textarea class="form-control mb-2 bg-light text-danger fw-bold" rows="3" readonly>{{ block_closed }}</textarea>
            <label class="fw-bold text-dark mb-1">เลขอั้น 3 ตัว (จ่ายครึ่ง):</label>
            <textarea class="form-control mb-2 bg-light text-dark" rows="3" readonly>{{ block_3d }}</textarea>
            <label class="fw-bold text-dark mb-1">เลขอั้น 2 ตัว (จ่ายครึ่ง):</label>
            <textarea class="form-control bg-light text-dark" rows="3" readonly>{{ block_2d }}</textarea>
        </div>
    </div>
</div>
"""

DB_INSPECTOR_TEMPLATE = """
<div class="card shadow p-4">
    <h2 class="text-primary mb-3 fw-bold">🗄️ ตรวจสอบตารางฐานข้อมูลในระบบ (Database Inspector)</h2>
    <p class="text-muted">เลือกตารางฐานข้อมูลที่ต้องการตรวจสอบรายละเอียด (รายชื่อตารางทั้งหมดใน PostgreSQL จะอัปเดตและเพิ่มขยายอัตโนมัติ)</p>
    
    <form method="GET" action="/db-inspector" class="row g-3 mb-4 align-items-end">
        <input type="hidden" name="user" value="{{ username }}">
        <input type="hidden" name="draw" value="{{ draw_date }}">
        <div class="col-md-6">
            <label class="form-label fw-bold text-dark">เลือกตารางฐานข้อมูล:</label>
            <select name="table_name" class="form-select form-select-lg" onchange="this.form.submit()">
                {% for t in tables %}
                    <option value="{{ t }}" {% if selected_table == t %}selected{% endif %}>{{ t }}</option>
                {% endfor %}
            </select>
        </div>
    </form>

    {% if selected_table %}
        <h4 class="text-success mb-3 fw-bold">📋 ข้อมูลในตาราง: <code>{{ selected_table }}</code> (แสดงผลล่าสุด 100 รายการ)</h4>
        <div class="table-responsive">
            <table class="table table-striped table-bordered text-center align-middle" style="font-size: 0.9rem;">
                <thead class="table-dark">
                    <tr>
                        {% for col in columns %}
                            <th>{{ col }}</th>
                        {% endfor %}
                    </tr>
                </thead>
                <tbody>
                    {% for r in rows %}
                    <tr>
                        {% for val in r %}
                            <td>{{ val }}</td>
                        {% endfor %}
                    </tr>
                    {% else %}
                    <tr><td colspan="{{ columns | length }}" class="text-muted py-4">ตารางนี้ยังไม่มีข้อมูล</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    {% endif %}
</div>
"""

AUDIT_ALL_CONTENT = """
<div class="card shadow p-4">
    <h2 class="text-primary mb-4 fw-bold">🔍 ตรวจสอบรายการซื้อของสมาชิกทั้งหมดในระบบ (Admin Master Audit)</h2>
    <div class="table-responsive">
        <table class="table table-striped table-bordered table-hover text-center align-middle" style="font-size: 0.95rem;">
            <thead class="table-dark">
                <tr>
                    <th>ลำดับที่</th>
                    <th>งวดวันที่</th>
                    <th>เวลาทำรายการ</th>
                    <th>เลขที่ใบเสร็จ</th>
                    <th>ผู้บันทึกโพย (ผู้ดูแล/เอเย่นต์)</th>
                    <th>ชื่อลูกค้า / สมาชิก</th>
                    <th>ประเภทหวย</th>
                    <th>หมายเลขที่ซื้อ</th>
                    <th>ยอดซื้อ (บาท)</th>
                    <th>อัตราจ่าย</th>
                    <th>ยอดซื้อสุทธิ (บาท)</th>
                </tr>
            </thead>
            <tbody>
                {% for r in audit_rows %}
                <tr>
                    <td>{{ loop.index }}</td>
                    <td><small>{{ r[1] }}</small></td>
                    <td><small>{{ r[2] }}</small></td>
                    <td><code>{{ r[7] }}</code></td>
                    <td><span class="badge bg-secondary">{{ r[3] }}</span></td>
                    <td><b>{{ r[5] }}</b></td>
                    <td>{{ r[9] }}</td>
                    <td><b class="text-primary fs-6">{{ r[8] }}</b></td>
                    <td>{{ "{:,.2f}".format(r[10] | float) }}</td>
                    <td><span class="badge bg-success">{{ r[14] }}</span></td>
                    <td class="text-success fw-bold">{{ "{:,.2f}".format(r[13] | float) }}</td>
                </tr>
                {% else %}
                <tr><td colspan="11" class="text-muted py-4">ยังไม่มีการบันทึกโพยใดๆ ในงวดนี้</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
"""

AUDIT_DISCOUNT_CONTENT = """
<div class="card shadow p-4">
    <h2 class="text-primary mb-3 fw-bold">🔍 รายงานตรวจสอบส่วนลดลูกค้าทุกรายในทุกบิล (Discount Audit Report)</h2>
    <p class="text-muted">งวดวันที่: <b>{{ draw_date }}</b> | ตรวจสอบความถูกต้องของเปอร์เซ็นต์และยอดเงินส่วนลดที่คำนวณจริง</p>
    
    <div class="table-responsive mt-3">
        <table class="table table-striped table-bordered table-hover text-center align-middle" style="font-size: 0.95rem;">
            <thead class="table-dark">
                <tr>
                    <th>ลำดับ</th>
                    <th>เวลาทำรายการ</th>
                    <th>เลขที่บิล</th>
                    <th>ชื่อลูกค้า</th>
                    <th>ผู้บันทึก (Agent)</th>
                    <th>ประเภท</th>
                    <th>หมายเลข</th>
                    <th>ยอดซื้อ (บาท)</th>
                    <th>ส่วนลด (%)</th>
                    <th>ส่วนลด (บาท)</th>
                    <th>ยอดสุทธิ (บาท)</th>
                </tr>
            </thead>
            <tbody>
                {% for r in discount_rows %}
                <tr>
                    <td>{{ loop.index }}</td>
                    <td><small>{{ r[2] }}</small></td>
                    <td><code>{{ r[7] }}</code></td>
                    <td><b>{{ r[5] }}</b></td>
                    <td><span class="badge bg-secondary">{{ r[3] }}</span></td>
                    <td>{{ r[9] }}</td>
                    <td><b class="text-primary">{{ r[8] }}</b></td>
                    <td>{{ "{:,.2f}".format(r[10] | float) }}</td>
                    <td>
                        {% set amt = r[10] | float %}
                        {% set disc = r[12] | float %}
                        {% if amt > 0 %}
                            <span class="badge bg-info text-dark">{{ "%.2f"|format((disc / amt) * 100) }}%</span>
                        {% else %}
                            0%
                        {% endif %}
                    </td>
                    <td class="text-danger fw-bold">{{ "{:,.2f}".format(disc) }}</td>
                    <td class="text-success fw-bold">{{ "{:,.2f}".format(r[13] | float) }}</td>
                </tr>
                {% else %}
                <tr><td colspan="11" class="text-muted py-4">ยังไม่มีรายการบันทึกบิลในงวดนี้</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
"""

DASHBOARD_CONTENT = """
<div class="card shadow p-4">
    <h2 class="text-primary mb-4 fw-bold">📊 สรุปยอดขายรวมประจำงวด (สายงานของคุณ)</h2>
    <div class="row text-center mb-4">
        <div class="col-md-6 mb-3">
            <div class="p-3 bg-warning text-dark rounded shadow fw-bold fs-4 border">ยอดรวม 2 ตัว: ฿{{ "{:,.2f}".format(tot_2d) }}</div>
        </div>
        <div class="col-md-6 mb-3">
            <div class="p-3 bg-warning text-dark rounded shadow fw-bold fs-4 border">ยอดรวม 3 ตัว: ฿{{ "{:,.2f}".format(tot_3d) }}</div>
        </div>
    </div>
    <h4 class="mb-3 fw-bold text-dark">รายละเอียดหมายเลขที่มียอดซื้อในสายงาน</h4>
    <div class="table-responsive">
        <table class="table table-striped table-bordered text-center align-middle">
            <thead class="table-dark">
                <tr><th>ประเภท</th><th>ตัวเลข</th><th>ยอดซื้อรวม</th><th>ผู้ซื้อ</th></tr>
            </thead>
            <tbody>
                {% for r in dash_rows %}
                <tr>
                    <td>{{ r[0] }}</td><td><b>{{ r[1] }}</b></td><td>{{ "{:,.2f}".format(r[2] | float) }}</td><td>{{ r[3] }}</td>
                </tr>
                {% else %}
                <tr><td colspan="4" class="text-muted">ยังไม่มีรายการซื้อในสายงานของคุณสำหรับงวดนี้</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
"""

REPORTS_CONTENT = """
<div class="card shadow p-4">
    <h2 class="text-primary mb-4 fw-bold">📈 รายงานสรุปยอดขายและสถิติต่างๆ</h2>
    <div class="row text-center mb-4">
        <div class="col-md-4 mb-2"><div class="p-3 bg-white border rounded shadow-sm"><h5>ยอดขายรวมทั้งสิ้น</h5><h3 class="text-dark fw-bold">฿{{ "{:,.2f}".format(rep_total_sales) }}</h3></div></div>
        <div class="col-md-4 mb-2"><div class="p-3 bg-white border rounded shadow-sm"><h5>ส่วนลดรวม</h5><h3 class="text-danger fw-bold">฿{{ "{:,.2f}".format(rep_total_disc) }}</h3></div></div>
        <div class="col-md-4 mb-2"><div class="p-3 bg-white border rounded shadow-sm"><h5>ยอดสุทธิหลังหักส่วนลด</h5><h3 class="text-primary fw-bold">฿{{ "{:,.2f}".format(rep_total_net) }}</h3></div></div>
    </div>
    <h4 class="mb-3 fw-bold text-dark">สรุปยอดขายแยกตามรายชื่อลูกค้า</h4>
    <div class="table-responsive">
        <table class="table table-striped table-bordered text-center align-middle">
            <thead class="table-dark">
                <tr><th>ชื่อลูกค้า / สายงาน</th><th>จำนวนบิล</th><th>ยอดซื้อรวม</th><th>ส่วนลด</th><th>ยอดสุทธิ</th></tr>
            </thead>
            <tbody>
                {% for c in rep_customers %}
                <tr>
                    <td><b>{{ c[0] }}</b></td><td>{{ c[1] }}</td><td>{{ "{:,.2f}".format(c[2] | float) }}</td><td>{{ "{:,.2f}".format(c[3] | float) }}</td><td class="text-success fw-bold">{{ "{:,.2f}".format(c[4] | float) }}</td>
                </tr>
                {% else %}
                <tr><td colspan="5" class="text-muted">ยังไม่มีข้อมูลยอดขายในงวดนี้</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
"""

RESULTS_CONTENT = """
<div class="card shadow p-4 mb-4">
    <h2 class="text-success mb-3 fw-bold">🏆 บันทึกผลการออกรางวัลประจำงวด (Admin Master)</h2>
    <form method="POST" action="/save-results" class="row g-3">
        <input type="hidden" name="user" value="{{ username }}">
        <input type="hidden" name="draw" value="{{ draw_date }}">
        <div class="col-md-6">
            <label class="form-label fw-bold text-dark">รางวัลที่ 1 (3 ตัวตรง):</label>
            <input type="text" name="prize_1" class="form-control form-control-lg" value="{{ prize_1 }}" placeholder="เช่น 123" required>
        </div>
        <div class="col-md-6">
            <label class="form-label fw-bold text-dark">เลขท้าย 2 ตัว:</label>
            <input type="text" name="bottom_2" class="form-control form-control-lg" value="{{ bottom_2 }}" placeholder="เช่น 45" required>
        </div>
        <div class="col-12">
            <button type="submit" class="btn btn-success btn-lg w-100 fw-bold">💾 บันทึกผลรางวัลและคำนวณสรุปผลภาพรวม</button>
        </div>
    </form>
</div>

<div class="card shadow p-4">
    <h3 class="text-primary mb-3 fw-bold">📊 รายงานสรุปผลรางวัลและกำไร / ขาดทุนสุทธิ</h3>
    <div class="row text-center mb-4">
        <div class="col-md-4 mb-2"><div class="p-3 bg-white border rounded shadow-sm"><h5>ยอดขายรวมทั้งระบบ</h5><h3 class="text-dark fw-bold">฿{{ "{:,.2f}".format(total_sales) }}</h3></div></div>
        <div class="col-md-4 mb-2"><div class="p-3 bg-white border rounded shadow-sm"><h5>หักส่วนลดรวม</h5><h3 class="text-danger fw-bold">฿{{ "{:,.2f}".format(total_discount) }}</h3></div></div>
        <div class="col-md-4 mb-2"><div class="p-3 bg-white border rounded shadow-sm"><h5>ยอดขายสุทธิ</h5><h3 class="text-primary fw-bold">฿{{ "{:,.2f}".format(total_net) }}</h3></div></div>
    </div>
    <div class="row text-center mb-4">
        <div class="col-md-6 mb-2"><div class="p-3 bg-white border rounded shadow-sm"><h5>จ่ายเงินรางวัลรวม</h5><h3 class="text-danger fw-bold">฿{{ "{:,.2f}".format(total_payout) }}</h3></div></div>
        <div class="col-md-6 mb-2"><div class="p-3 bg-warning text-dark border rounded shadow-sm"><h5>กำไร / ขาดทุนสุทธิ (Net Profit)</h5><h3 class="fw-bold">฿{{ "{:,.2f}".format(total_net - total_payout) }}</h3></div></div>
    </div>

    <h4 class="mt-4 mb-3 fw-bold text-dark">รายชื่อผู้ถูกรางวัลทั้งหมดในงวดนี้ (รวมทุกลูกค้าและทุกสายงาน)</h4>
    <div class="table-responsive mb-5">
        <table class="table table-striped table-bordered text-center align-middle">
            <thead class="table-dark">
                <tr><th>ผู้ซื้อ / ลูกค้า</th><th>ผู้บันทึก (Agent)</th><th>เลขที่ซื้อ</th><th>ประเภท</th><th>ยอดซื้อ</th><th>อัตราจ่ายประจำตัว</th><th>เงินรางวัลที่ได้รับ</th></tr>
            </thead>
            <tbody>
                {% for w in winners %}
                <tr>
                    <td><b>{{ w[0] }}</b></td><td><span class="badge bg-secondary">{{ w[1] }}</span></td><td><code>{{ w[2] }}</code></td><td>{{ w[3] }}</td><td>{{ "{:,.2f}".format(w[4] | float) }}</td><td><span class="badge bg-success">{{ w[5] }}</span></td><td class="text-success fw-bold">฿{{ "{:,.2f}".format(w[6] | float) }}</td>
                </tr>
                {% else %}
                <tr><td colspan="7" class="text-muted">ยังไม่มีผู้ถูกรางวัล หรือยังไม่ได้บันทึกผลรางวัล</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <h4 class="mt-5 mb-3 fw-bold text-dark">📋 รายละเอียดยอดขายรวมแยกตามรายชื่อลูกค้า / ผู้ซื้อ</h4>
    <div class="table-responsive mb-5">
        <table class="table table-striped table-bordered text-center align-middle">
            <thead class="table-dark">
                <tr><th>ลำดับ</th><th>ชื่อลูกค้า / ผู้ซื้อ</th><th>ผู้บันทึกโพย (Agent)</th><th>จำนวนบิล</th><th>ยอดซื้อรวม (บาท)</th><th>ส่วนลดรวม (บาท)</th><th>ยอดสุทธิ (บาท)</th></tr>
            </thead>
            <tbody>
                {% for s in sales_breakdown %}
                <tr>
                    <td>{{ loop.index }}</td>
                    <td><b>{{ s[0] }}</b></td>
                    <td><span class="badge bg-secondary">{{ s[1] }}</span></td>
                    <td>{{ s[2] }}</td>
                    <td>{{ "{:,.2f}".format(s[3] | float) }}</td>
                    <td class="text-danger fw-bold">{{ "{:,.2f}".format(s[4] | float) }}</td>
                    <td class="text-success fw-bold">{{ "{:,.2f}".format(s[5] | float) }}</td>
                </tr>
                {% else %}
                <tr><td colspan="7" class="text-muted">ยังไม่มีข้อมูลยอดขายในงวดนี้</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <h4 class="mt-4 mb-3 fw-bold text-dark">🏷️ รายละเอียดส่วนลดแยกตามรายชื่อลูกค้า / ผู้ซื้อ</h4>
    <div class="table-responsive">
        <table class="table table-striped table-bordered text-center align-middle">
            <thead class="table-dark">
                <tr><th>ลำดับ</th><th>ชื่อลูกค้า / ผู้ซื้อ</th><th>ผู้บันทึกโพย (Agent)</th><th>ยอดซื้อรวม (บาท)</th><th>ส่วนลดรวม (บาท)</th><th>คิดเป็น % เฉลี่ย</th></tr>
            </thead>
            <tbody>
                {% for d in discount_breakdown %}
                <tr>
                    <td>{{ loop.index }}</td>
                    <td><b>{{ d[0] }}</b></td>
                    <td><span class="badge bg-secondary">{{ d[1] }}</span></td>
                    <td>{{ "{:,.2f}".format(d[2] | float) }}</td>
                    <td class="text-danger fw-bold">{{ "{:,.2f}".format(d[3] | float) }}</td>
                    <td>
                        {% set total_amt = d[2] | float %}
                        {% set total_disc = d[3] | float %}
                        {% if total_amt > 0 %}
                            <span class="badge bg-info text-dark">{{ "%.2f"|format((total_disc / total_amt) * 100) }}%</span>
                        {% else %}
                            0%
                        {% endif %}
                    </td>
                </tr>
                {% else %}
                <tr><td colspan="6" class="text-muted">ยังไม่มีข้อมูลส่วนลดในงวดนี้</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
"""

CUSTOMER_CONTENT = """
{% if incomplete_customers %}
<div class="alert alert-danger border border-danger shadow p-3 mb-4 rounded">
    <h5 class="fw-bold text-danger"><i class="fa-solid fa-triangle-exclamation"></i> แจ้งเตือน: พบรายชื่อลูกค้าและสายงานที่ข้อมูล "ส่วนลด" หรือ "อัตราจ่ายรางวัล" ยังไม่ครบถ้วน จำนวน {{ incomplete_customers | length }} รายการ</h5>
    <p class="mb-2 text-dark">กรุณาดำเนินการคลิกปุ่ม <b>"✏️ แก้ไข"</b> ที่รายชื่อด้านล่างนี้เพื่อเติมข้อมูลให้ครบถ้วนสมบูรณ์ตามกฎของระบบ:</p>
    <ul class="mb-0 fw-bold text-danger">
        {% for inc in incomplete_customers %}
            <li>ลูกค้า: {{ inc[1] }} (รหัส ID: {{ inc[0] }}) — <i>สถานะ: ขาดข้อมูลส่วนลดหรืออัตราจ่ายรางวัล</i></li>
        {% endfor %}
    </ul>
</div>
{% endif %}

<div class="row">
    <div class="col-md-4 mb-4">
        <div class="card shadow p-4">
            {% if edit_customer %}
                <h4 class="text-warning mb-3 fw-bold">✏️ แก้ไขข้อมูลลูกค้า</h4>
                <form method="POST" action="/update-customer">
                    <input type="hidden" name="user" value="{{ username }}">
                    <input type="hidden" name="draw" value="{{ draw_date }}">
                    <input type="hidden" name="customer_id" value="{{ edit_customer[0] }}">
                    <div class="mb-3">
                        <label class="form-label fw-bold text-dark">ชื่อลูกค้า *:</label>
                        <input type="text" name="name" class="form-control" value="{{ edit_customer[1] }}" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label fw-bold text-dark">ส่วนลดรวม (%):</label>
                        <input type="number" step="0.01" name="disc_total" class="form-control" value="{{ edit_customer[2] if edit_customer[2] is not none else 0 }}">
                    </div>
                    <div class="row mb-3">
                        <div class="col"><label class="form-label text-dark small">ส่วนลด 3 ตัว (%):</label><input type="number" step="0.01" name="disc_3d" class="form-control" value="{{ edit_customer[6] if edit_customer[6] is not none else 0 }}"></div>
                        <div class="col"><label class="form-label text-dark small">ส่วนลด 2 ตัว (%):</label><input type="number" step="0.01" name="disc_2d" class="form-control" value="{{ edit_customer[7] if edit_customer[7] is not none else 0 }}"></div>
                    </div>
                    <div class="row mb-3">
                        <div class="col"><label class="form-label text-dark">จ่าย 3 ตรง *:</label><input type="number" step="0.01" name="pay_3d" class="form-control" value="{{ edit_customer[3] or 500 }}" required></div>
                        <div class="col"><label class="form-label text-dark">จ่าย 3 โต๊ด *:</label><input type="number" step="0.01" name="pay_3tod" class="form-control" value="{{ edit_customer[4] or 100 }}" required></div>
                    </div>
                    <div class="mb-3">
                        <label class="form-label text-dark">จ่าย 2 ตัว (บน/ล่าง) *:</label><input type="number" step="0.01" name="pay_2d" class="form-control" value="{{ edit_customer[5] or 70 }}" required>
                    </div>
                    <button type="submit" class="btn btn-warning w-100 fw-bold mb-2">💾 บันทึกการแก้ไข</button>
                    <a href="/customers?user={{ username }}&draw={{ draw_date }}" class="btn btn-outline-secondary w-100 fw-bold">ยกเลิก</a>
                </form>
            {% else %}
                <h4 class="text-success mb-3 fw-bold">➕ เพิ่มลูกค้ารายใหม่</h4>
                <form method="POST" action="/save-customer">
                    <input type="hidden" name="user" value="{{ username }}">
                    <input type="hidden" name="draw" value="{{ draw_date }}">
                    <div class="mb-3">
                        <label class="form-label fw-bold text-dark">ชื่อลูกค้า *:</label>
                        <input type="text" name="name" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label fw-bold text-dark">ส่วนลดรวม (%):</label>
                        <input type="number" step="0.01" name="disc_total" class="form-control" value="0">
                    </div>
                    <div class="row mb-3">
                        <div class="col"><label class="form-label text-dark small">ส่วนลด 3 ตัว (%):</label><input type="number" step="0.01" name="disc_3d" class="form-control" value="0"></div>
                        <div class="col"><label class="form-label text-dark small">ส่วนลด 2 ตัว (%):</label><input type="number" step="0.01" name="disc_2d" class="form-control" value="0"></div>
                    </div>
                    <div class="row mb-3">
                        <div class="col"><label class="form-label text-dark">จ่าย 3 ตรง *:</label><input type="number" step="0.01" name="pay_3d" class="form-control" value="500" required></div>
                        <div class="col"><label class="form-label text-dark">จ่าย 3 โต๊ด *:</label><input type="number" step="0.01" name="pay_3tod" class="form-control" value="100" required></div>
                    </div>
                    <div class="mb-3">
                        <label class="form-label text-dark">จ่าย 2 ตัว (บน/ล่าง) *:</label><input type="number" step="0.01" name="pay_2d" class="form-control" value="70" required>
                    </div>
                    <button type="submit" class="btn btn-success w-100 fw-bold">บันทึกลูกค้า</button>
                </form>
            {% endif %}
        </div>
    </div>
    <div class="col-md-8">
        <div class="card shadow p-4">
            <h4 class="text-primary mb-3 fw-bold">👥 รายชื่อลูกค้าของคุณ</h4>
            <div class="table-responsive">
                <table class="table table-striped table-bordered text-center align-middle">
                    <thead class="table-dark">
                        <tr><th>ID</th><th>ชื่อลูกค้า</th><th>ส่วนลดรวม</th><th>ลด 3 ตัว</th><th>ลด 2 ตัว</th><th>จ่าย 3 ตรง</th><th>จ่าย 3 โต๊ด</th><th>จ่าย 2 ตัว</th><th>จัดการ</th></tr>
                    </thead>
                    <tbody>
                        {% for c in customers_list %}
                        <tr {% if c[3] is none or c[4] is none or c[5] is none or c[3] == 0 or c[5] == 0 %}class="table-danger"{% endif %}>
                            <td>{{ c[0] }}</td>
                            <td><b>{{ c[1] }}</b></td>
                            <td>{{ c[2] or 0 }}%</td>
                            <td><span class="text-danger fw-bold">{{ c[6] or 0 }}%</span></td>
                            <td><span class="text-danger fw-bold">{{ c[7] or 0 }}%</span></td>
                            <td>{{ c[3] or '<span class="text-danger">ยังไม่ระบุ</span>' | safe }}</td>
                            <td>{{ c[4] or '<span class="text-danger">ยังไม่ระบุ</span>' | safe }}</td>
                            <td>{{ c[5] or '<span class="text-danger">ยังไม่ระบุ</span>' | safe }}</td>
                            <td>
                                <a href="/customers?user={{ username }}&draw={{ draw_date }}&edit_id={{ c[0] }}" class="btn btn-warning btn-sm fw-bold">✏️ แก้ไข</a>
                            </td>
                        </tr>
                        {% else %}
                        <tr><td colspan="9" class="text-muted">ยังไม่มีรายชื่อลูกค้า</td></tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>
"""

USERS_CONTENT = """
<div class="row">
    <div class="col-md-5 mb-4">
        <div class="card shadow p-4">
            <h4 class="text-success mb-3 fw-bold">⚙️ สร้างสายงานสมาชิก / กำหนดเรต</h4>
            <form method="POST" action="/save-user-level">
                <input type="hidden" name="user" value="{{ username }}">
                <input type="hidden" name="draw" value="{{ draw_date }}">
                <div class="mb-3">
                    <label class="form-label fw-bold text-dark">Username *:</label>
                    <input type="text" name="new_username" class="form-control" required>
                </div>
                <div class="mb-3">
                    <label class="form-label fw-bold text-dark">Password *:</label>
                    <div class="input-group">
                        <input type="password" name="new_password" id="newPasswordInput" class="form-control" required>
                        <button class="btn btn-outline-secondary" type="button" onclick="togglePassword()">
                            <i class="fa-solid fa-eye" id="eyeIcon"></i>
                        </button>
                    </div>
                </div>
                <script>
                    function togglePassword() {
                        const pwd = document.getElementById('newPasswordInput');
                        const icon = document.getElementById('eyeIcon');
                        if (pwd.type === 'password') {
                            pwd.type = 'text';
                            icon.classList.remove('fa-eye');
                            icon.classList.add('fa-eye-slash');
                        } else {
                            pwd.type = 'password';
                            icon.classList.remove('fa-eye-slash');
                            icon.classList.add('fa-eye');
                        }
                    }
                </script>
                <div class="mb-3">
                    <label class="form-label fw-bold text-dark">ระดับสิทธิ์ (Role) *:</label>
                    <select name="new_role" class="form-select">
                        {% if role == 'Admin' %}
                            <option value="Master Agent">Master Agent</option>
                            <option value="Agent">Agent</option>
                            <option value="Member">Member</option>
                        {% elif role == 'Master Agent' %}
                            <option value="Agent">Agent</option>
                            <option value="Member">Member</option>
                        {% elif role == 'Agent' %}
                            <option value="Member">Member</option>
                        {% endif %}
                    </select>
                </div>

                <div class="mb-3 border-top pt-3">
                    <label class="form-label fw-bold text-primary">💰 กำหนดส่วนลด (%):</label>
                    <div class="mb-2">
                        <label class="form-label text-dark small">ส่วนลดรวมทุกประเภท (%):</label>
                        <input type="number" step="0.01" name="disc_total" class="form-control" value="0">
                    </div>
                    <div class="row">
                        <div class="col"><label class="form-label text-dark small">ส่วนลด 3 ตัว (%):</label><input type="number" step="0.01" name="disc_3d" class="form-control" value="0"></div>
                        <div class="col"><label class="form-label text-dark small">ส่วนลด 2 ตัว (%):</label><input type="number" step="0.01" name="disc_2d" class="form-control" value="0"></div>
                    </div>
                </div>

                <div class="mb-3 border-top pt-3">
                    <label class="form-label fw-bold text-success">🏆 กำหนดอัตราจ่ายรางวัล:</label>
                    <div class="row mb-2">
                        <div class="col"><label class="form-label text-dark small">จ่าย 3 ตัวตรง *:</label><input type="number" step="0.01" name="pay_3d" class="form-control" value="500" required></div>
                        <div class="col"><label class="form-label text-dark small">จ่าย 3 ตัวโต๊ด *:</label><input type="number" step="0.01" name="pay_3tod" class="form-control" value="100" required></div>
                    </div>
                    <div class="mb-2">
                        <label class="form-label text-dark small">จ่าย 2 ตัว (บน/ล่าง) *:</label><input type="number" step="0.01" name="pay_2d" class="form-control" value="70" required>
                    </div>
                </div>

                <button type="submit" class="btn btn-success w-100 fw-bold py-2">💾 บันทึกสมาชิกใหม่และเรตเรท</button>
            </form>
        </div>
    </div>
    <div class="col-md-7">
        <div class="card shadow p-4">
            <h4 class="text-primary mb-3 fw-bold">🗂️ รายชื่อสมาชิกใต้สายงาน (ดับเบิลคลิกเพื่อเจาะลึกสายงาน)</h4>
            <div class="table-responsive">
                <table class="table table-striped table-bordered table-hover text-center align-middle" style="font-size: 0.9rem;">
                    <thead class="table-dark">
                        <tr><th>ID</th><th>Username</th><th>สิทธิ์</th><th>ส่วนลดรวม</th><th>ลด 3/2</th><th>จ่าย 3ตรง</th><th>จ่าย 2ตัว</th></tr>
                    </thead>
                    <tbody>
                        {% for u in users_list %}
                        <tr ondblclick="window.location.href='/users?user={{ u[1] }}&draw={{ draw_date }}'" style="cursor: pointer;" title="ดับเบิลคลิกเพื่อเจาะลึกสายงานของ {{ u[1] }}">
                            <td>{{ u[0] }}</td>
                            <td><b>{{ u[1] }}</b></td>
                            <td><span class="badge bg-secondary">{{ u[2] }}</span></td>
                            <td>{{ u[5] or 0 }}%</td>
                            <td><span class="text-danger">{{ u[6] or 0 }}%/{{ u[7] or 0 }}%</span></td>
                            <td>{{ u[8] or 500 }}</td>
                            <td>{{ u[10] or 70 }}</td>
                        </tr>
                        {% else %}
                        <tr><td colspan="7" class="text-muted">ยังไม่มีสมาชิกในสายงาน</td></tr>
                        {% endfor %}
                    </tbody>
                </table>
                <div class="form-text text-muted">💡 เคล็ดลับ: ดับเบิลคลิกที่แถวของสมาชิกเพื่อเปิดดูมุมมองสายงานใต้สังกัดของสมาชิกท่านนั้นๆ</div>
            </div>
        </div>
    </div>
</div>
"""

PASSWORD_TEMPLATE = """
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card shadow p-4 border">
            <h3 class="text-primary mb-3 fw-bold">🔑 เปลี่ยนรหัสผ่านส่วนตัว</h3>
            <form method="POST" action="/update-password">
                <input type="hidden" name="user" value="{{ username }}">
                <input type="hidden" name="draw" value="{{ draw_date }}">
                <div class="mb-3">
                    <label class="form-label fw-bold text-dark">รหัสผ่านปัจจุบัน:</label>
                    <input type="password" name="old_password" class="form-control" required>
                </div>
                <div class="mb-3">
                    <label class="form-label fw-bold text-dark">รหัสผ่านใหม่:</label>
                    <input type="password" name="new_password" class="form-control" required>
                </div>
                <div class="mb-3">
                    <label class="form-label fw-bold text-dark">ยืนยันรหัสผ่านใหม่:</label>
                    <input type="password" name="confirm_password" class="form-control" required>
                </div>
                <button type="submit" class="btn btn-primary w-100 fw-bold py-2">💾 บันทึกรหัสผ่านใหม่</button>
            </form>
        </div>
    </div>
</div>
"""

def get_blocked_display_data(draw_date):
    try:
        conn = connect_db()
        c = conn.cursor()
        # ดึงเฉพาะรายการเลขอั้นที่เป็นข้อมูลดิบตรงๆ ตามงวด (ไม่เอาเลขสลับตำแหน่งเบื้องหลังมาปะปน)
        c.execute("SELECT raw_num, status, type FROM BlockedNumbers WHERE (draw_date = %s OR draw_date ILIKE %s)", (draw_date, f"%{draw_date}%"))
        rows = c.fetchall()
        conn.close()
        
        l_c = []
        l_3 = []
        l_2 = []
        
        seen_raw = set()
        for r_num, status_val, type_val in rows:
            if not r_num: continue
            # ป้องกันข้อมูลซ้ำซ้อนในช่องแสดงผลดิบ
            identifier = f"{r_num}-{status_val}-{type_val}"
            if identifier in seen_raw: continue
            seen_raw.add(identifier)
            
            if status_val == "ปิดรับ":
                l_c.append(str(r_num))
            else:
                if type_val == "3ตัว" or len(str(r_num)) == 3:
                    l_3.append(str(r_num))
                elif type_val == "2ตัว" or len(str(r_num)) == 2:
                    l_2.append(str(r_num))
                    
        return ", ".join(l_c), ", ".join(l_3), ", ".join(l_2)
    except Exception as e:
        print("Get Blocked Display Error:", e)
        return "", "", ""

# ================= Routes =================

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
            return RedirectResponse(url=f"/campaigns?user={username}", status_code=status.HTTP_303_SEE_OTHER)
        else:
            return Template(LOGIN_TEMPLATE).render(error="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง!")
    except Exception as e:
        return Template(LOGIN_TEMPLATE).render(error=f"เกิดข้อผิดพลาด: {str(e)}")

@app.get("/campaigns", response_class=HTMLResponse)
def campaigns_page(user: str):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("SELECT role FROM Users WHERE username=%s", (user,))
        user_res = c.fetchone()
        role = user_res[0] if user_res else "Member"

        c.execute("SELECT lotto_name, draw_date, status, id FROM LotteryCampaigns ORDER BY id DESC")
        campaigns = c.fetchall()
        conn.close()
        content = Template(CAMPAIGN_TEMPLATE).render(username=user, role=role, campaigns=campaigns)
        return Template(LAYOUT).render(username=user, role=role, draw_date="เลือกงวด", content=content)
    except Exception as e:
        return f"Error: {str(e)}"

@app.post("/create-campaign")
def create_campaign(user: str = Form(...), lotto_name: str = Form(...), draw_date: str = Form(...)):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("INSERT INTO LotteryCampaigns (lotto_name, draw_date, status) VALUES (%s, %s, 'Active')", (lotto_name, draw_date))
        conn.commit()
        conn.close()
    except: pass
    return RedirectResponse(url=f"/campaigns?user={user}", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/toggle-campaign")
def toggle_campaign(id: int, user: str):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("SELECT status FROM LotteryCampaigns WHERE id=%s", (id,))
        curr = c.fetchone()
        if curr:
            new_status = "Closed" if curr[0] == "Active" else "Active"
            c.execute("UPDATE LotteryCampaigns SET status=%s WHERE id=%s", (new_status, id))
            conn.commit()
        conn.close()
    except: pass
    return RedirectResponse(url=f"/campaigns?user={user}", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/blocked-numbers", response_class=HTMLResponse)
def blocked_numbers_page(user: str, draw: str, msg: str = None, error: str = None, edit_id: int = None):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("SELECT role FROM Users WHERE username=%s", (user,))
        role = c.fetchone()[0]

        c.execute("SELECT id, draw_date, raw_num, status, type FROM BlockedNumbers WHERE draw_date = %s OR draw_date ILIKE %s ORDER BY id DESC", (draw, f"%{draw}%"))
        blocked_list = c.fetchall()

        edit_blocked = None
        if edit_id:
            c.execute("SELECT id, draw_date, raw_num, status, type FROM BlockedNumbers WHERE id = %s", (edit_id,))
            edit_blocked = c.fetchone()

        conn.close()

        content = Template(BLOCKED_TEMPLATE).render(username=user, draw_date=draw, blocked_list=blocked_list, edit_blocked=edit_blocked)
        return Template(LAYOUT).render(username=user, role=role, draw_date=draw, content=content, msg=msg, error=error)
    except Exception as e:
        return f"Error: {str(e)}"

@app.post("/save-blocked")
def save_blocked(user: str = Form(...), draw: str = Form(...), raw_input: str = Form(...), status: str = Form(...), type: str = Form(...)):
    try:
        conn = connect_db()
        c = conn.cursor()
        
        cleaned = raw_input.replace('\r\n', ',').replace('\n', ',').replace(' ', ',')
        raw_numbers = [item.strip() for item in cleaned.split(',') if item.strip()]
        
        for num_str in raw_numbers:
            if status == "ปิดรับ":
                c.execute("INSERT INTO BlockedNumbers (draw_date, raw_num, status, type) VALUES (%s, %s, %s, %s)", 
                          (draw.strip(), num_str, status, type))
            else:
                perms = set("".join(p) for p in itertools.permutations(num_str))
                for p_num in perms:
                    c.execute("INSERT INTO BlockedNumbers (draw_date, raw_num, status, type) VALUES (%s, %s, %s, %s)", 
                              (draw.strip(), p_num, status, type))
                              
        conn.commit()
        conn.close()
    except Exception as e:
        print("Save Blocked Error:", e)
        return RedirectResponse(url=f"/blocked-numbers?user={user}&draw={draw}&error=เกิดข้อผิดพลาด: {str(e)}", status_code=status.HTTP_303_SEE_OTHER)
        
    return RedirectResponse(url=f"/blocked-numbers?user={user}&draw={draw}&msg=ประมวลผลและบันทึกเลขอั้นสำเร็จ", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/update-blocked")
def update_blocked(user: str = Form(...), draw: str = Form(...), blocked_id: int = Form(...), raw_num: str = Form(...), status: str = Form(...), type: str = Form(...)):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("UPDATE BlockedNumbers SET raw_num=%s, status=%s, type=%s WHERE id=%s", (raw_num.strip(), status, type, blocked_id))
        conn.commit()
        conn.close()
    except Exception as e:
        return RedirectResponse(url=f"/blocked-numbers?user={user}&draw={draw}&error=เกิดข้อผิดพลาดในการแก้ไข: {str(e)}", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url=f"/blocked-numbers?user={user}&draw={draw}&msg=แก้ไขเลขอั้นสำเร็จ", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/delete-blocked")
def delete_blocked(id: int, user: str, draw: str):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("DELETE FROM BlockedNumbers WHERE id = %s", (id,))
        conn.commit()
        conn.close()
    except: pass
    return RedirectResponse(url=f"/blocked-numbers?user={user}&draw={draw}&msg=ลบเลขอั้นสำเร็จ", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/buy", response_class=HTMLResponse)
def buy_page(user: str, draw: str, selected: str = None, msg: str = None):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("SELECT role FROM Users WHERE username=%s", (user,))
        u_role_res = c.fetchone()
        role = u_role_res[0] if u_role_res else "Member"

        c.execute("SELECT id, name, 'Customer' FROM Customers WHERE owner_username=%s", (user,))
        custs = c.fetchall()
        if not custs and role == 'Admin':
            c.execute("SELECT id, name, 'Customer' FROM Customers")
            custs = c.fetchall()
            
        c.execute("SELECT id, username, 'User' FROM Users WHERE parent_user=%s", (user,))
        agents = c.fetchall()
        all_targets = custs + agents
        
        if not selected and all_targets:
            selected = f"{all_targets[0][0]}|{all_targets[0][1]}|{all_targets[0][2]}"
        
        selected_c_id = None
        c_id, c_type = None, None
        if selected:
            parts = selected.split('|')
            c_id, c_type = parts[0], parts[2]
            selected_c_id = int(c_id)

        drafts = []
        sum_amt, sum_disc, sum_net = 0.0, 0.0, 0.0
        
        if c_id:
            c.execute("SELECT id, num, amt_teng, status, type, payout_rate, discount, net FROM TempDraft WHERE username=%s AND customer_id=%s AND customer_type=%s", (user, c_id, c_type))
            for row in c.fetchall():
                drafts.append(row)
                sum_amt += float(row[2] or 0)
                sum_disc += float(row[6] or 0)
                sum_net += float(row[7] or 0)

        conn.close()
        b_closed, b_3d, b_2d = get_blocked_display_data(draw)

        content = Template(BUY_CONTENT).render(
            username=user, draw_date=draw, customers=all_targets, selected_target_raw=selected, 
            selected_c_id=selected_c_id, drafts=drafts, draft_totals={"sum_amt": sum_amt, "sum_disc": sum_disc, "sum_net": sum_net},
            block_closed=b_closed, block_3d=b_3d, block_2d=b_2d
        )
        return Template(LAYOUT).render(username=user, role=role, draw_date=draw, content=content, msg=msg)
    except Exception as e:
        return f"System Error: {str(e)}"

@app.post("/submit-buy")
def submit_buy(user: str = Form(...), draw: str = Form(...), customer_info: str = Form(...)):
    return RedirectResponse(url=f"/buy?user={user}&draw={draw}&selected={customer_info}", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/add-draft")
def add_draft(user: str = Form(...), draw: str = Form(...), customer_info: str = Form(...), raw_input: str = Form(...)):
    parts = customer_info.split('|')
    c_id, c_type = parts[0], parts[2]
    raw_input = raw_input.strip().upper().replace(' ', '').replace('X', '*').replace('+', '*').replace('/', '*')
    blocks = raw_input.split(',')
    
    try:
        conn = connect_db()
        c = conn.cursor()
        
        pay_3d, pay_3tod, pay_2d = 500.0, 100.0, 70.0
        disc_total, disc_3d, disc_2d = 0.0, 0.0, 0.0
        
        if c_type == 'Customer':
            c.execute("SELECT pay_3d, pay_3tod, pay_2d, disc_total, disc_3d, disc_2d FROM Customers WHERE id=%s", (c_id,))
            res = c.fetchone()
            if res:
                pay_3d = float(res[0]) if res[0] is not None and float(res[0]) > 0 else 500.0
                pay_3tod = float(res[1]) if res[1] is not None and float(res[1]) > 0 else 100.0
                pay_2d = float(res[2]) if res[2] is not None and float(res[2]) > 0 else 70.0
                disc_total = float(res[3]) if res[3] is not None else 0.0
                disc_3d = float(res[4]) if res[4] is not None else 0.0
                disc_2d = float(res[5]) if res[5] is not None else 0.0
        elif c_type == 'User':
            c.execute("SELECT pay_3d, pay_3tod, pay_2d, disc_total, disc_3d, disc_2d FROM Users WHERE id=%s", (c_id,))
            res = c.fetchone()
            if res:
                pay_3d = float(res[0]) if res[0] is not None and float(res[0]) > 0 else 500.0
                pay_3tod = float(res[1]) if res[1] is not None and float(res[1]) > 0 else 100.0
                pay_2d = float(res[2]) if res[2] is not None and float(res[2]) > 0 else 70.0
                disc_total = float(res[3]) if res[3] is not None else 0.0
                disc_3d = float(res[4]) if res[4] is not None else 0.0
                disc_2d = float(res[5]) if res[5] is not None else 0.0

        hold_nums = []
        for block in blocks:
            if not block: continue
            if '=' in block:
                num_str, amt_str = block.split('=')[0].strip(), block.split('=')[1].strip()
                if num_str: hold_nums.append(num_str)
                if '*' in amt_str:
                    ap = amt_str.split('*')
                    top = float(ap[0]) if ap[0].strip() else 0.0
                    bot = float(ap[1]) if ap[1].strip() else 0.0
                else:
                    top = float(amt_str) if amt_str.strip() else 0.0
                    bot = 0.0
                
                for n in hold_nums:
                    if len(n) == 3:
                        if top > 0:
                            d_rate = disc_3d if disc_3d > 0 else disc_total
                            disc_amt = top * (d_rate / 100.0)
                            net_amt = top - disc_amt
                            c.execute("INSERT INTO TempDraft (username, customer_id, customer_type, num, amt_teng, type, payout_rate, discount, net, status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", 
                                      (user, c_id, c_type, n, top, "3ตัวตรง", pay_3d, disc_amt, net_amt, "ปกติ"))
                        if bot > 0:
                            d_rate = disc_3d if disc_3d > 0 else disc_total
                            disc_amt = bot * (d_rate / 100.0)
                            net_amt = bot - disc_amt
                            c.execute("INSERT INTO TempDraft (username, customer_id, customer_type, num, amt_teng, type, payout_rate, discount, net, status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", 
                                      (user, c_id, c_type, n, bot, "3ตัวโต๊ด", pay_3tod, disc_amt, net_amt, "ปกติ"))
                    elif len(n) == 2:
                        if top > 0:
                            d_rate = disc_2d if disc_2d > 0 else disc_total
                            disc_amt = top * (d_rate / 100.0)
                            net_amt = top - disc_amt
                            c.execute("INSERT INTO TempDraft (username, customer_id, customer_type, num, amt_teng, type, payout_rate, discount, net, status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", 
                                      (user, c_id, c_type, n, top, "2ตัวบน", pay_2d, disc_amt, net_amt, "ปกติ"))
                        if bot > 0:
                            d_rate = disc_2d if disc_2d > 0 else disc_total
                            disc_amt = bot * (d_rate / 100.0)
                            net_amt = bot - disc_amt
                            c.execute("INSERT INTO TempDraft (username, customer_id, customer_type, num, amt_teng, type, payout_rate, discount, net, status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", 
                                      (user, c_id, c_type, n, bot, "2ตัวล่าง", pay_2d, disc_amt, net_amt, "ปกติ"))
                hold_nums = []
            else:
                hold_nums.append(block.strip())
        conn.commit()
        conn.close()
    except Exception as e:
        print("Add Draft Error:", e)
    return RedirectResponse(url=f"/buy?user={user}&draw={draw}&selected={customer_info}", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/confirm-bill")
def confirm_bill(user: str = Form(...), draw: str = Form(...), customer_info: str = Form(...)):
    parts = customer_info.split('|')
    c_id, c_name, c_type = parts[0], parts[1], parts[2]
    try:
        conn = connect_db()
        c = conn.cursor()
        
        disc_total, disc_3d, disc_2d = 0.0, 0.0, 0.0
        pay_3d_def, pay_3tod_def, pay_2d_def = 500.0, 100.0, 70.0
        
        if c_type == 'Customer':
            c.execute("SELECT disc_total, disc_3d, disc_2d, pay_3d, pay_3tod, pay_2d FROM Customers WHERE id=%s", (c_id,))
            c_res = c.fetchone()
            if c_res:
                disc_total = float(c_res[0] or 0)
                disc_3d = float(c_res[1] or 0)
                disc_2d = float(c_res[2] or 0)
                pay_3d_def = float(c_res[3] or 500)
                pay_3tod_def = float(c_res[4] or 100)
                pay_2d_def = float(c_res[5] or 70)
        elif c_type == 'User':
            c.execute("SELECT disc_total, disc_3d, disc_2d, pay_3d, pay_3tod, pay_2d FROM Users WHERE id=%s", (c_id,))
            c_res = c.fetchone()
            if c_res:
                disc_total = float(c_res[0] or 0)
                disc_3d = float(c_res[1] or 0)
                disc_2d = float(c_res[2] or 0)
                pay_3d_def = float(c_res[3] or 500)
                pay_3tod_def = float(c_res[4] or 100)
                pay_2d_def = float(c_res[5] or 70)

        c.execute("SELECT num, type, amt_teng, status FROM TempDraft WHERE username=%s AND customer_id=%s AND customer_type=%s", (user, c_id, c_type))
        drafts = c.fetchall()
        if drafts:
            bill_no = f"BILL-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')[:21]}-{c_id}"
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for n, t_type, amt, status_val in drafts:
                amt_val = float(amt or 0)
                
                final_rate = 500.0
                if t_type == "3ตัวตรง": final_rate = pay_3d_def
                elif t_type == "3ตัวโต๊ด": final_rate = pay_3tod_def
                elif t_type in ["2ตัวบน", "2ตัวล่าง"]: final_rate = pay_2d_def

                d_rate = 0.0
                if "3ตัว" in t_type:
                    d_rate = disc_3d if disc_3d > 0 else disc_total
                elif "2ตัว" in t_type:
                    d_rate = disc_2d if disc_2d > 0 else disc_total

                final_disc = amt_val * (d_rate / 100.0)
                final_net = amt_val - final_disc

                c.execute("INSERT INTO Transactions (draw_date, timestamp, username, customer_id, customer_name, customer_type, bill_no, num, type, amount, status, discount, net, payout_rate) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", 
                          (draw, ts, user, int(c_id), c_name, c_type, bill_no, n, t_type, amt_val, status_val, final_disc, final_net, final_rate))
            c.execute("DELETE FROM TempDraft WHERE username=%s AND customer_id=%s AND customer_type=%s", (user, c_id, c_type))
            conn.commit()
        conn.close()
    except Exception as e:
        print("Confirm Error:", e)
    return RedirectResponse(url=f"/buy?user={user}&draw={draw}&selected={customer_info}&msg=บันทึกบิลสำเร็จ!", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/audit-all", response_class=HTMLResponse)
def audit_all_page(user: str, draw: str):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("SELECT role FROM Users WHERE username=%s", (user,))
        role_res = c.fetchone()
        role = role_res[0] if role_res else "Member"
        if role != 'Admin':
            conn.close()
            return RedirectResponse(url=f"/buy?user={user}&draw={draw}", status_code=status.HTTP_303_SEE_OTHER)

        c.execute("SELECT * FROM Transactions WHERE (draw_date = %s OR draw_date ILIKE %s) ORDER BY id DESC", (draw, f"%{draw}%"))
        audit_rows = c.fetchall()
        conn.close()

        content = Template(AUDIT_ALL_CONTENT).render(audit_rows=audit_rows)
        return Template(LAYOUT).render(username=user, role=role, draw_date=draw, content=content)
    except Exception as e:
        return f"Error: {str(e)}"

@app.get("/audit-discount", response_class=HTMLResponse)
def audit_discount_page(user: str, draw: str):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("SELECT role FROM Users WHERE username=%s", (user,))
        role_res = c.fetchone()
        role = role_res[0] if role_res else "Member"
        
        c.execute("SELECT * FROM Transactions WHERE (draw_date = %s OR draw_date ILIKE %s) ORDER BY id DESC", (draw, f"%{draw}%"))
        discount_rows = c.fetchall()
        conn.close()

        content = Template(AUDIT_DISCOUNT_CONTENT).render(discount_rows=discount_rows, draw_date=draw)
        return Template(LAYOUT).render(username=user, role=role, draw_date=draw, content=content)
    except Exception as e:
        return f"Error: {str(e)}"

@app.get("/db-inspector", response_class=HTMLResponse)
def db_inspector_page(user: str, draw: str, table_name: str = None):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("SELECT role FROM Users WHERE username=%s", (user,))
        role_res = c.fetchone()
        role = role_res[0] if role_res else "Member"
        if role != 'Admin':
            conn.close()
            return RedirectResponse(url=f"/buy?user={user}&draw={draw}", status_code=status.HTTP_303_SEE_OTHER)

        c.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;")
        tables = [row[0] for row in c.fetchall()]

        rows = []
        columns = []
        selected_table = table_name if table_name in tables else (tables[0] if tables else None)

        if selected_table:
            c.execute(f"SELECT * FROM {selected_table} ORDER BY 1 DESC LIMIT 100;")
            rows = c.fetchall()
            columns = [desc[0] for desc in c.description]

        conn.close()

        content = Template(DB_INSPECTOR_TEMPLATE).render(
            tables=tables, selected_table=selected_table, columns=columns, rows=rows, draw_date=draw, username=user
        )
        return Template(LAYOUT).render(username=user, role=role, draw_date=draw, content=content)
    except Exception as e:
        return f"Error: {str(e)}"

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(user: str, draw: str):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("SELECT role FROM Users WHERE username=%s", (user,))
        role = c.fetchone()[0]

        if role == 'Admin':
            c.execute("SELECT type, SUM(amount) FROM Transactions WHERE (draw_date = %s OR draw_date ILIKE %s) GROUP BY type", (draw, f"%{draw}%"))
        else:
            c.execute("SELECT type, SUM(amount) FROM Transactions WHERE ((draw_date = %s OR draw_date ILIKE %s) AND username = %s) GROUP BY type", (draw, f"%{draw}%", user))
        
        data = {"2ตัวบน":0, "2ตัวล่าง":0, "3ตัวตรง":0, "3ตัวโต๊ด":0}
        for t, amt in c.fetchall():
            if t in data: data[t] = float(amt or 0)
        tot_2d = data["2ตัวบน"] + data["2ตัวล่าง"]
        tot_3d = data["3ตัวตรง"] + data["3ตัวโต๊ด"]
        
        if role == 'Admin':
            c.execute("SELECT type, num, SUM(amount), STRING_AGG(DISTINCT customer_name, ', ') FROM Transactions WHERE (draw_date = %s OR draw_date ILIKE %s) GROUP BY type, num ORDER BY SUM(amount) DESC", (draw, f"%{draw}%"))
        else:
            c.execute("SELECT type, num, SUM(amount), STRING_AGG(DISTINCT customer_name, ', ') FROM Transactions WHERE ((draw_date = %s OR draw_date ILIKE %s) AND username = %s) GROUP BY type, num ORDER BY SUM(amount) DESC", (draw, f"%{draw}%", user))
        
        dash_rows = c.fetchall()
        conn.close()

        content = Template(DASHBOARD_CONTENT).render(tot_2d=tot_2d, tot_3d=tot_3d, dash_rows=dash_rows)
        return Template(LAYOUT).render(username=user, role=role, draw_date=draw, content=content)
    except Exception as e:
        return f"Error: {str(e)}"

@app.get("/reports", response_class=HTMLResponse)
def reports_page(user: str, draw: str):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("SELECT role FROM Users WHERE username=%s", (user,))
        role = c.fetchone()[0]

        if role == 'Admin':
            c.execute("SELECT SUM(amount), SUM(discount), SUM(net) FROM Transactions WHERE (draw_date = %s OR draw_date ILIKE %s)", (draw, f"%{draw}%"))
        else:
            c.execute("SELECT SUM(amount), SUM(discount), SUM(net) FROM Transactions WHERE ((draw_date = %s OR draw_date ILIKE %s) AND username = %s)", (draw, f"%{draw}%", user))
        
        res = c.fetchone()
        rep_total_sales = float(res[0] or 0) if res and res[0] else 0.0
        rep_total_disc = float(res[1] or 0) if res and res[1] else 0.0
        rep_total_net = float(res[2] or 0) if res and res[2] else 0.0

        if role == 'Admin':
            c.execute("SELECT customer_name, COUNT(DISTINCT bill_no), SUM(amount), SUM(discount), SUM(net) FROM Transactions WHERE (draw_date = %s OR draw_date ILIKE %s) GROUP BY customer_name", (draw, f"%{draw}%"))
        else:
            c.execute("SELECT customer_name, COUNT(DISTINCT bill_no), SUM(amount), SUM(discount), SUM(net) FROM Transactions WHERE ((draw_date = %s OR draw_date ILIKE %s) AND username = %s) GROUP BY customer_name", (draw, f"%{draw}%", user))
        
        rep_customers = c.fetchall()
        conn.close()

        content = Template(REPORTS_CONTENT).render(rep_total_sales=rep_total_sales, rep_total_disc=rep_total_disc, rep_total_net=rep_total_net, rep_customers=rep_customers)
        return Template(LAYOUT).render(username=user, role=role, draw_date=draw, content=content)
    except Exception as e:
        return f"Error: {str(e)}"

@app.get("/results", response_class=HTMLResponse)
def results_page(user: str, draw: str):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("SELECT role FROM Users WHERE username=%s", (user,))
        role_res = c.fetchone()
        role = role_res[0] if role_res else "Member"
        if role != 'Admin':
            conn.close()
            return RedirectResponse(url=f"/buy?user={user}&draw={draw}", status_code=status.HTTP_303_SEE_OTHER)

        c.execute("SELECT prize_1, bottom_2 FROM DrawResults WHERE draw_date = %s OR draw_date ILIKE %s", (draw, f"%{draw}%"))
        res = c.fetchone()
        prize_1 = str(res[0]).strip() if res and res[0] else ""
        bottom_2 = str(res[1]).strip() if res and res[1] else ""

        c.execute("SELECT raw_num, status FROM BlockedNumbers WHERE draw_date = %s OR draw_date ILIKE %s", (draw, f"%{draw}%"))
        block_rows = c.fetchall()
        half_pay_numbers = set()
        for b_num, b_status in block_rows:
            if b_status != "ปิดรับ" and b_num:
                half_pay_numbers.add(str(b_num).strip())

        c.execute("SELECT SUM(amount), SUM(discount), SUM(net) FROM Transactions WHERE (draw_date = %s OR draw_date ILIKE %s)", (draw, f"%{draw}%"))
        sales_res = c.fetchone()
        total_sales = float(sales_res[0] or 0) if sales_res and sales_res[0] else 0.0
        total_discount = float(sales_res[1] or 0) if sales_res and sales_res[1] else 0.0
        total_net = float(sales_res[2] or 0) if sales_res and sales_res[2] else 0.0

        winners = []
        total_payout = 0.0
        
        c.execute("SELECT customer_name, username, num, type, amount, payout_rate FROM Transactions WHERE (draw_date = %s OR draw_date ILIKE %s)", (draw, f"%{draw}%"))
        txs = c.fetchall()
        
        for cname, uname, num, ttype, amt, rate in txs:
            amt_val = float(amt or 0)
            clean_num = str(num).strip()
            clean_type = str(ttype).strip()
            
            rate_val = float(rate or 0)
            if rate_val <= 0:
                if clean_type == "3ตัวตรง": rate_val = 500.0
                elif clean_type == "3ตัวโต๊ด": rate_val = 100.0
                elif clean_type in ["2ตัวบน", "2ตัวล่าง"]: rate_val = 70.0

            is_winner = False
            if clean_type == "3ตัวตรง" and prize_1 and clean_num == prize_1:
                is_winner = True
            elif clean_type == "3ตัวโต๊ด" and prize_1 and sorted(clean_num) == sorted(prize_1) and clean_num != prize_1:
                is_winner = True
            elif clean_type == "2ตัวบน" and prize_1 and len(prize_1) >= 2 and clean_num == prize_1[-2:]:
                is_winner = True
            elif clean_type == "2ตัวล่าง" and bottom_2 and clean_num == bottom_2:
                is_winner = True
            
            if is_winner:
                if clean_num in half_pay_numbers:
                    rate_val = rate_val / 2.0
                
                payout = amt_val * rate_val
                winners.append((cname, uname, clean_num, clean_type, amt_val, rate_val, payout))
                total_payout += payout

        c.execute("SELECT customer_name, username, COUNT(DISTINCT bill_no), SUM(amount), SUM(discount), SUM(net) FROM Transactions WHERE (draw_date = %s OR draw_date ILIKE %s) GROUP BY customer_name, username", (draw, f"%{draw}%"))
        sales_breakdown = c.fetchall()

        c.execute("SELECT customer_name, username, SUM(amount), SUM(discount) FROM Transactions WHERE (draw_date = %s OR draw_date ILIKE %s) GROUP BY customer_name, username", (draw, f"%{draw}%"))
        discount_breakdown = c.fetchall()

        conn.close()
        content = Template(RESULTS_CONTENT).render(
            username=user, draw_date=draw, prize_1=prize_1, bottom_2=bottom_2, 
            total_sales=total_sales, total_discount=total_discount, total_net=total_net, 
            winners=winners, total_payout=total_payout,
            sales_breakdown=sales_breakdown, discount_breakdown=discount_breakdown
        )
        return Template(LAYOUT).render(username=user, role=role, draw_date=draw, content=content)
    except Exception as e:
        return f"Error: {str(e)}"

@app.post("/save-results")
def save_results(user: str = Form(...), draw: str = Form(...), prize_1: str = Form(...), bottom_2: str = Form(...)):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("INSERT INTO DrawResults (draw_date, prize_1, bottom_2) VALUES (%s, %s, %s) ON CONFLICT (draw_date) DO UPDATE SET prize_1=EXCLUDED.prize_1, bottom_2=EXCLUDED.bottom_2", (draw.strip(), prize_1.strip(), bottom_2.strip()))
        conn.commit()
        conn.close()
    except: pass
    return RedirectResponse(url=f"/results?user={user}&draw={draw}&msg=บันทึกผลรางวัลสำเร็จ", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/customers", response_class=HTMLResponse)
def customers_page(user: str, draw: str, msg: str = None, error: str = None, edit_id: int = None):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("SELECT role FROM Users WHERE username=%s", (user,))
        role = c.fetchone()[0]
        
        c.execute("SELECT id, name, disc_total, pay_3d, pay_3tod, pay_2d, disc_3d, disc_2d FROM Customers WHERE owner_username=%s", (user,))
        custs_list = c.fetchall()
        if not custs_list and role == 'Admin':
            c.execute("SELECT id, name, disc_total, pay_3d, pay_3tod, pay_2d, disc_3d, disc_2d FROM Customers")
            custs_list = c.fetchall()
            
        incomplete_customers = []
        for cust in custs_list:
            if cust[3] is None or cust[4] is None or cust[5] is None or float(cust[3] or 0) <= 0 or float(cust[5] or 0) <= 0:
                incomplete_customers.append(cust)

        edit_customer = None
        if edit_id:
            c.execute("SELECT id, name, disc_total, pay_3d, pay_3tod, pay_2d, disc_3d, disc_2d FROM Customers WHERE id=%s", (edit_id,))
            edit_customer = c.fetchone()
            
        conn.close()
        content = Template(CUSTOMER_CONTENT).render(
            username=user, draw_date=draw, customers_list=custs_list, 
            edit_customer=edit_customer, incomplete_customers=incomplete_customers
        )
        return Template(LAYOUT).render(username=user, role=role, draw_date=draw, content=content, msg=msg, error=error)
    except Exception as e:
        return f"Error: {str(e)}"

@app.post("/save-customer")
def save_customer(user: str = Form(...), draw: str = Form(...), name: str = Form(...), disc_total: float = Form(0), disc_3d: float = Form(0), disc_2d: float = Form(0), pay_3d: float = Form(0), pay_3tod: float = Form(0), pay_2d: float = Form(0)):
    if not name or pay_3d is None or pay_3tod is None or pay_2d is None or pay_3d <= 0 or pay_3tod <= 0 or pay_2d <= 0:
        return RedirectResponse(url=f"/customers?user={user}&draw={draw}&error=กรุณากรอกข้อมูล ส่วนลด, อัตราจ่ายรางวัล ให้ครบถ้วน", status_code=status.HTTP_303_SEE_OTHER)

    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("INSERT INTO Customers (name, owner_username, discount_type, disc_total, disc_3d, disc_2d, pay_3d, pay_3tod, pay_2d) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", 
                  (name, user, 1, disc_total, disc_3d, disc_2d, pay_3d, pay_3tod, pay_2d))
        conn.commit()
        conn.close()
    except Exception as e:
        return RedirectResponse(url=f"/customers?user={user}&draw={draw}&error=เกิดข้อผิดพลาดในการบันทึก: {str(e)}", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url=f"/customers?user={user}&draw={draw}&msg=เพิ่มลูกค้าสำเร็จ", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/update-customer")
def update_customer(user: str = Form(...), draw: str = Form(...), customer_id: int = Form(...), name: str = Form(...), disc_total: float = Form(0), disc_3d: float = Form(0), disc_2d: float = Form(0), pay_3d: float = Form(0), pay_3tod: float = Form(0), pay_2d: float = Form(0)):
    if not name or pay_3d is None or pay_3tod is None or pay_2d is None or pay_3d <= 0 or pay_3tod <= 0 or pay_2d <= 0:
        return RedirectResponse(url=f"/customers?user={user}&draw={draw}&error=กรุณากรอกข้อมูล ส่วนลด, อัตราจ่ายรางวัล ให้ครบถ้วน", status_code=status.HTTP_303_SEE_OTHER)

    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("UPDATE Customers SET name=%s, disc_total=%s, disc_3d=%s, disc_2d=%s, pay_3d=%s, pay_3tod=%s, pay_2d=%s WHERE id=%s", 
                  (name, disc_total, disc_3d, disc_2d, pay_3d, pay_3tod, pay_2d, customer_id))
        conn.commit()
        conn.close()
    except Exception as e:
        return RedirectResponse(url=f"/customers?user={user}&draw={draw}&error=เกิดข้อผิดพลาดในการแก้ไข: {str(e)}", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url=f"/customers?user={user}&draw={draw}&msg=แก้ไขข้อมูลลูกค้าสำเร็จ", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/users", response_class=HTMLResponse)
def users_page(user: str, draw: str, msg: str = None, error: str = None):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("SELECT role FROM Users WHERE username=%s", (user,))
        role_res = c.fetchone()
        role = role_res[0] if role_res else "Member"

        target_user = user
        c.execute("SELECT id, username, role, parent_user, password, disc_total, disc_3d, disc_2d, pay_3d, pay_3tod, pay_2d FROM Users WHERE parent_user=%s OR username=%s", (target_user, target_user))
        users_list = c.fetchall()
        conn.close()

        content = Template(USERS_CONTENT).render(username=user, role=role, draw_date=draw, users_list=users_list)
        return Template(LAYOUT).render(username=user, role=role, draw_date=draw, content=content, msg=msg, error=error)
    except Exception as e:
        return f"Error: {str(e)}"

@app.post("/save-user-level")
def save_user_level(user: str = Form(...), draw: str = Form(...), new_username: str = Form(...), new_password: str = Form(...), new_role: str = Form(...), disc_total: float = Form(0), disc_3d: float = Form(0), disc_2d: float = Form(0), pay_3d: float = Form(0), pay_3tod: float = Form(0), pay_2d: float = Form(0)):
    if not new_username or not new_password or pay_3d is None or pay_3tod is None or pay_2d is None or pay_3d <= 0 or pay_3tod <= 0 or pay_2d <= 0:
        return RedirectResponse(url=f"/users?user={user}&draw={draw}&error=กรุณากรอกข้อมูล ส่วนลด, อัตราจ่ายรางวัล ให้ครบถ้วน", status_code=status.HTTP_303_SEE_OTHER)

    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("INSERT INTO Users (username, password, role, parent_user, disc_total, disc_3d, disc_2d, pay_3d, pay_3tod, pay_2d) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", 
                  (new_username, new_password, new_role, user, disc_total, disc_3d, disc_2d, pay_3d, pay_3tod, pay_2d))
        conn.commit()
        conn.close()
    except Exception as e:
        return RedirectResponse(url=f"/users?user={user}&draw={draw}&error=เกิดข้อผิดพลาดในการสร้างสมาชิก: {str(e)}", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url=f"/users?user={user}&draw={draw}&msg=สร้างสมาชิกใหม่พร้อมเรตส่วนลดสำเร็จ", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/password", response_class=HTMLResponse)
def password_page(user: str, draw: str, msg: str = None, error: str = None):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("SELECT role FROM Users WHERE username=%s", (user,))
        role = c.fetchone()[0]
        conn.close()
        
        content = Template(PASSWORD_TEMPLATE).render(username=user, draw_date=draw)
        return Template(LAYOUT).render(username=user, role=role, draw_date=draw, content=content, msg=msg, error=error)
    except Exception as e:
        return f"Error: {str(e)}"

@app.post("/update-password")
def update_password(user: str = Form(...), draw: str = Form(...), old_password: str = Form(...), new_password: str = Form(...), confirm_password: str = Form(...)):
    if new_password != confirm_password:
        return RedirectResponse(url=f"/password?user={user}&draw={draw}&error=รหัสผ่านใหม่ไม่ตรงกัน!", status_code=status.HTTP_303_SEE_OTHER)
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("SELECT id FROM Users WHERE username=%s AND password=%s", (user, old_password))
        if not c.fetchone():
            conn.close()
            return RedirectResponse(url=f"/password?user={user}&draw={draw}&error=รหัสผ่านปัจจุบันไม่ถูกต้อง!", status_code=status.HTTP_303_SEE_OTHER)
        c.execute("UPDATE Users SET password=%s WHERE username=%s", (new_password, user))
        conn.commit()
        conn.close()
        return RedirectResponse(url=f"/password?user={user}&draw={draw}&error=เปลี่ยนรหัสผ่านสำเร็จ!", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        return RedirectResponse(url=f"/password?user={user}&draw={draw}&error=เกิดข้อผิดพลาด: {str(e)}", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/logout")
def logout():
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
