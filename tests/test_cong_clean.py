#!/usr/bin/env python3
"""Kiểm CỔNG CLEAN — `/code-optimize` chỉ được chạy khi cổng này mở.

Hai chiều phải cùng đúng:
  · cây CHƯA dọn → cổng CHẶN và GỌI TÊN đúng xác còn sót;
  · cây đã dọn + có backup khớp → cổng MỞ;
và ca đối chứng ngược: lấy đúng cây đã mở được, gieo một file mồ côi, cổng phải đóng lại
và gọi tên file đó. Cổng chỉ biết đóng mà không biết đóng VÌ ĐÂU thì không dùng được —
người ta không biết phải dọn cái gì.

Không cần WordPress: cả hai điều kiện của cổng đều là phép kiểm tĩnh.

    python tests/test_cong_clean.py
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
SCRIPTS = os.path.join(REPO, "skills", "code-optimize", "scripts")
FX_BAN = os.path.join(GOC, "integration", "fixture-theme")          # cố tình có xác
FX_SACH = os.path.join(GOC, "integration", "fixture-bien-doi")      # sạch, trừ hook-dong.php

dat, hong = [], []


def kiem(ten, ok, chi_tiet=""):
    (dat if ok else hong).append((ten, chi_tiet))
    print(f"  {'đạt ' if ok else 'HỎNG'}  {ten}" + (f"\n          {chi_tiet}" if not ok else ""))


def chay(script, *args):
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, script)] + list(args),
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main():
    tmp = tempfile.mkdtemp(prefix="cong-clean-")
    try:
        return chay_trong(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def chay_trong(tmp):
    print("=" * 70)
    print("CỔNG CLEAN — kiểm hai chiều")
    print("=" * 70)

    print("\n[1] Cây CHƯA dọn → CHẶN, và gọi tên đúng xác")
    ma, ra = chay("cong_clean.py", "--theme", FX_BAN, "--backup", os.path.join(tmp, "khong-co"),
                  "--tien-to", "fxt_")
    kiem("exit 7 CHUA_CLEAN", ma == 7, f"exit={ma}")
    kiem("gọi tên file mồ côi template-parts/mo-coi.php", "template-parts/mo-coi.php" in ra)
    kiem("gọi tên file có hook mà không được nạp", "inc/hook-khong-ai-nap.php" in ra)
    kiem("gọi tên hàm không ai gọi fxt_gia_woo", "fxt_gia_woo" in ra)
    kiem("CHUA_CLEAN được ưu tiên báo trước KHONG_CO_DUONG_LUI (sửa code trước, backup sau)",
         "CHUA_CLEAN" in ra.splitlines()[-2] if len(ra.splitlines()) >= 2 else False,
         ra[-200:])

    # Cây sạch = fixture-bien-doi bỏ file hook-dong.php (file đó là ca hiệu chuẩn cho cổng
    # GRAPH, và nó cố tình chứa một callback ghép chuỗi mà bộ quét tĩnh không thấy — nên
    # với quet_chet.py nó trông như một hàm không ai gọi).
    sach = os.path.join(tmp, "sach")
    shutil.copytree(FX_SACH, sach)
    os.remove(os.path.join(sach, "inc", "hook-dong.php"))
    fn = os.path.join(sach, "functions.php")
    s = io.open(fn, encoding="utf-8").read()
    moc = "require_once FXB_DUONG_DAN . '/inc/hook-dong.php';\n"
    kiem("mốc require xuất hiện đúng 1 lần trước khi gỡ", s.count(moc) == 1, str(s.count(moc)))
    io.open(fn, "w", encoding="utf-8", newline="").write(s.replace(moc, ""))

    print("\n[2] Cây sạch nhưng KHÔNG có backup → CHẶN vì không có đường lùi")
    ma, ra = chay("cong_clean.py", "--theme", sach, "--backup", os.path.join(tmp, "khong-co"),
                  "--tien-to", "fxb_")
    kiem("exit 8 KHONG_CO_DUONG_LUI", ma == 8, f"exit={ma}\n{ra[-400:]}")
    kiem("điều kiện 1 đều đạt (cây đúng là sạch)",
         all(x in ra for x in ("dat   co_loader", "dat   file_chet", "dat   ham_chet")), ra[-600:])

    print("\n[3] Cây sạch + backup KHỚP → MỞ")
    bk = os.path.join(tmp, "backup")
    ma, _ = chay("sao_luu.py", "luu", "--nguon", sach, "--ra", bk)
    kiem("sao_luu.py luu xong", ma == 0)
    gate = os.path.join(tmp, "gate.json")
    ma, ra = chay("cong_clean.py", "--theme", sach, "--backup", bk, "--tien-to", "fxb_", "--ra", gate)
    kiem("exit 0 CONG_MO", ma == 0, f"exit={ma}\n{ra[-500:]}")
    kiem("in ra CONG_MO", "CONG_MO" in ra)
    kiem("nói rõ đây là kết luận TĨNH, cổng graph còn phải đối chứng", "TĨNH" in ra and "cong_graph" in ra)
    g = json.load(io.open(gate, encoding="utf-8")) if os.path.isfile(gate) else {}
    kiem("gate.json ghi mo=true và chan=[]", g.get("mo") is True and g.get("chan") == [], str(g.get("chan")))

    print("\n[4] Cây TRÔI khỏi backup → đóng lại (bản trong backup không còn là bản đang chạy)")
    io.open(os.path.join(sach, "footer.php"), "a", encoding="utf-8").write("\n<!-- sua sau backup -->\n")
    ma, ra = chay("cong_clean.py", "--theme", sach, "--backup", bk, "--tien-to", "fxb_")
    kiem("exit 8 khi cây khác backup", ma == 8, f"exit={ma}")
    kiem("gọi tên file đã trôi", "footer.php" in ra, ra[-400:])
    # trả về khớp
    shutil.rmtree(sach)
    ma, _ = chay("sao_luu.py", "phuc_hoi", "--tu", bk, "--den", sach, "--ghi")
    kiem("phục hồi từ backup để tiếp tục", ma == 0)

    print("\n[5] CA ĐỐI CHỨNG NGƯỢC — gieo một file mồ côi vào cây đã mở được")
    io.open(os.path.join(sach, "inc", "mo-coi-moi.php"), "w", encoding="utf-8").write(
        "<?php\ndefined( 'ABSPATH' ) || exit;\nfunction fxb_khong_ai_goi() {}\n")
    ma, ra = chay("cong_clean.py", "--theme", sach, "--backup", bk, "--tien-to", "fxb_")
    kiem("cổng ĐÓNG lại, exit 7", ma == 7, f"exit={ma}")
    kiem("gọi đúng tên file mồ côi vừa gieo", "inc/mo-coi-moi.php" in ra, ra[-500:])
    kiem("gọi đúng tên hàm không ai gọi vừa gieo", "fxb_khong_ai_goi" in ra, ra[-500:])

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
