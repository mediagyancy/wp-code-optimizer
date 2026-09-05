#!/usr/bin/env python3
"""Gỡ CSS chết: cả rule chết hẳn lẫn VẾ SELECTOR chết nằm lẫn với vế còn sống.

MẶC ĐỊNH LÀ CHẠY THỬ. Phải truyền --ghi mới ghi đè file. Lý do ở ngay dưới.

Hai mức:
  · rule mà mọi class-của-theme đều chết  -> bỏ cả rule
  · một vế trong danh sách ngăn bằng dấu phẩy đã chết, các vế khác còn sống
    -> chỉ bỏ vế đó. Lớp tiện ích (.is-active, .is-hidden) không mang tiền tố
    của theme nên không tính.

BA LỖI ĐÃ TỪNG CÓ TRONG CHÍNH FILE NÀY — sửa rồi, ghi lại để đừng tái phạm:

1. TÁCH DẤU PHẨY BẰNG sel.split(",") LÀ SAI.
   Nó không hiểu dấu phẩy nằm TRONG :is() :not() :where() :has(), trong
   [attr="a,b"], hay trong nth-child(2n, ...). Ca thật:
       .site-dead:is(.foo,.bar){color:red}
   bị cắt thành hai vế `.site-dead:is(.foo` và `.bar)`, vế đầu bị coi là chết,
   kết quả ghi ra file là `.bar){color:red}` — CSS sai cú pháp.
   Nay tách theo ĐỘ SÂU: chỉ cắt ở dấu phẩy nằm ngoài mọi ngoặc và mọi chuỗi.

2. PHÉP KIỂM CHỈ ĐẾM NGOẶC NÊN KHÔNG THẤY LỖI TRÊN.
   `.bar){color:red}` vẫn cân bằng ngoặc nhọn, nên chốt cũ báo PASS và script
   ĐÃ THỰC SỰ GHI ĐÈ file nguồn. Nay có thêm chốt selector: mỗi vế giữ lại phải
   cân bằng () [] và không rỗng.

3. HIỆU CHUẨN RỖNG KHI FILE KHÔNG CÓ @media.
   Bản cũ in "bỏ qua ca hiệu chuẩn" rồi vẫn chạy tiếp — tức là ghi file mà chưa
   chứng minh phép kiểm nhìn thấy gì. Nay luôn dựng được một ca hỏng: không có
   @media thì nuốt một dấu } bất kỳ. Không dựng được ca hỏng nào thì DỪNG.

Bảo vệ tên ghép chuỗi: một class còn sống nếu tên đầy đủ HOẶC một gốc của nó
(cắt tại -- hoặc __) xuất hiện trong PHP/JS. Vì tên biến thể hay được ghép:
'kl-the__bac--' . $n — grep tên đầy đủ không bao giờ thấy .kl-the__bac--2.

Dùng:
  python go_css.py --theme "..." --css assets/css/main.css            # chạy thử
  python go_css.py --theme "..." --css assets/css/main.css --ghi      # ghi thật
"""
import argparse
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



def doc(p):
    return open(p, encoding="utf-8", errors="replace").read()


def bo_nhieu(css):
    """Bỏ comment và nội dung chuỗi — content:'}{' là hợp lệ, đừng đếm nhầm."""
    css = re.sub(r"/\*.*?\*/", " ", css, flags=re.S)
    css = re.sub(r"'(?:\\.|[^'\\])*'", "''", css)
    css = re.sub(r'"(?:\\.|[^"\\])*"', '""', css)
    return css


def bo_ghi_chu(s):
    """Bỏ chú thích khỏi PHP/JS trước khi coi phần còn lại là markup.

    Một tên class chỉ được NHẮC TỚI trong chú thích thì không phải markup. Không
    bỏ ra thì chính câu `/* class fx-chet đã bỏ */` giữ cho .fx-chet sống mãi —
    tức là chú thích nói "đã bỏ" lại là thứ ngăn không cho bỏ. Fixture bắt được
    ca này bằng đúng một dòng chú thích.

    Cố ý thô và thận trọng: chỉ bỏ khối /* */ và những DÒNG bắt đầu bằng // # *.
    Không đụng `//` giữa dòng, vì `https://` cũng có nó.
    """
    s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
    giu = ["" if l.lstrip().startswith(("//", "#", "*")) else l for l in s.splitlines()]
    return chr(10).join(giu)


def tach_ve(sel):
    """Tách selector theo dấu phẩy Ở ĐỘ SÂU 0.

    Dấu phẩy trong :is(...), :not(...), [attr="a,b"] KHÔNG phải chỗ tách.
    Đây chính là chỗ bản trước cắt nát selector và vẫn báo PASS.
    """
    ve, dem, sau, chuoi = [], [], 0, None
    for c in sel:
        if chuoi:
            dem.append(c)
            if c == chuoi:
                chuoi = None
            continue
        if c in "'\"":
            chuoi = c
            dem.append(c)
            continue
        if c in "([":
            sau += 1
        elif c in ")]":
            sau -= 1
        if c == "," and sau == 0:
            ve.append("".join(dem))
            dem = []
            continue
        dem.append(c)
    ve.append("".join(dem))
    return ve


def ve_hop_le(v):
    """Một vế giữ lại phải không rỗng và cân bằng () [] — chốt bản trước không có."""
    t = v.strip()
    if not t:
        return False
    tron, vuong, chuoi = 0, 0, None
    for c in t:
        if chuoi:
            if c == chuoi:
                chuoi = None
            continue
        if c in "'\"":
            chuoi = c
        elif c == "(":
            tron += 1
        elif c == ")":
            tron -= 1
        elif c == "[":
            vuong += 1
        elif c == "]":
            vuong -= 1
        if tron < 0 or vuong < 0:
            return False
    return tron == 0 and vuong == 0 and chuoi is None


def kiem_cau_truc(css):
    """Ba chốt ngoặc nhọn + một chốt selector."""
    t = bo_nhieu(css)
    mo, dong = t.count("{"), t.count("}")
    if mo != dong:
        return False, f"lệch ngoặc nhọn: {mo} mở / {dong} đóng"
    # Ngăn xếp khối: mỗi phần tử là "at" hay "rule".
    #
    # Chốt này bắt ca @media bị NUỐT vào giữa một rule khác — lỗi kinh điển của
    # việc cắt chuỗi, và nó KHÔNG làm lệch tổng ngoặc nên đếm tổng không thấy.
    # Nhưng "at-rule nằm trong khối khác" là quá rộng: @media lồng @supports,
    # @layer lồng @media đều là CSS hợp lệ. Fixture bắt được đúng chỗ này.
    # Dấu hiệu hỏng thật là at-rule nằm trong một STYLE RULE, không phải trong
    # một at-rule khác.
    ngan, dong_so, dau_khoi = [], 1, 0
    for i, ch in enumerate(t):
        if ch == "\n":
            dong_so += 1
        elif ch == "{":
            ngan.append("at" if t[dau_khoi:i].lstrip().startswith("@") else "rule")
            dau_khoi = i + 1
        elif ch == "}":
            if not ngan:
                return False, f"dấu }} mồ côi ở dòng {dong_so}"
            ngan.pop()
            dau_khoi = i + 1
        elif ch == "@" and "rule" in ngan and re.match(
                r"@(media|supports|container|layer)\b", t[i:i + 12]):
            return False, f"at-rule nằm trong một style rule ở dòng {dong_so} — khối bị nuốt"
    for sel, _ in tach(css):
        if sel is None:
            continue
        sel_sach = re.sub(r"/\*.*?\*/", " ", sel, flags=re.S)
        if sel_sach.lstrip().startswith("@"):
            continue
        for v in tach_ve(sel_sach):
            if not ve_hop_le(v):
                return False, f"vế selector hỏng: {v.strip()[:48]!r}"
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
        ra.append((None, body[dau:]))
    return ra


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme", required=True)
    ap.add_argument("--css", required=True, help="đường dẫn CSS, tương đối với --theme")
    ap.add_argument("--tien-to", default="mytheme-,site-")
    ap.add_argument("--ghi", action="store_true",
                    help="ghi đè file thật. Không có cờ này thì chỉ chạy thử.")
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
                markup.append(bo_ghi_chu(doc(os.path.join(dp, f))))
    markup = "\n".join(markup)
    nho = {}

    def co(x):
        return bool(re.search(r"(?<![A-Za-z0-9_-])" + re.escape(x) + r"(?![A-Za-z0-9_-])", markup))

    def co_goc(x):
        """Như co() nhưng KHÔNG chặn ký tự đứng sau.

        Vì gốc tên luôn đứng ngay trước chỗ nối: markup ghi `fx-bac--<?php ... ?>`
        thì sau gốc `fx-bac` là dấu `-`, và lookahead của co() chặn đúng ký tự đó
        -> gốc không bao giờ khớp -> luật bảo vệ hỏng ngay tại chỗ nó sinh ra để
        bảo vệ. Fixture .fx-bac--N bắt được ca này.
        """
        return bool(re.search(r"(?<![A-Za-z0-9_-])" + re.escape(x), markup))

    def con_song(c):
        if c not in nho:
            ok, g = co(c), c
            while not ok:
                cat = max(g.rfind("--"), g.rfind("__"))
                if cat <= 0:
                    break
                g = g[:cat]
                ok = co_goc(g)
            nho[c] = ok
        return nho[c]

    bo_ve, bo_rule = [], []

    def loc(body):
        giu = []
        for sel, nguyen in tach(body):
            if sel is None:
                giu.append(nguyen)
                continue
            # Bỏ chú thích khỏi selector TRƯỚC khi quyết định.
            #
            # tach() gom mọi thứ từ sau dấu } trước tới dấu { làm "selector", nên
            # một chú thích đứng ngay trên rule cũng nằm trong đó. Không bỏ ra thì
            # `/* ghi chú */ @media print {` không được nhận là at-rule, và cả khối
            # đi lọt nguyên vẹn. Hai test @layer và @media bắt đúng ca này.
            # Chỉ dùng bản đã bỏ chú thích để QUYẾT ĐỊNH; xuất ra vẫn là `nguyen`.
            sel_sach = re.sub(r"/\*.*?\*/", " ", sel, flags=re.S)
            d = sel_sach.lstrip()
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
            ve = tach_ve(sel_sach)
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

    # ── hiệu chuẩn: LUÔN phải dựng được một ca hỏng, không có thì dừng
    ca = None
    vt = moi.find("@media")
    if vt >= 0:
        try:
            dg = moi.index("}", moi.index("{", vt))
            ca = ("nuốt dấu đóng trong @media", moi[:dg] + moi[dg + 1:])
        except ValueError:
            ca = None
    if ca is None:
        j = moi.rfind("}")
        if j >= 0:
            ca = ("nuốt một dấu } bất kỳ", moi[:j] + moi[j + 1:])
    if ca is None:
        sys.exit("KHÔNG dựng được ca hiệu chuẩn nào (file không có dấu }). Dừng, không ghi.")

    ok_hong, msg_hong = kiem_cau_truc(ca[1])
    ok_that, msg_that = kiem_cau_truc(moi)
    print(f"HIỆU CHUẨN ({ca[0]})  bản hỏng: {'PASS' if ok_hong else 'FAIL'}"
          f"   bản thật: {'PASS' if ok_that else 'FAIL'} {msg_that}")
    if ok_hong:
        sys.exit("THƯỚC MÙ — nó không thấy cả một dấu đóng bị nuốt. Không ghi.")
    if not ok_that:
        sys.exit("bản thật FAIL — không ghi.")

    print(f"\nbỏ {len(bo_ve)} vế selector, {len(bo_rule)} rule")
    for x in bo_rule[:20]:
        print("   rule:", x)
    if len(bo_rule) > 20:
        print(f"   … và {len(bo_rule)-20} rule nữa")

    if not a.ghi:
        print(f"\n[CHẠY THỬ] {len(raw)/1024:.1f} KB -> {len(moi.encode('utf-8'))/1024:.1f} KB")
        print("Chưa ghi gì. Xem danh sách trên, thấy đúng thì chạy lại kèm --ghi.")
        return 0

    tam = P + ".tmp"
    open(tam, "wb").write(moi.encode("utf-8"))
    if os.path.getsize(tam) == 0:
        os.remove(tam)
        sys.exit("file tạm rỗng, dừng")
    os.replace(tam, P)
    print(f"\n{len(raw)/1024:.1f} KB -> {os.path.getsize(P)/1024:.1f} KB")
    print("\nCHƯA XONG. Cấu trúc sạch không có nghĩa là không xoá nhầm.")
    print("Chạy doi_chung_live.py rồi dung_so_computed.py trước khi deploy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
