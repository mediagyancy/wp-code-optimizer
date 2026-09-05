#!/usr/bin/env python3
"""Canh URL trọng yếu — bắt loại hỏng im lặng.

Vì sao cần: có kiểu hỏng chỉ giết MỘT bề mặt trong khi trang chủ vẫn chạy ngon.
Đã xảy ra: trang thanh toán chết vì upload sai thứ tự, các trang khác không hề gì.
HTTP 200 không đủ — trang vẫn 200 khi nút thêm vào giỏ đã biến mất.

Nên mỗi URL đi kèm một CHUỖI MỐC phải có mặt trong HTML. Mất mốc = báo động,
kể cả khi trang trả 200.

Dùng:
    python wp_urlwatch.py sites/vidu.json          # kiểm một lần
    python wp_urlwatch.py sites/*.json --quiet             # chỉ in khi có lỗi (hợp cho cron)

Mã thoát: 0 = mọi mốc còn nguyên · 1 = có mốc mất hoặc URL lỗi · 2 = cấu hình sai.

Cấu hình (JSON):
{
  "site": "https://vidu.com",
  "theme_version_in_html": true,
  "checks": [
    {"url": "/",          "must_contain": ["Dự án A"]},
    {"url": "/gio-hang/", "must_contain": ["giỏ hàng"], "must_not_contain": ["Fatal error"]}
  ]
}
"""
import json, re, sys, time, urllib.request, urllib.error, glob, os

sys.stdout.reconfigure(encoding="utf-8")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126 wp-urlwatch"}
FATAL = ("Fatal error", "Parse error", "There has been a critical error", "Warning: require")


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", "replace")
            return r.status, body, dict(r.headers), time.time() - t0
    except urllib.error.HTTPError as e:
        return e.code, "", {}, time.time() - t0
    except Exception as e:
        return 0, str(e), {}, time.time() - t0


def run(cfg_path, quiet=False):
    try:
        cfg = json.load(open(cfg_path, encoding="utf-8"))
        site = cfg["site"].rstrip("/")
        checks = cfg["checks"]
    except Exception as e:
        print(f"[!] cấu hình hỏng {cfg_path}: {e}")
        return 2

    problems = []
    lines = []
    for c in checks:
        url = c["url"] if c["url"].startswith("http") else site + c["url"]
        status, body, hdr, dt = fetch(url)
        issues = []

        if status != 200:
            issues.append(f"HTTP {status}")
        else:
            for m in c.get("must_contain", []):
                if m not in body:
                    issues.append(f"MẤT MỐC: {m!r}")
            for m in c.get("must_not_contain", []):
                if m in body:
                    issues.append(f"XUẤT HIỆN: {m!r}")
            for f in FATAL:
                if f in body:
                    issues.append(f"LỖI PHP LỘ RA TRANG: {f!r}")

        cache = hdr.get("x-litespeed-cache") or hdr.get("X-LiteSpeed-Cache") or "-"
        mark = "OK  " if not issues else "FAIL"
        lines.append(f"{mark} {dt:5.2f}s cache={cache:<5} {url}")
        for i in issues:
            lines.append(f"       └─ {i}")
            problems.append((url, i))

    if cfg.get("theme_version_in_html"):
        st, body, _, _ = fetch(site)
        vers = sorted(set(re.findall(r"themes/[^/]+/[^\"']*?\?ver=([0-9][0-9.]*)", body))) if st == 200 else []
        lines.append(f"     version theme trong HTML: {', '.join(vers) if vers else '(không thấy)'}")
        # Chỉ cảnh báo khi version là semver. Nhiều theme dùng ?ver= dạng timestamp
        # (mỗi file một số) — đó là bình thường, cảnh báo ở đó là báo động giả.
        semver = [v for v in vers if re.match(r"^\d+\.\d+", v)]
        if len(semver) > 1:
            lines.append("       └─ nhiều version cùng lúc: có file chưa bump, hoặc deploy dở dang")

    if problems or not quiet:
        print(f"\n=== {site} · {time.strftime('%Y-%m-%d %H:%M')} ===")
        print("\n".join(lines))
    if problems:
        print(f"\n{len(problems)} vấn đề — kiểm ngay, đừng đợi khách báo.")
    return 1 if problems else 0


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    quiet = "--quiet" in sys.argv
    paths = []
    for a in args:
        paths.extend(glob.glob(a) or [a])
    if not paths:
        print(__doc__)
        return 2
    rc = 0
    for p in paths:
        if not os.path.exists(p):
            print(f"[!] không thấy {p}")
            rc = max(rc, 2)
            continue
        rc = max(rc, run(p, quiet))
    return rc


if __name__ == "__main__":
    sys.exit(main())
