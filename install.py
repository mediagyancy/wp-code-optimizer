#!/usr/bin/env python3
"""INSTALL — đưa skill từ repo này vào `~/.claude/skills`, và cập nhật khi repo đổi.

Vì sao có file này
------------------
Cách cài cũ là `cp -r skills/* ~/.claude/skills/`: chép một lần rồi đứt liên hệ với repo.
Bản cài không biết mình là bản nào, không ai báo khi repo có breaking change, và script đã
đổi tên (`sao_luu.py` → `backup.py`) thì bản cũ vẫn nằm đó chạy với cờ cũ. Repo đã trả giá:
ba bản chép của cùng tài liệu lệch nhau tới mức repo public dạy công thức sai (CLAUDE.md §7.5).

Script này là NGUỒN MỘT CHIỀU: repo → local. Không bao giờ chép ngược. Nó:

  · chép mọi file dưới `skills/<skill>/` sang `~/.claude/skills/<skill>/`, so sha256, chỉ ghi
    file khác;
  · gỡ file local mà repo KHÔNG còn — nhưng chỉ khi tên nằm trong danh sách đã đổi tên
    (`RENAMED`); file lạ (cấu hình site riêng, `_backup/`, `.bak`) thì GIỮ và liệt kê;
  · ghi `VERSION` của repo vào `~/.claude/skills/.wp-code-optimizer.version` và in
    "bản cũ → bản mới", kèm các dòng BREAKING của CHANGELOG giữa hai bản;
  · mặc định CHỈ THỬ; `--write` mới ghi. `--pull` chạy `git pull --ff-only` trước.

    python install.py                 # xem sẽ đổi gì
    python install.py --write         # cài / cập nhật
    python install.py --pull --write  # kéo repo mới nhất rồi cài

Exit: 0 xong · 1 có khác biệt (chế độ thử) · 3 REFUSED (git pull không fast-forward /
cây bẩn) · 4 NOT_CHECKABLE (không thấy thư mục skills).
"""
import argparse
import hashlib
import io
import os
import re
import shutil
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = os.path.dirname(os.path.abspath(__file__))
SKILLS_SRC = os.path.join(REPO, "skills")
VERSION_FILE = os.path.join(REPO, "VERSION")
STAMP_NAME = ".wp-code-optimizer.version"
# File local có tên cũ đã đổi trong repo — gỡ để không còn hai bản cùng một script.
RENAMED = {"sao_luu.py", "cong_clean.py", "cong_graph.py", "doi_ten.py", "quyet_dinh_tran.py"}
SKIP = ("__pycache__",)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def walk(root):
    out = {}
    for dp, dn, fn in os.walk(root):
        dn[:] = sorted(d for d in dn if d not in SKIP)
        for f in sorted(fn):
            p = os.path.join(dp, f)
            out[os.path.relpath(p, root).replace(os.sep, "/")] = p
    return out


def read_version(path):
    try:
        with io.open(path, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def breaking_lines(changelog, old, new):
    """Dòng chứa BREAKING/breaking trong các mục CHANGELOG từ sau `old` tới `new`."""
    if not os.path.exists(changelog):
        return []
    text = io.open(changelog, encoding="utf-8").read()
    parts = re.split(r"(?m)^## \[([^\]]+)\]", text)
    out = []
    for i in range(1, len(parts), 2):
        ver, body = parts[i], parts[i + 1]
        if ver == old:
            break
        for ln in body.splitlines():
            if "breaking" in ln.lower() and ln.strip().startswith(("#", "|", "-", "*", "`", "B", "b")):
                out.append(f"[{ver}] {ln.strip()[:110]}")
    return out


def plan(dst_root):
    """Trả (copy, remove, keep, same) — chỉ liệt kê, chưa ghi."""
    copy, remove, keep, same = [], [], [], 0
    for skill in sorted(os.listdir(SKILLS_SRC)):
        src_dir = os.path.join(SKILLS_SRC, skill)
        if not os.path.isdir(src_dir):
            continue
        dst_dir = os.path.join(dst_root, skill)
        src = walk(src_dir)
        dst = walk(dst_dir) if os.path.isdir(dst_dir) else {}
        for rel, sp in src.items():
            dp = os.path.join(dst_dir, rel)
            if rel in dst and sha(sp) == sha(dst[rel]):
                same += 1
            else:
                copy.append((f"{skill}/{rel}", sp, dp))
        for rel, dp in dst.items():
            if rel in src:
                continue
            (remove if os.path.basename(rel) in RENAMED else keep).append((f"{skill}/{rel}", dp))
    return copy, remove, keep, same


def main():
    ap = argparse.ArgumentParser(description="Cài / cập nhật skill từ repo vào ~/.claude/skills")
    ap.add_argument("--dest", default=os.path.join(os.path.expanduser("~"), ".claude", "skills"),
                    help="thư mục skill của Claude Code (mặc định ~/.claude/skills)")
    ap.add_argument("--pull", action="store_true", help="git pull --ff-only trước khi cài")
    ap.add_argument("--write", action="store_true", help="ghi thật; mặc định chỉ thử")
    a = ap.parse_args()

    if not os.path.isdir(SKILLS_SRC):
        print(f"NOT_CHECKABLE: không thấy {SKILLS_SRC}")
        return 4

    if a.pull:
        st = subprocess.run(["git", "-C", REPO, "status", "--porcelain"], capture_output=True, text=True)
        if st.stdout.strip():
            print("REFUSED: cây repo đang bẩn — commit hoặc bỏ thay đổi rồi mới --pull")
            return 3
        r = subprocess.run(["git", "-C", REPO, "pull", "--ff-only"], capture_output=True, text=True)
        print((r.stdout or "").strip() or (r.stderr or "").strip())
        if r.returncode != 0:
            print("REFUSED: git pull không fast-forward được")
            return 3

    new_ver = read_version(VERSION_FILE) or "?"
    stamp = os.path.join(a.dest, STAMP_NAME)
    old_ver = read_version(stamp) or "(chưa từng cài bằng install.py)"
    copy, remove, keep, same = plan(a.dest)

    print(f"INSTALL  {old_ver} -> {new_ver}   dest={a.dest}")
    for name, _, _ in copy:
        print(f"  copy    {name}")
    for name, _ in remove:
        print(f"  remove  {name}   (đã đổi tên trong repo)")
    for name, _ in keep:
        print(f"  keep    {name}   (chỉ có ở local — không đụng)")
    print(f"  = copy {len(copy)} · remove {len(remove)} · keep {len(keep)} · unchanged {same}")

    brk = breaking_lines(os.path.join(REPO, "CHANGELOG.md"), old_ver, new_ver) if old_ver != new_ver else []
    if brk:
        print("\nBREAKING kể từ bản đang cài — đọc trước khi chạy tool:")
        for ln in brk[:20]:
            print("  · " + ln)

    if not a.write:
        print("\nDRY_RUN — chưa ghi gì. Thấy đúng thì chạy lại kèm --write.")
        return 1 if (copy or remove) else 0

    for _, sp, dp in copy:
        os.makedirs(os.path.dirname(dp), exist_ok=True)
        shutil.copyfile(sp, dp)
    for _, dp in remove:
        os.remove(dp)
    os.makedirs(a.dest, exist_ok=True)
    with io.open(stamp, "w", encoding="utf-8", newline="\n") as f:
        f.write(new_ver + "\n")
    # Chốt sau: chạy lại kế hoạch, phải rỗng — "đã copy" chưa phải "đã cài".
    copy2, remove2, _, _ = plan(a.dest)
    if copy2 or remove2:
        print(f"BROKEN: sau khi ghi vẫn còn {len(copy2)} file khác, {len(remove2)} file thừa")
        return 5
    print(f"INSTALLED  {new_ver} — đã so lại từng file: 0 khác biệt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
