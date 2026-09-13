#!/usr/bin/env python3
"""KIỂM TÊN — luật đặt tên của repo là luật CỨNG, và đây là chốt giữ nó.

Vì sao có file này
------------------
Kiểm kê ngày 13/09/2026 cho thấy repo nói HAI ngôn ngữ và BA quy ước: `wp-delivery` nói
tiếng Anh (`STATIC_CHECKS_PASSED`, `--write-baseline`, key `pass`/`fail`/`kind`), cleaner
và lane mới nói tiếng Việt (`KHONG_KIEM_DUOC`, `--tien-to`, `file_nap_sau_render`) — và
ngay trong code mới cũng lẫn: `dynamic_unresolved` cạnh `phien_ban`; đếm thì lúc
`so_file`, lúc `hook_tong_so`, lúc `tong_vung_mu`; mặt Tầng 5 thì `chuky` không gạch,
`sanit` cụt.

Bài học lấy từ bảng tham chiếu Liquid của Haravan: MỘT namespace cho mỗi object, tên là
danh từ, hậu tố/tiền tố có nghĩa cố định, và một bảng tra được bằng mắt cho MỌI tên.
Luật ở `CLAUDE.md`, bảng ở `docs/BANG-THAM-CHIEU.md`. File này bắt hai thứ đó khớp code.

Ba việc
-------
  1. Quét mọi TÊN mà code phát ra ngoài: key JSON/dict/array, cờ CLI, mã lý do (UPPER).
  2. Áp luật: snake_case · tiếng Việt không dấu (trừ danh từ kỹ thuật mượn có trong
     allowlist) · đếm là `so_` · tổng là `tong_` · không hậu tố `_count`/`_total`.
  3. Bảng tham chiếu phải PHỦ mọi tên của lane mới — bảng thiếu tên là bảng chết dần.

Ratchet: `tests/ten-baseline.json` ghi số vi phạm ĐANG CÓ của từng file cũ (nợ). File
không có trong baseline thì nợ = 0. Nợ tăng → đỏ. Nợ giảm mà baseline chưa cập nhật →
cũng đỏ, để con số không bao giờ trượt ngược lên. `--cap-nhat` ghi lại baseline.

Tự hiệu chuẩn trước khi tin: gieo ca hỏng đã biết, chốt phải bắt; gieo ca đúng, chốt
phải im. Không đạt thì THUOC_CHUA_HIEU_CHUAN và không kiểm gì cả.

    python tests/kiem_ten.py            # kiểm
    python tests/kiem_ten.py --cap-nhat # ghi lại baseline sau khi TRẢ nợ
"""
import argparse
import io
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GOC = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(GOC)
BASELINE = os.path.join(GOC, "ten-baseline.json")
BANG = os.path.join(REPO, "docs", "BANG-THAM-CHIEU.md")

# File thuộc LANE MỚI: nợ = 0 và bảng tham chiếu phải phủ hết.
LANE_MOI = (
    "skills/code-optimize/scripts",
    "skills/wp-preview-builder/scripts",
    "tests/integration/adn-nen.php",
    "tests/integration/tang5.py",
    "tests/integration/chup_adn.py",
    "tests/integration/doi_theme.php",
)

# Danh từ kỹ thuật MƯỢN — được phép vì repo không có từ Việt nào đang dùng cho chúng, và
# dịch ra sẽ làm người đọc WordPress không nhận ra. Thêm vào đây là một quyết định, phải
# kèm lý do trong commit. Không thêm động từ/tính từ tiếng Anh.
MUON = {
    "hook", "asset", "handle", "nonce", "url", "css", "html", "js", "php", "sha256", "theme",
    "src", "ver", "deps", "extra", "queue", "scripts", "styles", "id", "json", "site", "repo",
    "port", "sanitise", "callback", "graph", "adn", "manifest", "slug", "render", "fire",
    "loader", "template", "cache", "option", "wp", "woo", "closure", "byte", "px", "cr",
    "probe", "protocol", "viewport", "runtime", "backup", "baseline", "clean", "priority",
    "mask", "tab", "class", "utf8", "crlf", "lf", "md", "sql", "http", "https", "ajax", "rest",
    "api", "path", "part", "meta", "post", "page", "shop", "cart", "customer", "widget",
}

# Từ tiếng Anh HAY LỌT — thấy là vi phạm. Cố ý là danh sách, không phải từ điển: chốt
# này bắt những từ đã từng lọt vào repo, và sẽ dài ra theo từng ca thật.
CAM = {
    "count", "total", "size", "check", "checks", "pass", "fail", "passed", "failed", "skip",
    "skipped", "write", "read", "unavailable", "error", "errors", "kind", "required", "must",
    "not", "edges", "nodes", "node", "edge", "dynamic", "unresolved", "static", "quality",
    "gates", "gate", "module", "legacy", "review", "closed", "ok", "version", "limits",
    "limit", "server", "string", "type", "name", "value", "list", "item", "items", "input",
    "output", "result", "results", "status", "message", "enabled", "disabled", "found",
    "missing", "new", "old", "first", "last", "next", "previous", "contain", "applicable",
    "tested", "verified", "production", "computed", "selector", "cookie", "request",
    "unit", "architecture", "large", "too", "grew", "change", "written", "tools", "text",
    "field", "menu", "upload", "credit", "sort", "with", "without",
    # KHONG dua gioi tu ngan vao day: `to`, `by`, `of`, `for`, `so` trung am tiet Viet
    # (`tien_to`, `so_file`). Ca hieu chuan `--tien-to` da bat dung loi nay o lan chay dau.
}

# Key phai dung sau `{`, `,`, `(` hoac o dau dong (sau thut le). Khong co lookbehind nay
# thi `if os.name != "nt":` bi doc thanh key "nt" — ca that o doi_ten.py.
RE_KEY_PY_PHP = re.compile(r"""(?:(?<=[{,(])\s*|(?m:^)[ \t]*)["']([A-Za-z_][A-Za-z0-9_-]*)["']\s*(?::|=>)(?!=)""")
RE_KEY_JS = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(?!:)", re.M)
RE_CO = re.compile(r"""add_argument\(\s*["'](--[A-Za-z0-9-]+)["']""")
# Ma ly do dung DAU chuoi, theo sau la het chuoi, khoang trang, dau `:` hoac `—`. Ban dau
# chi bat chuoi gom DUY NHAT ma → `print("KHONG_KIEM_DUOC: khong thay ...")` va
# `f"STATIC_CHECKS_PASSED — ..."` deu lot, tuc phan lon ma ly do that cua repo khong duoc quet.
RE_MA = re.compile(r"""["']([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)(?=["'\s:—])""")

# key KHÔNG phải tên do repo đặt: superglobal PHP, header HTTP, khoá của WordPress/Composer
BO_QUA_KEY = {
    "HTTP_HOST", "SERVER_NAME", "REQUEST_METHOD", "REQUEST_URI", "SCRIPT_NAME",
    "PYTHONIOENCODING", "function", "accepted_args", "callbacks", "theme-slug", "giai-doan",
    "__main__", "Content-Type", "User-Agent", "Accept-Encoding", "GLOBALS",
    "post_type", "posts_per_page", "DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST",
    # Thuoc tinh trinh duyet, probe bao cao NGUYEN VAN de doi chieu voi DevTools:
    "clientWidth", "innerWidth", "scrollWidth",
}

# Bon nhan bang chung cua repo (xac-minh.md), la tu vung da co truoc luat nay. Giu.
NHAN_BANG_CHUNG = {"CONCEPT_PREVIEW", "VISUAL_PASS", "PRODUCTION_VERIFIED", "NOT_TESTED",
                   "RUNTIME_NOT_TESTED"}


def rel(p):
    return os.path.relpath(p, REPO).replace(os.sep, "/")


def la_lane_moi(r):
    return any(r == x or r.startswith(x + "/") for x in LANE_MOI)


def tach(ten):
    return [t for t in re.split(r"[_-]+", ten.lower()) if t]


def loi_cua_ten(ten, loai):
    """Trả danh sách lý do vi phạm của MỘT tên. Rỗng = hợp lệ."""
    ra = []
    if loai == "co":
        than = ten.lstrip("-")
        if not re.fullmatch(r"[a-z][a-z0-9]*(-[a-z0-9]+)*", than):
            ra.append("co CLI phai kebab-case chu thuong")
    elif loai == "ma":
        if not re.fullmatch(r"[A-Z][A-Z0-9]*(_[A-Z0-9]+)+", ten):
            ra.append("ma ly do phai UPPER_SNAKE")
    else:
        if re.fullmatch(r"[A-Z][A-Z0-9]*(_[A-Z0-9]+)+", ten):
            return loi_cua_ten(ten, "ma")   # key viet HOA la ma ly do dat lam key (LOI_PHEP_DO, CHAN)
        if not re.fullmatch(r"[a-z][a-z0-9]*(_[a-z0-9]+)*", ten):
            ra.append("key phai snake_case chu thuong")
    if ten in NHAN_BANG_CHUNG:
        return ra
    tokens = tach(ten)
    xau = [t for t in tokens if t in CAM]
    if xau:
        ra.append("tu tieng Anh: " + ",".join(xau))
    # Hau to dem/tong: CHI cam dang tieng Anh va anti-pattern `_tong_so` da tung co trong
    # repo (`hook_tong_so`). KHONG cam am tiet `so`/`tong` dung cuoi noi chung — `tham_so`,
    # `chi_so`, `con_so` la tu Viet hop le; lan chay dau cua chot nay da bao sai `tham_so`.
    if tokens and tokens[-1] in ("count", "total") or tokens[-2:] == ["tong", "so"]:
        ra.append("dem/tong phai la TIEN TO so_/tong_, khong phai hau to _count/_total/_tong_so")
    if tokens[:2] == ["so", "luong"]:
        ra.append("dung `so_` thay cho `so_luong_`")
    return ra


def quet_file(p):
    """Trả danh sách (ten, loai, dong) tìm thấy trong một file."""
    return _quet_chuoi(io.open(p, encoding="utf-8", errors="replace").read(),
                       os.path.splitext(p)[1])


def _quet_chuoi(s, duoi=".py"):
    ra = []
    # Bo comment TRUOC khi quet, nhung GIU so dong: thay noi dung comment bang khoang
    # trang cung do dai. `'required' => false` trong comment giai thich regex cua
    # quet_chet.py tung bi doc thanh mot key that.
    def lam_trang(m):
        return re.sub(r"[^\n]", " ", m.group(0))

    if duoi == ".py":
        s = re.sub(r"(?m)^[ \t]*#.*$", lam_trang, s)
        s = re.sub(r'"""[\s\S]*?"""', lam_trang, s)
    else:
        s = re.sub(r"/\*[\s\S]*?\*/", lam_trang, s)
        s = re.sub(r"(?m)(?<![:\\])//.*$", lam_trang, s)

    def dong_cua(i):
        return s.count("\n", 0, i) + 1

    if duoi in (".py", ".php"):
        for m in RE_KEY_PY_PHP.finditer(s):
            k = m.group(1)
            if k in BO_QUA_KEY or k.startswith("--"):
                continue
            ra.append((k, "key", dong_cua(m.start())))
    if duoi == ".js":
        for m in RE_KEY_JS.finditer(s):
            k = m.group(1)
            if k in BO_QUA_KEY or k in ("const", "let", "var", "return", "case", "default"):
                continue
            ra.append((k, "key", dong_cua(m.start())))
    if duoi == ".py":
        for m in RE_CO.finditer(s):
            ra.append((m.group(1), "co", dong_cua(m.start())))
    for m in RE_MA.finditer(s):
        k = m.group(1)
        if k in BO_QUA_KEY:
            continue
        ra.append((k, "ma", dong_cua(m.start())))
    return ra


def liet_ke_file():
    ra = []
    for goc in ("skills", "tests"):
        for dp, dn, fn in os.walk(os.path.join(REPO, goc)):
            dn[:] = [d for d in dn if d not in ("__pycache__", "fixture-theme", "fixture-bien-doi", ".wp-it", "fixtures")]
            for f in fn:
                if f.endswith((".py", ".php", ".js")) and f != os.path.basename(__file__):
                    ra.append(os.path.join(dp, f))
    return sorted(ra)


def trich_ten_trong_bang(bang):
    """Mọi token tên bên trong bất kỳ cặp backtick nào của bảng tham chiếu.

    Bảng viết theo kiểu Haravan — `nut[].loai`, `chua_giai.hook_ten_bien[]`,
    `--graph g.json`, `{sha256, byte}` — nên một tên được coi là CÓ khi nó xuất hiện như một
    token nguyên vẹn trong span, không bắt buộc đứng một mình.
    """
    ra = set()
    for span in re.findall(r"`([^`]+)`", bang):
        ra.update(re.findall(r"(?<![A-Za-z0-9_-])(--?[A-Za-z][A-Za-z0-9_-]*|[A-Za-z_][A-Za-z0-9_]*)", span))
    return ra


def hieu_chuan():
    """Chốt phải bắt ca hỏng đã biết và im ở ca đúng. Ca hỏng lấy từ chính repo."""
    hong = [
        ("dynamic_unresolved", "key"), ("hook_tong_so", "key"), ("STATIC_CHECKS_PASSED", "ma"),
        ("--write-baseline", "co"), ("items_count", "key"), ("so_luong_file", "key"),
        ("camelCase", "key"), ("PROBE_VERSION", "ma"),
    ]
    dung = [
        ("file_nap_sau_render", "key"), ("so_file", "key"), ("KHONG_KIEM_DUOC", "ma"),
        ("--tien-to", "co"), ("chua_giai", "key"), ("hook_theme", "key"), ("sha256", "key"),
        ("PHIEN_BAN_PROBE", "ma"), ("tong_byte", "key"),
        ("tham_so", "key"), ("so_tham_so", "key"), ("KHONG_DOC_DUOC_THAM_SO", "ma"),
        ("LOI_PHEP_DO", "key"), ("NOT_TESTED", "ma"),
    ]
    # phep quet cung phai hieu chuan: `!= "nt":` KHONG phai key; `{"so_file": 1` la key
    if [t for t, l, _ in _quet_chuoi('if os.name != "nt":\n    pass') if l == "key"]:
        return False, "quet nham `!= \"nt\":` thanh key"
    thay = [t for t, l, _ in _quet_chuoi('d = {"so_file": 1,\n     "tong_byte": 2}') if l == "key"]
    if thay != ["so_file", "tong_byte"]:
        return False, "quet thieu key trong dict literal: " + str(thay)
    # phep kiem DO PHU cung phai hieu chuan: dang Haravan `dem.hook_tinh`, `--graph g.json`
    # phai duoc nhan; ten KHONG co trong bang thi phai bao thieu.
    mau_bang = "| `dem.hook_tinh` | | `--graph g.json` | `{sha256, byte}` |"
    co = trich_ten_trong_bang(mau_bang)
    if not {"hook_tinh", "--graph", "sha256", "byte"} <= co:
        return False, "khong nhan duoc ten trong dang Haravan: " + str(sorted(co))
    if "so_vung_mu" in co:
        return False, "bao co ten khong he co trong bang"
    for ten, loai in hong:
        if not loi_cua_ten(ten, loai):
            return False, f"khong bat duoc ca hong: {ten}"
    for ten, loai in dung:
        if loi_cua_ten(ten, loai):
            return False, f"bao sai o ca dung: {ten} -> {loi_cua_ten(ten, loai)}"
    return True, ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap-nhat", action="store_true", help="ghi lai baseline no")
    a = ap.parse_args()

    ok, ly_do = hieu_chuan()
    if not ok:
        print("THUOC_CHUA_HIEU_CHUAN: " + ly_do)
        return 2

    baseline = {}
    if os.path.isfile(BASELINE):
        baseline = json.load(io.open(BASELINE, encoding="utf-8"))

    bang = io.open(BANG, encoding="utf-8").read() if os.path.isfile(BANG) else ""
    # Bang viet theo kieu Haravan — `nut[].loai`, `chua_giai.hook_ten_bien[]`, `--graph g.json`,
    # `{sha256, byte}` — nen mot ten duoc coi la CO trong bang khi no xuat hien nhu mot token
    # nguyen ven ben trong BAT KY cap backtick nao, khong bat buoc dung mot minh.
    ten_trong_bang = trich_ten_trong_bang(bang)

    vi_pham = {}      # file -> [(ten, loai, dong, ly_do)]
    thieu_bang = {}   # file -> [ten]
    da_thay = set()
    for p in liet_ke_file():
        r = rel(p)
        for ten, loai, dong in quet_file(p):
            da_thay.add(ten)
            ly = loi_cua_ten(ten, loai)
            if ly:
                vi_pham.setdefault(r, []).append((ten, loai, dong, "; ".join(ly)))
            if la_lane_moi(r) and ten not in ten_trong_bang and not ly:
                thieu_bang.setdefault(r, []).append(ten)

    dem_moi = {f: len(v) for f, v in vi_pham.items()}
    do = []
    for f, n in sorted(dem_moi.items()):
        cho_phep = baseline.get(f, 0)
        if n > cho_phep:
            do.append((f, n, cho_phep, "NO TANG"))
        elif n < cho_phep and not a.cap_nhat:
            do.append((f, n, cho_phep, "NO GIAM ma baseline chua cap nhat — chay --cap-nhat"))
    for f, cho_phep in sorted(baseline.items()):
        if f not in dem_moi and cho_phep > 0 and not a.cap_nhat:
            do.append((f, 0, cho_phep, "NO GIAM ve 0 ma baseline chua cap nhat"))

    print("=" * 72)
    print("KIEM TEN — luat dat ten cua repo (CLAUDE.md), bang tra o docs/BANG-THAM-CHIEU.md")
    print("=" * 72)
    tong_vi_pham = sum(dem_moi.values())
    tong_no = sum(baseline.values())
    print(f"  ten da quet: {len(da_thay)} · vi pham hien tai: {tong_vi_pham} · no cho phep: {tong_no}")

    if do:
        print("\nRATCHET DO:")
        for f, n, cho_phep, vi_sao in do:
            print(f"  {f}: {n} vi pham, cho phep {cho_phep} — {vi_sao}")
            for ten, loai, dong, ly in vi_pham.get(f, [])[:8]:
                print(f"       :{dong}  {ten}  [{loai}]  {ly}")
    if thieu_bang:
        print("\nBANG THAM CHIEU THIEU TEN (lane moi phai phu het):")
        for f, ds in sorted(thieu_bang.items()):
            print(f"  {f}: {len(ds)} ten — " + ", ".join(sorted(set(ds))[:12])
                  + (" …" if len(set(ds)) > 12 else ""))

    if a.cap_nhat:
        with io.open(BASELINE + ".tmp", "w", encoding="utf-8") as f:
            json.dump(dict(sorted(dem_moi.items())), f, ensure_ascii=False, indent=2)
        os.replace(BASELINE + ".tmp", BASELINE)
        print(f"\nDA GHI baseline: {len(dem_moi)} file, {tong_vi_pham} vi pham duoc khoanh la no")
        return 0

    if not do and not thieu_bang:
        no_lane_moi = sum(n for f, n in dem_moi.items() if la_lane_moi(f))
        print(f"\n  lane moi: {no_lane_moi} vi pham (phai la 0) · file cu: no khong tang")
        print("=" * 72)
        return 0 if no_lane_moi == 0 else 1
    print("=" * 72)
    return 1


if __name__ == "__main__":
    sys.exit(main())
