#!/usr/bin/env python3
"""Quét code chết trong một theme/plugin WordPress. Chỉ ĐỌC, không sửa gì.

Trả lời bốn câu:
  1. File nào không có đường nào dẫn tới từ một điểm vào thật?
  2. File nào ĐĂNG KÝ HOOK nhưng KHÔNG ĐƯỢC NẠP? (nguy hiểm nhất — xem dưới)
  3. Hàm nào định nghĩa xong không nơi nào gọi?
  4. Class CSS nào không còn markup nào sinh ra?

ĐIỂM VÀO là gì (đọc kỹ, bản trước sai chỗ này):
  · file nạp chính (mặc định functions.php) — WordPress luôn chạy nó
  · mọi template ở thư mục gốc theme — WordPress chọn template từ đây
  · mọi override trong woocommerce/
Từ đó lần theo BA loại cạnh: require/include · tên hàm · get_template_part.

Bản trước coi "file có add_action = điểm vào". Luật đó SAI cả hai chiều và đã bị
một fixture tối thiểu bắt: một file chỉ khai constant rồi được require_once vẫn
bị báo chết (vì không có hàm nào để lần theo), còn một file KHÔNG ai nạp nhưng có
add_action lại được coi là sống. Đăng ký hook không làm file tự chạy — phải có ai
đó nạp nó trước đã. Đó chính là mục 2.

Giới hạn phải biết trước khi tin kết quả:
  · require dựng bằng biến (`require $f;`, glob rồi require trong vòng lặp) thì
    phân tích tĩnh không thấy. Tool in ra số require không phân giải được — thấy
    số đó khác 0 thì đừng tin mục 1 nữa.
  · Không thấy tên ghép chuỗi, không thấy hook đăng ký bằng biến.
  · Mục 4 chỉ là DANH SÁCH NGHI NGỜ, phải đối chứng bằng HTML thật —
    xem doi_chung_live.py.
  · Chỉ thấy file có trên đĩa. Plugin không tải về thì không nhìn thấy.

Dùng:
  python quet_chet.py --theme "đường/dẫn/theme"
  python quet_chet.py --theme "..." --loader functions.php --tien-to mytheme_
"""
import argparse
import json
import os
import re
import sys


def doc(p):
    return open(p, encoding="utf-8", errors="replace").read()


def quet_file(theme, duoi=(".php",)):
    ra = []
    for dp, dn, fn in os.walk(theme):
        if any(x in dp.replace(os.sep, "/") for x in ("/node_modules", "/vendor", "/.git")):
            continue
        for f in fn:
            if f.endswith(duoi):
                ra.append(os.path.join(dp, f))
    return ra


def rel(p, theme):
    return os.path.relpath(p, theme).replace(os.sep, "/")


def khong_dau(x):
    """Bỏ comment và chuỗi để đếm/khớp không bị nhiễu."""
    x = re.sub(r"/\*.*?\*/", " ", x, flags=re.S)
    x = re.sub(r"(?m)//.*$", " ", x)
    x = re.sub(r"(?m)^\s*#.*$", " ", x)
    return x


def bo_ghi_chu(s):
    """Bỏ chú thích khỏi PHP/JS trước khi coi phần còn lại là markup.

    Một tên class chỉ được NHẮC TỚI trong chú thích thì không phải markup. Không
    bỏ ra thì chính câu `/* class fx-chet đã bỏ */` giữ cho .fx-chet sống mãi —
    tức là chú thích nói "đã bỏ" lại là thứ ngăn không cho bỏ. Fixture bắt được
    ca này bằng đúng một dòng chú thích.

    Cố ý thô và thận trọng: chỉ bỏ khối /* */ và những DÒNG bắt đầu bằng // # *.
    Không đụng `//` giữa dòng, vì `https://` cũng có nó.
    """
    s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
    giu = ["" if l.lstrip().startswith(("//", "#", "*")) else l for l in s.splitlines()]
    return chr(10).join(giu)

def bo_script(s):
    """Bỏ nội dung mọi khối <script> trước khi tìm hàm PHP.

    File PHP của theme rất hay nhúng JavaScript thẳng vào. Không bỏ ra thì mọi
    `function ten(){...}` của JS bị đếm như hàm PHP, và vì không PHP nào gọi chúng
    nên chúng hiện ra trong danh sách "hàm không ai gọi" — báo động giả, và tệ hơn
    là dụ người ta đi xoá một hàm JS đang chạy.
    """
    return re.sub(r"<script\b[^>]*>.*?</script>", " ", s, flags=re.S | re.I)


def tim_ham(s):
    return re.findall(r"^\s*function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", bo_script(s), re.M)


def co_hook(s):
    return bool(re.search(r"^\s*(?:add_action|add_filter|add_shortcode)\s*\(", khong_dau(s), re.M))


# (?![A-Za-z0-9_]) là chốt sống còn. Thiếu nó thì `required` trong HTML và
# `'required' => false` trong mảng PHP cũng bị khớp thành một câu require: lần
# chạy đầu trên một theme thật ra 25 câu "không phân giải được", 24 trong đó là
# khớp nhầm kiểu này. Con số nhiễu đó tự nó vô hại, nhưng nó làm cảnh báo
# "đừng tin mục 1" bật lên vô cớ — và một cảnh báo bật sai vài lần là một cảnh
# báo người ta thôi đọc.
RE_NAP = re.compile(
    r"\b(?:require|include)(?:_once)?(?![A-Za-z0-9_])\s*(?:\(\s*)?([^;]+?)\s*\)?\s*;", re.I)


def tim_require(s, tu_file, src):
    """Trả về (danh sách file đích phân giải được, số require KHÔNG phân giải được).

    Chấp nhận các dạng hay gặp:
        require_once __DIR__ . '/inc/x.php';
        require_once MY_CONST . '/inc/x.php';
        require_once get_template_directory() . '/inc/x.php';
        require_once 'inc/x.php';
    Cách phân giải cố ý thô: lấy chuỗi trong nháy, bỏ tiền tố, rồi khớp đuôi
    đường dẫn với các file có thật. Thô nhưng KHÔNG im lặng — cái gì không khớp
    được thì đếm vào "không phân giải được" và in ra.
    """
    ra, mu = set(), 0
    for m in RE_NAP.finditer(khong_dau_giu_chuoi(s)):
        bieu = m.group(1)
        chuoi = re.findall(r"'([^']*)'|\"([^\"]*)\"", bieu)
        phan = "".join(a or b for a, b in chuoi).strip()
        if not phan:
            mu += 1
            continue
        phan = phan.lstrip("./").replace("\\", "/")
        ung = [f for f in src if f == phan or f.endswith("/" + phan)]
        if len(ung) == 1:
            ra.add(ung[0])
        elif len(ung) > 1:
            ra.update(ung)          # mơ hồ: nối hết, thà thừa còn hơn báo chết oan
        else:
            mu += 1
    return ra, mu


def khong_dau_giu_chuoi(x):
    """Bỏ comment nhưng GIỮ chuỗi — require cần đọc chuỗi bên trong."""
    x = re.sub(r"/\*.*?\*/", " ", x, flags=re.S)
    x = re.sub(r"(?m)//.*$", " ", x)
    return x


def dung_do_thi(theme, loader):
    php = quet_file(theme, (".php",))
    src = {rel(p, theme): doc(p) for p in php}

    chu = {}
    for f, s in src.items():
        for h in tim_ham(s):
            chu.setdefault(h, f)

    canh = {f: set() for f in src}
    mu_tong = 0
    for f, s in src.items():
        sach = khong_dau(s)
        for ten, g in chu.items():
            if g == f:
                continue
            if re.search(r"(?<![A-Za-z0-9_])" + re.escape(ten) + r"(?![A-Za-z0-9_])", sach):
                canh[f].add(g)
        for m in re.finditer(r"get_template_part\(\s*['\"]([^'\"]+)['\"]"
                             r"(?:\s*,\s*['\"]?([A-Za-z0-9-]*)['\"]?)?", s):
            goc, hau = m.group(1), m.group(2)
            for ung in ([goc + "-" + hau + ".php"] if hau else []) + [goc + ".php"]:
                if ung in src:
                    canh[f].add(ung)
                    break
        nap, mu = tim_require(s, f, src)
        canh[f] |= nap
        mu_tong += mu

    goc = set()
    if loader in src:
        goc.add(loader)
    for f in src:
        if "/" not in f or f.startswith("woocommerce/"):
            goc.add(f)

    thay, ngan = set(), list(goc)
    while ngan:
        f = ngan.pop()
        if f in thay:
            continue
        thay.add(f)
        ngan.extend(canh[f] - thay)

    chet = sorted(set(src) - thay)
    hook_khong_nap = sorted(f for f in chet if co_hook(src[f]))
    return src, chu, canh, chet, hook_khong_nap, mu_tong, (loader in src)


def ham_chet(theme, src, chu, tien_to):
    js = {rel(p, theme): doc(p) for p in quet_file(theme, (".js",))}
    khoi = khong_dau("\n".join(src.values())) + "\n" + "\n".join(js.values())
    ra = []
    for ten, f in sorted(chu.items()):
        if tien_to and not ten.startswith(tuple(tien_to)):
            continue
        n = len(re.findall(r"(?<![A-Za-z0-9_])" + re.escape(ten) + r"(?![A-Za-z0-9_])", khoi))
        if n <= 1:
            ra.append((ten, f))
    return ra


def con_song(c, markup, nho):
    if c in nho:
        return nho[c]

    def co(x):
        return bool(re.search(r"(?<![A-Za-z0-9_-])" + re.escape(x) + r"(?![A-Za-z0-9_-])", markup))

    def co_goc(x):
        """Như co() nhưng KHÔNG chặn ký tự đứng sau.

        Vì gốc tên luôn đứng ngay trước chỗ nối: markup ghi `fx-bac--<?php ... ?>`
        thì sau gốc `fx-bac` là dấu `-`, và lookahead của co() chặn đúng ký tự đó
        -> gốc không bao giờ khớp -> luật bảo vệ hỏng ngay tại chỗ nó sinh ra để
        bảo vệ. Fixture .fx-bac--N bắt được ca này.
        """
        return bool(re.search(r"(?<![A-Za-z0-9_-])" + re.escape(x), markup))
    ok = co(c)
    g = c
    while not ok:
        cat = max(g.rfind("--"), g.rfind("__"))
        if cat <= 0:
            break
        g = g[:cat]
        ok = co_goc(g)
    nho[c] = ok
    return ok


def class_nghi(theme, src, tien_to):
    js = "\n".join(doc(p) for p in quet_file(theme, (".js",)))
    markup = "\n".join(src.values()) + "\n" + js
    nho, ra = {}, {}
    for p in quet_file(theme, (".css",)):
        s = doc(p)
        nghi = [c for c in sorted(set(re.findall(r"\.(-?[A-Za-z_][A-Za-z0-9_-]*)", s)))
                if (not tien_to or c.startswith(tuple(tien_to)))
                and not con_song(c, markup, nho)]
        if nghi:
            ra[rel(p, theme)] = nghi
    return ra


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme", required=True)
    ap.add_argument("--loader", default="functions.php",
                    help="file nạp chính, tính từ gốc theme (mặc định functions.php)")
    ap.add_argument("--tien-to", default="", help="lọc hàm/class theo tiền tố, ngăn bằng dấu phẩy")
    ap.add_argument("--json", default="")
    a = ap.parse_args()

    theme = a.theme.rstrip("/\\")
    tien_to = [x.strip() for x in a.tien_to.split(",") if x.strip()]
    src, chu, canh, chet, hook_kn, mu, co_loader = dung_do_thi(theme, a.loader)

    print(f"THEME  {theme}")
    print(f"       {len(src)} file PHP · {len(chu)} hàm · loader `{a.loader}` "
          f"{'tìm thấy' if co_loader else '*** KHÔNG TÌM THẤY ***'}\n")

    if not co_loader:
        print("!! Không thấy file nạp chính. Nếu theme dùng tên khác, truyền --loader.")
        print("!! Chưa có nó thì mục 1 và 2 gần như chắc chắn sai — dừng đọc ở đây.\n")
    if mu:
        print(f"!! {mu} câu require/include KHÔNG phân giải được (đường dẫn dựng bằng biến).")
        print("!! Mỗi câu như vậy là một cạnh đồ thị bị thiếu — mục 1 có thể báo chết oan.\n")

    print("=" * 74)
    print("1. FILE KHÔNG CÓ ĐƯỜNG NÀO DẪN TỚI")
    print("=" * 74)
    tong = sum(len(src[f].splitlines()) for f in chet)
    for f in chet:
        print(f"   {f:52s} {len(src[f].splitlines()):5d} dòng")
    print(f"   -> {len(chet)} file / {tong} dòng" if chet else "   (không có)")

    print()
    print("=" * 74)
    print("2. FILE ĐĂNG KÝ HOOK NHƯNG KHÔNG ĐƯỢC NẠP")
    print("=" * 74)
    if hook_kn:
        for f in hook_kn:
            print(f"   {f}")
        print(f"   -> {len(hook_kn)} file")
        print("   Đây là loại nguy hiểm nhất: nhìn code tưởng tính năng đang chạy, thực tế")
        print("   không. Hoặc tính năng đang TẮT mà không ai biết, hoặc là rác. Cả hai đều")
        print("   phải xử lý, đừng để nguyên.")
    else:
        print("   (không có)")

    print()
    print("=" * 74)
    print("3. HÀM ĐỊNH NGHĨA NHƯNG KHÔNG NƠI NÀO GỌI")
    print("=" * 74)
    hc = ham_chet(theme, src, chu, tien_to)
    for ten, f in hc:
        print(f"   {ten:44s} {f}")
    print(f"   -> {len(hc)} hàm" if hc else "   (không có)")

    print()
    print("=" * 74)
    print("4. CLASS CSS NGHI CHẾT — PHẢI ĐỐI CHỨNG BẰNG HTML THẬT TRƯỚC KHI XOÁ")
    print("=" * 74)
    cn = class_nghi(theme, src, tien_to)
    for f, ds in sorted(cn.items()):
        print(f"   {f}: {len(ds)} class")
        for c in ds[:12]:
            print(f"      .{c}")
        if len(ds) > 12:
            print(f"      … và {len(ds)-12} class nữa")
    if not cn:
        print("   (không có)")

    print()
    print("ĐỌC KẾT QUẢ CHO ĐÚNG")
    print("  · Mục 1 chỉ đáng tin khi loader tìm thấy VÀ số require không phân giải được")
    print("    bằng 0. Hai dòng đó in ở đầu, đọc trước khi đọc danh sách.")
    print("  · Mục 4 CHỈ LÀ NGHI NGỜ — phân tích tĩnh mù trước markup do plugin sinh ra.")
    print("    Chạy doi_chung_live.py trên URL thật trước khi xoá bất cứ thứ gì.")
    print("  · Xoá xong phải QUÉT LẠI: xoá file làm chết thêm hàm ở file khác.")

    if a.json:
        json.dump({"file_chet": chet, "hook_khong_nap": hook_kn, "ham_chet": hc,
                   "class_nghi": cn, "require_khong_phan_giai": mu, "co_loader": co_loader},
                  open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"\nđã ghi {a.json}")

    return 1 if (chet or hook_kn or hc) else 0


if __name__ == "__main__":
    sys.exit(main())
