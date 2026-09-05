#!/usr/bin/env python3
"""Gỡ hàm PHP: docblock + thân hàm + dòng add_action/add_filter gắn ngay sau nó.

Vì sao không dùng str.replace theo mốc chuỗi: mốc hiếm khi duy nhất, và cắt nhầm
mốc kết thúc thì phần HỎNG nằm ở đoạn ĐỨNG SAU chỗ sửa, không phải chỗ vừa sửa —
loại lỗi đó rất khó thấy bằng mắt. Ở đây ranh giới hàm tìm bằng cân bằng ngoặc có
xử lý chuỗi và comment.

Trước khi ghi, script tự HIỆU CHUẨN trên chính file đang sửa: nó dựng một bản cắt
tới TRƯỚC dấu } đóng hàm — chắc chắn bỏ lại một dấu } mồ côi — rồi bắt php -l phải
FAIL ở đó. Thước không bắt được ca hỏng đã biết thì mọi PASS từ nó vô nghĩa, nên
script dừng chứ không ghi.

(Ca hiệu chuẩn "cắt hụt một dòng" nghe hợp lý nhưng là thước MÙ: dòng cuối vùng cắt
thường là dòng trống, bỏ hụt nó vẫn hợp lệ. Phải bỏ lại dấu đóng mới chắc.)

Dùng:
  python go_ham.py --file "inc/cart-page.php" --ham ham_a ham_b
  python go_ham.py --json ke-hoach.json      # {"file": ["ham1","ham2"], ...}
  python go_ham.py ... --thu                 # chạy thử, không ghi
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile


def doc_nhi_phan(p):
    raw = open(p, "rb").read()
    nl = "\r\n" if b"\r\n" in raw else "\n"
    return raw.decode("utf-8"), nl


def het_than(lines, bd):
    """Từ dòng 'function x(' trả về chỉ số dòng chứa } đóng thân hàm."""
    d = 0
    chuoi = None
    kc = False
    thay = False
    i = bd
    while i < len(lines):
        l = lines[i]
        j = 0
        while j < len(l):
            c = l[j]
            if kc:
                if c == "*" and j + 1 < len(l) and l[j + 1] == "/":
                    kc = False
                    j += 2
                    continue
                j += 1
                continue
            if chuoi:
                if c == "\\":
                    j += 2
                    continue
                if c == chuoi:
                    chuoi = None
                j += 1
                continue
            if c in "'\"":
                chuoi = c
                j += 1
                continue
            if c == "/" and j + 1 < len(l):
                if l[j + 1] == "/":
                    break
                if l[j + 1] == "*":
                    kc = True
                    j += 2
                    continue
            if c == "#":
                break
            if c == "{":
                d += 1
                thay = True
            elif c == "}":
                d -= 1
                if d == 0 and thay:
                    return i
            j += 1
        i += 1
    raise SystemExit("không tìm được dấu đóng thân hàm")


def vung(lines, ten):
    """(đầu, cuối, dòng-đóng-thân). Đầu lùi lên qua docblock, cuối nuốt hook + dòng trống."""
    bd = [i for i, l in enumerate(lines)
          if re.match(r"^\s*function\s+" + re.escape(ten) + r"\s*\(", l)]
    if len(bd) != 1:
        raise SystemExit(f"{ten}: tìm thấy {len(bd)} định nghĩa, phải đúng 1")
    a = bd[0]
    k = a - 1
    if k >= 0 and lines[k].strip().endswith("*/"):
        while k >= 0 and not lines[k].strip().startswith("/**"):
            k -= 1
        if k >= 0:
            a = k
    dong_than = het_than(lines, bd[0])
    b = dong_than
    hook = re.compile(r"^add_(action|filter)\(\s*['\"][^'\"]+['\"]\s*,\s*['\"]" + re.escape(ten) + r"['\"]")
    while b + 1 < len(lines):
        nx = lines[b + 1].strip()
        if hook.match(nx):
            b += 1
        elif nx == "" and b + 2 < len(lines) and hook.match(lines[b + 2].strip()):
            b += 2
        else:
            break
    while b + 1 < len(lines) and lines[b + 1].strip() == "":
        b += 1
    return a, b, dong_than


def php_l(noi_dung, im=True):
    t = os.path.join(tempfile.gettempdir(), "wpcc_kiem.php")
    open(t, "wb").write(noi_dung.encode("utf-8"))
    r = subprocess.run(["php", "-l", t], capture_output=True, text=True)
    if r.returncode != 0 and not im:
        print("      php -l:", r.stdout.strip().splitlines()[0][:100])
    return r.returncode == 0


def xu_ly(path, hams, thu=False):
    s, nl = doc_nhi_phan(path)
    lines = s.split(nl)
    vs = sorted([(h,) + vung(lines, h) for h in hams], key=lambda x: x[1])
    for k in range(1, len(vs)):
        if vs[k][1] <= vs[k - 1][2]:
            raise SystemExit(f"{path}: vùng chồng lấn {vs[k-1][0]} / {vs[k][0]}")

    def dung(hong=None):
        xoa = set()
        for h, a, b, dt in vs:
            xoa.update(range(a, (dt - 1 if h == hong else b) + 1))
        return nl.join(l for i, l in enumerate(lines) if i not in xoa)

    if php_l(dung(hong=vs[0][0])):
        raise SystemExit(f"{path}: THƯỚC MÙ — php -l không bắt được dấu đóng mồ côi. Không ghi.")
    moi = dung()
    if not php_l(moi, im=False):
        raise SystemExit(f"{path}: bản cắt đúng lại FAIL php -l. Không ghi.")

    bot = len(lines) - len(moi.split(nl))
    if thu:
        print(f"  [thử] {path}: -{bot} dòng ({len(hams)} hàm) — hiệu chuẩn đạt, chưa ghi")
        return bot
    tam = path + ".tmp"
    open(tam, "wb").write(moi.encode("utf-8"))
    if os.path.getsize(tam) == 0:
        os.remove(tam)
        raise SystemExit("file tạm rỗng, dừng")
    os.replace(tam, path)
    print(f"  {path}: -{bot} dòng ({len(hams)} hàm)")
    return bot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--ham", nargs="*", default=[])
    ap.add_argument("--json", help='{"đường/dẫn.php": ["ham1","ham2"]}')
    ap.add_argument("--thu", action="store_true", help="chạy thử, không ghi")
    a = ap.parse_args()

    ke = json.load(open(a.json, encoding="utf-8")) if a.json else {a.file: a.ham}
    if not ke or not any(ke.values()):
        ap.error("chưa cho biết file/hàm nào cần gỡ")

    tong = 0
    for f, hams in ke.items():
        tong += xu_ly(f, hams, a.thu)
    print(f"\nTỔNG: -{tong} dòng · hiệu chuẩn đạt ở cả {len(ke)} file")
    print("RUNTIME_NOT_TESTED — php -l không bắt được lỗi lúc chạy. Còn phải quét lại")
    print("code chết (xoá hàm làm chết thêm hàm khác) và kiểm trên site thật.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
