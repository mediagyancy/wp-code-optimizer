#!/usr/bin/env python3
"""Chốt riêng tư: repo công khai không được chứa đường dẫn máy, email, hay tên khách.

Vì sao KHÔNG hardcode tên khách vào file này: bản đầu làm thế, và máy quét tìm
thấy ngay chính danh sách của nó — tức là file phòng rò dữ liệu lại chính là chỗ
rò. Nên chia hai loại:

  · MẪU CHUNG — ship kèm repo, không nêu tên ai: đường dẫn tuyệt đối của Windows
    và Unix, email, vài dấu hiệu bí mật hay gặp.
  · TÊN RIÊNG — để ở tests/rieng-tu.local.txt, mỗi dòng một chuỗi. File đó bị
    .gitignore chặn, không bao giờ lên repo. Không có file thì bỏ qua phần này
    và NÓI RÕ là đã bỏ qua, chứ không im lặng coi như đã kiểm.

Máy quét tự hiệu chuẩn trước: gieo một chuỗi khớp mẫu vào một bản trong bộ nhớ
rồi bắt mình phải tìm ra. Không tìm ra thì thoát khác 0.

    python tests/kiem_rieng_tu.py
"""
import io
import os
import re
import sys

# Windows console mặc định cp1252, không in được tiếng Việt và sẽ ném
# UnicodeEncodeError giữa chừng — script chết trước cả khi kịp báo kết quả.
# Ép UTF-8 ngay tại script để chạy tay trên Windows cũng không cần đặt biến
# môi trường. CI đã bắt đúng ca này.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOI = os.path.abspath(__file__)
BS = chr(92)

MAU = [
    ("đường dẫn tuyệt đối Windows", re.compile(r"[A-Za-z]:" + re.escape(BS) + r"(?:Users|Claude)" + re.escape(BS))),
    ("đường dẫn tuyệt đối Windows (gạch xuôi)", re.compile(r"[A-Za-z]:/(?:Users|Claude)/")),
    ("thư mục nhà Unix", re.compile(r"/(?:home|Users)/[a-z][a-z0-9_.-]{2,}/")),
    # Bỏ qua địa chỉ noreply của GitHub và các tên miền RFC 2606/6761 dành riêng
    # cho ví dụ và thử nghiệm (.test .example .invalid .localhost). Chúng KHÔNG
    # bao giờ là địa chỉ thật, nên báo động ở đó chỉ dạy người ta bỏ qua cảnh báo —
    # và một cảnh báo bị bỏ qua vài lần là một cảnh báo đã chết.
    ("địa chỉ email", re.compile(r"[A-Za-z0-9._%+-]+@(?!users\.noreply\.github\.com)"
                                r"(?![A-Za-z0-9.-]*\.(?:test|example|invalid|localhost)\b)"
                                r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("khoá/mật khẩu viết thẳng", re.compile(r"(?i)\b(?:password|passwd|api[_-]?key|secret)\s*[=:]\s*['\"][^'\"]{6,}")),
]

DUOI = (".md", ".py", ".json", ".txt", ".data", ".yml", ".yaml", ".css", ".php")
BO_QUA_TM = {".git", "__pycache__", "node_modules"}
LOCAL = os.path.join(GOC, "tests", "rieng-tu.local.txt")


def cac_file():
    for dp, dn, fn in os.walk(GOC):
        dn[:] = [d for d in dn if d not in BO_QUA_TM]
        for f in fn:
            p = os.path.join(dp, f)
            # Bỏ qua chính máy quét và chính danh sách riêng tư — cả hai đương
            # nhiên chứa các chuỗi đang tìm, và danh sách thì .gitignore đã chặn.
            if f.endswith(DUOI) and os.path.abspath(p) not in (TOI, os.path.abspath(LOCAL)):
                yield p


def quet(ten_rieng, noi_dung_them=None):
    hit = []
    for p in cac_file():
        try:
            t = io.open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        if noi_dung_them:
            t += "\n" + noi_dung_them
        r = os.path.relpath(p, GOC).replace(os.sep, "/")
        for i, l in enumerate(t.splitlines(), 1):
            for nhan, mau in MAU:
                if mau.search(l):
                    hit.append((r, i, nhan, l.strip()[:64]))
                    break
            else:
                for k in ten_rieng:
                    if k in l:
                        hit.append((r, i, "tên riêng trong danh sách local", l.strip()[:64]))
                        break
    return hit


ten_rieng = []
if os.path.exists(LOCAL):
    ten_rieng = [l.strip() for l in io.open(LOCAL, encoding="utf-8").read().splitlines()
                 if l.strip() and not l.startswith("#")]
    print(f"danh sách tên riêng: {len(ten_rieng)} chuỗi (từ tests/rieng-tu.local.txt)")
else:
    print("danh sách tên riêng: KHÔNG CÓ tests/rieng-tu.local.txt")
    print("  -> chỉ quét mẫu chung. Phần tên khách/tên site CHƯA ĐƯỢC KIỂM.")
    print("  -> muốn kiểm thì tạo file đó, mỗi dòng một chuỗi. .gitignore đã chặn sẵn.")

print("\nHIỆU CHUẨN — gieo một chuỗi khớp mẫu rồi bắt máy quét phải tìm ra")
if not quet(ten_rieng, noi_dung_them="C:" + BS + "Users" + BS + "ai-do" + BS + "x.txt"):
    sys.exit("  THƯỚC MÙ: gieo chuỗi mà không tìm ra. Mọi kết quả 'sạch' đều vô nghĩa.")
print("  tìm ra -> tin được\n")

hit = quet(ten_rieng)
for f, i, nhan, l in hit:
    print(f"  {f}:{i}  [{nhan}]  {l}")
print(f"\ndòng chứa dữ liệu riêng: {len(hit)}   (phải là 0)")
sys.exit(1 if hit else 0)
