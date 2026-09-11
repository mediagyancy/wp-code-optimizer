#!/usr/bin/env python3
"""DIỄN TẬP phục hồi — không phải mô tả phục hồi.

Đây là FT-B trong kế hoạch: trước file này, repo có 0 dòng code phục hồi và 0 khẳng
định về backup. Lane biến đổi bị khoá vì thế, và nó chỉ được mở khi bài diễn tập này
chạy thật với kết quả 0 byte lệch.

Bài diễn tập có ba phần, và phần thứ ba là phần duy nhất đáng tin:

  1. HIỆU CHUẨN phép so: làm hỏng một bản sao đúng ba kiểu (sửa · xoá · thêm) rồi đòi
     `kiem` gọi đúng tên ba file đó. Phép so chưa bắt được ca hỏng thì mọi "0 lệch" nó
     báo sau đó đều vô nghĩa.
  2. Backup phải TỰ NHẤT QUÁN: làm hỏng một file BÊN TRONG backup, `phuc_hoi` phải từ
     chối — backup hỏng mà đem phục hồi thì hỏng lan sang cây đích và không còn bản nào
     tốt.
  3. PHỤC HỒI KHI NGUỒN ĐÃ MẤT: xoá hẳn cây nguồn, phục hồi chỉ từ thư mục backup, so
     byte với một bản gốc giữ ở nơi khác. Đây là tình huống thật của một đường lùi —
     lúc cần nó thì cây gốc đã không còn.

    python tests/test_sao_luu.py
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GOC = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(GOC)
SCRIPT = os.path.join(REPO, "skills", "code-optimize", "scripts", "sao_luu.py")
NGUON_FIXTURE = os.path.join(GOC, "integration", "fixture-bien-doi")

dat, hong = [], []


def kiem(ten, ok, chi_tiet=""):
    (dat if ok else hong).append((ten, chi_tiet))
    print(f"  {'đạt ' if ok else 'HỎNG'}  {ten}" + (f"\n          {chi_tiet}" if not ok else ""))


def chay(*args):
    r = subprocess.run([sys.executable, SCRIPT] + list(args), capture_output=True,
                       text=True, encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def so_byte(a, b):
    """So hai cây tới từng byte. Trả danh sách đường dẫn lệch."""
    def ds(g):
        ra = {}
        for dp, _dn, fn in os.walk(g):
            for f in fn:
                p = os.path.join(dp, f)
                ra[os.path.relpath(p, g).replace(os.sep, "/")] = open(p, "rb").read()
        return ra
    x, y = ds(a), ds(b)
    return sorted(set(x) ^ set(y)) + sorted(k for k in set(x) & set(y) if x[k] != y[k])


def main():
    tmp = tempfile.mkdtemp(prefix="sao-luu-")
    try:
        return chay_trong(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def chay_trong(tmp):
    goc = os.path.join(tmp, "goc")             # cây nguồn, sẽ bị xoá ở phần 3
    chuan = os.path.join(tmp, "chuan")         # bản gốc giữ riêng để so byte cuối cùng
    bk = os.path.join(tmp, "backup")
    shutil.copytree(NGUON_FIXTURE, goc)
    shutil.copytree(NGUON_FIXTURE, chuan)
    so_file_goc = sum(len(f) for _, _, f in os.walk(goc))

    print("=" * 70)
    print("SAO LƯU + PHỤC HỒI — diễn tập")
    print("=" * 70)

    print("\n[1] luu")
    ma, ra = chay("luu", "--nguon", goc, "--ra", bk)
    kiem("luu xong, exit 0", ma == 0, ra[-400:])
    mp = os.path.join(bk, "manifest.json")
    kiem("có manifest.json", os.path.isfile(mp))
    m = json.load(io.open(mp, encoding="utf-8")) if os.path.isfile(mp) else {}
    kiem(f"manifest đếm đúng {so_file_goc} file", m.get("so_file") == so_file_goc,
         f"manifest {m.get('so_file')}")
    kiem("mỗi file có sha256 64 ký tự",
         all(len(v["sha256"]) == 64 for v in m.get("file", {}).values()))
    ma, _ = chay("luu", "--nguon", goc, "--ra", bk)
    kiem("luu lần hai vào cùng chỗ bị TỪ CHỐI (không ghi đè backup)", ma == 3, f"exit={ma}")

    print("\n[2] kiem — hiệu chuẩn trên ba kiểu hỏng")
    ma, ra = chay("kiem", "--tu", bk, "--so-voi", goc)
    kiem("cây chưa đổi → 0 lệch, exit 0", ma == 0 and "0 file lech" in ra, ra[-300:])

    hong_copy = os.path.join(tmp, "hong")
    shutil.copytree(goc, hong_copy)
    io.open(os.path.join(hong_copy, "inc", "tham-so.php"), "a", encoding="utf-8").write("\n// sua\n")
    os.remove(os.path.join(hong_copy, "inc", "hook-b.php"))
    io.open(os.path.join(hong_copy, "inc", "moi.php"), "w", encoding="utf-8").write("<?php\n")
    ma, ra = chay("kiem", "--tu", bk, "--so-voi", hong_copy)
    kiem("cây hỏng → exit 1", ma == 1, f"exit={ma}")
    kiem("gọi đúng file SỬA", "KHAC" in ra and "inc/tham-so.php" in ra, ra[-500:])
    kiem("gọi đúng file XOÁ", "THIEU" in ra and "inc/hook-b.php" in ra, ra[-500:])
    kiem("gọi đúng file THÊM", "THEM" in ra and "inc/moi.php" in ra, ra[-500:])
    kiem("đếm đúng 3 lệch, không hơn", "3 file lech" in ra, ra[-300:])

    print("\n[3] --bo-cr — chỉ bỏ qua CRLF, không bỏ qua thay đổi thật")
    crlf = os.path.join(tmp, "crlf")
    shutil.copytree(goc, crlf)
    p = os.path.join(crlf, "index.php")
    d = open(p, "rb").read().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    open(p, "wb").write(d)
    ma1, _ = chay("kiem", "--tu", bk, "--so-voi", crlf)
    ma2, _ = chay("kiem", "--tu", bk, "--so-voi", crlf, "--bo-cr")
    kiem("đổi LF→CRLF: không cờ thì LỆCH, có --bo-cr thì KHỚP", ma1 == 1 and ma2 == 0,
         f"khong co={ma1} co_cr={ma2}")
    io.open(os.path.join(crlf, "footer.php"), "a", encoding="utf-8").write("x")
    ma3, ra = chay("kiem", "--tu", bk, "--so-voi", crlf, "--bo-cr")
    kiem("--bo-cr KHÔNG che được thay đổi nội dung thật", ma3 == 1 and "footer.php" in ra,
         f"exit={ma3}")

    print("\n[4] phuc_hoi — thử trước, ghi sau")
    dich = os.path.join(tmp, "dich")
    ma, ra = chay("phuc_hoi", "--tu", bk, "--den", dich)
    kiem("mặc định là THỬ, không ghi gì", ma == 0 and not os.path.exists(dich), ra[-300:])
    os.makedirs(dich)
    io.open(os.path.join(dich, "co-san.txt"), "w").write("x")
    ma, _ = chay("phuc_hoi", "--tu", bk, "--den", dich, "--ghi")
    kiem("cây đích không rỗng → TỪ CHỐI nếu không có --de-len", ma == 3, f"exit={ma}")

    print("\n[5] backup phải TỰ NHẤT QUÁN trước khi được dùng")
    bk_hong = os.path.join(tmp, "backup-hong")
    shutil.copytree(bk, bk_hong)
    io.open(os.path.join(bk_hong, "cay", "header.php"), "a", encoding="utf-8").write("!")
    ma, ra = chay("phuc_hoi", "--tu", bk_hong, "--den", os.path.join(tmp, "dich2"), "--ghi")
    kiem("backup bị sửa bên trong → phuc_hoi TỪ CHỐI, exit 5", ma == 5, f"exit={ma}")
    kiem("nói rõ là backup không tự nhất quán", "KHONG tu nhat quan" in ra, ra[-300:])
    kiem("và KHÔNG tạo ra cây đích", not os.path.exists(os.path.join(tmp, "dich2")))

    print("\n[6] PHỤC HỒI KHI NGUỒN ĐÃ MẤT — tình huống thật của một đường lùi")
    shutil.rmtree(goc)
    kiem("cây nguồn đã bị xoá hẳn", not os.path.exists(goc))
    dich3 = os.path.join(tmp, "dich3")
    ma, ra = chay("phuc_hoi", "--tu", bk, "--den", dich3, "--ghi")
    kiem("phuc_hoi --ghi chạy xong, exit 0", ma == 0, ra[-400:])
    kiem("tự kiem lại và báo 0 lệch so với manifest", "0 file lech" in ra, ra[-300:])
    lech = so_byte(chuan, dich3)
    kiem("SO BYTE với bản gốc giữ riêng: 0 file lệch", not lech, str(lech[:5]))
    kiem(f"đủ {so_file_goc} file", sum(len(f) for _, _, f in os.walk(dich3)) == so_file_goc)

    print("\n" + "=" * 70)
    print(f"đạt {len(dat)} · hỏng {len(hong)}")
    if hong:
        print("\nHỎNG:")
        for t, c in hong:
            print(f"  · {t}\n    {c}")
    print("=" * 70)
    return 1 if hong else 0


if __name__ == "__main__":
    sys.exit(main())
