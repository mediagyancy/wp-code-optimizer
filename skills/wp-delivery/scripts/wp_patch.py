# -*- coding: utf-8 -*-
"""Vá file bằng cắt-dán chuỗi, có chốt chặn.

LÝ DO TỒN TẠI (02/09/2026, một dự án thật):
Cùng một loại lỗi lặp hai lần trong một ngày, cả hai lần đều do MỐC CHÈN KHÔNG DUY NHẤT:

  lần 1 — mốc "/* ---------- TIN TỨC ---------- */" có ở CẢ khối CSS lẫn khối JS.
          Cắt đoạn theo hai mốc thì lấy phải cặp ngược nhau, sinh media lồng media,
          toàn bộ CSS phía sau rơi vào trong nó và mất tác dụng ở desktop.
  lần 2 — vẫn mốc đó, lần này `str.replace` không giới hạn số lần nên chèn khối CSS
          vào CẢ hai chỗ; bản rơi vào <script> làm chết toàn bộ JS của trang.

Cả hai lần đều KHÔNG bị đếm-ngoặc phát hiện. Nên chốt phải nằm ở chỗ khác:
mốc phải duy nhất, và sau khi vá phải kiểm CSS còn là CSS, JS còn là JS.

Dùng:
    import sys, os
    sys.path.insert(0, os.path.expanduser("skills/wp-delivery/scripts"))
    from wp_patch import thay, chen_truoc, chen_sau, cat_giua, kiem_html

    s = thay(s, cu, moi)              # cu phải xuất hiện ĐÚNG một lần
    s = chen_truoc(s, moc, khoi)      # moc phải xuất hiện ĐÚNG một lần
    kiem_html(s, ten_file)            # CSS/JS/ngoặc — ném lỗi nếu lệch
"""
import sys
import os
import re
import shutil
import subprocess
import tempfile

# Windows console mặc định cp1252, không in được tiếng Việt và sẽ ném
# UnicodeEncodeError giữa chừng — script chết trước cả khi kịp báo kết quả.
# Ép UTF-8 ngay tại script để chạy tay trên Windows cũng không cần đặt biến
# môi trường. CI đã bắt đúng ca này.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")



class VaLoi(Exception):
    """Bản vá không an toàn — dừng trước khi ghi."""


def _dem(s, moc):
    return s.count(moc)


def _bao(moc, n):
    goi = moc.strip().splitlines()[0][:70]
    if n == 0:
        return VaLoi(f"MỐC KHÔNG TỒN TẠI: {goi!r}")
    return VaLoi(
        f"MỐC KHÔNG DUY NHẤT ({n} lần): {goi!r}\n"
        "   Đây đúng là cách CSS lọt vào <script> hôm 02/09. Chọn mốc dài hơn, hoặc\n"
        "   dùng cat_giua()/vung() để giới hạn phạm vi trước khi thay."
    )


def thay(s, cu, moi, so_lan=1):
    """Thay chuỗi, bắt buộc `cu` xuất hiện đúng `so_lan` lần."""
    n = _dem(s, cu)
    if n != so_lan:
        raise _bao(cu, n)
    return s.replace(cu, moi, so_lan)


def chen_truoc(s, moc, khoi):
    """Chèn `khoi` ngay trước `moc`. `moc` phải duy nhất."""
    n = _dem(s, moc)
    if n != 1:
        raise _bao(moc, n)
    return s.replace(moc, khoi + moc, 1)


def chen_sau(s, moc, khoi):
    """Chèn `khoi` ngay sau `moc`. `moc` phải duy nhất."""
    n = _dem(s, moc)
    if n != 1:
        raise _bao(moc, n)
    return s.replace(moc, moc + khoi, 1)


def cat_giua(s, dau, cuoi):
    """Lấy đoạn [dau .. cuoi), cả hai mốc phải duy nhất và đúng thứ tự.

    Bản cũ dùng s.index(dau) rồi s.index(cuoi) mà không kiểm thứ tự — khi `cuoi`
    nằm TRƯỚC `dau` thì slice ra chuỗi rỗng, và replace('') chèn vào giữa mọi ký tự.
    """
    for m in (dau, cuoi):
        n = _dem(s, m)
        if n != 1:
            raise _bao(m, n)
    i, j = s.index(dau), s.index(cuoi)
    if j <= i:
        raise VaLoi(f"MỐC NGƯỢC THỨ TỰ: {cuoi.strip()[:40]!r} nằm TRƯỚC {dau.strip()[:40]!r}")
    return s[i:j]


def vung(s, ten):
    """Trả về (bắt đầu, kết thúc) của một vùng trong file HTML: 'style' hoặc 'script'."""
    mo, dong = ('<style>', '</style>') if ten == 'style' else ('<script>', '</script>')
    i = s.index(mo) + len(mo)
    j = s.rindex(dong)
    return i, j


def kiem_html(s, ten_file='(chuỗi)', bo_qua_node=False):
    """Kiểm bản vá TRƯỚC KHI GHI. Ném VaLoi kèm lý do cụ thể.

    1. ngoặc CSS cân, không âm giữa chừng
    2. CSS còn là CSS  — không có dấu hiệu JS lọt vào <style>
    3. JS còn là JS    — không có dấu hiệu CSS lọt vào <script>
    4. node --check trên từng khối <script> (nếu máy có node)
    """
    loi = []

    khoi_style = [m.group(1) for m in re.finditer(r'<style[^>]*>([\s\S]*?)</style>', s)]
    # CHỈ lấy script thật sự là JavaScript. Bỏ qua src ngoài, và bỏ qua mọi type khác
    # (application/ld+json, application/json, text/template…): JSON-LD không phải JS nên
    # node --check đương nhiên trượt — chính nó làm bản kiểm đầu tiên báo động giả.
    khoi_script = []
    for m in re.finditer(r'<script([^>]*)>([\s\S]*?)</script>', s):
        thuoc_tinh, than = m.group(1), m.group(2)
        if re.search(r'\bsrc\s*=', thuoc_tinh):
            continue
        kieu = re.search(r'\btype\s*=\s*["\']([^"\']+)', thuoc_tinh)
        if kieu and kieu.group(1).strip().lower() not in (
                'text/javascript', 'application/javascript', 'module'):
            continue
        khoi_script.append(than)

    for k, css in enumerate(khoi_style):
        sach = re.sub(r'/\*[\s\S]*?\*/', '', css)
        if sach.count('{') != sach.count('}'):
            loi.append(f"<style> #{k+1}: lệch ngoặc {sach.count('{')} mở / {sach.count('}')} đóng")
        sau = 0
        for ch in sach:
            if ch == '{':
                sau += 1
            elif ch == '}':
                sau -= 1
                if sau < 0:
                    loi.append(f"<style> #{k+1}: có dấu }} mồ côi")
                    break
        # JS lọt vào CSS
        for dau_hieu in ('function(', 'addEventListener', 'document.getElementById', '=>'):
            if dau_hieu in sach:
                loi.append(f"<style> #{k+1}: có dấu hiệu JS lọt vào — {dau_hieu!r}")

    for k, js in enumerate(khoi_script):
        if js.strip().startswith('{') or re.search(r'^\s*\.[a-zA-Z][\w-]*\s*\{', js, re.M):
            loi.append(f"<script> #{k+1}: có dấu hiệu CSS lọt vào (rule .class{{...}})")
        if re.search(r'^\s*@media\b', js, re.M):
            loi.append(f"<script> #{k+1}: có @media — CSS lọt vào <script>")

    if not bo_qua_node and shutil.which('node'):
        for k, js in enumerate(khoi_script):
            if not js.strip():
                continue
            tmp = tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8')
            tmp.write(js)
            tmp.close()
            # errors='replace': không có nó thì stderr tiếng Việt/ký tự lạ làm hỏng decode
            # trên Windows, subprocess trả stderr=None và bản kiểm chết giữa chừng.
            r = subprocess.run(['node', '--check', tmp.name],
                               capture_output=True, text=True,
                               encoding='utf-8', errors='replace')
            os.unlink(tmp.name)
            if r.returncode != 0:
                dong_loi = ((r.stderr or '').strip().splitlines() or [''])[:3]
                loi.append(f"<script> #{k+1}: node --check KHÔNG QUA — " + ' | '.join(dong_loi))

    if loi:
        raise VaLoi(f"BẢN VÁ KHÔNG AN TOÀN ({ten_file}), chưa ghi file:\n  - " + "\n  - ".join(loi))
    return True


def ghi_an_toan(duong_dan, noi_dung, kiem=True):
    """Kiểm rồi mới ghi. Không qua kiểm thì file cũ còn nguyên."""
    if kiem and duong_dan.lower().endswith(('.html', '.htm')):
        kiem_html(noi_dung, duong_dan)
    tmp = duong_dan + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(noi_dung)
    os.replace(tmp, duong_dan)
    return duong_dan
