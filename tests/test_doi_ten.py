#!/usr/bin/env python3
"""Kiểm `doi_ten.py` — mỗi chốt phải bắt đúng ca hỏng nó sinh ra để bắt.

Ba cách replace thẳng hỏng im lặng — khớp chuỗi con, va chạm tên, bỏ sót — mỗi cách là
một ca ở đây, và ca nào cũng có chiều đối chứng: chốt phải ĐỎ ở ca hỏng, và phải IM ở ca
đúng. Thêm hai ca về đường lùi: test đỏ thì cây phải về đúng từng byte; cây bẩn thì
không được đụng.

Chạy trong một git repo tạm, không đụng repo thật.

    python tests/test_doi_ten.py
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GOC = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(GOC)
SCRIPT = os.path.join(REPO, "skills", "code-optimize", "scripts", "doi_ten.py")

dat, hong = [], []


def kiem(ten, ok, chi_tiet=""):
    (dat if ok else hong).append((ten, chi_tiet))
    print(f"  {'đạt ' if ok else 'HỎNG'}  {ten}" + (f"\n          {chi_tiet}" if not ok else ""))


def chay(goc, *args):
    r = subprocess.run([sys.executable, SCRIPT, "--goc", goc] + list(args),
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def git(goc, *args):
    return subprocess.run(["git", "-C", goc] + list(args), capture_output=True, text=True)


def doc(p):
    return io.open(p, encoding="utf-8").read()


def dung_repo(tmp):
    goc = os.path.join(tmp, "repo")
    os.makedirs(os.path.join(goc, "a"))
    io.open(os.path.join(goc, "a", "x.py"), "w", encoding="utf-8", newline="").write(
        'd = {"so": 1, "so_file": 2, "tham_so": 3}\nprint(so)\n')
    io.open(os.path.join(goc, "a", "y.php"), "w", encoding="utf-8", newline="").write(
        "<?php\n$x = array( 'so' => 1, 'dem' => 9 );\n")
    io.open(os.path.join(goc, "README.md"), "w", encoding="utf-8", newline="").write(
        "khoa `so` va `so_file`\n")
    git(goc, "init", "-q")
    git(goc, "-c", "user.name=t", "-c", "user.email=t@t", "add", "-A")
    git(goc, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "goc")
    return goc


def chup(goc):
    ra = {}
    for dp, dn, fn in os.walk(goc):
        dn[:] = [d for d in dn if d != ".git"]
        for f in fn:
            p = os.path.join(dp, f)
            ra[os.path.relpath(p, goc)] = open(p, "rb").read()
    return ra


def main():
    tmp = tempfile.mkdtemp(prefix="doi-ten-")
    try:
        return chay_trong(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def chay_trong(tmp):
    print("=" * 70)
    print("DOI TEN — moi chot mot ca hong, mot ca dung")
    print("=" * 70)

    print("\n[1] Mac dinh chi THU, khong dung file")
    goc = dung_repo(tmp)
    truoc = chup(goc)
    ma, ra = chay(goc, "--cu", "so", "--moi", "dem_so")
    kiem("exit 0, liet ke cho se dung", ma == 0 and "a/x.py" in ra and "a/y.php" in ra, ra[-300:])
    kiem("khong doi gi", chup(goc) == truoc)

    print("\n[2] RANH GIOI TU — doi `so` KHONG duoc dung `so_file`, `tham_so`")
    ma, ra = chay(goc, "--cu", "so", "--moi", "dem_so", "--ghi")
    kiem("doi xong, exit 0", ma == 0, ra[-400:])
    x = doc(os.path.join(goc, "a", "x.py"))
    kiem("`so` doc lap da thanh `dem_so`", '"dem_so": 1' in x and "print(dem_so)" in x, x)
    kiem("`so_file` va `tham_so` GIU NGUYEN", '"so_file"' in x and '"tham_so"' in x, x)
    kiem("doi ca trong .md (bo sot doc la bo sot)", "`dem_so`" in doc(os.path.join(goc, "README.md")))
    kiem("dem dung: 4 cho", "da doi 4 cho" in ra, ra[-300:])
    git(goc, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "doi")

    print("\n[3] VA CHAM — ten moi da ton tai thi TU CHOI")
    ma, ra = chay(goc, "--cu", "dem_so", "--moi", "dem", "--ghi")
    kiem("exit 3 VA_CHAM", ma == 3 and "VA_CHAM" in ra, ra[-300:])
    kiem("chi ro cho da ton tai", "a/y.php" in ra)
    kiem("khong doi gi", "dem_so" in doc(os.path.join(goc, "a", "x.py")))

    print("\n[4] CHI TRONG NHAY — key JSON: `\"dem_so\"` doi, `print(dem_so)` KHONG doi")
    ma, ra = chay(goc, "--cu", "dem_so", "--moi", "so_moi", "--ghi", "--chi-trong-nhay")
    kiem("exit 0", ma == 0, ra[-300:])
    x = doc(os.path.join(goc, "a", "x.py"))
    kiem("key trong nhay doi", '"so_moi": 1' in x, x)
    kiem("dinh danh ngoai nhay giu nguyen", "print(dem_so)" in x, x)
    git(goc, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "nhay")

    print("\n[5] TEST DO thi PHUC HOI tung byte")
    truoc = chup(goc)
    ma, ra = chay(goc, "--cu", "so_moi", "--moi", "hong_roi", "--ghi", "--kiem",
                  sys.executable + " -c \"import sys; sys.exit(1)\"")
    kiem("exit 6 KIEM_DO", ma == 6 and "KIEM_DO" in ra, ra[-400:])
    kiem("cay ve dung tung byte", chup(goc) == truoc,
         str([k for k in truoc if truoc[k] != chup(goc).get(k)]))
    ma, ra = chay(goc, "--cu", "so_moi", "--moi", "ok_roi", "--ghi", "--kiem",
                  sys.executable + " -c \"import sys; sys.exit(0)\"")
    kiem("test xanh thi giu, exit 0", ma == 0 and "kiem xanh" in ra, ra[-300:])
    git(goc, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "ok")

    print("\n[6] CAY BAN thi TU CHOI — git phai la duong lui sach")
    io.open(os.path.join(goc, "a", "z.txt"), "w").write("dang do")
    git(goc, "add", "a/z.txt")
    ma, ra = chay(goc, "--cu", "ok_roi", "--moi", "bat_ky", "--ghi")
    kiem("exit 3, noi ro cay chua sach", ma == 3 and "chua sach" in ra, ra[-300:])
    kiem("khong doi gi", "ok_roi" in doc(os.path.join(goc, "a", "x.py")))

    print("\n[7] KHONG CO GI DE DOI thi tu choi, khong bao 'xong'")
    ma, ra = chay(goc, "--cu", "khong_ton_tai_dau", "--moi", "x")
    kiem("exit 3", ma == 3 and "khong co gi de doi" in ra, ra[-200:])

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
