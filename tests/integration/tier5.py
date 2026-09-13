#!/usr/bin/env python3
"""TẦNG 5 — chứng minh một phép BIẾN ĐỔI có giữ nguyên hành vi hay không.

Bốn tầng cũ của `wp-code-cleaner` sinh ra để chứng minh một phép XOÁ là an toàn, và
chúng làm việc đó tốt. Nhưng ba trong bốn tầng được tham số hoá bằng một DANH SÁCH ĐÃ
XOÁ: "class nào vừa xoá còn xuất hiện? phải là 0". Một phép viết lại không có danh sách
xoá, nên tập truy vấn rỗng, nên chúng PASS RỖNG. Tầng 2 thì còn tệ hơn: chốt mạnh nhất
của nó là "rule còn lại phải NGUYÊN VĂN như cũ" — một phép rewrite phá tiền đề ấy BẰNG
ĐỊNH NGHĨA.

Nên Tầng 5 không hỏi "thứ vừa xoá còn ai gọi". Nó chụp BỀ MẶT QUAN SÁT ĐƯỢC trước và
sau, rồi đòi hiệu bằng rỗng. Bảy mặt, mỗi mặt bắt một họ lỗi khác nhau:

    nap       file theme được nạp, THEO THỨ TỰ NẠP
    hook      (hook, priority, thứ tự trong bucket, callback, file:dòng)
    fire      chuỗi hook fire thật, THEO THỨ TỰ THỰC THI
    asset     hàng đợi script/style + handle do theme đăng ký
    signatures    tên hàm -> tham số có thứ tự kèm GIÁ TRỊ MẶC ĐỊNH
    html      HTML toàn văn, so theo byte sau khi mask
    sanitizers  TĨNH: mỗi điểm đọc superglobal -> hàm sanitizers bọc ngoài

Mặt `sanitizers` là mặt tĩnh duy nhất, và nó phải tồn tại: ca "mất lời gọi sanitizers" không
để lại dấu nào ở runtime trên request không có tham số đó.

BA KỶ LUẬT, cả ba là cổng chứ không phải cảnh báo
-------------------------------------------------
1. NOISE ĐO ĐƯỢC, KHÔNG ĐOÁN. Chụp bản KHÔNG ĐỔI hai lượt trước đã. Mọi thứ lệch giữa
   hai lượt ấy là noise của chính phép đo, và nó bị TRỪ đi. Mask viết bằng tay là mask
   đoán; mask dựa trên hai lượt baseline là mask có số liệu. Mượn từ hạ tầng
   shadow-traffic (mẫu ba chiều của Diffy), không phải từ unit test.
2. THƯỚC PHẢI BẮT ĐƯỢC CA HỎNG ĐÃ BIẾT. Sáu ca tiêm ở dưới là ca hiệu chuẩn. Ca nào
   không mặt nào bắt được thì lớp đó là `NOT_TESTED` — không phải "đã kiểm".
3. FAIL-CLOSED. Không chụp được, không có baseline, hai lượt baseline đã lệch → thoát
   khác 0 với một reason code. Không bao giờ im lặng báo sạch. Repo này đã trả giá hai
   lần cho fail-open: một lần ở v0.2.0, và một lần TÁI PHÁT trong chính code viết ra để
   chống nó ở v0.4.0.

    python tests/integration/tier5.py --workdir .wp-it
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GOC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, GOC)
from dung_wp import php_args  # noqa: E402

THEME_SLUG = "fixture-bien-doi"

# ─────────────────────────────────────────────────────────────────────────────
# MASK — mỗi mask là một VÙNG MÙ BẰNG CẤU TRÚC, nên mỗi mask phải mang lý do.
#
# Danh sách này cố ý ngắn. Cách dùng đúng: chạy hai lượt baseline, xem noise CÒN LẠI
# sau khi mask, rồi chỉ thêm mask cho thứ thực sự quan sát được là không tất định —
# không thêm cho thứ mình tưởng tượng là sẽ không tất định. Một mask không có ca noise
# thật chống lưng là một chỗ regression vô hình mà ta tự tay tạo ra.
# ─────────────────────────────────────────────────────────────────────────────
MASK = [
    (re.compile(r'(name="_wpnonce"\s+value=")[0-9a-f]{8,}(")'), r"\1<NONCE>\2",
     "nonce do WordPress sinh trong chinh SUT, doi moi request theo thoi gian"),
    (re.compile(r'(\b_wpnonce=)[0-9a-f]{8,}'), r"\1<NONCE>",
     "nonce trong query string, cung ly do"),
    (re.compile(r'("nonce":")[0-9a-f]{8,}(")'), r"\1<NONCE>\2",
     "nonce nhung trong JSON cua script core"),
]


def mask_html(s):
    for mau, thay, _ly_do in MASK:
        s = mau.sub(thay, s)
    return s


# ─────────────────────────────────────────────────────────────────────────────
# NOISE CỦA MẶT `fire` — mask này KHÔNG phải do đoán, nó do ĐO RA.
#
# Lượt chạy đầu tiên của bộ đo báo `NOISE_TOO_HIGH` ở đúng mặt `fire`, lệch từ ký tự
# 3523, và chỗ lệch chỉ ra nguyên nhân rất rõ:
#
#     luot A: … "option_stylesheet", "stylesheet", "extra_theme_headers", …
#     luot B: … "option_stylesheet", "stylesheet", "pre_option_stylesheet", "pre_option", …
#
# Tức lượt sau đọc option từ cache còn ấm nên KHÔNG fire lại `pre_option_*`, lượt
# trước thì fire. Đây là hành vi của tầng cache option/transient của WordPress, không
# phải hành vi của theme — và nó phụ thuộc vào trạng thái cache, thứ mà một bộ đo chạy
# hai lượt liên tiếp không điều khiển được.
#
# VÙNG MÙ PHẢI KHAI BÁO, KHÔNG ĐƯỢC ẨN: sau khi lọc họ hook này, mặt `fire` KHÔNG còn
# trả lời được câu "phép biến đổi có làm đổi tập option/transient được đọc hay không".
# Đó là một câu hỏi thật và nó thành `NOT_TESTED`. Đổi nó lấy một baseline ổn định là
# một đánh đổi có chủ ý: một mặt đo báo lệch ở MỌI lượt là một mặt đo sẽ bị tắt, và
# một mặt bị tắt thì không bảo vệ được gì.
# ─────────────────────────────────────────────────────────────────────────────
FIRE_NOISE = re.compile(
    r"^("
    r"pre_option(_.*)?|option_.*|default_option_.*|pre_update_option.*|"
    r"pre_wp_load_alloptions|alloptions|pre_cache_alloptions|"
    r"pre_(site_)?transient_.*|(site_)?transient_.*|"
    r"pre_determine_locale|"
    r"extra_theme_headers|theme_file_path|stylesheet|template|stylesheet_directory.*|"
    r"template_directory.*|"
    # `query` là hook của $wpdb, fire mỗi khi có truy vấn DB THẬT. Nó fire hay không
    # tuỳ trạng thái cache, không tuỳ code theme: chạy Tầng 5 ngay sau khi một bộ test
    # khác đổi theme (switch_theme.php flush cache) thì lượt A đọc site_option từ DB còn
    # lượt B đọc từ cache — lệch từ ký tự 11076, đúng ở
    # `default_site_option_can_compress_scripts` → `query`. Cùng họ với option/transient
    # ở trên, và cùng đánh đổi: mặt `fire` không trả lời "có đổi số truy vấn DB không".
    r"query|pre_get_site_option_.*|(default_)?site_option_.*"
    r")$"
)


def loc_noise_fire(chuoi):
    """Bỏ họ hook cache/option khỏi chuỗi fire. GIỮ NGUYÊN thứ tự phần còn lại."""
    return [h for h in chuoi if not FIRE_NOISE.match(h)]


# ─────────────────────────────────────────────────────────────────────────────
# MẶT TĨNH: điểm đọc superglobal -> hàm sanitizers bọc ngoài
# ─────────────────────────────────────────────────────────────────────────────
SANITIZERS = {
    "esc_html", "esc_attr", "esc_url", "esc_url_raw", "esc_textarea", "esc_js",
    "sanitize_text_field", "sanitize_textarea_field", "sanitize_key", "sanitize_email",
    "sanitize_title", "sanitize_file_name", "absint", "intval", "floatval",
    "wp_kses", "wp_kses_post", "filter_var",
}
# wp_unslash KHONG phai sanitiser: no bo dau gach cheo, khong lam sach gi. Xep no vao
# nhom sanitizers la tu lua minh — va do dung la cach mot lo XSS di qua mot ban review.
NOT_SANITIZER = {"wp_unslash", "stripslashes", "trim", "strval"}

SUPERGLOBALS = re.compile(r"\$_(GET|POST|REQUEST|COOKIE|SERVER)\s*\[")


def mat_sanit(goc_theme):
    """Quét mã nguồn: mỗi điểm đọc superglobal kèm tập hàm sanitizers bọc ngoài.

    Cố ý đơn giản — đọc theo dòng, không dựng AST. Giới hạn phải nói rõ: một lời gọi
    sanitizers đặt ở dòng khác (ví dụ gán vào biến rồi mới esc_html ở dòng sau) sẽ bị
    báo là KHÔNG có sanitiser. Đó là dương tính giả, và dương tính giả ở đây là hướng
    an toàn. Hướng nguy hiểm là âm tính giả, và cách duy nhất biết nó có xảy ra hay
    không là ca tiêm số 4 ở dưới — nếu ca đó không làm mặt này đổi thì mặt này mù.
    """
    ra = []
    for thu_muc, _, ten_file in os.walk(goc_theme):
        for t in sorted(ten_file):
            if not t.endswith(".php"):
                continue
            p = os.path.join(thu_muc, t)
            tuong_doi = os.path.relpath(p, goc_theme).replace("\\", "/")
            with open(p, encoding="utf-8", errors="replace") as f:
                for so, dong in enumerate(f, 1):
                    for m in SUPERGLOBALS.finditer(dong):
                        truoc = dong[: m.start()]
                        ham = set(re.findall(r"([a-z_][a-z0-9_]*)\s*\(", truoc))
                        ra.append({
                            "file": tuong_doi,
                            "line": so,
                            "indirect": "$_" + m.group(1),
                            "sanitizers": sorted(ham & SANITIZERS),
                            "skipped": sorted(ham & NOT_SANITIZER),
                        })
    return ra


# ─────────────────────────────────────────────────────────────────────────────
# CHỤP ADN
# ─────────────────────────────────────────────────────────────────────────────
def chup(W, goc_theme):
    """Chạy dna.php, trả (adn, loi). Tự xử lý ca switch_theme cần chạy lại."""
    for lan in range(3):
        r = subprocess.run(
            ["php"] + php_args() + [os.path.join(W, "dna.php"),
                                    "--theme-slug=" + THEME_SLUG],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = r.stdout or ""
        m = re.search(r"\{.*\}", out, re.S)
        if not m:
            return None, "CAPTURE_FAILED: " + (out[-400:] + (r.stderr or "")[-400:])
        d = json.loads(m.group(0))
        if d.get("error") == "RERUN_NEEDED":
            continue
        if d.get("error"):
            return None, d["error"] + ": " + json.dumps(d, ensure_ascii=False)[:300]
        d["html_mask"] = mask_html(d.pop("html_raw"))
        d["sanitizers"] = mat_sanit(goc_theme)
        return d, None
    return None, "CAPTURE_FAILED: switch_theme khong on dinh sau 3 lan"


def bay_mat(d):
    """Bảy mặt, ở dạng so sánh được. Thứ tự được GIỮ ở mọi mặt cần thứ tự."""
    return {
        "files": d["files_after_render"],
        "hooks": [[h["hook"], h["priority"], h["order"], h["callback"], h["file"], h["line"]]
                 for h in d["theme_hooks"]],
        "fires": loc_noise_fire(d["fire_sequence"]),
        "assets": {"script_queue": d["scripts"]["queue"], "theme_scripts": d["scripts"]["theme"],
                  "style_queue": d["styles"]["queue"], "theme_styles": d["styles"]["theme"]},
        "signatures": [[f["name"], [[p["name"], p["default"], p["required"]] for p in f["params"]]]
                  for f in d["signatures"]],
        "html": d["html_mask"],
        "sanitizers": d["sanitizers"],
    }


def lech(a, b):
    """Tập tên mặt có khác nhau. So bằng JSON đã chuẩn hoá để thứ tự khoá không sinh noise."""
    ra = []
    ma, mb = bay_mat(a), bay_mat(b)
    for ten in ("files", "hooks", "fires", "assets", "signatures", "html", "sanitizers"):
        if json.dumps(ma[ten], sort_keys=True, ensure_ascii=False) != \
           json.dumps(mb[ten], sort_keys=True, ensure_ascii=False):
            ra.append(ten)
    return ra


# ─────────────────────────────────────────────────────────────────────────────
# SÁU CA TIÊM — đây là bộ hiệu chuẩn. Mỗi ca là một lỗi refactor THẬT mà cả bốn tầng
# cũ đều bỏ lọt (ca 4 thì tầng 2 bắt được MỘT PHẦN, có điều kiện và chưa xác minh).
# ─────────────────────────────────────────────────────────────────────────────
INJECTIONS = [
    {
        "case_id": "1-thu-tu-dang-ky",
        "name": "hoi hook doi THU TU DANG KY o cung priority",
        "file": "functions.php",
        "old": ("require_once FXB_DUONG_DAN . '/inc/hook-a.php';\n"
               "require_once FXB_DUONG_DAN . '/inc/hook-b.php';"),
        "new": ("require_once FXB_DUONG_DAN . '/inc/hook-b.php';\n"
                "require_once FXB_DUONG_DAN . '/inc/hook-a.php';"),
        "expect": "hooks",
    },
    {
        "case_id": "2-doi-priority",
        "name": "add_action doi priority 5 -> 50",
        "file": "inc/uu-tien.php",
        "old": "add_action( 'wp_head', 'fxb_meta_som', 5 );",
        "new": "add_action( 'wp_head', 'fxb_meta_som', 50 );",
        "expect": "hooks",
    },
    {
        "case_id": "3-gia-tri-mac-dinh",
        "name": "ham doi GIA TRI MAC DINH cua tham so",
        "file": "inc/tham-so.php",
        "old": "function fxb_gia( $so, $ty_le = 1.1 ) {",
        "new": "function fxb_gia( $so, $ty_le = 1.2 ) {",
        "expect": "signatures",
    },
    {
        "case_id": "4-mat-sanitizers",
        "name": "mat loi goi esc_html quanh $_GET",
        "file": "inc/loc-dau-vao.php",
        "old": "return esc_html( wp_unslash( $_GET['fxb_tim'] ?? '' ) );",
        "new": "return wp_unslash( $_GET['fxb_tim'] ?? '' );",
        "expect": "sanitizers",
    },
    {
        "case_id": "5-doi-diem-lifecycle",
        "name": "get_template_part doi sang SAU wp_head()",
        "file": "header.php",
        "old": ("\t<?php get_template_part( 'template-parts/bo-phan' ); ?>\n"
               "\t<?php wp_head(); ?>"),
        "new": ("\t<?php wp_head(); ?>\n"
                "\t<?php get_template_part( 'template-parts/bo-phan' ); ?>"),
        "expect": "assets",
    },
    {
        "case_id": "6-dao-chieu-dieu-kien",
        "name": "dieu kien bi DAO CHIEU",
        "file": "inc/dieu-kien.php",
        "old": "if ( ! is_admin() ) {",
        "new": "if ( is_admin() ) {",
        "expect": "hooks",
    },
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", required=True, help="thu muc lam viec cua integration test")
    a = ap.parse_args()
    W = os.path.abspath(a.workdir)
    site = os.path.join(W, "site")
    if not os.path.isdir(site):
        print("NOT_CHECKABLE: chua dung WordPress — chay dung_wp.py truoc")
        return 4

    # theme fixture cho phep bien doi, dat vao site
    goc_theme = os.path.join(site, "wp-content", "themes", THEME_SLUG)
    if os.path.exists(goc_theme):
        shutil.rmtree(goc_theme)
    shutil.copytree(os.path.join(GOC, "fixture-bien-doi"), goc_theme)
    shutil.copy(os.path.join(GOC, "dna.php"), os.path.join(W, "dna.php"))

    print("=" * 72)
    print("TANG 5 — hieu chuan thuoc do tuong duong hanh vi")
    print("=" * 72)

    # ── 0. LAM AM: mot luot bi BO DI, truoc khi do bat cu gi.
    #
    # Request DAU TIEN tren mot site vua cai khac moi request sau no, va khac theo cach
    # khong lien quan gi toi theme: wp_get_custom_css_post() lan dau chay WP_Query tim
    # post custom CSS roi ghi id vao theme_mod; lan sau doc theme_mod. CI chay tren site
    # vua dung nen luot A la luot dau lanh, luot B am → mat `fire` lech tu ky tu 17058 o
    # `theme_mod_custom_css_post_id`, NOISE_TOO_HIGH, exit 6. Local khong bao gio thay vi
    # .wp-it o may da am sau hang chuc luot chay.
    #
    # Them ten hook vao danh sach loc la whack-a-mole: lan sau se la mot cache khac. Cach
    # dung la cach moi benchmark lam — bo luot dau. Ca TRUOC va SAU bien doi deu duoc do
    # sau luot am nay nen phep so van cong bang; baseline noise cung do theo cung giao thuc.
    print("\n[0] Lam am — mot luot bi bo, de luot dau lanh khong thanh noise")
    _am, loi = chup(W, goc_theme)
    if loi:
        print("   " + loi)
        return 5

    # ── 1. NOISE: chup ban KHONG DOI hai luot
    print("\n[1] Do NOISE — chup ban khong doi code hai luot")
    n1, loi = chup(W, goc_theme)
    if loi:
        print("   " + loi)
        return 5
    n2, loi = chup(W, goc_theme)
    if loi:
        print("   " + loi)
        return 5

    noise = lech(n1, n2)
    print(f"   moi truong: PHP {n1['env']['php']} · WP {n1['env']['wp']} "
          f"· Woo {n1['env']['woo']} · theme {n1['env']['theme_slug']}")
    print(f"   hook cua theme: {len(n1['theme_hooks'])} · tong hook dang ky: {n1['hook_count']}")
    print(f"   file nap: {len(n1['files_after_render'])} · chuoi fire: {len(n1['fire_sequence'])} muc")
    print(f"   chu ky ham: {len(n1['signatures'])} · diem doc superglobal: {len(n1['sanitizers'])}")
    print(f"   HTML sau mask: {len(n1['html_mask'])} ky tu")
    if noise:
        print(f"\n   NOISE_TOO_HIGH: hai luot khong doi code da lech o mat {noise}")
        print("   Phep do chua dung duoc. Phai chuan hoa cac mat nay truoc, hoac them mask")
        print("   KEM LY DO, roi do lai. Khong duoc di tiep: baseline khong on dinh thi moi")
        print("   ket qua 'bat duoc' hay 'bo lot' ben duoi deu vo nghia.")
        for ten in noise:
            ma, mb = bay_mat(n1)[ten], bay_mat(n2)[ten]
            sa = json.dumps(ma, ensure_ascii=False, sort_keys=True)
            sb = json.dumps(mb, ensure_ascii=False, sort_keys=True)
            i = next((k for k in range(min(len(sa), len(sb))) if sa[k] != sb[k]), 0)
            print(f"      · {ten}: lech tu ky tu {i}\n        A: …{sa[max(0,i-60):i+60]}…"
                  f"\n        B: …{sb[max(0,i-60):i+60]}…")
        return 6
    print("   noise = 0 tren ca bay mat. Baseline on dinh, du dieu kien di tiep.")

    # ── 2. SAU CA TIEM
    print("\n[2] Sau ca tiem — moi ca la mot loi refactor that")
    bang = []
    for ca in INJECTIONS:
        p = os.path.join(goc_theme, ca["file"])
        with open(p, encoding="utf-8") as f:
            nguyen = f.read()
        if ca["old"] not in nguyen:
            print(f"   {ca['case_id']}: UNCALIBRATED — khong tim thay moc trong {ca['file']}")
            return 7
        if nguyen.count(ca["old"]) != 1:
            print(f"   {ca['case_id']}: UNCALIBRATED — moc xuat hien "
                  f"{nguyen.count(ca['old'])} lan trong {ca['file']}, phai dung 1")
            return 7
        try:
            with open(p, "w", encoding="utf-8", newline="") as f:
                f.write(nguyen.replace(ca["old"], ca["new"]))
            hong, loi = chup(W, goc_theme)
        finally:
            with open(p, "w", encoding="utf-8", newline="") as f:
                f.write(nguyen)
        if loi:
            print(f"   {ca['case_id']}: {loi}")
            return 5

        bat = lech(n1, hong)
        dat_ky_vong = ca["expect"] in bat
        bang.append({"case_id": ca["case_id"], "name": ca["name"], "caught": bat,
                     "expect": ca["expect"], "passed": bool(bat)})
        dau = "DO " if bat else "XANH"
        print(f"   {dau}  {ca['case_id']:24s} {ca['name']}")
        print(f"         mat bat duoc: {bat if bat else 'KHONG MAT NAO — ca nay la NOT_TESTED'}"
              f"   (cho doi: {ca['expect']}"
              f"{'' if dat_ky_vong else ' — KHONG dung nhu du doan'})")

    # ── 3. KET LUAN
    print("\n" + "=" * 72)
    bat_duoc = [b for b in bang if b["passed"]]
    bo_lot = [b for b in bang if not b["passed"]]
    print(f"Tang 5 bat duoc {len(bat_duoc)}/6 ca. Bo lot {len(bo_lot)}.")
    if bo_lot:
        print("\nCAC LOP VAN LA NOT_TESTED (khong mat nao bat duoc):")
        for b in bo_lot:
            print(f"  · {b['case_id']} — {b['name']}")
        print("\nLane bien doi CHI duoc mo cho loai bien doi nam trong vung da phu.")
    dung_du_doan = [b for b in bang if b["passed"] and b["expect"] in b["caught"]]
    print(f"\nSo ca ma mat DU DOAN truoc bat dung: {len(dung_du_doan)}/6")
    print("=" * 72)
    return 0 if len(bat_duoc) == 6 else 8


if __name__ == "__main__":
    sys.exit(main())
