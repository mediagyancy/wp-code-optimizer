#!/usr/bin/env python3
"""Cổng 3 — chất lượng code. `php -l` sạch chưa đủ để deploy.

Cổng ghi file bảo vệ file khỏi rỗng và lỗi cú pháp. Cổng này bảo vệ code khỏi sai
chuẩn WordPress, sai tương thích PHP, và sai kiểu/hợp đồng. Hai cổng không thay nhau.

Mỗi phép kiểm báo RIÊNG một trạng thái, không gộp thành một chữ PASS:

    pass            đã chạy và sạch trong phạm vi đã khai
    fail            đã chạy và có lỗi                      → chặn
    unavailable     thiếu binary hoặc config               → chặn, KHÔNG được coi là pass
    not_applicable  không có file thuộc loại đó            → ghi rõ

`unavailable` fail-closed. Thiếu PHPStan nghĩa là PHPSTAN_UNAVAILABLE, không phải
"không có lỗi". Muốn đi tiếp thì cài công cụ, hoặc xin ngoại lệ cụ thể từ người dùng —
ngoại lệ không tự cấp, và không biến phép kiểm thành pass.

Dùng:
    # kiểm đúng file đang sửa (cách dùng chính — legacy không chặn việc của bạn)
    python wp_quality.py --repo "/duong/dan/repo" --files "wp-content/themes/mytheme/inc/cart.php"

    # kiểm toàn bộ phạm vi khai trong config (chỉ để nhìn hiện trạng)
    python wp_quality.py --repo "/duong/dan/repo" --all

Mã thoát: 0 mọi phép kiểm áp dụng đều pass · 1 có fail · 2 có unavailable.
"""
import argparse, os, shutil, subprocess, sys

sys.stdout.reconfigure(encoding="utf-8")

# Nơi đặt phpcs/phpstan. CỐ Ý để NGOÀI repo của site: thư mục vendor/ của bộ
# công cụ nặng vài chục MB và không có việc gì trên production, nên đừng cho nó
# cơ hội đi theo một lần kéo FTP.
#   · đặt biến môi trường WP_QUALITY_TOOLS trỏ tới <bộ-công-cụ>/vendor/bin
#   · không đặt thì script tự tìm phpcs/phpstan trong PATH
TOOLS = os.environ.get("WP_QUALITY_TOOLS", "")


def cong_cu(ten):
    """Trả về đường dẫn công cụ, ưu tiên WP_QUALITY_TOOLS rồi mới tới PATH.

    Không tìm thấy thì trả về chuỗi rỗng — chỗ gọi phải đọc đó thành
    <TEN>_UNAVAILABLE và CHẶN, tuyệt đối không đọc thành "không có lỗi".
    """
    if TOOLS:
        p = os.path.join(TOOLS, ten)
        for hau in ("", ".bat", ".phar"):
            if os.path.exists(p + hau):
                return p + hau
    return shutil.which(ten) or ""


def php():
    return shutil.which("php")


def run(cmd, cwd):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=600)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return -1, str(e)


def check_phpcs(repo, files):
    cfg = next((c for c in ("phpcs.xml.dist", "phpcs.xml", ".phpcs.xml.dist")
                if os.path.exists(os.path.join(repo, c))), None)
    bin_ = cong_cu("phpcs")
    if not php():
        return "unavailable", "không có PHP"
    if not os.path.exists(bin_):
        return "unavailable", f"chưa cài phpcs ({bin_})"
    if not cfg:
        return "unavailable", "repo chưa có phpcs.xml.dist — chuẩn chưa được khai thì không kiểm được"
    cmd = [php(), bin_, "--report=summary", f"--standard={cfg}"] + (files or [])
    code, out = run(cmd, repo)
    if code == 0:
        return "pass", f"theo {cfg}"
    tail = [l for l in out.splitlines() if "TOTAL" in l or "ERRORS" in l]
    return "fail", (tail[-1].strip() if tail else out.strip()[:200])


def check_phpstan(repo, files):
    cfg = next((c for c in ("phpstan.neon.dist", "phpstan.neon")
                if os.path.exists(os.path.join(repo, c))), None)
    bin_ = cong_cu("phpstan")
    if not php():
        return "unavailable", "không có PHP"
    if not os.path.exists(bin_):
        return "unavailable", f"chưa cài phpstan ({bin_})"
    if not cfg:
        return "unavailable", "repo chưa có phpstan.neon.dist"
    # --memory-limit bắt buộc: stub WooCommerce nặng, worker vượt mặc định rồi crash,
    # và PHPStan báo chính cái crash đó thành "Found 1 error" — đọc nhầm thành lỗi code.
    cmd = [php(), bin_, "analyse", "--no-progress", "--error-format=table",
           "--memory-limit=3G", f"--configuration={cfg}"] + (files or [])
    code, out = run(cmd, repo)
    if code == 0:
        return "pass", f"level theo {cfg}"
    if "memory limit" in out or "process crashed" in out:
        return "unavailable", "PHPStan crash vì hết bộ nhớ — đây KHÔNG phải lỗi code, tăng --memory-limit"
    errs = [l for l in out.splitlines() if "Found " in l and "error" in l]
    return "fail", (errs[-1].strip() if errs else out.strip()[:200])


def check_tests(repo):
    """Không bịa lệnh test. Đọc file cấu hình thật của repo."""
    for f in ("phpunit.xml.dist", "phpunit.xml"):
        if os.path.exists(os.path.join(repo, f)):
            bin_ = cong_cu("phpunit")
            if not os.path.exists(bin_):
                return "unavailable", f"có {f} nhưng chưa cài phpunit"
            code, out = run([php(), bin_, f"--configuration={f}"], repo)
            return ("pass" if code == 0 else "fail"), out.strip().splitlines()[-1][:200] if out else ""
    return "unavailable", "repo chưa có test suite — TESTS_UNAVAILABLE, không phải 'không có lỗi'"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--files", nargs="*", help="đường dẫn tương đối trong repo; bỏ trống = dùng --all")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--skip-tests", action="store_true")
    a = ap.parse_args()

    repo = os.path.abspath(a.repo)
    if not os.path.isdir(repo):
        print(f"Không thấy repo {repo}")
        return 2

    files = [] if a.all else (a.files or [])
    php_files = [f for f in files if f.lower().endswith(".php")]
    scope = "toàn bộ phạm vi trong config" if a.all else f"{len(files)} file"

    print(f"=== Cổng 3 — chất lượng code · {os.path.basename(repo)} · {scope}\n")

    results = []
    if files and not php_files:
        results.append(("PHPCS", "not_applicable", "không có file PHP trong phạm vi"))
        results.append(("PHPSTAN", "not_applicable", "không có file PHP trong phạm vi"))
    else:
        results.append(("PHPCS", *check_phpcs(repo, php_files)))
        results.append(("PHPSTAN", *check_phpstan(repo, php_files)))

    if a.skip_tests:
        results.append(("TESTS", "not_applicable", "bỏ qua theo yêu cầu — phải ghi lý do trong Change Manifest"))
    else:
        results.append(("TESTS", *check_tests(repo)))

    label = {"pass": "PASSED", "fail": "FAILED", "unavailable": "UNAVAILABLE",
             "not_applicable": "NOT_APPLICABLE"}
    for name, state, msg in results:
        print(f"{name}_{label[state]:<16} {msg}")

    states = [s for _, s, _ in results]
    print()
    if "fail" in states:
        print("QUALITY_GATES_FAILED     có phép kiểm báo lỗi — sửa trước khi ghi/deploy")
        rc = 1
    elif "unavailable" in states:
        print("QUALITY_GATES_BLOCKED    có phép kiểm không chạy được.")
        print("                         KHÔNG được đọc thành 'không có lỗi'. Cài công cụ,")
        print("                         hoặc xin người dùng duyệt ngoại lệ cho đúng lần này.")
        rc = 2
    else:
        print("QUALITY_GATES_PASSED     mọi phép kiểm áp dụng đều sạch")
        rc = 0
    print("RUNTIME_NOT_TESTED       cổng này không chạy WordPress — vẫn phải kiểm trên site thật")
    return rc


if __name__ == "__main__":
    sys.exit(main())
