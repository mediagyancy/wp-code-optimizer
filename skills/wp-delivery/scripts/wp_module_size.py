#!/usr/bin/env python3
"""Đo kích cỡ module — chuông báo kiến trúc, không phải trò đếm dòng.

Ngưỡng chỉ là chuông. Một file 100 dòng giữ ba trách nhiệm vẫn phải tách; một bảng
khai báo dài thuần dữ liệu có thể được miễn. Script này không thay người đọc code,
nó chỉ chỉ chỗ đáng nhìn và chặn việc âm thầm phình thêm.

Vấn đề thật của mã kế thừa: cấm cứng theo ngưỡng thì không sửa được gì, vì file
legacy đã vượt sẵn (đo 01/09/2026: `theme-b/functions.php` 1.218 LOC, `inc/bao-gia.php`
1.477 LOC). Nên luật là:

    file MỚI      → áp ngưỡng chặn
    file LEGACY   → không áp ngưỡng, nhưng LOC RÒNG KHÔNG ĐƯỢC TĂNG

"Legacy" nghĩa là đã có trong baseline. Baseline chụp một lần, commit vào repo.

Dùng:
    # chụp hiện trạng (chạy một lần cho mỗi theme)
    python wp_module_size.py --scan "<theme>" --write-baseline "<theme>/.module-size.json"

    # kiểm trước khi ghi/deploy
    python wp_module_size.py --check "<theme>" --baseline "<theme>/.module-size.json"

    # xem báo cáo, không cần baseline
    python wp_module_size.py --scan "<theme>"

Mã thoát: 0 sạch · 1 có vi phạm chặn · 2 sai tham số.
"""
import argparse, json, os, re, sys

sys.stdout.reconfigure(encoding="utf-8")

# ngưỡng: (mục tiêu, xem lại, chặn)
LIMITS = {
    "functions.php": (80, 80, 80),
    "php":  (300, 450, 450),
    "js":   (300, 450, 450),
    "css":  (400, 600, 600),
}
FUNC_TARGET, FUNC_REVIEW, FUNC_BLOCK = 40, 80, 80
SKIP_DIRS = {"node_modules", "vendor", "dist", "build", ".git", "_backup"}


def loc(path):
    """LOC thực: bỏ dòng trống và dòng thuần comment."""
    n = 0
    try:
        for line in open(path, encoding="utf-8", errors="replace"):
            s = line.strip()
            if not s or s.startswith(("//", "#", "*", "/*", "*/", "<!--")):
                continue
            n += 1
    except Exception:
        return 0
    return n


def php_functions(path):
    """Đo độ dài từng function/method bằng cân bằng ngoặc. Đủ dùng, không cần parser."""
    try:
        src = open(path, encoding="utf-8", errors="replace").read()
    except Exception:
        return []
    out = []
    for m in re.finditer(r"function\s+([A-Za-z_]\w*)\s*\(", src):
        name = m.group(1)
        i = src.find("{", m.end())
        if i == -1:
            continue
        depth, j = 0, i
        while j < len(src):
            if src[j] == "{":
                depth += 1
            elif src[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        body = src[i:j]
        n = sum(1 for l in body.split("\n")
                if l.strip() and not l.strip().startswith(("//", "#", "*", "/*")))
        out.append((name, n, src[:m.start()].count("\n") + 1))
    return out


def kind(path):
    base = os.path.basename(path).lower()
    if base == "functions.php":
        return "functions.php"
    ext = os.path.splitext(path)[1].lower()
    return {".php": "php", ".js": "js", ".css": "css"}.get(ext)


def scan(root):
    rows = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            k = kind(p)
            if not k:
                continue
            if fn.endswith((".min.js", ".min.css")):
                continue
            rel = os.path.relpath(p, root).replace("\\", "/")
            rows[rel] = {"loc": loc(p), "kind": k}
    return rows


def verdict(k, n):
    target, review, block = LIMITS[k]
    if n > block:
        return "CHAN"
    if n > review:
        return "XEM_LAI"
    if n > target:
        return "XEM_LAI"
    return "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan")
    ap.add_argument("--check")
    ap.add_argument("--baseline")
    ap.add_argument("--write-baseline")
    ap.add_argument("--top", type=int, default=12)
    a = ap.parse_args()

    root = a.scan or a.check
    if not root or not os.path.isdir(root):
        print("Cần --scan hoặc --check trỏ tới một thư mục.")
        return 2

    rows = scan(root)

    if a.write_baseline:
        json.dump({k: v["loc"] for k, v in sorted(rows.items())},
                  open(a.write_baseline, "w", encoding="utf-8"), indent=1)
        print(f"BASELINE_WRITTEN         {a.write_baseline} — {len(rows)} file")
        print("Commit file này. Từ nay file có trong đây là LEGACY: không áp ngưỡng,")
        print("nhưng LOC không được tăng. File không có trong đây là MỚI: áp ngưỡng chặn.")
        return 0

    base = {}
    if a.baseline and os.path.exists(a.baseline):
        base = json.load(open(a.baseline, encoding="utf-8"))
    elif a.check:
        print(f"[!] Không thấy baseline {a.baseline!r} — coi MỌI file là mới.")
        print("    Chụp baseline trước bằng --write-baseline, nếu không mã kế thừa sẽ chặn hết.\n")

    blocked, review, grown = [], [], []
    for rel, info in sorted(rows.items(), key=lambda x: -x[1]["loc"]):
        n, k = info["loc"], info["kind"]
        was = base.get(rel)
        if was is None:                      # file mới
            v = verdict(k, n)
            if v == "CHAN":
                blocked.append((rel, n, k, "file mới vượt ngưỡng chặn"))
            elif v == "XEM_LAI":
                review.append((rel, n, k, "file mới trên mục tiêu"))
        elif n > was:                        # legacy phình thêm
            grown.append((rel, n, k, f"legacy tăng {n - was} LOC (baseline {was})"))

    print(f"=== {root}")
    print(f"{len(rows)} file · lớn nhất:")
    for rel, info in sorted(rows.items(), key=lambda x: -x[1]["loc"])[:a.top]:
        n, k = info["loc"], info["kind"]
        tag = "legacy" if rel in base else "mới"
        print(f"  {n:6d} LOC  {verdict(k, n):8s} {tag:6s} {rel}")

    long_funcs = []
    for rel, info in rows.items():
        if info["kind"] in ("php", "functions.php"):
            for name, n, line in php_functions(os.path.join(root, rel)):
                if n > FUNC_BLOCK:
                    long_funcs.append((rel, name, n, line))
    long_funcs.sort(key=lambda x: -x[2])
    if long_funcs:
        print(f"\nHàm dài quá {FUNC_BLOCK} LOC: {len(long_funcs)}")
        for rel, name, n, line in long_funcs[:6]:
            print(f"  {n:6d} LOC  {rel}:{line}  {name}()")

    print()
    if blocked:
        print(f"MODULE_TOO_LARGE         {len(blocked)} file mới vượt ngưỡng chặn")
        for rel, n, k, why in blocked[:8]:
            code = "FUNCTIONS_PHP_TOO_LARGE" if k == "functions.php" else "MODULE_TOO_LARGE"
            print(f"  {code:24s} {rel} — {n} LOC ({why})")
    if grown:
        print(f"LEGACY_GREW              {len(grown)} file kế thừa phình thêm")
        for rel, n, k, why in grown[:8]:
            print(f"  {'':24s} {rel} — {why}")
    if review:
        print(f"REVIEW_ARCHITECTURE      {len(review)} file mới trên mục tiêu (chưa chặn)")
        for rel, n, k, why in review[:6]:
            print(f"  {'':24s} {rel} — {n} LOC")
    if not (blocked or grown):
        print("SIZE_CHECKS_PASSED       không có file mới vượt ngưỡng, không có legacy phình thêm")
    print("\nNgưỡng chỉ là chuông báo: file dưới ngưỡng mà giữ nhiều trách nhiệm vẫn phải tách.")
    return 1 if (blocked or grown) else 0


if __name__ == "__main__":
    sys.exit(main())
