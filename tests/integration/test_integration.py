#!/usr/bin/env python3
"""Integration test: so kết luận của bộ quét với SỰ THẬT từ WordPress đang chạy.

Đây là tầng mà fixture tĩnh KHÔNG thay được. Fixture chứng minh bộ phân tích đọc
đúng cú pháp; nó không chứng minh kết luận còn đúng trên một site có WooCommerce
và plugin sinh markup lúc chạy. Ở đây WordPress tự nói ai đúng:

  · get_included_files()  -> file theme nào THỰC SỰ được nạp
  · HTML render ra        -> class nào THỰC SỰ xuất hiện
  · $wp_filter            -> hook nào THỰC SỰ đăng ký

Hai khẳng định quan trọng nhất, và chúng bất đối xứng có chủ ý:

  · "tool báo chết mà WordPress có nạp"  -> HỎNG NẶNG. Tin theo là xoá code
    đang chạy. Không được phép có, dù chỉ một.
  · "WordPress không nạp mà tool không báo" -> bỏ sót, tiếc nhưng KHÔNG mất gì.
    Vẫn kiểm, nhưng đây là hướng an toàn.

    python tests/integration/test_integration.py --ra <thư-mục-làm-việc>
"""
import argparse
import json
import os
import re
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GOC = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(GOC))
SCRIPTS = os.path.join(REPO, "skills", "wp-code-cleaner", "scripts")
sys.path.insert(0, GOC)
from dung_wp import php_args  # noqa: E402

dat, hong = [], []


def kiem(ten, ok, chi_tiet=""):
    (dat if ok else hong).append((ten, chi_tiet))
    print(f"  {'đạt ' if ok else 'HỎNG'}  {ten}" + (f"\n          {chi_tiet}" if not ok else ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ra", required=True)
    a = ap.parse_args()
    W = os.path.abspath(a.ra)
    theme = os.path.join(W, "site", "wp-content", "themes", "fixture-theme")

    if not os.path.exists(theme):
        sys.exit("chưa dựng WordPress — chạy dung_wp.py trước")

    # ── sự thật nền, lấy từ WordPress đang chạy
    r = subprocess.run(["php"] + php_args() + [os.path.join(W, "su-that-nen.php")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"\{.*\}", r.stdout or "", re.S)
    if not m:
        print((r.stdout or "")[-800:], (r.stderr or "")[-400:])
        sys.exit("không lấy được sự thật nền")
    nen = json.loads(m.group(0))
    nap = set(nen["file_da_nap"])
    lop_that = set(nen["class_trong_html"])

    print(f"\nSỰ THẬT NỀN từ WordPress đang chạy")
    print(f"  WooCommerce bật: {nen['woocommerce_active']}")
    print(f"  file theme WordPress THỰC SỰ nạp: {len(nap)}")
    print(f"  class THỰC SỰ có trong HTML: {len(lop_that)}  {sorted(lop_that)}")
    print(f"  HTML render: {nen['do_dai_html']} ký tự")

    # ── kết luận của bộ quét
    print("\nSO VỚI KẾT LUẬN CỦA quet_chet.py")
    q = subprocess.run([sys.executable, os.path.join(SCRIPTS, "quet_chet.py"),
                        "--theme", theme, "--tien-to", "fxt_"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    ra = (q.stdout or "") + (q.stderr or "")
    bao_chet = set(re.findall(r"^   (\S+\.php)\s+\d+ dòng", ra, re.M))

    sai_nang = sorted(bao_chet & nap)
    kiem("KHÔNG file nào bị báo chết mà WordPress thật có nạp",
         not sai_nang,
         f"tin theo là xoá code đang chạy: {sai_nang}")

    bo_sot = sorted(f for f in ("inc/hook-khong-ai-nap.php", "template-parts/mo-coi.php")
                    if f not in bao_chet)
    kiem("file WordPress KHÔNG nạp thì bị báo chết", not bo_sot, f"bỏ sót: {bo_sot}")

    kiem("require có điều kiện class_exists('WooCommerce') được tính là nạp",
         "inc/chi-khi-co-woo.php" in nap and "inc/chi-khi-co-woo.php" not in bao_chet,
         "WooCommerce đang bật nên file này CÓ nạp")

    kiem("WordPress xác nhận hàm trong file không được nạp là KHÔNG tồn tại",
         nen["ham_ton_tai"]["fxt_khong_bao_gio_chay"] is False)
    kiem("WordPress xác nhận hook init của file đó KHÔNG đăng ký",
         nen["hook_init_dang_ky"] is False,
         "add_action không làm file tự chạy — phải có ai nạp trước")
    kiem("mục 2 của tool chỉ đúng file đó",
         re.search(r"2\. FILE ĐĂNG KÝ HOOK.*?inc/hook-khong-ai-nap\.php", ra, re.S) is not None)

    # ── kết luận của bộ gỡ CSS
    print("\nSO VỚI KẾT LUẬN CỦA go_css.py")
    css = os.path.join(theme, "assets", "css", "main.css")
    truoc = open(css, encoding="utf-8").read()
    g = subprocess.run([sys.executable, os.path.join(SCRIPTS, "go_css.py"),
                        "--theme", theme, "--css", "assets/css/main.css",
                        "--tien-to", "fxt-", "--ghi"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    sau = open(css, encoding="utf-8").read()
    open(css, "w", encoding="utf-8").write(truoc)  # trả fixture về nguyên trạng

    def lop(x):
        return set(re.findall(r"\.(-?[A-Za-z_][A-Za-z0-9_-]*)", x))

    da_xoa = lop(truoc) - lop(sau)
    xoa_nham = sorted(da_xoa & lop_that)
    print(f"  tool xoá {len(da_xoa)} class: {sorted(da_xoa)}")
    kiem("KHÔNG class nào bị xoá mà thật sự đang hiện trên trang",
         not xoa_nham, f"xoá nhầm class đang render: {xoa_nham}")
    kiem("class ghép chuỗi .fxt-bac--N được giữ",
         "fxt-bac--1" in lop(sau) and "fxt-bac--1" in lop_that,
         "WordPress render ra fxt-bac--1, tool phải giữ")
    kiem("class chết thật thì bị xoá",
         "fxt-chet" in " ".join(da_xoa) or any(c.startswith("fxt-chet") for c in da_xoa))
    kiem("CSS sau khi ghi vẫn cân bằng ngoặc", sau.count("{") == sau.count("}"))

    # ── vòng 2: chết theo dây chuyền, kiểm bằng chính sự thật nền
    #
    # Vòng 1 tool GIỮ .fxt-chet__part, và đó là đúng: template-parts/mo-coi.php còn
    # trên đĩa nên tên class ấy còn markup. WordPress không render nó (không ai
    # get_template_part), nhưng "không render" khác "không tồn tại" — xoá CSS trước
    # khi xoá file là để lại một file gọi class không còn style.
    # Quy trình bắt xoá file trước rồi QUÉT LẠI. Ở đây kiểm đúng điều đó.
    print("\nVÒNG 2 — sau khi xoá template-part mồ côi (chết theo dây chuyền)")
    mo_coi = os.path.join(theme, "template-parts", "mo-coi.php")
    luu = open(mo_coi, encoding="utf-8").read()
    kiem("vòng 1 GIỮ .fxt-chet__part vì file mồ côi còn trên đĩa",
         "fxt-chet__part" not in da_xoa,
         "xoá CSS trước khi xoá file là sai thứ tự")
    os.remove(mo_coi)
    try:
        subprocess.run([sys.executable, os.path.join(SCRIPTS, "go_css.py"),
                        "--theme", theme, "--css", "assets/css/main.css",
                        "--tien-to", "fxt-", "--ghi"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        sau2 = open(css, encoding="utf-8").read()
    finally:
        open(css, "w", encoding="utf-8").write(truoc)
        open(mo_coi, "w", encoding="utf-8").write(luu)

    da_xoa2 = lop(truoc) - lop(sau2)
    kiem("vòng 2 mới xoá .fxt-chet__part", "fxt-chet__part" in da_xoa2)
    kiem("vòng 2 vẫn KHÔNG đụng class đang render",
         not (da_xoa2 & lop_that),
         f"xoá nhầm: {sorted(da_xoa2 & lop_that)}")

    print(f"\n{'='*62}")
    print(f"đạt {len(dat)} · hỏng {len(hong)}")
    if hong:
        print("\nHỎNG:")
        for t, c in hong:
            print(f"  · {t}\n    {c}")
    print("=" * 62)
    return 1 if hong else 0


if __name__ == "__main__":
    sys.exit(main())
