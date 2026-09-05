#!/usr/bin/env python3
"""Bộ test cho wp-code-optimizer. Chỉ dùng thư viện chuẩn, chạy được trên
Windows lẫn Linux, không cần cài gì.

    python tests/chay_test.py

Mỗi test khẳng định một KẾT QUẢ CỤ THỂ, không phải "chạy không lỗi". Ba lỗi P0
đã từng lọt qua vì người viết nhìn output bằng mắt rồi gật đầu — nhìn bằng mắt
không phải phép kiểm.

Mã thoát: 0 tất cả đạt · 1 có test hỏng.
"""
import io
import os
import re
import subprocess
import sys
import tempfile

GOC = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(GOC)
SCRIPTS = os.path.join(REPO, "skills", "wp-code-cleaner", "scripts")
FX = os.path.join(GOC, "fixtures")

dat, hong = [], []


def kiem(ten, dieu_kien, chi_tiet=""):
    (dat if dieu_kien else hong).append((ten, chi_tiet))
    print(f"  {'đạt ' if dieu_kien else 'HỎNG'}  {ten}" + (f"   {chi_tiet}" if not dieu_kien else ""))


def chay(script, *args):
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, script)] + list(args),
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return r.returncode, (r.stdout or "") + (r.stderr or "")


# ───────────────────────────────────────────────────── quet_chet.py
print("\nquet_chet.py — đồ thị khả dụng")
ma, ra = chay("quet_chet.py", "--theme", os.path.join(FX, "php"), "--tien-to", "fx_")

chet = set(re.findall(r"^   (\S+\.php)\s+\d+ dòng", ra, re.M))

# Mọi dạng require phải được nhìn thấy. Thiếu một dạng = một file bị báo chết oan.
for f in ["inc/qua-dir.php", "inc/qua-hang-so.php", "inc/qua-ham.php",
          "inc/duong-dan-tran.php", "inc/require-khong-once.php",
          "inc/qua-include-once.php", "inc/co-dieu-kien.php"]:
    kiem(f"require nhìn thấy: {f}", f not in chet, f"bị báo chết oan")

kiem("template-part được get_template_part thì sống",
     "template-parts/duoc-goi.php" not in chet)
kiem("get_template_part có hậu tố (slug) cũng lần được",
     "template-parts/co-hau-ban.php" not in chet)
kiem("template-part mồ côi bị bắt", "template-parts/mo-coi.php" in chet)

kiem("file có hook mà KHÔNG ai nạp bị bắt", "inc/hook-khong-ai-nap.php" in chet)
kiem("và nó nằm ở mục 2 (nguy hiểm nhất)",
     re.search(r"2\. FILE ĐĂNG KÝ HOOK.*?inc/hook-khong-ai-nap\.php", ra, re.S) is not None)

kiem("chữ 'required' trong HTML/mảng KHÔNG bị đếm thành require",
     "1 câu require/include KHÔNG phân giải được" in ra,
     "đếm sai số require động — đúng ra chỉ có 1")

kiem("hàm PHP đang được gọi thì không bị báo chết", "fx_ham_php_that" not in ra)
kiem("hàm JavaScript trong <script> không bị đếm là hàm PHP", "fxJsOnly" not in ra)

ma2, ra2 = chay("quet_chet.py", "--theme", os.path.join(FX, "php"), "--loader", "khong-co.php")
kiem("thiếu loader thì cảnh báo to, không im lặng",
     "KHÔNG TÌM THẤY" in ra2 and "dừng đọc ở đây" in ra2)

# ───────────────────────────────────────────────────── go_css.py
print("\ngo_css.py — gỡ CSS chết")
css_dir = os.path.join(FX, "css")
css_file = os.path.join(css_dir, "assets", "css", "main.css")
goc_css = io.open(css_file, encoding="utf-8").read()

ma, ra = chay("go_css.py", "--theme", css_dir, "--css", "assets/css/main.css",
              "--tien-to", "fx-")

kiem("mặc định KHÔNG ghi file (phải truyền --ghi)",
     io.open(css_file, encoding="utf-8").read() == goc_css,
     "file đã bị đổi dù không có --ghi")
kiem("có in [CHẠY THỬ]", "[CHẠY THỬ]" in ra)
kiem("hiệu chuẩn: bản hỏng FAIL, bản thật PASS",
     "bản hỏng: FAIL" in ra and "bản thật: PASS" in ra)

# Ghi ra thư mục tạm để kiểm nội dung, không đụng fixture
with tempfile.TemporaryDirectory() as tmp:
    import shutil
    tam = os.path.join(tmp, "css")
    shutil.copytree(css_dir, tam)
    ma, ra = chay("go_css.py", "--theme", tam, "--css", "assets/css/main.css",
                  "--tien-to", "fx-", "--ghi")
    sau = io.open(os.path.join(tam, "assets", "css", "main.css"), encoding="utf-8").read()

kiem("dấu phẩy trong :is() KHÔNG bị cắt -> không sinh selector rác",
     ".bar)" not in sau and ".b)" not in sau,
     "selector bị cắt nát, đây đúng là lỗi P0 cũ")
kiem("rule chết trong :is() bị bỏ", ".fx-chet:is(" not in sau)
kiem("rule chết trong :not() bị bỏ", ".fx-chet:not(" not in sau)
kiem("rule chết trong :where() bị bỏ", ".fx-chet:where(" not in sau)
kiem("rule chết trong :has() bị bỏ", ".fx-chet:has(" not in sau)
kiem("dấu phẩy trong [attr] không bị cắt", 'data-list="a,b,c"' in sau)
kiem("vế sống trong danh sách selector được giữ", ".fx-song__b" in sau)
kiem("vế chết trong danh sách selector bị bỏ", ".fx-chet__a" not in sau)
kiem("content:'}{' không làm lệch phép đếm ngoặc", 'content: "}{"' in sau)
kiem("tên ghép chuỗi .fx-bac--N được GIỮ (luật bảo vệ gốc tên)",
     ".fx-bac--1" in sau and ".fx-bac--2" in sau,
     "đã xoá nhầm nhãn đang hiện trên trang")
kiem("@media lồng @supports là hợp lệ, không bị coi là khối bị nuốt",
     "@supports" in sau)
kiem("@layer giữ vế sống, bỏ vế chết",
     ".fx-song__l" in sau and ".fx-chet__l" not in sau)
kiem("@media chỉ chứa rule chết thì bỏ cả khối", "@media print" not in sau)
kiem("@font-face không có class thì không đụng tới", "@font-face" in sau)
kiem("ngoặc nhọn cân bằng sau khi ghi", sau.count("{") == sau.count("}"))

# Ca hỏng cố ý: at-rule bị nuốt vào giữa một style rule -> phải chặn
with tempfile.TemporaryDirectory() as tmp:
    import shutil
    tam = os.path.join(tmp, "css")
    shutil.copytree(css_dir, tam)
    p = os.path.join(tam, "assets", "css", "main.css")
    s = io.open(p, encoding="utf-8").read().replace(
        '.fx-song--x { color: green }',
        '.fx-song--x { color: green; @media print { .x{a:b} }')
    io.open(p, "w", encoding="utf-8").write(s)
    ma, ra = chay("go_css.py", "--theme", tam, "--css", "assets/css/main.css",
                  "--tien-to", "fx-", "--ghi")
    kiem("CSS đầu vào đã hỏng thì TỪ CHỐI ghi", "không ghi" in ra and ma != 0)

# ───────────────────────────────────────────────────── doi_chung_live.py
print("\ndoi_chung_live.py — fail-closed")
ma, ra = chay("doi_chung_live.py")
kiem("không truyền gì thì KHÔNG được báo 'sạch'",
     "KHONG_KIEM_DUOC" in ra and "NOT_TESTED" in ra and ma != 0,
     f"exit={ma} — fail-open, đây là lỗi P0 cũ")

# ───────────────────────────────────────────────────── tổng kết
print(f"\n{'='*60}")
print(f"đạt {len(dat)} · hỏng {len(hong)}")
if hong:
    print("\nTEST HỎNG:")
    for t, c in hong:
        print(f"  · {t}   {c}")
print("=" * 60)
sys.exit(1 if hong else 0)
