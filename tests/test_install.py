#!/usr/bin/env python3
"""Kiểm `install.py` — repo → `~/.claude/skills` một chiều, có đường lùi bằng cách không đụng file lạ.

Chạy trong một thư mục đích tạm, không đụng `~/.claude` thật. Hai chiều:
  · cài mới → mọi file có mặt, dấu VERSION được ghi, chạy lại là 0 khác biệt (tất định);
  · sửa một file local → lần cài sau ghi đè đúng file đó, KHÔNG đụng file lạ (cấu hình site)
    và GỠ script mang tên cũ đã đổi;
  · chế độ thử không ghi gì; VERSION trong repo khớp `version:` của mọi SKILL.md.

    python tests/test_install.py
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GOC = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(GOC)
INSTALL = os.path.join(REPO, "install.py")
dat, hong = [], []


def kiem(ten, ok, chi_tiet=""):
    (dat if ok else hong).append((ten, chi_tiet))
    print(f"  {'đạt ' if ok else 'HỎNG'}  {ten}" + (f"\n          {chi_tiet}" if not ok else ""))


def chay(*args):
    r = subprocess.run([sys.executable, INSTALL] + list(args), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main():
    tmp = tempfile.mkdtemp(prefix="install-")
    try:
        return run(os.path.join(tmp, "skills"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run(dest):
    print("=" * 70)
    print("INSTALL — repo → local một chiều")
    print("=" * 70)
    ver = io.open(os.path.join(REPO, "VERSION"), encoding="utf-8").read().strip()
    kiem("VERSION là semver", re.fullmatch(r"\d+\.\d+\.\d+", ver) is not None, ver)
    mismatched = []
    for skill in sorted(os.listdir(os.path.join(REPO, "skills"))):
        s = io.open(os.path.join(REPO, "skills", skill, "SKILL.md"), encoding="utf-8").read()
        m = re.search(r"(?m)^version:\s*(\S+)", s)
        if not m:
            mismatched.append(f"{skill}: thiếu version:")
        elif m.group(1) != ver and skill != "wp-corewebvital":   # wp-corewebvital có version riêng 2.x từ trước
            mismatched.append(f"{skill}: {m.group(1)}")
    kiem("mọi SKILL.md mang version: khớp VERSION (trừ wp-corewebvital 2.x có sẵn)", not mismatched, mismatched)

    print("\n[1] Chế độ thử không ghi")
    ma, ra = chay("--dest", dest)
    kiem("dry run: exit 1 (có việc phải làm), DRY_RUN, không tạo thư mục",
         ma == 1 and "DRY_RUN" in ra and not os.path.exists(dest), ra[-300:])

    print("\n[2] Cài mới")
    ma, ra = chay("--dest", dest, "--write")
    kiem("exit 0, INSTALLED", ma == 0 and "INSTALLED" in ra, ra[-300:])
    kiem("dấu version ghi đúng", io.open(os.path.join(dest, ".wp-code-optimizer.version"), encoding="utf-8").read().strip() == ver)
    kiem("có skills/wp-code-cheatsheet/scripts/cheatsheet.py", os.path.exists(os.path.join(dest, "wp-code-cheatsheet", "scripts", "cheatsheet.py")))
    ma, ra = chay("--dest", dest)
    kiem("chạy lại ở chế độ thử: exit 0, copy 0 · remove 0", ma == 0 and "copy 0 · remove 0" in ra, ra[-300:])

    print("\n[3] Local trôi: sửa một file, thêm file lạ, thêm script tên cũ")
    target = os.path.join(dest, "code-optimize", "scripts", "backup.py")
    with io.open(target, "a", encoding="utf-8") as f:
        f.write("\n# sua tay o local\n")
    site = os.path.join(dest, "wp-delivery", "scripts", "sites", "khach.json")
    os.makedirs(os.path.dirname(site), exist_ok=True)
    io.open(site, "w", encoding="utf-8").write("{}")
    old = os.path.join(dest, "code-optimize", "scripts", "sao_luu.py")
    io.open(old, "w", encoding="utf-8").write("# ban cu\n")
    ma, ra = chay("--dest", dest)
    kiem("thử: liệt kê đúng 1 copy, 1 remove, 1 keep",
         "copy 1 · remove 1 · keep 1" in ra and "keep    wp-delivery/scripts/sites/khach.json" in ra, ra[-500:])
    ma, ra = chay("--dest", dest, "--write")
    kiem("ghi: exit 0", ma == 0, ra[-300:])
    kiem("file sửa tay bị ghi đè về bản repo", "sua tay o local" not in io.open(target, encoding="utf-8").read())
    kiem("file lạ (sites/khach.json) còn nguyên", os.path.exists(site))
    kiem("script tên cũ sao_luu.py đã gỡ", not os.path.exists(old))
    ma, ra = chay("--dest", dest)
    kiem("sau ghi: 0 khác biệt, chỉ còn keep 1", ma == 0 and "copy 0 · remove 0 · keep 1" in ra, ra[-300:])

    print("\n[4] Đối chứng ngược: repo thiếu skills → NOT_CHECKABLE")
    fake = tempfile.mkdtemp(prefix="install-fake-")
    shutil.copy(INSTALL, os.path.join(fake, "install.py"))
    r = subprocess.run([sys.executable, os.path.join(fake, "install.py"), "--dest", dest], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    kiem("exit 4", r.returncode == 4 and "NOT_CHECKABLE" in (r.stdout or ""), (r.stdout or "")[-200:])
    shutil.rmtree(fake, ignore_errors=True)

    print("\n" + "=" * 70)
    print(f"đạt {len(dat)} · hỏng {len(hong)}")
    print("=" * 70)
    return 1 if hong else 0


if __name__ == "__main__":
    sys.exit(main())
