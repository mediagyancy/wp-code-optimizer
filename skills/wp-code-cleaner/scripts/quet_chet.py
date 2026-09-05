#!/usr/bin/env python3
"""Quét code chết trong một theme/plugin WordPress. Chỉ ĐỌC, không sửa gì.

Trả lời ba câu, theo thứ tự quan trọng dần:
  1. File nào không có đường nào dẫn tới từ một template WordPress thật?
  2. Hàm nào định nghĩa xong không nơi nào gọi?
  3. Class CSS nào không còn markup nào sinh ra?

Cách dựng đồ thị: gốc là mọi template ở thư mục gốc theme (WordPress chọn
template từ đây), mọi override WooCommerce, và mọi file được loader require
MÀ CÓ đăng ký hook — vì file đăng ký hook thì tự nó là điểm vào, không cần ai gọi.
Cạnh đi theo tên hàm và theo get_template_part.

Giới hạn phải biết trước khi tin kết quả:
  · Phân tích tĩnh không thấy tên ghép chuỗi ('kl-the__bac--' . $n) và không thấy
    hook đăng ký bằng biến. Mục 3 vì vậy chỉ là DANH SÁCH NGHI NGỜ, phải đối chứng
    bằng HTML thật trước khi xoá — xem doi_chung_live.py.
  · Nó chỉ thấy file có trên đĩa. Plugin không tải về thì không nhìn thấy.

Dùng:
  python quet_chet.py --theme "đường/dẫn/theme"
  python quet_chet.py --theme "..." --loader functions.php --json ra.json
"""
import argparse
import json
import os
import re
import sys

MAC_DINH_LOADER = "functions.php"


def doc(p):
    return open(p, encoding="utf-8", errors="replace").read()


def quet_file(theme, duoi=(".php",)):
    ra = []
    for dp, dn, fn in os.walk(theme):
        if any(x in dp.replace(os.sep, "/") for x in ("/node_modules", "/vendor", "/.git")):
            continue
        for f in fn:
            if f.endswith(duoi):
                ra.append(os.path.join(dp, f))
    return ra


def rel(p, theme):
    return os.path.relpath(p, theme).replace(os.sep, "/")


def khong_dau(x):
    """Bỏ comment và chuỗi để đếm/khớp không bị nhiễu."""
    x = re.sub(r"/\*.*?\*/", " ", x, flags=re.S)
    x = re.sub(r"(?m)//.*$", " ", x)
    x = re.sub(r"(?m)^\s*#.*$", " ", x)
    return x


def tim_ham(s):
    return re.findall(r"^\s*function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", s, re.M)


def co_hook(s):
    return bool(re.search(r"^\s*(?:add_action|add_filter|add_shortcode|register_)", s, re.M))


def dung_do_thi(theme, loader):
    php = quet_file(theme, (".php",))
    src = {rel(p, theme): doc(p) for p in php}

    chu = {}          # ham -> file dinh nghia
    for f, s in src.items():
        for h in tim_ham(s):
            chu.setdefault(h, f)

    canh = {f: set() for f in src}
    for f, s in src.items():
        sach = khong_dau(s)
        for ten, g in chu.items():
            if g == f:
                continue
            if re.search(r"(?<![A-Za-z0-9_])" + re.escape(ten) + r"(?![A-Za-z0-9_])", sach):
                canh[f].add(g)
        for m in re.finditer(r"get_template_part\(\s*['\"]([^'\"]+)['\"]"
                             r"(?:\s*,\s*['\"]?([A-Za-z0-9-]*)['\"]?)?", s):
            goc, hau = m.group(1), m.group(2)
            for ung in ([goc + "-" + hau + ".php"] if hau else []) + [goc + ".php"]:
                if ung in src:
                    canh[f].add(ung)
                    break

    goc = set()
    for f in src:
        if "/" not in f:
            goc.add(f)                       # template o goc theme
        elif f.startswith("woocommerce/"):
            goc.add(f)                       # override WooCommerce
        elif co_hook(src[f]):
            goc.add(f)                       # file tu dang ky hook = diem vao

    thay, ngan = set(), list(goc)
    while ngan:
        f = ngan.pop()
        if f in thay:
            continue
        thay.add(f)
        ngan.extend(canh[f] - thay)

    return src, chu, canh, sorted(set(src) - thay)


def ham_chet(theme, src, chu, tien_to):
    js = {rel(p, theme): doc(p) for p in quet_file(theme, (".js",))}
    khoi = khong_dau("\n".join(src.values())) + "\n" + "\n".join(js.values())
    ra = []
    for ten, f in sorted(chu.items()):
        if tien_to and not ten.startswith(tuple(tien_to)):
            continue
        n = len(re.findall(r"(?<![A-Za-z0-9_])" + re.escape(ten) + r"(?![A-Za-z0-9_])", khoi))
        if n <= 1:                            # chi con chinh dong dinh nghia
            ra.append((ten, f))
    return ra


def class_nghi(theme, src, tien_to):
    """Class trong CSS mà không markup nào sinh ra. CHỈ LÀ NGHI NGỜ."""
    css_files = quet_file(theme, (".css",))
    js = "\n".join(doc(p) for p in quet_file(theme, (".js",)))
    markup = "\n".join(src.values()) + "\n" + js
    ra = {}
    for p in css_files:
        s = doc(p)
        cls = set(re.findall(r"\.(-?[A-Za-z_][A-Za-z0-9_-]*)", s))
        nghi = []
        for c in sorted(cls):
            if tien_to and not c.startswith(tuple(tien_to)):
                continue
            if con_song(c, markup):
                continue
            nghi.append(c)
        if nghi:
            ra[rel(p, theme)] = nghi
    return ra


def con_song(c, markup):
    """Sống nếu tên đầy đủ HOẶC một gốc của nó có trong markup.

    Xét gốc vì tên biến thể hay được ghép chuỗi: 'kl-the__bac--' . $n.
    Grep tên đầy đủ không bao giờ thấy .kl-the__bac--2, và xoá nhầm nó là mất
    một nhãn đang hiện trên trang. Giữ thừa vài rule rẻ hơn nhiều.
    """
    def co(x):
        return bool(re.search(r"(?<![A-Za-z0-9_-])" + re.escape(x) + r"(?![A-Za-z0-9_-])", markup))
    if co(c):
        return True
    g = c
    while True:
        cat = max(g.rfind("--"), g.rfind("__"))
        if cat <= 0:
            return False
        g = g[:cat]
        if co(g):
            return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme", required=True, help="thư mục gốc theme hoặc plugin")
    ap.add_argument("--loader", default=MAC_DINH_LOADER, help="file nạp (mặc định functions.php)")
    ap.add_argument("--tien-to", default="", help="lọc theo tiền tố, ngăn bằng dấu phẩy (vd: mytheme_,mg_)")
    ap.add_argument("--json", default="", help="ghi kết quả ra file JSON")
    a = ap.parse_args()

    theme = a.theme.rstrip("/\\")
    tien_to = [x.strip() for x in a.tien_to.split(",") if x.strip()]
    src, chu, canh, chet = dung_do_thi(theme, a.loader)

    print(f"THEME  {theme}")
    print(f"       {len(src)} file PHP · {len(chu)} hàm\n")

    print("=" * 74)
    print("1. FILE KHÔNG CÓ ĐƯỜNG NÀO DẪN TỚI")
    print("=" * 74)
    tong = 0
    for f in chet:
        n = len(src[f].splitlines())
        tong += n
        print(f"   {f:52s} {n:5d} dòng")
    print(f"   -> {len(chet)} file / {tong} dòng" if chet else "   (không có)")

    print()
    print("=" * 74)
    print("2. HÀM ĐỊNH NGHĨA NHƯNG KHÔNG NƠI NÀO GỌI")
    print("=" * 74)
    hc = ham_chet(theme, src, chu, tien_to)
    for ten, f in hc:
        print(f"   {ten:44s} {f}")
    print(f"   -> {len(hc)} hàm" if hc else "   (không có)")

    print()
    print("=" * 74)
    print("3. CLASS CSS NGHI CHẾT — PHẢI ĐỐI CHỨNG BẰNG HTML THẬT TRƯỚC KHI XOÁ")
    print("=" * 74)
    cn = class_nghi(theme, src, tien_to)
    for f, ds in sorted(cn.items()):
        print(f"   {f}: {len(ds)} class")
        for c in ds[:12]:
            print(f"      .{c}")
        if len(ds) > 12:
            print(f"      … và {len(ds)-12} class nữa")
    if not cn:
        print("   (không có)")

    print()
    print("LƯU Ý ĐỌC KẾT QUẢ")
    print("  · Mục 1 và 2 đáng tin: dựa trên tên hàm và get_template_part, đều là tên tĩnh.")
    print("  · Mục 3 CHỈ LÀ NGHI NGỜ. Phân tích tĩnh không thấy markup do plugin sinh ra")
    print("    lúc chạy. Chạy doi_chung_live.py trên URL thật trước khi xoá bất cứ thứ gì.")
    print("  · Xoá xong phải QUÉT LẠI: xoá file làm chết thêm hàm ở file khác.")
    print("    Lặp tới khi cả ba mục đều rỗng mới là xong.")

    if a.json:
        json.dump({"file_chet": chet, "ham_chet": hc, "class_nghi": cn},
                  open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"\nđã ghi {a.json}")

    return 1 if (chet or hc) else 0


if __name__ == "__main__":
    sys.exit(main())
