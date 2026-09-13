#!/usr/bin/env python3
"""HÀM QUYẾT ĐỊNH tràn ngang — tách khỏi trình duyệt để kiểm được trong CI.

Vì sao file này tồn tại
-----------------------
Phép đo tràn ngang đã hỏng một lần, và hỏng theo cách tệ nhất: nó trả về **0** trên
một trang tràn **296px**. Công thức cũ là

    tran_ngang = max(de.scrollWidth, body.scrollWidth) − window.innerWidth

Trong giả lập mobile, `innerWidth` **phình theo nội dung**: đặt viewport 344px mà nội
dung rộng 640px thì `innerWidth = 640` và `scrollWidth = 640`. Phép trừ hai số cùng
phình ra đúng 0 — và 0 trông y hệt một trang sạch. Không có dấu hiệu nào. Âm tính giả
đúng nghĩa. Đã đo trên CẢ Browser pane lẫn chrome-devtools MCP.

Công thức đúng dùng `documentElement.clientWidth`, là bề rộng viewport thật và KHÔNG
phình theo nội dung:

    tran_ngang = max(de.scrollWidth, body.scrollWidth) − de.clientWidth

Nhưng một công thức đúng nằm trong một file JavaScript chỉ chạy được trong trình duyệt
thì **không có cách nào chặn việc ai đó lặng lẽ đổi lại về `innerWidth`**. CI không có
trình duyệt. Nên phần quyết định được tách ra đây, thành hàm thuần, và được ghim bằng
đúng bộ số của ca hỏng thật. Từ nay muốn quay về `innerWidth` thì phải làm đỏ một
khẳng định có tên.

Đây không phải phép kiểm thay cho phép đo trong trình duyệt. Nó là phép kiểm cho
CÔNG THỨC. Hai thứ khác nhau, và cái thứ hai là cái đã từng hỏng.

    python overflow_rule.py            # tự hiệu chuẩn, in kết quả
"""
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PHIEN_BAN = "1.0.0"

# Bề rộng bắt buộc đo. 344 không phải số tròn cho đẹp: đó là màn ngoài Galaxy Z Fold 6,
# màn hẹp nhất CÓ THẬT trong tay người dùng Việt. Mặc định 375 là hẹp nhất là một giả
# định, và giả định đó đã bỏ lọt lỗi.
WIDTHS = (344, 375, 768, 1280, 1440)

# 280 chỉ đo khi cần biết giới hạn chịu đựng, không nằm trong bộ nghiệm thu.
EXTRA_WIDTHS = (280,)

# Biên cho phép, và hai biên này KHÁC NHAU có chủ ý:
#
#   · Ở mức TRANG: không có biên. Tràn 1px vẫn là tràn, vì ở mức trang con số này là
#     hiệu của hai phép đo nguyên, không có chỗ cho sai số làm tròn.
#   · Ở mức PHẦN TỬ: biên 1px, vì `getBoundingClientRect()` trả số thực và một phần tử
#     đặt đúng mép hay ra số kiểu 344.0000001. Không có biên thì mọi trang đều có vài
#     "thủ phạm" ảo ở đúng mép phải.
#
# Hai biên lệch nhau là điều PHẢI nói ra, không phải chi tiết để ẩn: nó là lý do một
# trang có thể báo "tràn 0.4px" ở mức trang mà không liệt được phần tử nào.
PAGE_TOLERANCE_PX = 0
ELEMENT_TOLERANCE_PX = 1


def tran_ngang(scroll_width, client_width):
    """Công thức DUY NHẤT được phép dùng. `client_width` là `documentElement.clientWidth`.

    Cố ý KHÔNG nhận `inner_width`: không nhận thì không dùng sai được.
    """
    if not client_width:
        raise ValueError("client_width = 0 — viewport chưa sẵn sàng, số đo vô nghĩa")
    return max(0, scroll_width - client_width)


def tran_ngang_sai_cach_cu(scroll_width, inner_width):
    """Công thức CŨ, giữ lại CHỈ để ca hiệu chuẩn chứng minh nó sai.

    Không gọi hàm này ở bất cứ đâu khác. Nó tồn tại để một khẳng định có tên chứng minh
    rằng nó trả 0 trên ca tràn 296px — tức để cái sai được ghi lại bằng số, chứ không
    chỉ bằng một câu cảnh báo trong tài liệu.
    """
    return max(0, scroll_width - inner_width)


def co_tran(scroll_width, client_width):
    return tran_ngang(scroll_width, client_width) > PAGE_TOLERANCE_PX


def phan_tu_vuot(right, client_width):
    """Phần tử có vượt mép phải không, đã tính biên làm tròn."""
    return right > client_width + ELEMENT_TOLERANCE_PX


# ─────────────────────────────────────────────────────────────────────────────
# CA HIỆU CHUẨN — số thật, từ ca hỏng thật, đo ngày 02/09/2026
# ─────────────────────────────────────────────────────────────────────────────
KNOWN_CASES = [
    {
        "name": "ca tran 296px tai viewport 344 (Browser pane, gia lap mobile)",
        "client_width": 344,
        "inner_width": 640,
        "scroll_width": 640,
        "expected": 296,
        "old_formula": 0,
        "note": "noi dung rong 640 lam innerWidth phinh theo; hai so cung phinh "
                   "nen phep tru ra 0 — AM TINH GIA tren ca hong da biet",
    },
    {
        "name": "trang sach tai viewport 344",
        "client_width": 344,
        "inner_width": 344,
        "scroll_width": 344,
        "expected": 0,
        "old_formula": 0,
        "note": "ca duong tinh: cong thuc moi khong duoc bao tran o trang sach",
    },
    {
        "name": "tran 1px tai viewport 375",
        "client_width": 375,
        "inner_width": 375,
        "scroll_width": 376,
        "expected": 1,
        "old_formula": 1,
        "note": "muc TRANG khong co bien — tran 1px van la tran",
    },
]


def hieu_chuan():
    """Cho hàm quyết định chạy qua đúng ca nó phải bắt. Trả (ok, danh sách dòng báo cáo)."""
    dong, ok = [], True
    for ca in KNOWN_CASES:
        moi = tran_ngang(ca["scroll_width"], ca["client_width"])
        cu = tran_ngang_sai_cach_cu(ca["scroll_width"], ca["inner_width"])
        dat_moi = moi == ca["expected"]
        dat_cu = cu == ca["old_formula"]
        ok = ok and dat_moi and dat_cu
        dong.append(
            f"  {'dat ' if dat_moi and dat_cu else 'BROKEN'}  {ca['name']}\n"
            f"         cong thuc dung: {moi}px (mong {ca['expected']})   ·   "
            f"cong thuc cu: {cu}px (mong {ca['old_formula']})\n"
            f"         {ca['note']}")

    # Chốt quan trọng nhất: phải TỒN TẠI một ca mà hai công thức cho kết quả KHÁC nhau.
    # Không có ca đó thì bộ hiệu chuẩn này không phân biệt được hai công thức, và mọi
    # "passed" ở trên đều vô nghĩa — đúng loại thước mù mà repo này đã trả giá để học.
    co_ca_phan_biet = any(
        tran_ngang(c["scroll_width"], c["client_width"])
        != tran_ngang_sai_cach_cu(c["scroll_width"], c["inner_width"])
        for c in KNOWN_CASES)
    ok = ok and co_ca_phan_biet
    dong.append(
        f"  {'dat ' if co_ca_phan_biet else 'BROKEN'}  bo hieu chuan PHAN BIET duoc hai cong thuc\n"
        f"         khong co ca nao phan biet duoc thi bo nay khong kiem gi ca")

    # Biên ở hai mức phải khác nhau — nếu ai đó gộp chúng lại thì ca 1px ở mức trang sẽ
    # im lặng trở thành "không tràn".
    bien_khac = PAGE_TOLERANCE_PX != ELEMENT_TOLERANCE_PX
    ok = ok and bien_khac
    dong.append(
        f"  {'dat ' if bien_khac else 'BROKEN'}  bien muc TRANG ({PAGE_TOLERANCE_PX}) khac bien muc "
        f"PHAN TU ({ELEMENT_TOLERANCE_PX})")

    # Bộ bề rộng phải đủ, và phải có 344 lẫn 1440 — hai đầu hay bị rụng nhất.
    du_be_rong = 344 in WIDTHS and 1440 in WIDTHS and len(WIDTHS) == 5
    ok = ok and du_be_rong
    dong.append(
        f"  {'dat ' if du_be_rong else 'BROKEN'}  bo be rong du 5 moc ke ca 344 va 1440: {WIDTHS}")

    return ok, dong


def main():
    print("=" * 70)
    print(f"HAM QUYET DINH TRAN NGANG v{PHIEN_BAN} — tu hieu chuan")
    print("=" * 70)
    ok, dong = hieu_chuan()
    for d in dong:
        print(d)
    print("=" * 70)
    if not ok:
        print("UNCALIBRATED — khong duoc dung ham nay de ket luan")
        return 2
    print("Hieu chuan dat. Cong thuc da duoc ghim bang so cua ca hong that.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
