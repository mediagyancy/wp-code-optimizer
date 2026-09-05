#!/usr/bin/env python3
"""Đối chứng bằng HTML THẬT của production. Chỉ đọc, không sửa gì.

Vì sao tầng này không thay được: phân tích tĩnh chỉ thấy markup do THEME viết ra.
Nó mù trước markup do WooCommerce, plugin, shortcode hay block sinh ra lúc chạy.
Đây là tầng duy nhất nhìn thấy thứ trình duyệt thật sự nhận được.

Hỏi hai câu:
  1. Class/mốc vừa xoá còn xuất hiện trên trang nào không?  (phải = 0)
  2. File vừa xoá đã thật sự biến mất khỏi host chưa?       (404 = đã xoá)

Câu 2 cần đối chứng hai đầu, nếu không thì không biết phép dò có nói thật không:
một file chắc chắn CÒN phải ra 200, một tên bịa phải ra 404.

CẢNH BÁO VỀ TẢI: đừng gắn ?cb=… vào URL để "chắc chắn đọc bản mới". Cache-busting
ép cache bỏ qua, nên mỗi lượt là một lần chạy PHP + truy vấn DB đầy đủ. Ngày
05/09/2026 chính cách kiểm đó đã góp phần làm một host hết sạch kết nối MySQL
(max_user_connections = 30) ngay giữa lúc đang kiểm. Script này dùng URL canonical
và có nghỉ giữa các request.

Dùng:
  python doi_chung_live.py --url-file urls.txt --xoa-class-file class.txt
  python doi_chung_live.py --site https://vd.com --theme-slug ten-theme \
                           --xoa-file-file danh-sach-xoa.txt
  # so hai bản CSS: class nào có ở bản cũ mà mất ở bản mới
  python doi_chung_live.py --url-file urls.txt --css-cu cu.css --css-moi moi.css
"""
import argparse
import gzip
import re
import sys
import time
import urllib.error
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (kiem-tra-noi-bo)", "Accept-Encoding": "gzip"}


def tai(u, timeout=60):
    rq = urllib.request.Request(u, headers=UA)
    with urllib.request.urlopen(rq, timeout=timeout) as r:
        d = r.read()
        raw = gzip.decompress(d) if r.headers.get("Content-Encoding") == "gzip" else d
        return r.status, raw.decode("utf-8", "replace")


def ma_http(u, timeout=30):
    try:
        return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA["User-Agent"]}),
                                      timeout=timeout).status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return -1


def doc_dong(p):
    return [l.strip() for l in open(p, encoding="utf-8").read().splitlines()
            if l.strip() and not l.strip().startswith("#")]


def lop(css):
    return set(re.findall(r"\.(-?[A-Za-z_][A-Za-z0-9_-]*)", css))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url-file", help="mỗi dòng một URL công khai")
    ap.add_argument("--url", nargs="*", default=[])
    ap.add_argument("--xoa-class-file", help="mỗi dòng một tên class vừa xoá")
    ap.add_argument("--xoa-moc-file", help="mốc khác cần vắng mặt (data-attr, id, tên biến JS)")
    ap.add_argument("--css-cu", help="bản CSS trước khi cắt")
    ap.add_argument("--css-moi", help="bản CSS sau khi cắt — tự suy ra danh sách class đã xoá")
    ap.add_argument("--site", help="vd https://vidu.com — cần cho --xoa-file-file")
    ap.add_argument("--theme-slug", default="", help="slug theme, để dựng đường dẫn wp-content")
    ap.add_argument("--xoa-file-file", help="mỗi dòng một đường dẫn file vừa xoá, tính từ gốc theme")
    ap.add_argument("--con-file", default="", help="một file chắc chắn CÒN, làm đối chứng dương")
    ap.add_argument("--nghi", type=float, default=0.4, help="giây nghỉ giữa các request")
    a = ap.parse_args()

    urls = list(a.url) + (doc_dong(a.url_file) if a.url_file else [])
    moc = set()
    if a.xoa_class_file:
        moc |= {"." + c.lstrip(".") for c in doc_dong(a.xoa_class_file)}
    if a.xoa_moc_file:
        moc |= set(doc_dong(a.xoa_moc_file))
    if a.css_cu and a.css_moi:
        mat = lop(open(a.css_cu, encoding="utf-8", errors="replace").read()) - \
              lop(open(a.css_moi, encoding="utf-8", errors="replace").read())
        moc |= {"." + c for c in mat}
        print(f"suy ra từ hai bản CSS: {len(mat)} class đã biến mất\n")

    # Fail-closed. Bản trước không có khối này: chạy trần không tham số nào thì nó
    # in "TỔNG SỐ CA NGUY: 0 / Sạch ở tầng này" và thoát 0 — tức là "chưa kiểm gì"
    # trông y hệt "đã kiểm và sạch". Một phép kiểm nói dối theo hướng an toàn giả
    # còn tệ hơn không có phép kiểm, vì nó tạo ra niềm tin.
    chay = []
    if urls and moc:
        chay.append(f"{len(moc)} mốc trên {len(urls)} URL")
    if a.xoa_file_file and a.site:
        chay.append("dò file đã xoá trên host")
    if not chay:
        print("KHONG_KIEM_DUOC — không có phép kiểm nào chạy được.\n")
        if not urls:
            print("  · thiếu URL: truyền --url hoặc --url-file")
        if not moc:
            print("  · thiếu mốc cần vắng mặt: truyền --xoa-class-file / --xoa-moc-file,")
            print("    hoặc --css-cu và --css-moi để tự suy ra danh sách class đã xoá")
        if not (a.xoa_file_file and a.site):
            print("  · muốn dò file đã xoá thì cần cả --site lẫn --xoa-file-file")
        print("\nĐây KHÔNG phải 'sạch'. Không kiểm gì thì trạng thái là NOT_TESTED.")
        return 2
    print("sẽ chạy: " + " · ".join(chay) + "\n")

    loi = 0

    if urls and moc:
        cls = {m[1:] for m in moc if m.startswith(".")}
        khac = {m for m in moc if not m.startswith(".")}
        print("=" * 78)
        print("1. MỐC VỪA XOÁ CÓ CÒN TRÊN TRANG THẬT KHÔNG  (phải = 0)")
        print("=" * 78)
        for u in urls:
            try:
                ma, h = tai(u)
            except Exception as e:
                print(f"  {u[:56]:56s} KHÔNG TẢI ĐƯỢC: {e}")
                loi += 1
                continue
            tren = set()
            for m in re.finditer(r'class="([^"]*)"', h):
                tren.update(m.group(1).split())
            con_cls = sorted(cls & tren)
            con_khac = sorted(k for k in khac if k in h)
            n = len(con_cls) + len(con_khac)
            loi += n
            print(f"  {u[:56]:56s} {ma}  {len(tren):4d} class  -> {n} mốc còn")
            for c in con_cls:
                print(f"        NGUY: .{c}")
            for k in con_khac:
                print(f"        NGUY: {k}")
            time.sleep(a.nghi)

    if a.xoa_file_file and a.site:
        base = a.site.rstrip("/") + "/wp-content/themes/" + a.theme_slug.strip("/") + "/"
        print()
        print("=" * 78)
        print("2. FILE VỪA XOÁ ĐÃ BIẾN MẤT KHỎI HOST CHƯA  (404 = rồi)")
        print("=" * 78)
        con = []
        for p in doc_dong(a.xoa_file_file):
            m = ma_http(base + p)
            if m != 404:
                con.append((p, m))
                loi += 1
            print(f"  {p:52s} {m}")
            time.sleep(a.nghi)
        print("\n  --- đối chứng hai đầu (không có nó thì không biết phép dò có thật không) ---")
        if a.con_file:
            m = ma_http(base + a.con_file)
            print(f"  {a.con_file:52s} {m}  (mong 200) {'đúng' if m == 200 else 'LỆCH'}")
            loi += (m != 200)
        m = ma_http(base + "khong-he-ton-tai-abc123.php")
        print(f"  {'(tên bịa)':52s} {m}  (mong 404) {'đúng' if m == 404 else 'LỆCH'}")
        loi += (m != 404)
        if con:
            print(f"\n  {len(con)} file VẪN CÒN trên host:")
            for p, m in con:
                print(f"     {p}  HTTP {m}")

    print()
    print("=" * 78)
    print(f"TỔNG SỐ CA NGUY: {loi}   (phải là 0)")
    print("=" * 78)
    if loi == 0:
        print("Sạch ở tầng này. Nhưng tầng này chỉ thấy MẶT TRƯỚC CÔNG KHAI.")
        print("Trang cần đăng nhập hoặc cần giỏ có hàng (đặt hàng, thanh toán) KHÔNG lấy được")
        print("qua HTTP trần — những bề mặt đó vẫn là NOT_TESTED cho tới khi thao tác tay.")
    return 1 if loi else 0


if __name__ == "__main__":
    sys.exit(main())
