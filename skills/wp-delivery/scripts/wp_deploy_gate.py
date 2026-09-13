#!/usr/bin/env python3
"""Cổng deploy liên worktree — "bản tôi sắp đẩy có đè lên việc của ai không?"

`wp_freshness.py` trả lời "local có khớp host không" bằng cách so asset công khai.
Script này trả lời câu khác, và là câu đã trả giá đắt hơn: **trên host đang có thứ
gì mà git không biết, và tôi sắp đè lên nó không?**

Ba ca thật trên một site WooCommerce, cùng một buổi:

1. Một file `inc/` — bản đang chạy trên host có 287 dòng CHƯA TỪNG commit. Một
   phiên khác suýt deploy bản lấy từ `main` và xoá trắng số dòng đó.
2. `inc/hero-banner.php` + 3 file của một tính năng — sống trên host, không có
   trong `main`. Một đợt giao `functions.php` dựng từ `main` đã xoá hai dòng
   `require`, tắt tính năng. `function_exists()` làm nó hỏng IM LẶNG: `php -l`
   sạch, không một dòng lỗi PHP, và trang chỉ suy biến về nội dung demo.
3. Version `1.24.1` bị hai phiên cùng tự đặt cho hai gói khác nhau, nên về sau
   không ai phân biệt được host đang chạy bản của ai.

Bản đầu của script này quét thiếu và bỏ lọt ca thứ tư, do một phiên khác tìm ra
bằng tay: hai mu-plugin đang phục vụ ĐIỀU HƯỚNG TOÀN SITE trên host mà `main`
không có bản nào — chúng chỉ sống ở một nhánh chưa merge. Phép kiểm 6 nay quét cả
`mu-plugins/` và toàn bộ cây theme, không chỉ hai thư mục.

Dùng:
    python wp_deploy_gate.py --repo "<gốc repo>" \\
        --site https://SITE --theme THEME_SLUG \\
        --branch tinh-nang/logo --version 1.24.5 \\
        --files functions.php assets/css/home.css

    python wp_deploy_gate.py --repo ... --site ... --theme ... --chi-xem-so

Mã thoát: 0 = qua cổng · 1 = có chốt chặn hoặc có phép kiểm không đo được.

Script KHÔNG tự sửa gì. Nó chỉ đo và chặn.
"""
import argparse, json, os, random, re, subprocess, sys, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126 wp-deploy-gate"}

# Thư mục quét cho phép kiểm 6, kèm gốc URL tương ứng trên host.
# Bản đầu chỉ có hai dòng inc/ và template-parts/ — và đã bỏ lọt mu-plugins.
VUNG_QUET = [
    ("theme", ""),          # toàn bộ cây theme
    ("mu-plugins", ""),     # mu-plugin: nạp ở MỌI request, mất là hỏng toàn site
]


def git(repo, *args):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def so_chung(repo):
    """Sổ dùng chung cho MỌI worktree: đặt trong .git chung, không phải cây làm việc."""
    _, d, _ = git(repo, "rev-parse", "--git-common-dir")
    if not d:
        return None
    if not os.path.isabs(d):
        d = os.path.join(repo, d)
    thu_muc = os.path.join(os.path.abspath(d), "wp-deploy")
    os.makedirs(thu_muc, exist_ok=True)
    return os.path.join(thu_muc, "state.json")


def doc_so(duong_dan):
    if not duong_dan or not os.path.exists(duong_dan):
        return {"chiem_cho": [], "nhat_ky": []}
    try:
        with open(duong_dan, encoding="utf-8") as f:
            d = json.load(f)
        d.setdefault("chiem_cho", [])
        d.setdefault("nhat_ky", [])
        return d
    except Exception:
        return {"chiem_cho": [], "nhat_ky": []}


def http_ma(url, timeout=20):
    req = urllib.request.Request(url, headers=UA, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def ver_host(site, theme, timeout=25):
    """Version theme ĐANG CHẠY Ở ORIGIN, không phải bản LiteSpeed còn giữ.

    Đo được một lần: canonical trả `1.24.30` kèm
    `x-litespeed-cache: hit`, cùng lúc origin trả `1.24.31`. Bản đầu gọi thẳng
    URL trang chủ nên đọc phải bản cache, rồi chốt 5 báo "main khai 1.24.31
    nhưng host chạy 1.24.30" — chặn một gói hoàn toàn hợp lệ. Cache còn
    max-age 604800 nên chờ hết hạn không phải cách.

    Thêm tham số ngẫu nhiên để server coi là URL mới (cache miss), kèm
    Cache-Control cho tầng cache trung gian. Câu hỏi đúng ở đây là "origin
    đang chạy gì", không phải "khách thấy gì" — chốt 5 so với `main`, mà
    `main` phải khai đúng bản đã nằm trên đĩa host.
    """
    tham_so = "?cb=%d" % random.randrange(1 << 30)
    h = dict(UA)
    h["Cache-Control"] = "no-cache"
    h["Pragma"] = "no-cache"
    req = urllib.request.Request(site.rstrip("/") + "/" + tham_so, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            html = r.read().decode("utf-8", "replace")
    except Exception:
        return None
    m = re.search(r"themes/" + re.escape(theme) + r"/[^\"']*\?ver=([0-9][0-9.]*)", html)
    return m.group(1) if m else None


def ver_trong_git(repo, ref, theme_rel):
    _, s, _ = git(repo, "show", f"{ref}:{theme_rel}/functions.php")
    # Khớp mọi hằng số kiểu `define('<TIỀN_TỐ>_THEME_VERSION', '1.2.3')` — không gắn
    # cứng một theme. Đổi mẫu ở đây nếu theme khai version bằng header thay vì hằng số.
    m = re.search(r"[A-Z][A-Z0-9_]*_THEME_VERSION['\"]?\s*,\s*['\"]([0-9][0-9.]*)", s or "")
    return m.group(1) if m else None


def so_sanh_ver(a, b):
    """-1 nếu a < b, 0 nếu bằng, 1 nếu a > b. So theo từng bậc số, không so chuỗi."""
    pa = [int(x) for x in re.findall(r"\d+", a or "0")]
    pb = [int(x) for x in re.findall(r"\d+", b or "0")]
    n = max(len(pa), len(pb))
    pa += [0] * (n - len(pa)); pb += [0] * (n - len(pb))
    return (pa > pb) - (pa < pb)


def da_gop_vao_main(repo, branch, main_ref="main"):
    rc, _, _ = git(repo, "merge-base", "--is-ancestor", branch, main_ref)
    return rc == 0


# ---------------------------------------------------------------- các phép kiểm

def kiem_nhanh_loi_thoi(repo, branch, main_ref="main"):
    """Nhánh đã là ancestor của main thì không có gì để rebase — miễn chốt này.

    Bản đầu chặn cả nhánh đã merge, báo động giả. Một phiên khác gặp đúng ca đó.
    """
    if da_gop_vao_main(repo, branch, main_ref):
        return "pass", "nhánh đã gộp vào main — không còn gì để rebase"
    _, s, _ = git(repo, "rev-list", "--count", f"{branch}..{main_ref}")
    n = int(s) if s.isdigit() else -1
    if n < 0:
        return "unavailable", "không đếm được khoảng cách tới main"
    if n == 0:
        return "pass", "nhánh đã sát main"
    return "fail", (f"nhánh đứng sau main {n} commit — rebase trước khi đóng gói, "
                    "không thì gói mang theo nền cũ và xoá việc của người khác")


def kiem_file_chua_commit(repo, theme_rel, files):
    ban = []
    for f in files:
        rel = f"{theme_rel}/{f}"
        _, s, _ = git(repo, "status", "--porcelain", "--", rel)
        if s:
            ban.append(f"{s.split()[0]} {f}")
    if not ban:
        return "pass", f"cả {len(files)} file đã commit"
    return "fail", ("file trong gói còn thay đổi CHƯA COMMIT — deploy xong là git "
                    "không còn biết host đang chạy gì: " + " · ".join(ban))


def kiem_version(so, version, branch, vh):
    """Chặn số TRÙNG do tự đặt, KHÔNG chặn số đi theo host.

    Hai chuyện khác nhau: hai phiên cùng tự đặt một số cho hai gói khác nhau là
    hỏng; còn một số đi theo host xuất hiện ở nhiều nhánh là đúng, vì `main` phải
    khai đúng số đang chạy. Bản đầu gộp hai ca vào một và chặn nhầm cách làm đúng.
    """
    if not version:
        return "not_applicable", "không khai --version"
    if vh and version == vh:
        return "pass", f"{version} chính là version đang chạy trên host — không phải trùng"
    d = doc_so(so)
    trung = [x for x in d["nhat_ky"]
             if x.get("version") == version and x.get("nhanh") != branch
             and x.get("trang_thai") != "RUT_LAI"]
    if trung:
        x = trung[0]
        return "fail", (f"version {version} đã được nhánh `{x.get('nhanh')}` dùng lúc "
                        f"{x.get('luc')} — hai gói cùng số thì về sau không ai phân biệt "
                        "được host đang chạy bản của ai")
    return "pass", f"version {version} chưa ai dùng"


def kiem_version_tut(repo, branch, theme_rel, vh):
    """Version trong nhánh không được NHỎ HƠN version đang chạy trên host.

    Ca thật: hai nhánh còn commit "Bump 1.22.2 -> 1.23.0" trong lịch sử trong khi
    host đã ở 1.24.4. Merge mà commit bump cũ lọt qua là `main` khai số tụt lại —
    cây giao hàng mất mốc đối chiếu, đúng thứ nó tồn tại để bảo vệ.
    """
    if not vh:
        return "unavailable", "không đọc được version host"
    vb = ver_trong_git(repo, branch, theme_rel)
    if not vb:
        return "unavailable", "không đọc được version trong nhánh"
    c = so_sanh_ver(vb, vh)
    if c < 0:
        return "fail", (f"nhánh khai {vb} trong khi host chạy {vh} — merge kiểu này là "
                        "kéo version tụt lại. Rebase và lấy số của main ở dòng version; "
                        "commit nào CHỈ chứa bump thì drop hẳn bằng --onto")
    return "pass", f"nhánh {vb} ≥ host {vh}"


def kiem_chiem_cho(so, branch, files):
    d = doc_so(so)
    va = []
    for c in d["chiem_cho"]:
        if c.get("nhanh") == branch:
            continue
        chung = set(c.get("files", [])) & set(files)
        if chung:
            va.append(f"{', '.join(sorted(chung))} ← `{c.get('nhanh')}` giữ từ {c.get('luc')}")
    if not va:
        return "pass", "không file nào đang bị nhánh khác giữ"
    return "fail", "file đang bị nhánh khác chiếm chỗ: " + " | ".join(va)


def kiem_main_khop_host(repo, theme_rel, vh, main_ref="main"):
    vm = ver_trong_git(repo, main_ref, theme_rel)
    if not vh or not vm:
        return "unavailable", f"không đọc được version (host={vh} main={vm})"
    if vh == vm:
        return "pass", f"main và host cùng {vh} — cây giao hàng còn mốc đối chiếu"
    return "fail", (f"main khai {vm} nhưng host chạy {vh}. Hoặc có đợt chưa commit, "
                    "hoặc có commit chưa deploy — phải biết là cái nào trước khi đẩy tiếp")


# GỠ NGÀY 09/09/2026 — chốt 8 "đợt đã lên host mà chưa merge".
#
# Nó hỏi `merge-base --is-ancestor <ĐẦU NHÁNH> main`, tức lấy trạng thái HÔM NAY
# của nhánh để xét một đợt đã deploy TỪ TRƯỚC. Nhánh nào deploy lần thứ hai trở
# đi thì đầu nhánh luôn đi trước main đúng bằng đợt sắp đẩy, nên chốt này không
# bao giờ ĐẠT lại được.
#
# Và nó mâu thuẫn thẳng với chốt 5: muốn qua chốt 8 phải merge version sắp đẩy
# vào main, trong khi luật dự án bắt main khai đúng version ĐANG CHẠY trên host.
# Hai chốt đòi hai thứ ngược nhau.
#
# Tác hại nó canh — file sống trên host mà main không có — đã được CHỐT 6 đo
# trực tiếp: hỏi thẳng host từng file bằng mã HTTP. Chốt 8 chỉ suy gián tiếp qua
# tên nhánh. Chủ site chốt 09/09/2026: 7 chốt là đủ.


def kiem_file_mo_coi(repo, site, theme, theme_rel, mu_rel, main_ref="main", timeout=20,
                     theme_rel_main=None):
    """File TỒN TẠI trên host mà `main` không có.

    GIỚI HẠN PHẢI NHỚ: server thực thi `.php` chứ không trả source — mọi file PHP
    trả `HTTP 200` với `0 byte`. Đo được lúc 14:0x ngày 05/09/2026 trên cả
    `mu-plugins/` lẫn `inc/`, trong khi `.css` cùng lúc trả 127.611 byte thật.
    Nên mã 200 chứng minh **sự tồn tại**, KHÔNG chứng minh **nội dung khớp**.

    Áp đúng luật của chính bộ công cụ này — *một dấu hiệu chỉ dùng được nếu nó
    vắng mặt ở trạng thái hỏng* — thì với câu hỏi "nội dung có khớp không", mã 200
    không vắng mặt khi nội dung lệch, nên nó là phép đo mù cho câu hỏi đó. Muốn so
    nội dung `.php` chỉ có một đường: tải bản host về qua FTP rồi diff.

    Quét TOÀN BỘ cây theme và cả `wp-content/mu-plugins/` trong MỌI nhánh, hỏi host
    từng file bằng mã HTTP. Bản đầu chỉ quét `inc/` và `template-parts/` nên mù với
    mu-plugin — mà mu-plugin nạp ở mọi request, mất là hỏng toàn site.
    """
    _, br, _ = git(repo, "branch", "--format=%(refname:short)")
    nhanh = [b for b in br.splitlines() if b.strip()]
    if not nhanh:
        return "unavailable", "không liệt kê được nhánh", []

    goc_theme = f"{site.rstrip('/')}/wp-content/themes/{theme}/"
    goc_mu = f"{site.rstrip('/')}/wp-content/mu-plugins/"

    theme_rel_main = theme_rel_main or theme_rel
    # Đợt đổi tên thư mục: nhánh khác còn ở thư mục cũ, nhánh này ở thư mục mới —
    # liệt kê cả hai, quy về cùng một đường dẫn tương đối trong theme để so với main.
    tien_to_theme = sorted({theme_rel, theme_rel_main})
    ung_vien = {}   # duong_dan_url -> nhãn
    for b in nhanh:
        for pre, goc in [(t, goc_theme) for t in tien_to_theme] + [(mu_rel, goc_mu)]:
            _, s, _ = git(repo, "ls-tree", "-r", "--name-only", b, f"{pre}/")
            for line in s.splitlines():
                if line.endswith(".php"):
                    ung_vien[line] = goc + line[len(pre) + 1:]

    def chuan(line):
        # quy 'themes/<bất kỳ tên>/x.php' về 'themes/*/x.php' để hai tên thư mục so được nhau
        for t in tien_to_theme:
            if line.startswith(t + "/"):
                return "<theme>/" + line[len(t) + 1:]
        return line
    ung_vien = {chuan(k): v for k, v in ung_vien.items()}

    co_trong_main = set()
    for pre in (theme_rel_main, mu_rel):
        _, s, _ = git(repo, "ls-tree", "-r", "--name-only", main_ref, f"{pre}/")
        co_trong_main.update(chuan(l) for l in s.splitlines() if l.endswith(".php"))

    nghi = sorted(set(ung_vien) - co_trong_main)
    if not nghi:
        return "pass", ("mọi file PHP các nhánh biết đều CÓ MẶT trong main "
                        "— nội dung thì phép kiểm này không so được"), []

    mo_coi = []
    for f in nghi[:60]:
        if http_ma(ung_vien[f], timeout) == 200:
            nhan = f.split("/wp-content/", 1)[-1] if "/wp-content/" in f else f
            mo_coi.append(nhan)
    if not mo_coi:
        return "pass", f"{len(nghi)} file chỉ có ở nhánh khác, host chưa có — không sao", []
    return "fail", ("FILE TỒN TẠI TRÊN HOST MÀ MAIN KHÔNG CÓ — dựng lại từ main sẽ xoá "
                    "chúng khỏi host, và xoá im lặng: " + " · ".join(mo_coi)
                    + "  [mã HTTP chỉ dò được SỰ TỒN TẠI; nội dung .php phải so qua FTP]"), mo_coi


# ---------------------------------------------------------------------- in ấn

BIEU = {"pass": "ĐẠT   ", "fail": "CHẶN  ", "unavailable": "KHÔNG ĐO ĐƯỢC",
        "not_applicable": "BỎ QUA"}


def main():
    p = argparse.ArgumentParser(description="Cổng deploy liên worktree")
    p.add_argument("--repo", required=True)
    p.add_argument("--site", required=True)
    p.add_argument("--theme", required=True, help="tên thư mục theme trong NHÁNH")
    p.add_argument("--theme-host", help="tên thư mục theme ĐANG CHẠY trên host, nếu khác --theme "
                   "(ví dụ giữa đợt đổi tên thư mục: host còn tên cũ, nhánh đã tên mới)")
    p.add_argument("--theme-main", help="tên thư mục theme trong MAIN, nếu khác --theme")
    p.add_argument("--theme-rel", default="wp-content/themes",
                   help="đường dẫn tới thư mục themes trong repo; đổi nếu repo lồng sâu hơn "
                        "(ví dụ 'source code/wp-content/themes')")
    p.add_argument("--mu-rel", default="wp-content/mu-plugins",
                   help="đường dẫn tới thư mục mu-plugins trong repo")
    p.add_argument("--branch")
    p.add_argument("--version")
    p.add_argument("--files", nargs="*", default=[])
    p.add_argument("--main-ref", default="main",
                   help="nhánh/commit đóng vai main — đổi để HIỆU CHUẨN script "
                        "trên một ca hỏng đã biết trong quá khứ")
    p.add_argument("--chi-xem-so", action="store_true")
    a = p.parse_args()

    repo = os.path.abspath(a.repo)
    theme_rel = f"{a.theme_rel}/{a.theme}"
    theme_host = a.theme_host or a.theme
    theme_rel_main = f"{a.theme_rel}/{a.theme_main or a.theme}"
    so = so_chung(repo)

    if a.chi_xem_so:
        d = doc_so(so)
        print(f"SỔ CHUNG  {so}")
        if not d["chiem_cho"]:
            print("  không nhánh nào đang chiếm chỗ")
        for c in d["chiem_cho"]:
            print(f"  `{c.get('nhanh')}` giữ {len(c.get('files', []))} file từ {c.get('luc')}"
                  f"  — {c.get('ghi_chu', '')}")
            for f in c.get("files", []):
                print(f"       {f}")
        print(f"\nNHẬT KÝ DEPLOY ({len(d['nhat_ky'])} đợt)")
        for x in d["nhat_ky"][-12:]:
            print(f"  {x.get('luc')}  {str(x.get('version')):<8} {str(x.get('nhanh')):<28} "
                  f"{x.get('trang_thai', '?')}")
        return 0

    if not a.branch:
        _, a.branch, _ = git(repo, "rev-parse", "--abbrev-ref", "HEAD")

    vh = ver_host(a.site, theme_host)

    print(f"=== CỔNG DEPLOY · {a.site} · nhánh `{a.branch}` · host {vh or '?'} ===\n")
    ket = []
    ket.append(("1. nhánh có lỗi thời không", *kiem_nhanh_loi_thoi(repo, a.branch, a.main_ref)))
    if a.files:
        ket.append(("2. file trong gói đã commit chưa", *kiem_file_chua_commit(repo, theme_rel, a.files)))
    else:
        ket.append(("2. file trong gói đã commit chưa", "not_applicable", "không khai --files"))
    ket.append(("3. version đã ai dùng chưa", *kiem_version(so, a.version, a.branch, vh)))
    ket.append(("4. file có bị nhánh khác giữ", *kiem_chiem_cho(so, a.branch, a.files)))
    ket.append(("5. main có khớp host", *kiem_main_khop_host(repo, theme_rel_main, vh, a.main_ref)))
    r6 = kiem_file_mo_coi(repo, a.site, theme_host, theme_rel, a.mu_rel, a.main_ref,
                          theme_rel_main=theme_rel_main)
    ket.append(("6. file mồ côi trên host", r6[0], r6[1]))
    ket.append(("7. version nhánh có tụt sau host", *kiem_version_tut(repo, a.branch, theme_rel, vh)))

    rong = max(len(k[0]) for k in ket)
    for ten, tt, msg in ket:
        print(f"{BIEU.get(tt, tt):<14} {ten:<{rong}}  {msg}")

    chan = [k for k in ket if k[1] == "fail"]
    khong_do = [k for k in ket if k[1] == "unavailable"]
    print()
    if chan:
        print(f"DEPLOY_GATE_FAILED       {len(chan)} chốt chặn — sửa xong mới được dựng gói")
        return 1
    if khong_do:
        print(f"DEPLOY_GATE_INCONCLUSIVE {len(khong_do)} phép kiểm không đo được — "
              "fail-closed, đừng đọc thành 'không có lỗi'")
        return 1
    print("DEPLOY_GATE_PASSED       qua cổng liên worktree")
    print("RUNTIME_NOT_TESTED       cổng này không chạy WordPress — vẫn phải xác minh sau deploy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
