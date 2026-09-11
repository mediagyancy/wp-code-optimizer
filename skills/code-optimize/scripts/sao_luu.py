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
đoạn văn thành ba lệnh, và `tests/test_sao_luu.py` bắt nó chạy thật trước khi ai được tin.

Ba lệnh
-------
    sao_luu.py luu      --nguon <cây>  --ra <thư-mục-backup>
    sao_luu.py kiem     --tu <backup>  --so-voi <cây>        [--bo-cr]
    sao_luu.py phuc_hoi --tu <backup>  --den <cây-đích>      [--ghi]

`luu`      chép toàn cây + ghi `manifest.json`: SHA-256 từng file, số file, tổng byte.
`kiem`     so một cây đang sống với manifest — báo file THÊM / THIẾU / KHÁC. Đây là
           phép phát hiện drift, và cũng là phép hiệu chuẩn cho `phuc_hoi`.
`phuc_hoi` dựng lại cây đích CHỈ từ thư mục backup, rồi tự `kiem` lại cây vừa dựng.
           Mặc định là thử (`--thu`); muốn ghi thật phải bật `--ghi`. Từ chối ghi vào
           cây đích không rỗng nếu không có `--de-len`.

Hai điều phải biết trước khi tin
--------------------------------
1. **Nguồn backup phải là bản lấy từ HOST, không phải từ git.** File này sao chép một
   cây trên đĩa; nó không biết cây đó từ đâu tới. Đã có hai ca chứng minh git THIẾU
   trên đúng loại codebase này: 20 file đang chạy thật chưa từng vào git (một file CSS
   chênh 1.119 dòng), và 9 file nguồn plugin bị `.gitignore` chặn — "không còn bản sao
   nào ngoài đĩa". Backup dựng từ git là backup thiếu, và thiếu thì chỉ lộ ra lúc cần
   phục hồi. Tải cây từ host qua FTP trước, rồi mới `luu`.

2. **So byte là so byte.** Phục hồi thì phải ra đúng từng byte, nên `phuc_hoi` so SHA-256
   nguyên văn. Cờ `--bo-cr` CHỈ dành cho `kiem` khi so local với bản tải từ host — CRLF
   và LF làm hai file giống nhau lệch đúng số dòng (`checkout.css` từng lệch đúng 1.049
   byte = 1.049 dòng). Không bao giờ dùng `--bo-cr` để làm một phép phục hồi "đạt".
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

PHIEN_BAN_MANIFEST = 1
TEN_MANIFEST = "manifest.json"
TEN_CAY = "cay"
BO_QUA_MAC_DINH = (".git",)


def sha256(p, bo_cr=False):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        d = f.read()
    if bo_cr:
        d = d.replace(b"\r", b"")
    h.update(d)
    return h.hexdigest()


def liet_ke(goc, bo_qua):
    """Mọi file dưới `goc`, đường dẫn tương đối dùng `/`, sort để manifest ổn định."""
    ra = []
    for dp, dn, fn in os.walk(goc):
        dn[:] = sorted(d for d in dn if d not in bo_qua)
        for f in sorted(fn):
            p = os.path.join(dp, f)
            ra.append(os.path.relpath(p, goc).replace(os.sep, "/"))
    return ra


def luu(nguon, ra, bo_qua):
    nguon = os.path.abspath(nguon)
    ra = os.path.abspath(ra)
    if not os.path.isdir(nguon):
        print("KHONG_KIEM_DUOC: khong thay cay nguon " + nguon)
        return 4
    if os.path.exists(ra) and os.listdir(ra):
        print("TU_CHOI: thu muc backup da co noi dung, khong ghi de len — " + ra)
        return 3

    cay = os.path.join(ra, TEN_CAY)
    os.makedirs(cay, exist_ok=True)
    tep = liet_ke(nguon, bo_qua)
    if not tep:
        print("KHONG_KIEM_DUOC: cay nguon rong — khong co gi de sao luu")
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
        print("HONG: ban chep khac ban goc o " + str(len(lech)) + " file — backup KHONG dung duoc")
        for r in lech[:8]:
            print("   " + r)
        return 5

    manifest = {
        "phien_ban": PHIEN_BAN_MANIFEST,
        "thoi_diem": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "nguon": nguon.replace("\\", "/"),
        "bo_qua": list(bo_qua),
        "so_file": len(tep),
        "tong_byte": tong,
        "file": bang,
    }
    tmp = os.path.join(ra, TEN_MANIFEST + ".tmp")
    with io.open(tmp, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    os.replace(tmp, os.path.join(ra, TEN_MANIFEST))
    print(f"DA_LUU  {len(tep)} file · {tong:,} byte · {ra}")
    return 0


def doc_manifest(tu):
    p = os.path.join(os.path.abspath(tu), TEN_MANIFEST)
    if not os.path.isfile(p):
        return None, "KHONG_KIEM_DUOC: khong thay " + p
    with io.open(p, encoding="utf-8") as f:
        m = json.load(f)
    if m.get("phien_ban") != PHIEN_BAN_MANIFEST or not m.get("file"):
        return None, "KHONG_KIEM_DUOC: manifest sai phien ban hoac rong"
    return m, None


def so(m, cay, bo_qua, bo_cr=False, cay_backup=None):
    """So một cây với manifest. Trả dict {them, thieu, khac}.

    `cay_backup` chỉ cần khi `bo_cr`: manifest lưu hash NGUYÊN VĂN, nên muốn so sau khi
    bỏ `\\r` thì phải hash lại bản trong backup theo cùng cách — không thì đang so hai
    phép đo khác nhau và kết quả vô nghĩa.
    """
    co = set(liet_ke(cay, bo_qua)) if os.path.isdir(cay) else set()
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
    return {"them": them, "thieu": thieu, "khac": khac}


def in_so(kq, gioi_han=10):
    for ten, nhan in (("thieu", "THIEU"), ("khac", "KHAC "), ("them", "THEM ")):
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
    kq = so(m, os.path.abspath(so_voi), tuple(m.get("bo_qua", BO_QUA_MAC_DINH)), bo_cr,
            cay_backup=os.path.join(os.path.abspath(tu), TEN_CAY))
    tong = sum(len(v) for v in kq.values())
    print(f"KIEM  {so_voi}  so voi backup {m['so_file']} file"
          + ("  (da bo \\r truoc khi so)" if bo_cr else ""))
    if tong == 0:
        print("  KHOP  0 file lech")
        return 0
    in_so(kq)
    print(f"  -> {tong} file lech")
    return 1


def phuc_hoi(tu, den, ghi, de_len):
    m, loi = doc_manifest(tu)
    if loi:
        print(loi)
        return 4
    tu = os.path.abspath(tu)
    den = os.path.abspath(den)
    cay = os.path.join(tu, TEN_CAY)

    # Chốt 1: backup phải TỰ NHẤT QUÁN trước khi dùng nó để phục hồi bất cứ gì.
    # Một backup hỏng mà đem phục hồi thì hỏng lan sang cây đích, và lúc đó không còn
    # bản nào tốt.
    kq_tu = so(m, cay, tuple(m.get("bo_qua", BO_QUA_MAC_DINH)))
    if any(kq_tu.values()):
        print("HONG: backup KHONG tu nhat quan voi manifest cua chinh no — khong phuc hoi")
        in_so(kq_tu)
        return 5

    if os.path.isdir(den) and os.listdir(den) and not de_len:
        print("TU_CHOI: cay dich khong rong — them --de-len neu chac chan muon ghi de")
        return 3

    if not ghi:
        print(f"THU  se phuc hoi {m['so_file']} file · {m['tong_byte']:,} byte -> {den}")
        print("     (chua ghi gi; them --ghi de phuc hoi that)")
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
    kq = so(m, den, tuple(m.get("bo_qua", BO_QUA_MAC_DINH)))
    tong = sum(len(v) for v in kq.values())
    print(f"PHUC_HOI  {m['so_file']} file -> {den}")
    if tong == 0:
        print("  KHOP  0 file lech — phuc hoi DA XAC MINH")
        return 0
    print("  HONG  cay phuc hoi KHONG khop manifest")
    in_so(kq)
    return 5


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="lenh", required=True)

    a = sub.add_parser("luu")
    a.add_argument("--nguon", required=True)
    a.add_argument("--ra", required=True)
    a.add_argument("--bo-qua", default=",".join(BO_QUA_MAC_DINH),
                   help="thu muc bo qua, ngan bang dau phay (mac dinh: .git)")

    b = sub.add_parser("kiem")
    b.add_argument("--tu", required=True)
    b.add_argument("--so-voi", required=True)
    b.add_argument("--bo-cr", action="store_true",
                   help="bo \\r truoc khi so — CHI khi so local voi ban tai tu host")

    c = sub.add_parser("phuc_hoi")
    c.add_argument("--tu", required=True)
    c.add_argument("--den", required=True)
    c.add_argument("--ghi", action="store_true", help="phuc hoi that (mac dinh chi thu)")
    c.add_argument("--de-len", action="store_true", help="cho phep ghi de cay dich khong rong")

    x = ap.parse_args()
    if x.lenh == "luu":
        bo_qua = tuple(t.strip() for t in x.bo_qua.split(",") if t.strip())
        return luu(x.nguon, x.ra, bo_qua)
    if x.lenh == "kiem":
        return kiem(x.tu, x.so_voi, x.bo_cr)
    return phuc_hoi(x.tu, x.den, x.ghi, x.de_len)


if __name__ == "__main__":
    sys.exit(main())
