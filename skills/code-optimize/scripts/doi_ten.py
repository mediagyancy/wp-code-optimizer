#!/usr/bin/env python3
"""ĐỔI TÊN AN TOÀN — A → B trên cả cây, có chốt trước, chốt sau, và đường lùi tự động.

Vì sao không dùng replace thẳng
-------------------------------
`replace` (hay `sed`) hỏng theo ba cách, và cả ba đều IM LẶNG:

  1. **Khớp chuỗi con.** Đổi `so` thành `dem` sẽ biến `so_file` thành `dem_file` và
     `tham_so` thành `tham_dem`. Không lỗi, không cảnh báo, chỉ là code sai ở chỗ khác.
  2. **Va chạm tên.** Nếu B đã tồn tại với nghĩa khác, sau khi đổi hai thứ khác nhau
     mang cùng một tên và không còn cách nào tách ra.
  3. **Bỏ sót.** Một chỗ dùng A trong file mình không mở (test, doc, JSON mẫu, script
     khác đọc cùng key) vẫn là A. Chương trình chạy, nhưng hai nửa nói hai tên.

Cách "đổi A → C độc nhất → test → C → B" bắt được (2) và cho biết mình đã đụng chỗ nào,
nhưng KHÔNG bắt được (3): chỗ bỏ sót không bao giờ đi qua C. Và nó nhân đôi số lần sửa.

Script này bắt cả ba, không cần bước trung gian:

  · khớp theo RANH GIỚI TỪ — `(?<![A-Za-z0-9_])A(?![A-Za-z0-9_])`; hoặc `--chi-trong-nhay`
    để chỉ đổi dạng `"A"` / `'A'` (key JSON, mã lý do);
  · chốt TRƯỚC: `đếm(B) == 0`, không thì `VA_CHAM` và dừng; in mọi `file:dòng` sẽ đụng;
  · mặc định CHỈ THỬ; `--ghi` mới đổi thật, và chỉ khi cây git SẠCH hoặc có `--backup`
    do `sao_luu.py luu` tạo — đó là đường lùi CỦA NGƯỜI. Đường lùi CỦA SCRIPT là snapshot
    byte của từng file đụng tới, chụp trước khi sửa: `git checkout` trên Windows trả về
    CRLF cho file LF nên không byte-exact, đã đo;
  · chốt SAU: `đếm(A) == 0` và `đếm(B) == n` — khác là bỏ sót hoặc đụng nhầm, phục hồi;
  · `--kiem "<lệnh>"` (lặp được): chạy sau khi đổi; bất kỳ lệnh nào exit ≠ 0 → phục hồi
    toàn bộ file đã đụng và thoát ≠ 0. Đổi tên mà test đỏ thì chưa đổi xong.

    python doi_ten.py --cu dynamic_unresolved --moi chua_giai --goc . --chi-trong-nhay
    python doi_ten.py --cu A --moi B --goc . --ghi --kiem "python tests/chay_test.py"

Exit: 0 xong · 3 từ chối (cây bẩn / va chạm / không có gì để đổi) · 5 chốt sau lệch,
đã phục hồi · 6 test đỏ, đã phục hồi · 4 KHONG_KIEM_DUOC
"""
import argparse
import io
import os
import re
import shlex
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BO_QUA_TM = (".git", "__pycache__", ".wp-it", "node_modules", "vendor")
DUOI = (".py", ".php", ".js", ".md", ".json", ".yml", ".yaml", ".txt", ".css", ".html")


def mau(ten, chi_trong_nhay):
    t = re.escape(ten)
    if chi_trong_nhay:
        return re.compile(r"""(["'])""" + t + r"""\1""")
    return re.compile(r"(?<![A-Za-z0-9_])" + t + r"(?![A-Za-z0-9_])")


def liet_ke(goc):
    for dp, dn, fn in os.walk(goc):
        dn[:] = sorted(d for d in dn if d not in BO_QUA_TM)
        for f in sorted(fn):
            if f.endswith(DUOI):
                yield os.path.join(dp, f)


def dem(goc, rx):
    """{file: [dòng, ...]} cho mọi chỗ khớp."""
    ra = {}
    for p in liet_ke(goc):
        try:
            s = io.open(p, encoding="utf-8").read()
        except UnicodeDecodeError:
            continue
        dong = [s.count("\n", 0, m.start()) + 1 for m in rx.finditer(s)]
        if dong:
            ra[p] = dong
    return ra


def tong(d):
    return sum(len(v) for v in d.values())


def rel(p, goc):
    """Duong dan tuong doi, LUON dung `/` — de output giong nhau tren Windows va Linux,
    va de test tim `a/x.py` khong do tren may nay ma xanh tren CI."""
    return os.path.relpath(p, goc).replace(os.sep, "/")


def tach_lenh(lenh):
    r"""shlex.split che do POSIX nuot dau `\` trong `C:\...\python.exe` -> WinError 2. Tren
    Windows tach o che do non-POSIX roi tu bo dau nhay bao ngoai tung token."""
    if os.name != "nt":
        return shlex.split(lenh)
    return [t[1:-1] if len(t) >= 2 and t[0] == t[-1] and t[0] in "\"'" else t
            for t in shlex.split(lenh, posix=False)]


def git_sach(goc):
    r = subprocess.run(["git", "-C", goc, "status", "--porcelain"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None
    return r.stdout.strip() == ""


def phuc_hoi(snapshot):
    """Trả từng file về đúng BYTE đã chụp trước khi đụng.

    Không dùng `git checkout --` để phục hồi, dù cây git sạch là điều kiện bắt buộc.
    Lý do đo được: trên Windows với `core.autocrlf`, checkout trả file về CRLF trong
    khi bản gốc là LF — phép phục hồi "xong" mà file lệch từng byte. Đúng cạm bẫy CRLF
    đã có trong `cam-bay.md` (`checkout.css` lệch 1.049 byte = 1.049 dòng). Git là đường
    lùi CỦA NGƯỜI (luôn về được), còn đường lùi CỦA SCRIPT phải là byte-exact.
    """
    loi = []
    for p, d in snapshot.items():
        try:
            tmp = p + ".tmp"
            with open(tmp, "wb") as f:
                f.write(d)
            os.replace(tmp, p)
        except OSError as e:
            loi.append(f"{p}: {e}")
    return not loi, "; ".join(loi)[-400:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cu", required=True, help="ten cu A")
    ap.add_argument("--moi", required=True, help="ten moi B")
    ap.add_argument("--goc", default=".", help="thu muc goc de quet")
    ap.add_argument("--chi-trong-nhay", action="store_true",
                    help="chi doi dang \"A\"/'A' — dung cho key JSON va ma ly do")
    ap.add_argument("--ghi", action="store_true", help="doi that (mac dinh chi thu)")
    ap.add_argument("--backup", default="", help="thu muc backup do sao_luu.py luu tao (cay khong phai git)")
    ap.add_argument("--kiem", action="append", default=[],
                    help="lenh kiem sau khi doi; lap duoc; exit khac 0 thi phuc hoi")
    a = ap.parse_args()

    goc = os.path.abspath(a.goc)
    if not os.path.isdir(goc):
        print("KHONG_KIEM_DUOC: khong thay " + goc)
        return 4
    if a.cu == a.moi:
        print("TU_CHOI: ten cu va ten moi giong nhau")
        return 3

    rx_cu, rx_moi = mau(a.cu, a.chi_trong_nhay), mau(a.moi, a.chi_trong_nhay)

    # ── chốt TRƯỚC
    co_cu = dem(goc, rx_cu)
    co_moi = dem(goc, rx_moi)
    n = tong(co_cu)
    print("=" * 72)
    print(f"DOI TEN  {a.cu}  ->  {a.moi}" + ("   (chi trong nhay)" if a.chi_trong_nhay else "   (ranh gioi tu)"))
    print("=" * 72)
    if n == 0:
        print("TU_CHOI: khong thay ten cu o dau — khong co gi de doi")
        return 3
    if tong(co_moi):
        print(f"VA_CHAM: ten moi `{a.moi}` DA TON TAI o {tong(co_moi)} cho — doi se tron hai nghia vao mot")
        for p, ds in sorted(co_moi.items())[:8]:
            print(f"   {rel(p, goc)}:{','.join(map(str, ds[:6]))}")
        return 3
    print(f"  se dung {n} cho trong {len(co_cu)} file:")
    for p, ds in sorted(co_cu.items()):
        print(f"   {rel(p, goc)}:{','.join(map(str, ds[:8]))}" + (" …" if len(ds) > 8 else ""))

    if not a.ghi:
        print("\nTHU — chua doi gi. Them --ghi de doi that.")
        return 0

    # ── đường lùi phải có TRƯỚC khi đụng
    if a.backup:
        if not os.path.isfile(os.path.join(a.backup, "manifest.json")):
            print("TU_CHOI: --backup khong co manifest.json — chay sao_luu.py luu truoc")
            return 3
    else:
        sach = git_sach(goc)
        if sach is None:
            print("TU_CHOI: thu muc khong phai git repo — can --backup do sao_luu.py luu tao")
            return 3
        if not sach:
            print("TU_CHOI: cay git chua sach — commit hoac cat rieng thay doi dang do truoc, "
                  "de git la duong lui duy nhat va sach")
            return 3

    # ── chụp BYTE của mọi file sẽ đụng, TRƯỚC khi đụng — đây là đường lùi của script
    snapshot = {p: open(p, "rb").read() for p in co_cu}

    # ── đổi, mỗi file qua tạm → đổi tên. Đọc/ghi ở mức byte, tách dòng theo đúng
    #    ký tự đang có, để một file CRLF vẫn là CRLF sau khi đổi.
    for p, goc_byte in snapshot.items():
        s = goc_byte.decode("utf-8")
        if a.chi_trong_nhay:
            moi = rx_cu.sub(lambda m: m.group(1) + a.moi + m.group(1), s)
        else:
            moi = rx_cu.sub(a.moi, s)
        tmp = p + ".tmp"
        with open(tmp, "wb") as f:
            f.write(moi.encode("utf-8"))
        os.replace(tmp, p)

    # ── chốt SAU
    sau_cu, sau_moi = tong(dem(goc, rx_cu)), tong(dem(goc, rx_moi))
    if sau_cu != 0 or sau_moi != n:
        ok, ghi = phuc_hoi(snapshot)
        print(f"CHOT_SAU_LECH: con {sau_cu} cho ten cu (mong 0), {sau_moi} cho ten moi (mong {n}) — "
              f"{'DA PHUC HOI' if ok else 'PHUC HOI THAT BAI: ' + ghi}")
        return 5
    print(f"\n  da doi {n} cho · ten cu con: 0 · ten moi: {n}")

    # ── test; đỏ thì lùi
    for lenh in a.kiem:
        r = subprocess.run(tach_lenh(lenh), cwd=goc, capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        if r.returncode != 0:
            ok, ghi = phuc_hoi(snapshot)
            print(f"KIEM_DO: `{lenh}` exit {r.returncode} — "
                  f"{'DA PHUC HOI ' + str(len(co_cu)) + ' file' if ok else 'PHUC HOI THAT BAI: ' + ghi}")
            print(((r.stdout or "") + (r.stderr or ""))[-600:])
            return 6
        print(f"  kiem xanh: {lenh}")

    print("\nXONG. Nho: ten phat ra ngoai la HOP DONG — them dong CHANGELOG va cap nhat "
          "docs/BANG-THAM-CHIEU.md, roi chay tests/kiem_ten.py.")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
