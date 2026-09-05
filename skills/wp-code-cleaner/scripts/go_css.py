#!/usr/bin/env python3
"""Gỡ CSS chết: cả rule chết hẳn lẫn VẾ SELECTOR chết nằm lẫn với vế còn sống.

Hai mức, mức sau bắt được cái mức trước bỏ sót:
  · rule mà mọi class-của-theme đều chết  -> bỏ cả rule
  · một vế trong danh sách ngăn bằng dấu phẩy đã chết, các vế khác còn sống
    -> chỉ bỏ vế đó. Lớp tiện ích (.is-active, .is-hidden) không mang tiền tố
    của theme nên không tính — nó không nói gì về việc vế đó còn dùng hay không.

Bảo vệ tên ghép chuỗi: một class còn sống nếu tên đầy đủ HOẶC một gốc của nó
(cắt tại -- hoặc __) xuất hiện trong PHP/JS. Vì tên biến thể hay được ghép:
'kl-the__bac--' . $n — grep tên đầy đủ không bao giờ thấy .kl-the__bac--2, và
xoá nhầm nó là mất một nhãn đang hiện trên trang thật. Giữ thừa vài rule rẻ hơn.

Ba chốt cấu trúc trước khi ghi (đếm tổng ngoặc thôi là phép kiểm mù):
  1. tổng { = tổng }
  2. độ sâu không bao giờ âm      -> bắt dấu } mồ côi
  3. không at-rule nào nằm trong khối khác -> bắt @media bị nuốt
Và hiệu chuẩn: dựng bản cố ý nuốt một dấu đóng trong @media, bắt phép kiểm phải
FAIL ở đó trước khi tin nó nói bản thật sạch.

Dùng:
  python go_css.py --theme "..." --css assets/css/main.css --tien-to mytheme-,kl-,mg-
  python go_css.py ... --thu
"""
import argparse
import os
import re
import sys


def doc(p):
    return open(p, encoding="utf-8", errors="replace").read()


def bo_nhieu(css):
    """Bỏ comment và nội dung chuỗi — content:'}{' là hợp lệ, đừng đếm nhầm."""
    css = re.sub(r"/\*.*?\*/", " ", css, flags=re.S)
    css = re.sub(r"'(?:\\.|[^'\\])*'", "''", css)
    css = re.sub(r'"(?:\\.|[^"\\])*"', '""', css)
    return css


def kiem_cau_truc(css):
    t = bo_nhieu(css)
    mo, dong = t.count("{"), t.count("}")
    if mo != dong:
        return False, f"lệch ngoặc: {mo} mở / {dong} đóng"
    d = 0
    dong_so = 1
    ngan = []
    for i, ch in enumerate(t):
        if ch == "\n":
            dong_so += 1
        elif ch == "{":
            d += 1
            ngan.append(d)
        elif ch == "}":
            d -= 1
            if d < 0:
                return False, f"dấu }} mồ côi ở dòng {dong_so}"
            if ngan:
                ngan.pop()
        elif ch == "@" and d > 0:
            sau = t[i:i + 12]
            if re.match(r"@(media|supports|container|layer)\b", sau):
                return False, f"at-rule nằm trong khối khác ở dòng {dong_so} — khối bị nuốt"
    return True, ""


def tach(body):
    ra, i, n, dau, d, sel = [], 0, len(body), 0, 0, None
    while i < n:
        c = body[i]
        if c == "/" and i + 1 < n and body[i + 1] == "*":
            j = body.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if c in "'\"":
            j = i + 1
            while j < n:
                if body[j] == "\\":
                    j += 2
                    continue
                if body[j] == c:
                    break
                j += 1
            i = j + 1
            continue
        if c == "{":
            if d == 0:
                sel = body[dau:i]
            d += 1
        elif c == "}":
            d -= 1
            if d == 0:
                ra.append((sel, body[dau:i + 1]))
                dau = i + 1
                sel = None
        i += 1
    if body[dau:]:
        ra.append((None, body[dau:]))   # giữ cả khoảng trắng cuối, đừng nuốt
    return ra


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme", required=True)
    ap.add_argument("--css", required=True, help="đường dẫn CSS, tương đối với --theme")
    ap.add_argument("--tien-to", default="mytheme-,site-")
    ap.add_argument("--thu", action="store_true")
    a = ap.parse_args()

    theme = a.theme.rstrip("/\\")
    tien_to = tuple(x.strip() for x in a.tien_to.split(",") if x.strip())
    P = os.path.join(theme, a.css)

    markup = []
    for dp, dn, fn in os.walk(theme):
        if any(x in dp.replace(os.sep, "/") for x in ("/node_modules", "/vendor", "/.git")):
            continue
        for f in fn:
            if f.endswith((".php", ".js")):
                markup.append(doc(os.path.join(dp, f)))
    markup = "\n".join(markup)
    nho = {}

    def co(x):
        return bool(re.search(r"(?<![A-Za-z0-9_-])" + re.escape(x) + r"(?![A-Za-z0-9_-])", markup))

    def con_song(c):
        if c not in nho:
            ok = co(c)
            g = c
            while not ok:
                cat = max(g.rfind("--"), g.rfind("__"))
                if cat <= 0:
                    break
                g = g[:cat]
                ok = co(g)
            nho[c] = ok
        return nho[c]

    bo_ve, bo_rule = [], []

    def loc(body):
        giu = []
        for sel, nguyen in tach(body):
            if sel is None:
                giu.append(nguyen)
                continue
            d = sel.lstrip()
            if d.startswith("@"):
                if re.match(r"@(media|supports|container|layer)\b", d):
                    mo, dg = nguyen.index("{"), nguyen.rindex("}")
                    trong = loc(nguyen[mo + 1:dg])
                    if trong.strip() == "":
                        bo_rule.append(sel.strip()[:60] + "  (at-rule rỗng)")
                        continue
                    giu.append(nguyen[:mo + 1] + trong + nguyen[dg:])
                else:
                    giu.append(nguyen)
                continue
            ve = sel.split(",")
            giu_ve = []
            for v in ve:
                cls = [c for c in re.findall(r"\.(-?[A-Za-z_][A-Za-z0-9_-]*)", v)
                       if c.startswith(tien_to)]
                if cls and all(not con_song(c) for c in cls):
                    bo_ve.append(v.strip().replace("\n", " ")[:64])
                    continue
                giu_ve.append(v)
            if not giu_ve:
                bo_rule.append(sel.strip().replace("\n", " ")[:64])
                continue
            giu.append((",".join(giu_ve) + nguyen[nguyen.index("{"):]) if len(giu_ve) != len(ve)
                       else nguyen)
        return "".join(giu)

    raw = open(P, "rb").read()
    s = raw.decode("utf-8")
    nl = "\r\n" if "\r\n" in s else "\n"
    moi = re.sub(r"(?:" + re.escape(nl) + r"){3,}", nl * 2, loc(s))

    vt = moi.find("@media")
    if vt < 0:
        print("CẢNH BÁO: file không có @media, bỏ qua ca hiệu chuẩn at-rule.")
        ok_hong = False
    else:
        dg = moi.index("}", moi.index("{", vt))
        ok_hong, _ = kiem_cau_truc(moi[:dg] + moi[dg + 1:])
    ok_that, msg = kiem_cau_truc(moi)
    print(f"HIỆU CHUẨN  bản hỏng: {'PASS' if ok_hong else 'FAIL'}   "
          f"bản thật: {'PASS' if ok_that else 'FAIL'} {msg}")
    if ok_hong:
        raise SystemExit("THƯỚC MÙ — nó không thấy cả một dấu đóng bị nuốt. Không ghi.")
    if not ok_that:
        raise SystemExit("bản thật FAIL — không ghi.")

    print(f"\nbỏ {len(bo_ve)} vế selector, {len(bo_rule)} rule")
    for x in bo_rule[:20]:
        print("   rule:", x)
    if len(bo_rule) > 20:
        print(f"   … và {len(bo_rule)-20} rule nữa")

    if a.thu:
        print(f"\n[thử] {len(raw)/1024:.1f} KB -> {len(moi.encode('utf-8'))/1024:.1f} KB — chưa ghi")
        return 0
    tam = P + ".tmp"
    open(tam, "wb").write(moi.encode("utf-8"))
    if os.path.getsize(tam) == 0:
        os.remove(tam)
        raise SystemExit("file tạm rỗng, dừng")
    os.replace(tam, P)
    print(f"\n{len(raw)/1024:.1f} KB -> {os.path.getsize(P)/1024:.1f} KB")
    print("\nCHƯA XONG. Cấu trúc sạch không có nghĩa là không xoá nhầm.")
    print("Chạy doi_chung_live.py rồi dung_so_computed.py trước khi deploy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
