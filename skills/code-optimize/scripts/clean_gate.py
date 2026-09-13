#!/usr/bin/env python3
"""CỔNG CLEAN — `/code-optimize` chỉ được chạy khi cổng này mở. Fail-closed.

Câu hỏi cổng trả lời: "cây này đã DỌN XONG và CÓ ĐƯỜNG LÙI chưa?" Hai điều kiện, thiếu
một là chặn:

  1. **Dọn xong** — theo đúng định nghĩa xong của `wp-code-cleaner`: quét lại ra RỖNG.
     Không file mồ côi, không file đăng ký hook mà không được nạp, không hàm không ai gọi,
     không câu require nào không phân giải được, và loader phải tìm thấy. Đây là tiêu chí
     của chính cleaner ("Lặp tới khi rỗng"), không phải tiêu chí mới — cổng chỉ biến câu
     đó thành một phép kiểm máy chạy được.

  2. **Có đường lùi** — một backup toàn cây do `backup.py save` tạo, và cây hiện tại phải
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

    python clean_gate.py --theme <cây> --backup <thư-mục-backup> [--prefix fx_] [--out gate.json]

Exit: 0 mở · 7 NOT_CLEAN · 8 NO_ROLLBACK · 4 NOT_CHECKABLE
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
SAO_LUU = os.path.join(GOC, "backup.py")


def chay(*lenh):
    r = subprocess.run([sys.executable] + list(lenh), capture_output=True, text=True,
                       encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme", required=True)
    ap.add_argument("--backup", required=True,
                    help="thu muc backup do backup.py save tao; cay phai MATCH manifest")
    ap.add_argument("--loader", default="functions.php")
    ap.add_argument("--prefix", default="", help="tien to ham, ngan bang dau phay (nhu quet_chet.py)")
    ap.add_argument("--out", default="", help="ghi clean-gate.json")
    a = ap.parse_args()

    theme = os.path.abspath(a.theme)
    if not os.path.isdir(theme):
        print("NOT_CHECKABLE: khong thay cay " + theme)
        return 4
    if not os.path.isfile(QUET_CHET):
        print("NOT_CHECKABLE: khong thay quet_chet.py o " + QUET_CHET)
        return 4

    ket_qua = {"version": 1, "theme": theme.replace("\\", "/"), "conditions": {}}
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
        if a.prefix:
            lenh += ["--prefix", a.prefix]
        _ma, ra = chay(*lenh)
        if not os.path.isfile(tmp) or os.path.getsize(tmp) == 0:
            print("NOT_CHECKABLE: quet_chet.py khong ghi duoc JSON\n" + ra[-600:])
            return 4
        q = json.load(io.open(tmp, encoding="utf-8"))
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass

    kiem_tra = [
        ("has_loader", q.get("has_loader") is True, "loader khong tim thay — muc 1 va 2 cua quet gan chac chan sai"),
        ("unresolved_requires", q.get("unresolved_requires", 1) == 0,
         f"{q.get('unresolved_requires')} cau require khong phan giai duoc — moi cau la mot canh do thi thieu"),
        ("dead_files", not q.get("dead_files"), "file khong co duong nao dan toi: " + ", ".join(q.get("dead_files", [])[:6])),
        ("unloaded_hooks", not q.get("unloaded_hooks"), "file dang ky hook ma khong duoc nap: " + ", ".join(q.get("unloaded_hooks", [])[:6])),
        ("dead_functions", not q.get("dead_functions"), "ham khong ai goi: " + ", ".join(h[0] for h in q.get("dead_functions", [])[:6])),
    ]
    for ten, ok, ly_do in kiem_tra:
        ket_qua["conditions"][ten] = ok
        print(f"  {'dat ' if ok else 'CHAN'}  {ten}" + ("" if ok else f"\n        {ly_do}"))
        if not ok:
            chan.append("NOT_CLEAN:" + ten)

    # ── Điều kiện 2: có backup, và cây KHỚP backup
    print("\n[2] Đường lùi — backup toàn cây phải tồn tại và KHỚP cây hiện tại")
    bk = os.path.abspath(a.backup)
    if not os.path.isfile(os.path.join(bk, "manifest.json")):
        ket_qua["conditions"]["backup_exists"] = False
        print(f"  CHAN  khong thay manifest.json trong {bk}\n        chay: backup.py save --source <cay> --out <backup>")
        chan.append("NO_ROLLBACK:backup_exists")
    else:
        ket_qua["conditions"]["backup_exists"] = True
        print("  dat   backup_exists")
        ma, ra = chay(SAO_LUU, "check", "--from", bk, "--against", theme)
        khop = ma == 0
        ket_qua["conditions"]["tree_matches_backup"] = khop
        print(f"  {'dat ' if khop else 'CHAN'}  tree_matches_backup"
              + ("" if khop else "\n        cay hien tai KHAC backup — neu toi uu hong thi ban trong backup "
                                 "khong phai ban dang chay. Luu lai truoc.\n        "
                                 + ra.strip().replace("\n", "\n        ")[-500:]))
        if not khop:
            chan.append("NO_ROLLBACK:tree_matches_backup")

    ket_qua["blockers"] = chan
    ket_qua["open"] = not chan
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        t = a.out + ".tmp"
        with io.open(t, "w", encoding="utf-8") as f:
            json.dump(ket_qua, f, ensure_ascii=False, indent=2)
        os.replace(t, a.out)
        print("\nđã ghi " + a.out)

    print("\n" + "=" * 72)
    if not chan:
        print("GATE_OPEN — cây đã dọn xong theo định nghĩa của cleaner, và có đường lùi đã khớp.")
        print("Đọc cho đúng: 'dọn xong' ở đây là kết luận TĨNH. Cổng graph (graph_gate.py) sẽ")
        print("đối chứng nó với runtime ngay bước sau — đừng coi cổng này là bằng chứng cuối.")
        print("=" * 72)
        return 0
    if any(c.startswith("NOT_CLEAN") for c in chan):
        print("NOT_CLEAN — chạy wp-code-cleaner cho tới khi quet_chet.py ra rỗng, rồi quay lại.")
        print("=" * 72)
        return 7
    print("NO_ROLLBACK — tạo hoặc làm mới backup bằng backup.py rồi quay lại.")
    print("=" * 72)
    return 8


if __name__ == "__main__":
    sys.exit(main())
