from fastapi import FastAPI, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Template
import psycopg2
from datetime import datetime
import itertools

app = FastAPI(title="Lotto ERP Full Enterprise Cloud")

# ⚠ อย่าลืมเปลี่ยน [YOUR-PASSWORD] เป็นรหัสผ่านฐานข้อมูล Supabase ของคุณ
DB_URI = "postgresql://postgres.mpyswshlrxwpirzdexrn:Clublifekorat3888@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres"

def connect_db():
    return psycopg2.connect(DB_URI)

# ================= HTML Layout & Templates =================

LAYOUT = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lotto ERP Cloud</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script>
        function updateClock() {
            const now = new Date();
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            const seconds = String(now.getSeconds()).padStart(2, '0');
            const day = String(now.getDate()).padStart(2, '0');
            const month = String(now.getMonth() + 1).padStart(2, '0');
            const year = now.getFullYear() + 543;
            document.getElementById('live-clock').innerText = `🕒 ${day}/${month}/${year} ${hours}:${minutes}:${seconds}`;
        }
        setInterval(updateClock, 1000);
        window.onload = updateClock;
    </script>
</head>
<body class="bg-light">
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark px-3">
        <a class="navbar-brand fw-bold text-warning" href="/buy?user={{ username }}&draw={{ draw_date }}">☁️ Lotto ERP</a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
            <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarNav">
            <ul class="navbar-nav me-auto">
                <li class="nav-item"><a class="nav-link" href="/dashboard?user={{ username }}&draw={{ draw_date }}">📊 แดชบอร์ด</a></li>
                <li class="nav-item"><a class="nav-link" href="/buy?user={{ username }}&draw={{ draw_date }}">🛒 บันทึกโพย</a></li>
                {% if role in ['Admin', 'Master Agent'] %}
                <li class="nav-item"><a class="nav-link" href="/risk?user={{ username }}&draw={{ draw_date }}">⚠️ เช็คความเสี่ยง</a></li>
                <li class="nav-item"><a class="nav-link" href="/results?user={{ username }}&draw={{ draw_date }}">🏆 ออกผลรางวัล</a></li>
                {% endif %}
                <li class="nav-item"><a class="nav-link" href="/block?user={{ username }}&draw={{ draw_date }}">🚫 จัดการเลขอั้น</a></li>
                <li class="nav-item"><a class="nav-link" href="/customers?user={{ username }}&draw={{ draw_date }}">👥 จัดการลูกค้า</a></li>
                <li class="nav-item"><a class="nav-link" href="/users?user={{ username }}&draw={{ draw_date }}">⚙️ จัดการสมาชิก</a></li>
            </ul>
            <div class="d-flex align-items-center">
                <span id="live-clock" class="text-info fw-bold me-3 font-monospace">🕒 กำลังโหลด...</span>
                <span class="text-light me-3">ผู้ใช้: <b>{{ username }} ({{ role }})</b></span>
                <a href="/campaigns?user={{ username }}" class="btn btn-outline-warning btn-sm me-2">📌 จัดการ/เปิดงวดหวย</a>
                <a href="/logout" class="btn btn-outline-danger btn-sm">ออกจากระบบ</a>
            </div>
        </div>
    </nav>

    <div class="bg-warning text-dark text-center py-2 fw-bold shadow-sm" style="font-size: 1.1rem;">
        📌 กำลังปฏิบัติงานในงวด: <span class="text-danger text-decoration-underline">{{ draw_date }}</span>
    </div>

    <div class="container my-4">
        {% if msg %}
            <div class="alert alert-success text-center fw-bold">{{ msg }}</div>
        {% endif %}
        {% if error %}
            <div class="alert alert-danger text-center fw-bold">{{ error }}</div>
        {% endif %}
        {{ content | safe }}
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

CAMPAIGN_TEMPLATE = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>เลือกงวดหวย - Lotto ERP</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-dark text-light">
    <div class="container my-5" style="max-width: 600px;">
        <div class="card bg-secondary p-4 shadow">
            <h2 class="text-center text-warning mb-4">📌 จัดการและเลือกงวดหวย</h2>
            
            {% if role == 'Admin' %}
            <div class="card bg-dark p-3 mb-4 border border-warning">
                <h5 class="text-warning mb-3">➕ เปิดงวดหวยใหม่ (Admin)</h5>
                <form method="POST" action="/create-campaign">
                    <input type="hidden" name="user" value="{{ username }}">
                    <div class="mb-2">
                        <label class="form-label">ชื่อหวย:</label>
                        <input type="text" name="lotto_name" class="form-control" placeholder="เช่น หวยรัฐบาล, หวยลาว" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">งวดวันที่:</label>
                        <input type="text" name="draw_date" class="form-control" placeholder="เช่น 16 ตุลาคม 2026" required>
                    </div>
                    <button type="submit" class="btn btn-warning w-100 fw-bold">เปิดงวดใหม่</button>
                </form>
            </div>
            {% endif %}

            <h5 class="text-light mb-3">ราย่องวดหวยทั้งหมด</h5>
            <div class="list-group">
                {% for camp in campaigns %}
                    <a href="/buy?user={{ username }}&draw={{ camp[0] }} งวด {{ camp[1] }}" class="list-group-item list-group-item-action list-group-item-dark py-3 mb-2 text-center fs-5 fw-bold text-warning border border-light">
                        🎯 {{ camp[0] }} งวดวันที่ {{ camp[1] }}
                    </a>
                {% else %}
                    <div class="text-center text-white py-4">ยังไม่มีงวดหวยในฐานข้อมูล</div>
                {% endfor %}
            </div>
            
            <div class="text-center mt-4">
                <a href="/logout" class="btn btn-outline-danger btn-sm">ออกจากระบบ</a>
            </div>
        </div>
    </div>
</body>
</html>
"""

BUY_CONTENT = """
<div class="row">
    <div class="col-lg-8">
        <div class="card shadow p-4 mb-4">
            <form id="custForm" method="POST" action="/submit-buy">
                <input type="hidden" name="user" value="{{ username }}">
                <input type="hidden" name="draw" value="{{ draw_date }}">
                <div class="mb-3">
                    <label class="form-label fw-bold">เลือกลูกค้า / สายงาน:</label>
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
                    <label class="form-label fw-bold">คีย์รายการ (เช่น 123=100*100, 456=50 หรือ 12,34=50):</label>
                    <input type="text" name="raw_input" class="form-control form-control-lg" placeholder="พิมพ์เลขและราคา..." required autofocus>
                    <div class="form-text text-danger">*ห้ามใส่ลูกน้ำในยอดเงิน เช่น 1000 ห้ามพิมพ์ 1,000</div>
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
            <h4 class="text-primary mb-3">📋 1. รายการร่าง (รอยืนยัน)</h4>
            <div class="table-responsive">
                <table class="table table-striped table-bordered text-center align-middle">
                    <thead class="table-dark">
                        <tr><th>เลข</th><th>บน / ตรง</th><th>ล่าง / โต๊ด</th><th>สถานะเลขอั้น</th></tr>
                    </thead>
                    <tbody>
                        {% for d in drafts %}
                        <tr>
                            <td><b>{{ d[1] }}</b></td>
                            <td>{{ d[2] if d[2] and d[2] > 0 else '-' }}</td>
                            <td>{{ d[3] if d[3] and d[3] > 0 else '-' }}</td>
                            <td><span class="badge bg-danger">{{ d[4] }}</span></td>
                        </tr>
                        {% else %}
                        <tr><td colspan="4" class="text-muted">ยังไม่มีรายการในร่าง</td></tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% if drafts %}
            <form method="POST" action="/confirm-bill">
                <input type="hidden" name="user" value="{{ username }}">
                <input type="hidden" name="draw" value="{{ draw_date }}">
                <input type="hidden" name="customer_info" value="{{ selected_target_raw }}">
                <button type="submit" class="btn btn-primary btn-lg w-100 fw-bold">✅ ยืนยันโพยเข้าระบบ</button>
            </form>
            {% endif %}
        </div>

        <div class="card shadow p-4">
            <h4 class="text-success mb-3">📜 2. บิลล่าสุดของลูกค้ารายนี้</h4>
            <div class="table-responsive">
                <table class="table table-striped table-bordered text-center align-middle">
                    <thead class="table-success">
                        <tr><th>เลขที่บิล</th><th>เวลา</th><th>เลข</th><th>ยอดซื้อ</th><th>สถานะ</th></tr>
                    </thead>
                    <tbody>
                        {% for s in saved_bills %}
                        <tr>
                            <td>{{ s[0] }}</td><td>{{ s[1] }}</td><td><b>{{ s[2] }}</b></td><td>{{ "{:,.2f}".format(s[3] or 0) }}</td><td>{{ s[4] }}</td>
                        </tr>
                        {% else %}
                        <tr><td colspan="5" class="text-muted">ยังไม่มีประวัติบิลในงวดนี้</td></tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <div class="col-lg-4">
        <div class="card shadow p-3 bg-white mb-4">
            <h5 class="text-danger fw-bold mb-3">🚫 เลขอั้น (งวดปัจจุบัน)</h5>
            <label class="fw-bold text-dark mb-1">เลขอั้นปิดรับ:</label>
            <textarea class="form-control mb-2 bg-light text-danger fw-bold" rows="3" readonly>{{ block_closed }}</textarea>
            <label class="fw-bold text-dark mb-1">เลขอั้น 3 ตัว (จ่ายครึ่ง):</label>
            <textarea class="form-control mb-2 bg-light" rows="4" readonly>{{ block_3d }}</textarea>
            <label class="fw-bold text-dark mb-1">เลขอั้น 2 ตัว (จ่ายครึ่ง):</label>
            <textarea class="form-control bg-light" rows="4" readonly>{{ block_2d }}</textarea>
        </div>
    </div>
</div>
"""

DASHBOARD_CONTENT = """
<div class="card shadow p-4">
    <h2 class="text-primary mb-4">📊 สรุปยอดขายรวมประจำงวด</h2>
    <div class="row text-center mb-4">
        <div class="col-md-6 mb-3">
            <div class="p-3 bg-warning text-dark rounded shadow fw-bold fs-4">ยอดรวม 2 ตัว: ฿{{ "{:,.2f}".format(tot_2d) }}</div>
        </div>
        <div class="col-md-6 mb-3">
            <div class="p-3 bg-warning text-dark rounded shadow fw-bold fs-4">ยอดรวม 3 ตัว: ฿{{ "{:,.2f}".format(tot_3d) }}</div>
        </div>
    </div>
    <h4 class="mb-3">รายละเอียดหมายเลขที่มียอดซื้อ</h4>
    <div class="table-responsive">
        <table class="table table-striped table-bordered text-center align-middle">
            <thead class="table-dark">
                <tr><th>ประเภท</th><th>ตัวเลข</th><th>ยอดซื้อรวม</th><th>ผู้ซื้อ</th></tr>
            </thead>
            <tbody>
                {% for r in dash_rows %}
                <tr>
                    <td>{{ r[0] }}</td><td><b>{{ r[1] }}</b></td><td>{{ "{:,.2f}".format(r[2] or 0) }}</td><td>{{ r[3] }}</td>
                </tr>
                {% else %}
                <tr><td colspan="4" class="text-muted">ยังไม่มีรายการซื้อในงวดนี้</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
"""

RISK_CONTENT = """
<div class="card shadow p-4">
    <h2 class="text-danger mb-4">⚠️ ตรวจสอบความเสี่ยงและยอดแทงรวม (Admin Control)</h2>
    <div class="table-responsive">
        <table class="table table-striped table-bordered text-center align-middle">
            <thead class="table-dark">
                <tr><th>ประเภท</th><th>ตัวเลข</th><th>ยอดแทงรวมสุทธิ</th><th>สถานะความเสี่ยง</th></tr>
            </thead>
            <tbody>
                {% for r in risk_rows %}
                <tr {% if r[2] and r[2] > 5000 %}class="table-danger"{% endif %}>
                    <td>{{ r[0] }}</td>
                    <td><b>{{ r[1] }}</b></td>
                    <td>{{ "{:,.2f}".format(r[2] or 0) }}</td>
                    <td>
                        {% if r[2] and r[2] > 5000 %}
                            <span class="badge bg-danger">⚠️ ยอดสูงเกินเพดาน (ความเสี่ยงสูง)</span>
                        {% else %}
                            <span class="badge bg-success">ปกติ</span>
                        {% endif %}
                    </td>
                </tr>
                {% else %}
                <tr><td colspan="4" class="text-muted">ยังไม่มีข้อมูลการแทงในงวดนี้</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
"""

RESULTS_CONTENT = """
<div class="card shadow p-4 mb-4">
    <h2 class="text-success mb-3">🏆 บันทึกผลการออกรางวัลประจำงวด</h2>
    <form method="POST" action="/save-results" class="row g-3">
        <input type="hidden" name="user" value="{{ username }}">
        <input type="hidden" name="draw" value="{{ draw_date }}">
        <div class="col-md-6">
            <label class="form-label fw-bold">รางวัลที่ 1 (3 ตัวตรง):</label>
            <input type="text" name="prize_1" class="form-control form-control-lg" value="{{ prize_1 }}" placeholder="เช่น 123" required>
        </div>
        <div class="col-md-6">
            <label class="form-label fw-bold">เลขท้าย 2 ตัว:</label>
            <input type="text" name="bottom_2" class="form-control form-control-lg" value="{{ bottom_2 }}" placeholder="เช่น 45" required>
        </div>
        <div class="col-12">
            <button type="submit" class="btn btn-success btn-lg w-100 fw-bold">💾 บันทึกผลรางวัลและคำนวณสรุปยอด</button>
        </div>
    </form>
</div>

<div class="card shadow p-4">
    <h3 class="text-primary mb-3">📊 สรุปผลกำไร / ขาดทุน และรายงานผลรางวัล</h3>
    <div class="row text-center mb-4">
        <div class="col-md-4 mb-2"><div class="p-3 bg-light border rounded"><h5>ยอดขายรวม</h5><h3 class="text-dark">฿{{ "{:,.2f}".format(total_sales) }}</h3></div></div>
        <div class="col-md-4 mb-2"><div class="p-3 bg-light border rounded"><h5>หักส่วนลดรวม</h5><h3 class="text-danger">฿{{ "{:,.2f}".format(total_discount) }}</h3></div></div>
        <div class="col-md-4 mb-2"><div class="p-3 bg-light border rounded"><h5>ยอดขายสุทธิ (คงเหลือ)</h5><h3 class="text-primary">฿{{ "{:,.2f}".format(total_net) }}</h3></div></div>
    </div>
    <div class="row text-center mb-4">
        <div class="col-md-6 mb-2"><div class="p-3 bg-light border rounded"><h5>จ่ายเงินรางวัลรวม</h5><h3 class="text-danger">฿{{ "{:,.2f}".format(total_payout) }}</h3></div></div>
        <div class="col-md-6 mb-2"><div class="p-3 bg-warning text-dark border rounded"><h5>กำไร / ขาดทุนสุทธิ</h5><h3 class="fw-bold">฿{{ "{:,.2f}".format(total_net - total_payout) }}</h3></div></div>
    </div>

    <h4 class="mt-4 mb-3">รายชื่อผู้ถูกรางวัลในงวดนี้</h4>
    <div class="table-responsive">
        <table class="table table-striped table-bordered text-center align-middle">
            <thead class="table-dark">
                <tr><th>ผู้ซื้อ / ลูกค้า</th><th>เลขอั้น/เลขที่ซื้อ</th><th>ประเภท</th><th>ยอดซื้อ</th><th>เงินรางวัลที่ได้รับ</th></tr>
            </thead>
            <tbody>
                {% for w in winners %}
                <tr>
                    <td>{{ w[0] }}</td><td><b>{{ w[1] }}</b></td><td>{{ w[2] }}</td><td>{{ "{:,.2f}".format(w[3] or 0) }}</td><td class="text-success fw-bold">฿{{ "{:,.2f}".format(w[4] or 0) }}</td>
                </tr>
                {% else %}
                <tr><td colspan="5" class="text-muted">ยังไม่มีผู้ถูกรางวัล หรือยังไม่ได้บันทึกผลรางวัล</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
"""

BLOCK_CONTENT = """
<div class="card shadow p-4">
    <h3 class="text-danger mb-3">🚫 จัดการเลขอั้น</h3>
    <form method="POST" action="/save-block" class="row g-3 mb-4">
        <input type="hidden" name="user" value="{{ username }}">
        <input type="hidden" name="draw" value="{{ draw_date }}">
        <div class="col-md-4">
            <label class="form-label fw-bold">พิมพ์เลข (คั่นด้วย ,):</label>
            <input type="text" name="raw_nums" class="form-control" placeholder="เช่น 123, 456" required>
        </div>
        <div class="col-md-3">
            <label class="form-label fw-bold">สถานะอั้น:</label>
            <select name="block_status" class="form-select">
                <option value="อั้นจ่ายครึ่ง">อั้นจ่ายครึ่ง</option>
                <option value="ปิดรับ">ปิดรับ</option>
            </select>
        </div>
        <div class="col-md-3 d-flex align-items-end">
            <div class="form-check">
                <input class="form-check-input" type="checkbox" name="do_perm" value="1" id="permCheck">
                <label class="form-check-label fw-bold" for="permCheck">อั้นกลับด้วย (6กลับ)</label>
            </div>
        </div>
        <div class="col-md-2 d-flex align-items-end">
            <button type="submit" class="btn btn-danger w-100 fw-bold">บันทึกลงระบบ</button>
        </div>
    </form>
    
    <h4 class="mb-3">รายการเลขอั้นในระบบ</h4>
    <div class="table-responsive">
        <table class="table table-striped table-bordered text-center align-middle">
            <thead class="table-dark">
                <tr><th>เลข (อั้น)</th><th>ประเภท</th><th>สถานะ</th><th>จัดการ</th></tr>
            </thead>
            <tbody>
                {% for b in blocks %}
                <tr>
                    <td><b>{{ b[1] }}</b></td><td>{{ b[2] }}</td><td><span class="badge bg-danger">{{ b[3] }}</span></td>
                    <td><a href="/delete-block?id={{ b[0] }}&user={{ username }}&draw={{ draw_date }}" class="btn btn-outline-danger btn-sm">ลบ</a></td>
                </tr>
                {% else %}
                <tr><td colspan="4" class="text-muted">ยังไม่มีเลขอั้นในงวดนี้</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
"""

CUSTOMER_CONTENT = """
<div class="row">
    <div class="col-md-4 mb-4">
        <div class="card shadow p-4">
            <h4 class="text-success mb-3">➕ เพิ่มลูกค้ารายใหม่</h4>
            <form method="POST" action="/save-customer">
                <input type="hidden" name="user" value="{{ username }}">
                <input type="hidden" name="draw" value="{{ draw_date }}">
                <div class="mb-3">
                    <label class="form-label fw-bold">ชื่อลูกค้า:</label>
                    <input type="text" name="name" class="form-control" required>
                </div>
                <div class="mb-3">
                    <label class="form-label fw-bold">ส่วนลดรวม (%):</label>
                    <input type="number" step="0.01" name="disc_total" class="form-control" value="0">
                </div>
                <div class="row mb-3">
                    <div class="col"><label class="form-label">จ่าย 3 ตรง:</label><input type="number" step="0.01" name="pay_3d" class="form-control" value="0"></div>
                    <div class="col"><label class="form-label">จ่าย 3 โต๊ด:</label><input type="number" step="0.01" name="pay_3tod" class="form-control" value="0"></div>
                </div>
                <div class="mb-3">
                    <label class="form-label">จ่าย 2 ตัว:</label><input type="number" step="0.01" name="pay_2d" class="form-control" value="0">
                </div>
                <button type="submit" class="btn btn-success w-100 fw-bold">บันทึกลูกค้า</button>
            </form>
        </div>
    </div>
    <div class="col-md-8">
        <div class="card shadow p-4">
            <h4 class="text-primary mb-3">👥 รายชื่อลูกค้าของคุณ</h4>
            <div class="table-responsive">
                <table class="table table-striped table-bordered text-center align-middle">
                    <thead class="table-dark">
                        <tr><th>ID</th><th>ชื่อลูกค้า</th><th>ส่วนลด (%)</th><th>จ่าย 3 ตรง</th><th>จ่าย 3 โต๊ด</th><th>จ่าย 2 ตัว</th></tr>
                    </thead>
                    <tbody>
                        {% for c in customers_list %}
                        <tr>
                            <td>{{ c[0] }}</td><td><b>{{ c[1] }}</b></td><td>{{ c[2] }}</td><td>{{ c[3] }}</td><td>{{ c[4] }}</td><td>{{ c[5] }}</td>
                        </tr>
                        {% else %}
                        <tr><td colspan="6" class="text-muted">ยังไม่มีรายชื่อลูกค้า</td></tr>
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
    <div class="col-md-4 mb-4">
        <div class="card shadow p-4">
            <h4 class="text-success mb-3">⚙️ สร้างสายงานสมาชิก (4 ระดับ)</h4>
            <form method="POST" action="/save-user-level">
                <input type="hidden" name="user" value="{{ username }}">
                <input type="hidden" name="draw" value="{{ draw_date }}">
                <div class="mb-3">
                    <label class="form-label fw-bold">Username:</label>
                    <input type="text" name="new_username" class="form-control" required>
                </div>
                <div class="mb-3">
                    <label class="form-label fw-bold">Password:</label>
                    <input type="password" name="new_password" class="form-control" required>
                </div>
                <div class="mb-3">
                    <label class="form-label fw-bold">ระดับสิทธิ์ (Role):</label>
                    <select name="new_role" class="form-select">
                        <option value="Admin">Admin</option>
                        <option value="Master Agent">Master Agent</option>
                        <option value="Agent">Agent</option>
                        <option value="Member">Member</option>
                    </select>
                </div>
                <button type="submit" class="btn btn-success w-100 fw-bold">บันทึกสมาชิกใหม่</button>
            </form>
        </div>
    </div>
    <div class="col-md-8">
        <div class="card shadow p-4">
            <h4 class="text-primary mb-3">🗂️ รายชื่อสมาชิกใต้สายงาน</h4>
            <div class="table-responsive">
                <table class="table table-striped table-bordered text-center align-middle">
                    <thead class="table-dark">
                        <tr><th>ID</th><th>Username</th><th>ระดับสิทธิ์</th><th>ผู้ดูแล (Parent)</th></tr>
                    </thead>
                    <tbody>
                        {% for u in users_list %}
                        <tr>
                            <td>{{ u[0] }}</td><td><b>{{ u[1] }}</b></td><td><span class="badge bg-secondary">{{ u[2] }}</span></td><td>{{ u[3] }}</td>
                        </tr>
                        {% else %}
                        <tr><td colspan="4" class="text-muted">ยังไม่มีสมาชิกในสายงาน</td></tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>
"""

def get_blocked_display_data(draw_date):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("SELECT DISTINCT raw_num, status, type FROM BlockedNumbers WHERE draw_date = %s OR draw_date ILIKE %s", (draw_date, f"%{draw_date}%"))
        rows = c.fetchall()
        conn.close()
        l_c = [r[0] for r in rows if r[1]=="ปิดรับ"]
        l_3 = [r[0] for r in rows if r[1]!="ปิดรับ" and (r[2]=="3ตัว" or len(r[0])==3)]
        l_2 = [r[0] for r in rows if r[1]!="ปิดรับ" and (r[2]=="2ตัว" or len(r[0])==2)]
        return ", ".join(l_c), ", ".join(l_3), ", ".join(l_2)
    except:
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

        c.execute("SELECT lotto_name, draw_date FROM LotteryCampaigns ORDER BY id DESC")
        campaigns = c.fetchall()
        conn.close()
        return Template(CAMPAIGN_TEMPLATE).render(username=user, role=role, campaigns=campaigns)
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
        if not custs:
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

        drafts, saved_bills = [], []
        if c_id:
            c.execute("SELECT id, num, amt_teng, amt_tod, type FROM TempDraft WHERE username=%s AND customer_id=%s AND customer_type=%s", (user, c_id, c_type))
            drafts = c.fetchall()
            c.execute("SELECT bill_no, timestamp, num, amount, status FROM Transactions WHERE (draw_date = %s OR draw_date ILIKE %s) AND username=%s AND customer_id=%s AND customer_type=%s ORDER BY id DESC LIMIT 20", (draw, f"%{draw}%", user, c_id, c_type))
            saved_bills = c.fetchall()

        conn.close()
        b_closed, b_3d, b_2d = get_blocked_display_data(draw)

        content = Template(BUY_CONTENT).render(
            username=user, draw_date=draw, customers=all_targets, selected_target_raw=selected, 
            selected_c_id=selected_c_id, drafts=drafts, saved_bills=saved_bills,
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
        print("Add Draft Error:", e)
    return RedirectResponse(url=f"/buy?user={user}&draw={draw}&selected={customer_info}", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/confirm-bill")
def confirm_bill(user: str = Form(...), draw: str = Form(...), customer_info: str = Form(...)):
    parts = customer_info.split('|')
    c_id, c_name, c_type = parts[0], parts[1], parts[2]
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("SELECT num, type, amt_teng, amt_tod FROM TempDraft WHERE username=%s AND customer_id=%s AND customer_type=%s", (user, c_id, c_type))
        drafts = c.fetchall()
        if drafts:
            bill_no = f"B-{datetime.now().strftime('%H%M%S')}"
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for n, t_type, a1, a2 in drafts:
                amt = float(a1 or 0) if float(a1 or 0) > 0 else float(a2 or 0)
                c.execute("INSERT INTO Transactions (draw_date, timestamp, username, customer_id, customer_name, customer_type, bill_no, num, type, amount, status, discount, net, payout_rate) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", 
                          (draw, ts, user, int(c_id), c_name, c_type, bill_no, n, t_type, amt, "ปกติ", 0.0, amt, 0.0))
            c.execute("DELETE FROM TempDraft WHERE username=%s AND customer_id=%s AND customer_type=%s", (user, c_id, c_type))
            conn.commit()
        conn.close()
    except: pass
    return RedirectResponse(url=f"/buy?user={user}&draw={draw}&selected={customer_info}&msg=บันทึกบิลสำเร็จ!", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(user: str, draw: str):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("SELECT role FROM Users WHERE username=%s", (user,))
        role = c.fetchone()[0]

        c.execute("SELECT type, SUM(amount) FROM Transactions WHERE (draw_date = %s OR draw_date ILIKE %s) GROUP BY type", (draw, f"%{draw}%"))
        data = {"2ตัวบน":0, "2ตัวล่าง":0, "3ตัวตรง":0, "3ตัวโต๊ด":0}
        for t, amt in c.fetchall():
            if t in data: data[t] = float(amt or 0)
        tot_2d = data["2ตัวบน"] + data["2ตัวล่าง"]
        tot_3d = data["3ตัวตรง"] + data["3ตัวโต๊ด"]
        
        c.execute("SELECT type, num, SUM(amount), STRING_AGG(DISTINCT customer_name, ', ') FROM Transactions WHERE (draw_date = %s OR draw_date ILIKE %s) GROUP BY type, num ORDER BY SUM(amount) DESC", (draw, f"%{draw}%"))
        dash_rows = c.fetchall()
        conn.close()

        content = Template(DASHBOARD_CONTENT).render(tot_2d=tot_2d, tot_3d=tot_3d, dash_rows=dash_rows)
        return Template(LAYOUT).render(username=user, role=role, draw_date=draw, content=content)
    except Exception as e:
        return f"Error: {str(e)}"

@app.get("/risk", response_class=HTMLResponse)
def risk_page(user: str, draw: str):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("SELECT role FROM Users WHERE username=%s", (user,))
        role = c.fetchone()[0]

        c.execute("SELECT type, num, SUM(amount) FROM Transactions WHERE (draw_date = %s OR draw_date ILIKE %s) GROUP BY type, num ORDER BY SUM(amount) DESC", (draw, f"%{draw}%"))
        risk_rows = c.fetchall()
        conn.close()

        content = Template(RISK_CONTENT).render(risk_rows=risk_rows)
        return Template(LAYOUT).render(username=user, role=role, draw_date=draw, content=content)
    except Exception as e:
        return f"Error: {str(e)}"

@app.get("/results", response_class=HTMLResponse)
def results_page(user: str, draw: str):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("SELECT role FROM Users WHERE username=%s", (user,))
        role = c.fetchone()[0]

        c.execute("SELECT prize_1, bottom_2 FROM DrawResults WHERE draw_date = %s", (draw,))
        res = c.fetchone()
        prize_1 = res[0] if res else ""
        bottom_2 = res[1] if res else ""

        c.execute("SELECT SUM(amount), SUM(discount), SUM(net) FROM Transactions WHERE (draw_date = %s OR draw_date ILIKE %s)", (draw, f"%{draw}%"))
        sales_res = c.fetchone()
        total_sales = float(sales_res[0] or 0)
        total_discount = float(sales_res[1] or 0)
        total_net = float(sales_res[2] or 0)

        winners = []
        total_payout = 0.0
        if prize_1 and bottom_2:
            c.execute("SELECT customer_name, num, type, amount FROM Transactions WHERE (draw_date = %s OR draw_date ILIKE %s)", (draw, f"%{draw}%"))
            txs = c.fetchall()
            for cname, num, ttype, amt in txs:
                payout = 0.0
                amt_val = float(amt or 0)
                if ttype == "3ตัวตรง" and num == prize_1:
                    payout = amt_val * 500
                elif ttype == "3ตัวโต๊ด" and sorted(num) == sorted(prize_1) and num != prize_1:
                    payout = amt_val * 100
                elif ttype == "2ตัวบน" and num == prize_1[-2:]:
                    payout = amt_val * 90
                elif ttype == "2ตัวล่าง" and num == bottom_2:
                    payout = amt_val * 90
                
                if payout > 0:
                    winners.append((cname, num, ttype, amt_val, payout))
                    total_payout += payout

        conn.close()
        content = Template(RESULTS_CONTENT).render(
            prize_1=prize_1, bottom_2=bottom_2, total_sales=total_sales, 
            total_discount=total_discount, total_net=total_net, winners=winners, total_payout=total_payout
        )
        return Template(LAYOUT).render(username=user, role=role, draw_date=draw, content=content)
    except Exception as e:
        return f"Error: {str(e)}"

@app.post("/save-results")
def save_results(user: str = Form(...), draw: str = Form(...), prize_1: str = Form(...), bottom_2: str = Form(...)):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("INSERT INTO DrawResults (draw_date, prize_1, bottom_2) VALUES (%s, %s, %s) ON CONFLICT (draw_date) DO UPDATE SET prize_1=EXCLUDED.prize_1, bottom_2=EXCLUDED.bottom_2", (draw, prize_1, bottom_2))
        conn.commit()
        conn.close()
    except: pass
    return RedirectResponse(url=f"/results?user={user}&draw={draw}&msg=บันทึกผลรางวัลสำเร็จ", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/block", response_class=HTMLResponse)
def block_page(user: str, draw: str, msg: str = None):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("SELECT role FROM Users WHERE username=%s", (user,))
        role = c.fetchone()[0]
        c.execute("SELECT id, perm_num, type, status FROM BlockedNumbers WHERE (draw_date = %s OR draw_date ILIKE %s) ORDER BY id DESC", (draw, f"%{draw}%"))
        blocks = c.fetchall()
        conn.close()
        content = Template(BLOCK_CONTENT).render(username=user, draw_date=draw, blocks=blocks)
        return Template(LAYOUT).render(username=user, role=role, draw_date=draw, content=content, msg=msg)
    except Exception as e:
        return f"Error: {str(e)}"

@app.post("/save-block")
def save_block(user: str = Form(...), draw: str = Form(...), raw_nums: str = Form(...), block_status: str = Form(...), do_perm: str = Form(None)):
    try:
        conn = connect_db()
        c = conn.cursor()
        for num in raw_nums.split(','):
            num = num.strip()
            if num:
                perms = list(set([''.join(p) for p in itertools.permutations(num)])) if do_perm else [num]
                for p in perms:
                    t = "3ตัว" if len(p)==3 else "2ตัว"
                    c.execute("INSERT INTO BlockedNumbers (draw_date, raw_num, perm_num, type, status, custom_rate) VALUES (%s,%s,%s,%s,%s,%s)", (draw, num, p, t, block_status, 0.0))
        conn.commit()
        conn.close()
    except: pass
    return RedirectResponse(url=f"/block?user={user}&draw={draw}&msg=บันทึกเลขอั้นสำเร็จ", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/delete-block")
def delete_block(id: int, user: str, draw: str):
    try:
        conn = connect_db()
        conn.cursor().execute("DELETE FROM BlockedNumbers WHERE id=%s", (id,))
        conn.commit()
        conn.close()
    except: pass
    return RedirectResponse(url=f"/block?user={user}&draw={draw}&msg=ลบเลขอั้นเรียบร้อย", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/customers", response_class=HTMLResponse)
def customers_page(user: str, draw: str, msg: str = None):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("SELECT role FROM Users WHERE username=%s", (user,))
        role = c.fetchone()[0]
        c.execute("SELECT id, name, disc_total, pay_3d, pay_3tod, pay_2d FROM Customers WHERE owner_username=%s", (user,))
        custs_list = c.fetchall()
        if not custs_list:
            c.execute("SELECT id, name, disc_total, pay_3d, pay_3tod, pay_2d FROM Customers")
            custs_list = c.fetchall()
        conn.close()
        content = Template(CUSTOMER_CONTENT).render(username=user, draw_date=draw, customers_list=custs_list)
        return Template(LAYOUT).render(username=user, role=role, draw_date=draw, content=content, msg=msg)
    except Exception as e:
        return f"Error: {str(e)}"

@app.post("/save-customer")
def save_customer(user: str = Form(...), draw: str = Form(...), name: str = Form(...), disc_total: float = Form(0), pay_3d: float = Form(0), pay_3tod: float = Form(0), pay_2d: float = Form(0)):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("INSERT INTO Customers (name, owner_username, discount_type, disc_total, pay_3d, pay_3tod, pay_2d) VALUES (%s,%s,%s,%s,%s,%s,%s)", 
                  (name, user, 1, disc_total, pay_3d, pay_3tod, pay_2d))
        conn.commit()
        conn.close()
    except: pass
    return RedirectResponse(url=f"/customers?user={user}&draw={draw}&msg=เพิ่มลูกค้าสำเร็จ", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/users", response_class=HTMLResponse)
def users_page(user: str, draw: str, msg: str = None):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("SELECT role FROM Users WHERE username=%s", (user,))
        role = c.fetchone()[0]
        c.execute("SELECT id, username, role, parent_user FROM Users WHERE parent_user=%s OR username=%s", (user, user))
        users_list = c.fetchall()
        conn.close()
        content = Template(USERS_CONTENT).render(username=user, draw_date=draw, users_list=users_list)
        return Template(LAYOUT).render(username=user, role=role, draw_date=draw, content=content, msg=msg)
    except Exception as e:
        return f"Error: {str(e)}"

@app.post("/save-user-level")
def save_user_level(user: str = Form(...), draw: str = Form(...), new_username: str = Form(...), new_password: str = Form(...), new_role: str = Form(...)):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute("INSERT INTO Users (username, password, role, parent_user) VALUES (%s, %s, %s, %s)", (new_username, new_password, new_role, user))
        conn.commit()
        conn.close()
    except: pass
    return RedirectResponse(url=f"/users?user={user}&draw={draw}&msg=สร้างสมาชิกใหม่สำเร็จ", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/logout")
def logout():
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
