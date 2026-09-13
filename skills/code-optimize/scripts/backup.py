#!/usr/bin/env python3
"""Sao lưu TOÀN CÂY và phục hồi — có diễn tập, có so byte, không có đoạn văn.

Vì sao file này tồn tại
-----------------------
Trước nó, repo này có **0 dòng code phục hồi** và **0 khẳng định test** nào nhắc tới
backup hay restore — trong khi bộ test đã có 38 khẳng định. `wp_safe_write.py` ghi `.bak`
cạnh TỪNG file, tức không có mốc thời điểm nhất quán của cả cây: phục hồi một phép viết
lại trải trên nhiều file bằng các `.bak` rời là lắp lại một cái cây từ những mảnh chụp
ở những thời điểm khác nhau. Và `wp-delivery/SKILL.md` có `rollback_plan: []` — một danh
sách rỗng trong template.

Một đường lùi chưa từng chạy là một đoạn văn, không phải một đường lùi. File này biến
đoạn văn thành ba lệnh, và `tests/test_backup.py` bắt nó chạy thật trước khi ai được tin.

Ba lệnh
-------
    backup.py save      --source <cây>  --out <thư-mục-backup>
    backup.py check     --from <backup>  --against <cây>        [--ignore-cr]
    backup.py restore --from <backup>  --to <cây-đích>      [--write]

`luu`      chép toàn cây + ghi `manifest.json`: SHA-256 từng file, số file, tổng byte.
`kiem`     so một cây đang sống với manifest — báo file THÊM / THIẾU / KHÁC. Đây là
           phép phát hiện drift, và cũng là phép hiệu chuẩn cho `restore`.
`restore` dựng lại cây đích CHỈ từ thư mục backup, rồi tự `kiem` lại cây vừa dựng.
           Mặc định là thử (`--thu`); muốn ghi thật phải bật `--write`. Từ chối ghi vào
           cây đích không rỗng nếu không có `--overwrite`.

Hai điều phải biết trước khi tin
--------------------------------
1. **Nguồn backup phải là bản lấy từ HOST, không phải từ git.** File này sao chép một
   cây trên đĩa; nó không biết cây đó từ đâu tới. Đã có hai ca chứng minh git THIẾU
   trên đúng loại codebase này: 20 file đang chạy thật chưa từng vào git (một file CSS
   chênh 1.119 dòng), và 9 file nguồn plugin bị `.gitignore` chặn — "không còn bản sao
   nào ngoài đĩa". Backup dựng từ git là backup thiếu, và thiếu thì chỉ lộ ra lúc cần
   phục hồi. Tải cây từ host qua FTP trước, rồi mới `luu`.

2. **So byte là so byte.** Phục hồi thì phải ra đúng từng byte, nên `restore` so SHA-256
   nguyên văn. Cờ `--ignore-cr` CHỈ dành cho `kiem` khi so local với bản tải từ host — CRLF
   và LF làm hai file giống nhau lệch đúng số dòng (`checkout.css` từng lệch đúng 1.049
   byte = 1.049 dòng). Không bao giờ dùng `--ignore-cr` để làm một phép phục hồi "đạt".
"""
import argparse
import hashlib
import io
import json
import os
import shutil
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

MANIFEST_VERSION = 1
MANIFEST_NAME = "manifest.json"
TREE_DIR = "cay"
DEFAULT_EXCLUDES = (".git",)


def sha256(p, bo_cr=False):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        d = f.read()
    if bo_cr:
        d = d.replace(b"\r", b"")
    h.update(d)
    return h.hexdigest()


def liet_ke(goc, excluded):
    """Mọi file dưới `goc`, đường dẫn tương đối dùng `/`, sort để manifest ổn định."""
    ra = []
    for dp, dn, fn in os.walk(goc):
        dn[:] = sorted(d for d in dn if d not in excluded)
        for f in sorted(fn):
            p = os.path.join(dp, f)
            ra.append(os.path.relpath(p, goc).replace(os.sep, "/"))
    return ra


def luu(nguon, ra, excluded):
    nguon = os.path.abspath(nguon)
    ra = os.path.abspath(ra)
    if not os.path.isdir(nguon):
        print("NOT_CHECKABLE: khong thay cay nguon " + nguon)
        return 4
    if os.path.exists(ra) and os.listdir(ra):
        print("REFUSED: thu muc backup da co noi dung, khong ghi de len — " + ra)
        return 3

    cay = os.path.join(ra, TREE_DIR)
    os.makedirs(cay, exist_ok=True)
    tep = liet_ke(nguon, excluded)
    if not tep:
        print("NOT_CHECKABLE: cay nguon rong — khong co gi de sao luu")
        return 4

    bang = {}
    tong = 0
    for r in tep:
        src = os.path.join(nguon, r)
        dst = os.path.join(cay, r)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        bang[r] = {"sha256": sha256(src), "byte": os.path.getsize(src)}
        tong += bang[r]["byte"]

    # Chốt: hash của bản CHÉP phải bằng hash của bản gốc. Không thì chính phép chép đã
    # hỏng và manifest đang mô tả một cái cây không tồn tại trong backup.
    lech = [r for r in tep if sha256(os.path.join(cay, r)) != bang[r]["sha256"]]
    if lech:
        print("BROKEN: ban chep khac ban goc o " + str(len(lech)) + " file — backup KHONG dung duoc")
        for r in lech[:8]:
            print("   " + r)
        return 5

    manifest = {
        "version": MANIFEST_VERSION,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source": nguon.replace("\\", "/"),
        "excluded": list(excluded),
        "file_count": len(tep),
        "total_bytes": tong,
        "file": bang,
    }
    tmp = os.path.join(ra, MANIFEST_NAME + ".tmp")
    with io.open(tmp, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    os.replace(tmp, os.path.join(ra, MANIFEST_NAME))
    print(f"SAVED  {len(tep)} file · {tong:,} byte · {ra}")
    return 0


def doc_manifest(tu):
    p = os.path.join(os.path.abspath(tu), MANIFEST_NAME)
    if not os.path.isfile(p):
        return None, "NOT_CHECKABLE: khong thay " + p
    with io.open(p, encoding="utf-8") as f:
        m = json.load(f)
    if m.get("version") != MANIFEST_VERSION or not m.get("file"):
        return None, "NOT_CHECKABLE: manifest sai phien ban hoac rong"
    return m, None


def so(m, cay, excluded, bo_cr=False, cay_backup=None):
    """So một cây với manifest. Trả dict {them, thieu, khac}.

    `cay_backup` chỉ cần khi `bo_cr`: manifest lưu hash NGUYÊN VĂN, nên muốn so sau khi
    bỏ `\\r` thì phải hash lại bản trong backup theo cùng cách — không thì đang so hai
    phép đo khác nhau và kết quả vô nghĩa.
    """
    co = set(liet_ke(cay, excluded)) if os.path.isdir(cay) else set()
    mong = set(m["file"])
    them = sorted(co - mong)
    thieu = sorted(mong - co)
    khac = []
    for r in sorted(mong & co):
        h_mong = m["file"][r]["sha256"]
        if bo_cr and cay_backup:
            goc = os.path.join(cay_backup, r)
            if os.path.isfile(goc):
                h_mong = sha256(goc, bo_cr=True)
        if sha256(os.path.join(cay, r), bo_cr=bo_cr) != h_mong:
            khac.append(r)
    return {"added": them, "missing": thieu, "changed": khac}


def in_so(kq, gioi_han=10):
    for ten, nhan in (("missing", "THIEU"), ("changed", "KHAC "), ("added", "THEM ")):
        bo = kq[ten]
        if not bo:
            continue
        print(f"  {nhan}  {len(bo)}")
        for r in bo[:gioi_han]:
            print("         " + r)
        if len(bo) > gioi_han:
            print(f"         … và {len(bo) - gioi_han} file nữa")


def kiem(tu, so_voi, bo_cr):
    m, loi = doc_manifest(tu)
    if loi:
        print(loi)
        return 4
    kq = so(m, os.path.abspath(so_voi), tuple(m.get("excluded", DEFAULT_EXCLUDES)), bo_cr,
            cay_backup=os.path.join(os.path.abspath(tu), TREE_DIR))
    tong = sum(len(v) for v in kq.values())
    print(f"KIEM  {so_voi}  so voi backup {m['file_count']} file"
          + ("  (da bo \\r truoc khi so)" if bo_cr else ""))
    if tong == 0:
        print("  MATCH  0 file lech")
        return 0
    in_so(kq)
    print(f"  -> {tong} file lech")
    return 1


def restore(tu, den, ghi, de_len):
    m, loi = doc_manifest(tu)
    if loi:
        print(loi)
        return 4
    tu = os.path.abspath(tu)
    den = os.path.abspath(den)
    cay = os.path.join(tu, TREE_DIR)

    # Chốt 1: backup phải TỰ NHẤT QUÁN trước khi dùng nó để phục hồi bất cứ gì.
    # Một backup hỏng mà đem phục hồi thì hỏng lan sang cây đích, và lúc đó không còn
    # bản nào tốt.
    kq_tu = so(m, cay, tuple(m.get("excluded", DEFAULT_EXCLUDES)))
    if any(kq_tu.values()):
        print("BROKEN: backup KHONG tu nhat quan voi manifest cua chinh no — khong phuc hoi")
        in_so(kq_tu)
        return 5

    if os.path.isdir(den) and os.listdir(den) and not de_len:
        print("REFUSED: cay dich khong rong — them --overwrite neu chac chan muon ghi de")
        return 3

    if not ghi:
        print(f"THU  se phuc hoi {m['file_count']} file · {m['total_bytes']:,} byte -> {den}")
        print("     (chua ghi gi; them --write de phuc hoi that)")
        return 0

    if os.path.isdir(den) and de_len:
        shutil.rmtree(den)
    os.makedirs(den, exist_ok=True)
    for r in sorted(m["file"]):
        src = os.path.join(cay, r)
        dst = os.path.join(den, r)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)

    # Chốt 2: cây vừa dựng phải khớp manifest TỚI TỪNG BYTE. "Đã copy xong" không phải
    # "đã phục hồi xong" — phục hồi xong là khi phép so nói 0 lệch.
    kq = so(m, den, tuple(m.get("excluded", DEFAULT_EXCLUDES)))
    tong = sum(len(v) for v in kq.values())
    print(f"RESTORED  {m['file_count']} file -> {den}")
    if tong == 0:
        print("  MATCH  0 file lech — phuc hoi DA XAC MINH")
        return 0
    print("  BROKEN  cay phuc hoi KHONG khop manifest")
    in_so(kq)
    return 5


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="lenh", required=True)

    a = sub.add_parser("save")
    a.add_argument("--source", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--exclude", default=",".join(DEFAULT_EXCLUDES),
                   help="thu muc bo qua, ngan bang dau phay (mac dinh: .git)")

    b = sub.add_parser("check")
    b.add_argument("--from", dest="from_dir", required=True)
    b.add_argument("--against", required=True)
    b.add_argument("--ignore-cr", action="store_true",
                   help="bo \\r truoc khi so — CHI khi so local voi ban tai tu host")

    c = sub.add_parser("restore")
    c.add_argument("--from", dest="from_dir", required=True)
    c.add_argument("--to", dest="to_dir", required=True)
    c.add_argument("--write", action="store_true", help="phuc hoi that (mac dinh chi thu)")
    c.add_argument("--overwrite", action="store_true", help="cho phep ghi de cay dich khong rong")

    x = ap.parse_args()
    if x.lenh == "save":
        excluded = tuple(t.strip() for t in x.exclude.split(",") if t.strip())
        return luu(x.source, x.out, excluded)
    if x.lenh == "check":
        return kiem(x.from_dir, x.against, x.ignore_cr)
    return restore(x.from_dir, x.to_dir, x.write, x.overwrite)


if __name__ == "__main__":
    sys.exit(main())
