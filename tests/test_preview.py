#!/usr/bin/env python3
"""Kiểm wp-preview-builder — chạy được trong CI, KHÔNG cần trình duyệt.

Ranh giới của bộ kiểm này phải nói rõ ngay: nó **không** chứng minh probe chạy đúng
trong một trang thật. Nó chứng minh **CÔNG THỨC** là công thức đúng, và chứng minh
không ai lặng lẽ đổi lại về `innerWidth`.

Hai thứ đó khác nhau, và thứ thứ hai là thứ đã từng hỏng: công thức cũ trả **0** trên
một trang tràn **296px**. Một cái sai nằm trong file JavaScript thì CI không có trình
duyệt để bắt — nên phần quyết định được tách sang Python và ghim bằng số của ca hỏng thật.

    python tests/test_preview.py
"""
import io
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GOC = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(GOC)
SKILL = os.path.join(REPO, "skills", "wp-preview-builder")
sys.path.insert(0, os.path.join(SKILL, "scripts"))

import quyet_dinh_tran as qd  # noqa: E402

dat, hong = [], []


def kiem(ten, ok, chi_tiet=""):
    (dat if ok else hong).append((ten, chi_tiet))
    print(f"  {'đạt ' if ok else 'HỎNG'}  {ten}" + (f"\n          {chi_tiet}" if not ok else ""))


def doc(p):
    return io.open(p, encoding="utf-8", errors="replace").read()


# ─────────────────────────────────────────────────────────────────────────────
# Phép kiểm: một script đo layout có dùng innerWidth để TÍNH không?
#
# Hàm này phải tự hiệu chuẩn. Một phép grep viết hớ hênh sẽ PASS trên mọi file, kể cả
# file sai — và lúc đó nó tệ hơn không kiểm, vì nó chế ra cảm giác đã kiểm.
# ─────────────────────────────────────────────────────────────────────────────
# DẤU TRỪ KHÔNG CHỈ LÀ `-`.
#
# Bản đầu của phép kiểm này chỉ khớp `-` ASCII — và nó SẼ KHÔNG bắt được chính dòng sai
# gốc trong `docs/QUY-DINH-CLAUDE-WORDPRESS.md`, vì dòng đó viết bằng dấu trừ toán học
# Unicode `−` (U+2212) cho đẹp chữ. Tức phép kiểm sinh ra để chặn một dòng cụ thể lại mù
# trước đúng dòng ấy.
#
# Đây là lý do ca hiệu chuẩn ở dưới dùng NGUYÊN VĂN dòng sai lịch sử, không dùng một biến
# thể tự nghĩ ra. Ca hiệu chuẩn tự nghĩ thường quá yếu — nó chỉ kiểm được những cách hỏng
# mà người viết đã tưởng tượng ra.
TRU = r"[-−–—]"
MAU_XAU = [
    re.compile(r"scrollWidth\s*" + TRU + r"\s*(?:window\.)?innerWidth"),
    re.compile(TRU + r"\s*window\.innerWidth"),
    re.compile(r"\)\s*" + TRU + r"\s*(?:window\.)?innerWidth"),
    # Dạng SO SÁNH, không có dấu trừ nào: `scrollWidth == innerWidth`. Ca hiệu chuẩn
    # lấy từ docs/KINH-NGHIEM-WORDPRESS.md bắt được dạng này — bản đầu của MAU_XAU
    # chỉ nghĩ tới dạng phép trừ nên mù hoàn toàn trước nó.
    re.compile(r"scrollWidth\s*[=!<>]=\s*(?:window\.)?innerWidth"),
]


def dung_innerwidth_de_tinh(noi_dung):
    """True nếu có dấu hiệu innerWidth tham gia một phép tính."""
    return any(m.search(noi_dung) for m in MAU_XAU)


def hieu_chuan_phep_grep():
    """Cho phép kiểm chạy qua đúng ca nó phải bắt, trước khi tin nó."""
    ca_hong = [
        # NGUYÊN VĂN dòng sai đã từng nằm trong docs/QUY-DINH-CLAUDE-WORDPRESS.md,
        # kèm dấu trừ Unicode U+2212 đúng như bản gốc. Đây là ca hiệu chuẩn quan trọng
        # nhất của cả file: phép kiểm phải bắt được đúng cái nó sinh ra để chặn.
        "tràn ngang = max(documentElement.scrollWidth, body.scrollWidth) − innerWidth",
        "- **Kiểm bằng số**: `scrollWidth == innerWidth` ở 375px",
        "const overflowX = Math.max(de.scrollWidth, body.scrollWidth) - window.innerWidth;",
        "const o = scrollWidth - innerWidth;",
        "return scrollWidth -  window.innerWidth;",
    ]
    ca_dung = [
        "const overflowX = Math.max(de.scrollWidth, body.scrollWidth) - vw;",
        "innerWidth: window.innerWidth,   // bao cao de doi chieu",
        "const vw = de.clientWidth;",
        "tràn ngang = max(documentElement.scrollWidth, body.scrollWidth) − documentElement.clientWidth",
    ]
    for s in ca_hong:
        if not dung_innerwidth_de_tinh(s):
            return False, "khong bat duoc ca hong: " + s
    for s in ca_dung:
        if dung_innerwidth_de_tinh(s):
            return False, "bao sai o ca dung: " + s
    return True, ""


def main():
    print("=" * 70)
    print("wp-preview-builder")
    print("=" * 70)

    print("\n[1] Hàm quyết định tràn ngang tự hiệu chuẩn")
    ok, dong = qd.hieu_chuan()
    kiem("bộ hiệu chuẩn của quyet_dinh_tran.py ĐẠT", ok, "\n".join(dong))
    kiem("ca tràn 296px có trong bộ hiệu chuẩn",
         any(c["tran_dung"] == 296 for c in qd.CA_LICH_SU),
         "thieu ca hong that thi bo hieu chuan khong chung minh gi")
    kiem("công thức cũ ĐƯỢC GIỮ LẠI để chứng minh nó sai",
         qd.tran_ngang_sai_cach_cu(640, 640) == 0 and qd.tran_ngang(640, 344) == 296,
         "phai giu ca hai de mot khang dinh co ten chung minh duoc khac biet")
    kiem("tran_ngang() TỪ CHỐI client_width = 0",
         _nem_loi(lambda: qd.tran_ngang(640, 0)),
         "viewport 0 phai nem loi, khong duoc tra mot con so")

    print("\n[2] Bộ bề rộng")
    kiem("đủ 5 mốc", len(qd.BE_RONG) == 5, str(qd.BE_RONG))
    kiem("có 344 — màn hẹp nhất có thật, không phải giả định", 344 in qd.BE_RONG)
    kiem("có 1440 — mốc hay bị rụng khi chép lại danh sách", 1440 in qd.BE_RONG)

    print("\n[3] Phép kiểm innerWidth tự hiệu chuẩn trước khi được dùng")
    ok_grep, vi_sao = hieu_chuan_phep_grep()
    kiem("phép kiểm bắt được ca hỏng VÀ không báo sai ca đúng", ok_grep, vi_sao)

    print("\n[4] probe.js không dùng innerWidth để tính")
    p = os.path.join(SKILL, "scripts", "probe.js")
    kiem("probe.js tồn tại", os.path.isfile(p), p)
    if os.path.isfile(p):
        s = doc(p)
        kiem("không có biểu thức nào trừ innerWidth", not dung_innerwidth_de_tinh(s))
        kiem("dùng documentElement.clientWidth", "de.clientWidth" in s)
        kiem("vẫn BÁO CÁO innerWidth để đối chiếu", "innerWidth: window.innerWidth" in s)
        kiem("fail-closed khi viewport = 0", "LOI_PHEP_DO" in s)
        kiem("kiểm protocol để bắt ca data: URL", "location.protocol" in s)
        kiem("in ra số phần tử đã lọc, không ẩn đi", "da_loc_bo_vi_vo_hai" in s)

    print("\n[5] Tài liệu trong repo không còn dạy công thức cũ")
    for ten in ("QUY-DINH-CLAUDE-WORDPRESS.md", "KINH-NGHIEM-WORDPRESS.md"):
        dp = os.path.join(REPO, "docs", ten)
        if not os.path.isfile(dp):
            kiem(f"{ten} tồn tại", False, dp)
            continue
        s = doc(dp)
        # Dùng CHÍNH phép kiểm đã hiệu chuẩn ở mục [3], không dùng một phép lọc theo từ
        # khoá riêng. Lọc theo từ khoá ("có chữ KHÔNG thì bỏ qua") vừa bỏ sót vừa báo sai:
        # nó tha một dòng sai chỉ vì dòng đó tình cờ có chữ "không", và nó bắt một dòng
        # đúng chỉ vì dòng đó giải thích về innerWidth.
        #
        # Hệ quả của lựa chọn này: tài liệu KHÔNG được tái hiện công thức sai dưới dạng
        # công thức, kể cả để giải thích. Mô tả bằng lời thì được. Bản verbatim của dòng
        # sai sống ở đúng hai nơi — ca hiệu chuẩn trong file test này, và
        # `skills/wp-preview-builder/references/cam-bay-preview.md`, nơi việc của nó là
        # ghi lại ca hỏng.
        xau = [l for l in s.splitlines() if dung_innerwidth_de_tinh(l)]
        kiem(f"{ten} không còn công thức nào dùng innerWidth", not xau,
             "con lai:\n          " + "\n          ".join(xau[:4]))

    dq = os.path.join(REPO, "docs", "QUY-DINH-CLAUDE-WORDPRESS.md")
    if os.path.isfile(dq):
        s = doc(dq)
        kiem("bộ bề rộng trong tài liệu có đủ 1440",
             not re.search(r"344\s*→\s*375\s*→\s*768\s*→\s*1280\s*$", s, re.M),
             "con dong liet ke thieu 1440")
        kiem("tài liệu có nhắc clientWidth", "clientWidth" in s)

    print("\n[6] Skill có đủ phần bắt buộc")
    sk = os.path.join(SKILL, "SKILL.md")
    kiem("SKILL.md tồn tại", os.path.isfile(sk))
    if os.path.isfile(sk):
        s = doc(sk)
        for phan in ("CONCEPT_PREVIEW", "NOT_TESTED", "clientWidth", "344", "1440",
                     "có sẵn từ trước"):
            kiem(f"SKILL.md nhắc `{phan}`", phan in s)
    ref = os.path.join(SKILL, "references", "cam-bay-preview.md")
    kiem("references/cam-bay-preview.md tồn tại", os.path.isfile(ref))
    if os.path.isfile(ref):
        s = doc(ref)
        kiem("cạm bẫy kèm SỐ của ca hỏng thật (296px)", "296" in s)
        kiem("có mục về chỗ CHƯA có luật, không giả vờ đã phủ hết",
             "chưa có luật" in s or "Chưa có luật" in s or "chưa có" in s)

    print("\n" + "=" * 70)
    print(f"đạt {len(dat)} · hỏng {len(hong)}")
    if hong:
        print("\nHỎNG:")
        for t, c in hong:
            print(f"  · {t}\n    {c}")
    print("=" * 70)
    return 1 if hong else 0


def _nem_loi(fn):
    try:
        fn()
        return False
    except Exception:
        return True


if __name__ == "__main__":
    sys.exit(main())
