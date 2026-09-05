#!/usr/bin/env python3
"""Cổng tươi mới — bản local có khớp bản đang chạy trên host không?

Trả lời đúng một câu hỏi, và trả lời bằng đo chứ không bằng niềm tin:
"những file tôi sắp sửa, trên host có đúng như bản tôi đang mở không?"

Vì sao cần: local và host từng cùng ghi version theme 1.17.1 mà main.css lệch
1.492 ký tự trong 3 khối — deploy lần sau sẽ mang theo thay đổi chưa ai duyệt.

Dùng:
    python wp_freshness.py --site https://vidu.com \\
        --theme mytheme --local "/duong/dan/repo/wp-content/themes/mytheme"

    # chỉ vài file
    python wp_freshness.py --site ... --theme ... --local ... \\
        --files assets/css/main.css assets/js/cart.js

Mã thoát: 0 = mọi file so được đều khớp · 1 = có lệch · 2 = không so được gì.
Lệch xuống dòng CRLF/LF được bỏ qua — đó không phải khác biệt thật.

Giới hạn phải nhớ: server không cho tải .php qua trình duyệt, nên script này
KHÔNG kiểm được file PHP. Muốn chắc phần PHP thì tải theme từ FTP về rồi so tay.
"""
import argparse, hashlib, os, re, sys, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126 wp-freshness"}
WEB_EXT = (".css", ".js", ".svg", ".woff2", ".json")


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, b"", {}
    except Exception as e:
        return 0, str(e).encode(), {}


def norm(b):
    """Chuẩn hoá xuống dòng: CRLF của Windows và LF của host không phải khác biệt thật."""
    return b.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def h(b):
    return hashlib.sha256(norm(b)).hexdigest()[:12]


def theme_versions(html, theme):
    """Version lộ ra trong HTML qua ?ver= — cách rẻ nhất biết host đang chạy bản nào."""
    pat = re.compile(r"themes/" + re.escape(theme) + r"/[^\"']*?\?ver=([0-9][0-9.]*)")
    return sorted(set(pat.findall(html)))


def theme_assets(html, theme):
    """Các asset công khai của theme mà trang chủ thực sự nạp."""
    pat = re.compile(r"themes/" + re.escape(theme) + r"/([^\"'?]+)")
    return sorted({m for m in pat.findall(html) if m.endswith(WEB_EXT)})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--theme", required=True)
    ap.add_argument("--local", required=True, help="thư mục theme trên máy")
    ap.add_argument("--files", nargs="*", help="đường dẫn tương đối trong theme; bỏ trống = tự dò từ trang chủ")
    ap.add_argument("--url", default=None, help="trang dùng để dò asset (mặc định: trang chủ)")
    a = ap.parse_args()

    site = a.site.rstrip("/")
    page = a.url or site

    print(f"SITE   {site}")
    print(f"THEME  {a.theme}")
    print(f"LOCAL  {a.local}\n")

    status, body, _ = fetch(page)
    if status != 200:
        print(f"[!] Không tải được {page} (HTTP {status}). Không kết luận được gì.")
        return 2
    html = body.decode("utf-8", "replace")

    vers = theme_versions(html, a.theme)
    print("VERSION theme lộ ra trong HTML:", ", ".join(vers) if vers else "(không thấy ?ver=)")
    if len(vers) > 1:
        print("    ^ nhiều version cùng lúc — có file chưa được bump, hoặc deploy dở dang")
    print()

    rels = a.files or theme_assets(html, a.theme)
    if not rels:
        print("[!] Không dò được asset nào của theme trên trang này.")
        print("    Thử --url một trang khác, hoặc chỉ định --files.")
        return 2

    print(f"{'FILE':<44} {'HOST':<14} {'LOCAL':<14} KẾT LUẬN")
    print("-" * 92)
    diff = same = skip = 0
    for rel in rels:
        url = f"{site}/wp-content/themes/{a.theme}/{rel}"
        st, remote, _ = fetch(url)
        lp = os.path.join(a.local, rel.replace("/", os.sep))
        if st != 200:
            print(f"{rel:<44} {'HTTP ' + str(st):<14} {'-':<14} không tải được")
            skip += 1
            continue
        if not os.path.exists(lp):
            print(f"{rel:<44} {h(remote):<14} {'thiếu':<14} local KHÔNG CÓ file này")
            skip += 1
            continue
        local = open(lp, "rb").read()
        if h(remote) == h(local):
            print(f"{rel:<44} {h(remote):<14} {h(local):<14} khớp")
            same += 1
        else:
            d = len(norm(local)) - len(norm(remote))
            print(f"{rel:<44} {h(remote):<14} {h(local):<14} LỆCH ({d:+d} ký tự)")
            diff += 1

    print("-" * 92)
    print(f"khớp {same} · lệch {diff} · không so được {skip}")
    print("\nNhắc: file PHP không tải được qua trình duyệt nên KHÔNG nằm trong phép so này.")
    if diff:
        print("\nCÓ LỆCH → chưa được sửa. Xác định bản nào mới hơn trước, đừng đè bừa.")
        print("Bản local mới hơn: đợt deploy tới sẽ mang theo thay đổi đó — phải biết trước.")
        print("Bản host mới hơn: ai đó sửa thẳng trên hosting, kéo về trước khi làm gì tiếp.")
        return 1
    if same == 0:
        return 2
    print("\nKHỚP → qua cổng, được sửa tiếp.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
