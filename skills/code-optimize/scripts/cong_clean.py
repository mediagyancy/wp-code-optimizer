#!/usr/bin/env python3
"""CỔNG CLEAN — `/code-optimize` chỉ được chạy khi cổng này mở. Fail-closed.

Câu hỏi cổng trả lời: "cây này đã DỌN XONG và CÓ ĐƯỜNG LÙI chưa?" Hai điều kiện, thiếu
một là chặn:

  1. **Dọn xong** — theo đúng định nghĩa xong của `wp-code-cleaner`: quét lại ra RỖNG.
     Không file mồ côi, không file đăng ký hook mà không được nạp, không hàm không ai gọi,
     không câu require nào không phân giải được, và loader phải tìm thấy. Đây là tiêu chí
     của chính cleaner ("Lặp tới khi rỗng"), không phải tiêu chí mới — cổng chỉ biến câu
     đó thành một phép kiểm máy chạy được.

  2. **Có đường lùi** — một backup toàn cây do `sao_luu.py luu` tạo, và cây hiện tại phải
     KHỚP manifest của backup đó. Khớp nghĩa là: nếu phép tối ưu sắp tới làm hỏng gì, bản
     trong backup chính là bản đang chạy bây giờ, không phải một bản nào khác.

Vì sao không chỉ hỏi người dùng "đã clean chưa"
------------------------------------------------
Vì câu trả lời "rồi" không kiểm được, và vì bước xoá cuối cùng của một đợt dọn thường
làm chết thêm hàm ở file khác — cleaner ghi rõ "Xoá xong phải QUÉT LẠI". Một cây vừa dọn
mà chưa quét lại có thể đang chứa xác mới. Cổng quét lại, và đó là toàn bộ việc của nó.

Vì sao chặn thay vì cảnh báo
----------------------------
Vì repo này đã trả giá hai lần cho fail-open (v0.2.0, rồi TÁI PHÁT ở v0.4.0 trong chính
code viết ra để chống nó), và vì lane tối ưu có bán kính lớn hơn lane dọn: nó BIẾN ĐỔI
code, không chỉ xoá. Tối ưu trên một cây chưa sạch là tối ưu cả phần xác — rồi phải dọn
lại sau khi đã viết lại, tức dọn hai lần và mỗi lần đều rủi ro.

    python cong_clean.py --theme <cây> --backup <thư-mục-backup> [--tien-to fx_] [--ra gate.json]

Exit: 0 mở · 7 CHUA_CLEAN · 8 KHONG_CO_DUONG_LUI · 4 KHONG_KIEM_DUOC
"""
import argparse
import io
import json
import os
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

GOC = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(GOC)))
QUET_CHET = os.path.join(REPO, "skills", "wp-code-cleaner", "scripts", "quet_chet.py")
SAO_LUU = os.path.join(GOC, "sao_luu.py")


def chay(*lenh):
    r = subprocess.run([sys.executable] + list(lenh), capture_output=True, text=True,
                       encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme", required=True)
    ap.add_argument("--backup", required=True,
                    help="thu muc backup do sao_luu.py luu tao; cay phai KHOP manifest")
    ap.add_argument("--loader", default="functions.php")
    ap.add_argument("--tien-to", default="", help="tien to ham, ngan bang dau phay (nhu quet_chet.py)")
    ap.add_argument("--ra", default="", help="ghi clean-gate.json")
    a = ap.parse_args()

    theme = os.path.abspath(a.theme)
    if not os.path.isdir(theme):
        print("KHONG_KIEM_DUOC: khong thay cay " + theme)
        return 4
    if not os.path.isfile(QUET_CHET):
        print("KHONG_KIEM_DUOC: khong thay quet_chet.py o " + QUET_CHET)
        return 4

    ket_qua = {"phien_ban": 1, "theme": theme.replace("\\", "/"), "dieu_kien": {}}
    chan = []

    # ── Điều kiện 1: quét lại phải ra RỖNG
    print("=" * 72)
    print("CỔNG CLEAN")
    print("=" * 72)
    print("\n[1] Quét lại bằng quet_chet.py — phải ra RỖNG")
    fd, tmp = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        lenh = [QUET_CHET, "--theme", theme, "--loader", a.loader, "--json", tmp]
        if a.tien_to:
            lenh += ["--tien-to", a.tien_to]
        _ma, ra = chay(*lenh)
        if not os.path.isfile(tmp) or os.path.getsize(tmp) == 0:
            print("KHONG_KIEM_DUOC: quet_chet.py khong ghi duoc JSON\n" + ra[-600:])
            return 4
        q = json.load(io.open(tmp, encoding="utf-8"))
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass

    kiem_tra = [
        ("co_loader", q.get("co_loader") is True, "loader khong tim thay — muc 1 va 2 cua quet gan chac chan sai"),
        ("require_khong_phan_giai", q.get("require_khong_phan_giai", 1) == 0,
         f"{q.get('require_khong_phan_giai')} cau require khong phan giai duoc — moi cau la mot canh do thi thieu"),
        ("file_chet", not q.get("file_chet"), "file khong co duong nao dan toi: " + ", ".join(q.get("file_chet", [])[:6])),
        ("hook_khong_nap", not q.get("hook_khong_nap"), "file dang ky hook ma khong duoc nap: " + ", ".join(q.get("hook_khong_nap", [])[:6])),
        ("ham_chet", not q.get("ham_chet"), "ham khong ai goi: " + ", ".join(h[0] for h in q.get("ham_chet", [])[:6])),
    ]
    for ten, ok, ly_do in kiem_tra:
        ket_qua["dieu_kien"][ten] = ok
        print(f"  {'dat ' if ok else 'CHAN'}  {ten}" + ("" if ok else f"\n        {ly_do}"))
        if not ok:
            chan.append("CHUA_CLEAN:" + ten)

    # ── Điều kiện 2: có backup, và cây KHỚP backup
    print("\n[2] Đường lùi — backup toàn cây phải tồn tại và KHỚP cây hiện tại")
    bk = os.path.abspath(a.backup)
    if not os.path.isfile(os.path.join(bk, "manifest.json")):
        ket_qua["dieu_kien"]["backup_ton_tai"] = False
        print(f"  CHAN  khong thay manifest.json trong {bk}\n        chay: sao_luu.py luu --nguon <cay> --ra <backup>")
        chan.append("KHONG_CO_DUONG_LUI:backup_ton_tai")
    else:
        ket_qua["dieu_kien"]["backup_ton_tai"] = True
        print("  dat   backup_ton_tai")
        ma, ra = chay(SAO_LUU, "kiem", "--tu", bk, "--so-voi", theme)
        khop = ma == 0
        ket_qua["dieu_kien"]["cay_khop_backup"] = khop
        print(f"  {'dat ' if khop else 'CHAN'}  cay_khop_backup"
              + ("" if khop else "\n        cay hien tai KHAC backup — neu toi uu hong thi ban trong backup "
                                 "khong phai ban dang chay. Luu lai truoc.\n        "
                                 + ra.strip().replace("\n", "\n        ")[-500:]))
        if not khop:
            chan.append("KHONG_CO_DUONG_LUI:cay_khop_backup")

    ket_qua["chan"] = chan
    ket_qua["mo"] = not chan
    if a.ra:
        os.makedirs(os.path.dirname(os.path.abspath(a.ra)), exist_ok=True)
        t = a.ra + ".tmp"
        with io.open(t, "w", encoding="utf-8") as f:
            json.dump(ket_qua, f, ensure_ascii=False, indent=2)
        os.replace(t, a.ra)
        print("\nđã ghi " + a.ra)

    print("\n" + "=" * 72)
    if not chan:
        print("CONG_MO — cây đã dọn xong theo định nghĩa của cleaner, và có đường lùi đã khớp.")
        print("Đọc cho đúng: 'dọn xong' ở đây là kết luận TĨNH. Cổng graph (cong_graph.py) sẽ")
        print("đối chứng nó với runtime ngay bước sau — đừng coi cổng này là bằng chứng cuối.")
        print("=" * 72)
        return 0
    if any(c.startswith("CHUA_CLEAN") for c in chan):
        print("CHUA_CLEAN — chạy wp-code-cleaner cho tới khi quet_chet.py ra rỗng, rồi quay lại.")
        print("=" * 72)
        return 7
    print("KHONG_CO_DUONG_LUI — tạo hoặc làm mới backup bằng sao_luu.py rồi quay lại.")
    print("=" * 72)
    return 8


if __name__ == "__main__":
    sys.exit(main())
