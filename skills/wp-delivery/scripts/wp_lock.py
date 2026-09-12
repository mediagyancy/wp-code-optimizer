#!/usr/bin/env python3
"""Sổ chiếm chỗ + nhật ký deploy dùng chung cho mọi worktree của một repo.

Vì sao cần: một buổi có 13 worktree cùng trỏ vào một site WooCommerce đang chạy. Hai
phiên cùng tự đặt version `1.24.1` cho hai gói khác nhau; một đợt giao `functions.php`
dựng từ `main` tắt mất một tính năng của phiên khác. Không ai làm sai quy trình
của riêng mình — họ chỉ **không có chỗ nào để nhìn thấy nhau**.

Sổ đặt ở `<.git chung>/wp-deploy/state.json`, KHÔNG đặt trong cây làm việc: mỗi
worktree có một cây riêng nên file trong cây không ai thấy của ai — đúng cái bệnh
cần chữa. `.git` thì mọi worktree dùng chung.

Ngoài sổ máy đọc, script còn rải một file `_UU-TIEN-DEPLOY.md` vào GỐC MỌI CÂY để
phiên nào chạy `git status` cũng đập vào mắt. Cách này đã dùng thật hôm 05/09 và
bốn phiên đều nhường đúng.

Dùng:
    # trước khi sửa: giữ chỗ
    python wp_lock.py --repo R --claim --branch tinh-nang/logo \\
        --files functions.php assets/css/main.css --note "đợt logo, host 1.24.3->1.24.4"

    # xin số version kế tiếp, không bao giờ trùng
    python wp_lock.py --repo R --next-version --site https://SITE --theme THEME_SLUG

    # ghi nhật ký khi gói lên host
    python wp_lock.py --repo R --log --branch tinh-nang/logo --version 1.24.4 \\
        --status PRODUCTION_VERIFIED

    # xong việc: trả chỗ
    python wp_lock.py --repo R --release --branch tinh-nang/logo

    python wp_lock.py --repo R --list

Mã thoát: 0 = xong · 1 = từ chối (chỗ đang có người giữ).
"""
import argparse, json, os, re, subprocess, sys, time, urllib.request

sys.stdout.reconfigure(encoding="utf-8")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126 wp-lock"}
TEN_FILE_CANH_BAO = "_UU-TIEN-DEPLOY.md"


def git(repo, *a):
    r = subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def duong_dan_so(repo):
    _, d, _ = git(repo, "rev-parse", "--git-common-dir")
    if not os.path.isabs(d):
        d = os.path.join(repo, d)
    tm = os.path.join(os.path.abspath(d), "wp-deploy")
    os.makedirs(tm, exist_ok=True)
    return os.path.join(tm, "state.json")


def doc(p):
    if not os.path.exists(p):
        return {"chiem_cho": [], "nhat_ky": []}
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        return {"chiem_cho": [], "nhat_ky": []}
    d.setdefault("chiem_cho", [])
    d.setdefault("nhat_ky", [])
    return d


def ghi(p, d):
    """Ghi qua file tạm rồi đổi tên — sổ này nhiều phiên cùng đụng, hỏng là mất cả."""
    tam = p + ".tmp"
    with open(tam, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tam, p)


def cac_cay(repo):
    _, s, _ = git(repo, "worktree", "list")
    return [l.split()[0] for l in s.splitlines() if l.strip()]


def rai_canh_bao(repo, d):
    """Sinh file cảnh báo ở mọi cây. Không ai giữ chỗ thì xoá sạch."""
    cay = cac_cay(repo)
    if not d["chiem_cho"]:
        n = 0
        for c in cay:
            p = os.path.join(c, TEN_FILE_CANH_BAO)
            if os.path.exists(p):
                os.remove(p)
                n += 1
        return n, len(cay), True

    dong = ["# ĐANG CÓ ĐỢT DEPLOY — nhường đường", "",
            "> File này do `wp_lock.py` sinh ra. **Đừng commit.** Nó tự biến mất khi",
            "> chủ đợt trả chỗ. Sổ gốc: `<.git chung>/wp-deploy/state.json`.", ""]
    for c in d["chiem_cho"]:
        dong += [f"## `{c['nhanh']}` giữ chỗ từ {c['luc']}", "",
                 f"{c.get('ghi_chu', '')}", "",
                 "Các file đang bị chiếm — đừng sửa, đừng đóng gói, đừng bump version:", ""]
        dong += [f"- `{f}`" for f in c.get("files", [])]
        dong += [""]
    dong += ["## Ba việc xin dừng cho tới khi file này biến mất", "",
             "1. Không bump hằng số version theme — xin số bằng `wp_lock.py --next-version`.",
             "2. Không đóng gói / deploy các file ở trên.",
             "3. Không merge vào `main` trước chủ đợt.", "",
             "Cần đụng gấp thì nhắn thẳng phiên đang giữ, đừng sửa song song.", ""]
    noi_dung = "\n".join(dong)

    n = 0
    for c in cay:
        try:
            with open(os.path.join(c, TEN_FILE_CANH_BAO), "w", encoding="utf-8") as f:
                f.write(noi_dung)
            n += 1
        except Exception:
            pass
    return n, len(cay), False


def ver_host(site, theme):
    try:
        req = urllib.request.Request(site.rstrip("/") + "/", headers=UA)
        with urllib.request.urlopen(req, timeout=25) as r:
            html = r.read().decode("utf-8", "replace")
    except Exception:
        return None
    m = re.search(r"themes/" + re.escape(theme) + r"/[^\"']*\?ver=([0-9][0-9.]*)", html)
    return m.group(1) if m else None


def tang(v):
    p = v.split(".")
    p[-1] = str(int(p[-1]) + 1)
    return ".".join(p)


def main():
    ap = argparse.ArgumentParser(description="Sổ chiếm chỗ liên worktree")
    ap.add_argument("--repo", required=True)
    ap.add_argument("--claim", action="store_true")
    ap.add_argument("--release", action="store_true")
    ap.add_argument("--log", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--next-version", action="store_true")
    ap.add_argument("--branch")
    ap.add_argument("--files", nargs="*", default=[])
    ap.add_argument("--note", default="")
    ap.add_argument("--version")
    ap.add_argument("--status", default="PACKAGE_READY")
    ap.add_argument("--site")
    ap.add_argument("--theme")
    a = ap.parse_args()

    repo = os.path.abspath(a.repo)
    p = duong_dan_so(repo)
    d = doc(p)
    luc = time.strftime("%d/%m/%Y %H:%M")

    if a.next_version:
        vh = ver_host(a.site, a.theme) if a.site and a.theme else None
        da_dung = {x.get("version") for x in d["nhat_ky"] if x.get("version")}
        goc = vh or (max(da_dung) if da_dung else "1.0.0")
        v = tang(goc)
        while v in da_dung:
            v = tang(v)
        print(f"HOST đang chạy : {vh or 'không đọc được'}")
        print(f"Sổ đã ghi      : {len(da_dung)} version — {', '.join(sorted(da_dung)) or 'chưa có'}")
        print(f"SỐ NÊN DÙNG    : {v}")
        print("\nGhi vào sổ ngay khi dựng gói, đừng đợi lên host:")
        print(f"  python wp_lock.py --repo \"{a.repo}\" --log --branch <nhánh> "
              f"--version {v} --status PACKAGE_READY")
        return 0

    if a.list:
        print(f"SỔ CHUNG  {p}\n")
        if not d["chiem_cho"]:
            print("  không nhánh nào đang giữ chỗ")
        for c in d["chiem_cho"]:
            print(f"  `{c['nhanh']}` từ {c['luc']} — {c.get('ghi_chu', '')}")
            for f in c.get("files", []):
                print(f"      {f}")
        print(f"\nNHẬT KÝ DEPLOY ({len(d['nhat_ky'])} đợt)")
        for x in d["nhat_ky"][-15:]:
            print(f"  {x.get('luc'):<17} {x.get('version', '?'):<9} "
                  f"{x.get('nhanh', '?'):<28} {x.get('trang_thai', '?')}")
        return 0

    if not a.branch:
        _, a.branch, _ = git(repo, "rev-parse", "--abbrev-ref", "HEAD")

    if a.claim:
        va = []
        for c in d["chiem_cho"]:
            if c["nhanh"] == a.branch:
                continue
            chung = set(c.get("files", [])) & set(a.files)
            if chung:
                va.append(f"{', '.join(sorted(chung))} ← `{c['nhanh']}`")
        if va:
            print("TU_CHOI_GIU_CHO  file đang có người giữ: " + " | ".join(va))
            print("Nhắn thẳng phiên đó, đừng sửa song song.")
            return 1
        d["chiem_cho"] = [c for c in d["chiem_cho"] if c["nhanh"] != a.branch]
        d["chiem_cho"].append({"nhanh": a.branch, "files": a.files,
                               "ghi_chu": a.note, "luc": luc})
        ghi(p, d)
        n, tong, _ = rai_canh_bao(repo, d)
        print(f"DA_GIU_CHO       `{a.branch}` giữ {len(a.files)} file")
        print(f"DA_RAI_CANH_BAO  {n}/{tong} cây có {TEN_FILE_CANH_BAO}")
        return 0

    if a.release:
        truoc = len(d["chiem_cho"])
        d["chiem_cho"] = [c for c in d["chiem_cho"] if c["nhanh"] != a.branch]
        ghi(p, d)
        n, tong, sach = rai_canh_bao(repo, d)
        print(f"DA_TRA_CHO       gỡ {truoc - len(d['chiem_cho'])} mục của `{a.branch}`")
        print(f"{'DA_XOA_CANH_BAO ' if sach else 'DA_CAP_NHAT_CB  '} {n}/{tong} cây")
        return 0

    if a.log:
        d["nhat_ky"].append({"luc": luc, "nhanh": a.branch, "version": a.version,
                             "files": a.files, "trang_thai": a.status})
        ghi(p, d)
        print(f"DA_GHI_NHAT_KY   {a.version} · `{a.branch}` · {a.status}")
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
