#!/usr/bin/env python3
"""Dựng CODE NODES — đồ thị GIẢ THUYẾT của một theme/plugin WordPress. Chỉ ĐỌC.

Vì sao gọi là GIẢ THUYẾT, không gọi là đồ thị
---------------------------------------------
Đồ thị này dựng bằng phân tích tĩnh, và phân tích tĩnh MÙ trước đúng thứ nối
WordPress lại với nhau: hook là một CHUỖI. `add_action( $ten, $cb )` không cho biết
gì; `add_action( 'wp_ajax_' . $act, ... )` cũng vậy. Đã kiểm bằng cách đọc source
của các tool hiện có, không bằng cách đọc mô tả: không một tool tĩnh nào đang được
bảo trì giải được cạnh đó — `wp-hooks/generator` chỉ bắt `do_action`/`apply_filters`
(phía PHÁT hook), `wp-hook-check` thì cố tình bỏ qua hook tên biến.

Nên file này KHÔNG tự nhận là nguồn sự thật. Nó phát biểu một giả thuyết, và
`cong_graph.py` đối chứng giả thuyết đó với ADN chụp từ một WordPress đang chạy.
Khoảng lệch giữa hai bên được IN RA, không được ẩn đi — một đồ thị sai mà tự tin
còn tệ hơn không có đồ thị, vì nó làm người ta xoá code đang chạy với cảm giác có
cơ sở.

Khác `quet_chet.py` ở đâu
-------------------------
`quet_chet.py` dựng `canh = {file: set(file)}` để trả lời "file nào không ai dẫn
tới" rồi BỎ đồ thị đi — `--json` của nó chỉ ghi kết luận, không ghi nodes/edges.
File này giữ đồ thị lại, ở mức chi tiết hơn: node là file · hàm · hook · handle
asset, và cạnh có KIỂU. Hai tool trả lời hai câu khác nhau, nên để cạnh nhau chứ
không gộp: `quet_chet.py` hỏi "cái gì chết", file này hỏi "cái gì nối với cái gì".

Mọi thứ không phân giải được thì ĐẾM VÀO `dynamic_unresolved`, không đoán. Con số
đó là thước đo độ tin cậy của chính đồ thị: nó khác 0 nghĩa là có cạnh bị thiếu, và
mọi kết luận kiểu "không ai gọi" phải đọc kèm con số ấy.

    python code_nodes.py --theme "duong/dan/theme" [--ra graph.json]
"""
import argparse
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BO_QUA_TM = ("/node_modules", "/vendor", "/.git")


def doc(p):
    return open(p, encoding="utf-8", errors="replace").read()


def rel(p, goc):
    return os.path.relpath(p, goc).replace(os.sep, "/")


def quet_file(goc, duoi):
    ra = []
    for dp, _dn, fn in os.walk(goc):
        if any(x in dp.replace(os.sep, "/") for x in BO_QUA_TM):
            continue
        for f in sorted(fn):
            if f.endswith(duoi):
                ra.append(os.path.join(dp, f))
    return sorted(ra)


def bo_ghi_chu_giu_chuoi(x):
    """Bỏ comment, GIỮ chuỗi — mọi cạnh ở đây nằm trong chuỗi nên không được bỏ chuỗi."""
    x = re.sub(r"/\*.*?\*/", " ", x, flags=re.S)
    x = re.sub(r"(?m)//.*$", " ", x)
    return x


def bo_script(s):
    """Bỏ khối <script> trước khi tìm hàm PHP.

    Không bỏ thì mọi `function ten(){}` của JavaScript bị đếm như hàm PHP. Bài học
    này đã có commit riêng trong repo (`fix(quet_chet): đừng đếm hàm JavaScript
    trong <script> của file PHP như hàm PHP`) nên đừng học lại lần hai.
    """
    return re.sub(r"<script\b[^>]*>.*?</script>", " ", s, flags=re.S | re.I)


# Lookahead (?![A-Za-z0-9_]) là chốt sống còn, mượn nguyên từ quet_chet.py: thiếu nó
# thì `required` trong HTML và `'required' => false` trong mảng PHP cũng khớp thành
# một câu require. Lần chạy đầu của quet_chet trên theme thật ra 25 câu "không phân
# giải được", 24 trong đó là khớp nhầm kiểu này.
RE_NAP = re.compile(
    r"\b(?:require|include)(?:_once)?(?![A-Za-z0-9_])\s*(?:\(\s*)?([^;]+?)\s*\)?\s*;", re.I)

RE_HAM = re.compile(r"^[ \t]*function[ \t]+([A-Za-z_][A-Za-z0-9_]*)[ \t]*\(", re.M)

# add_action / add_filter / add_shortcode: bắt cả ca phân giải được lẫn ca không.
RE_DANG_KY = re.compile(
    r"\b(add_action|add_filter|add_shortcode)\s*\(\s*([^,)]+?)\s*,\s*([^,)]+?)\s*"
    r"(?:,\s*([^,)]+?)\s*)?(?:,\s*([^,)]+?)\s*)?\)")

RE_PHAT = re.compile(
    r"\b(do_action|apply_filters|do_action_ref_array|apply_filters_ref_array)\s*\(\s*([^,)]+)")

# ĐỪNG cố bắt cả một lời gọi nhiều tham số bằng MỘT regex. Hai ca đã trả giá ngay
# trong lúc viết file này:
#
#   · `([^,)]+?)` lazy đứng trước cái đuôi toàn optional khớp đúng MỘT ký tự rồi dừng,
#     nên handle `'fxb-main'` bị bắt thành dấu `'`. Hậu quả không phải một lỗi ồn ào
#     mà là `dynamic_unresolved` phồng lên 2 vì lỗi của chính tool — tức con số đo độ
#     tin cậy của đồ thị bị chính tool làm cho vô dụng.
#   · Đổi sang `[^,()]+` greedy thì handle đúng, nhưng tham số `src` là
#     `get_template_directory_uri() . '...'` có dấu ngoặc, nên char class dừng giữa
#     tham số và mảng dependency không bao giờ được đọc — cạnh `phu_thuoc` im lặng
#     biến mất. Lần này tool không báo mù ở đâu cả: nó báo `dynamic_unresolved = 0`
#     trong khi đang thiếu cạnh. Đó là hướng nguy hiểm.
#
# Cách đúng là cách repo này đã dùng ở `go_ham.py` và `go_css.py`: CẮT THEO CÂN BẰNG
# NGOẶC, có xử lý chuỗi và comment. Chỉ dùng regex để tìm ĐIỂM MỞ của lời gọi.
RE_MO_ENQUEUE = re.compile(r"\bwp_(?:enqueue|register)_(script|style)\s*\(")
RE_MO_DANG_KY = re.compile(r"\b(add_action|add_filter|add_shortcode)\s*\(")


def tach_tham_so(s, i_mo):
    """Tách danh sách tham số của một lời gọi, bắt đầu từ chỉ số dấu `(`.

    Trả (danh sách tham số đã strip, chỉ số sau dấu `)` đóng) hoặc (None, None) nếu
    ngoặc không cân bằng — không cân bằng thì NÓI là không đọc được, không đoán.

    Tôn trọng: chuỗi nháy đơn/kép (kèm escape), và ngoặc lồng. Không xử lý heredoc —
    10up khuyên tránh Heredoc/Nowdoc vì nó phá late escaping, và ở đây nó cũng phá
    phép cắt này; gặp heredoc trong tham số thì ngoặc sẽ lệch và hàm trả None, đúng
    như mong muốn.
    """
    if i_mo >= len(s) or s[i_mo] != "(":
        return None, None
    sau, muc, tham_so, hien_tai = i_mo + 1, 1, [], []
    nhay = None
    i = sau
    while i < len(s):
        c = s[i]
        if nhay:
            hien_tai.append(c)
            if c == "\\":
                if i + 1 < len(s):
                    hien_tai.append(s[i + 1])
                    i += 2
                    continue
            elif c == nhay:
                nhay = None
            i += 1
            continue
        if c in "'\"":
            nhay = c
            hien_tai.append(c)
        elif c in "([{":
            muc += 1
            hien_tai.append(c)
        elif c in ")]}":
            muc -= 1
            if muc == 0:
                tham_so.append("".join(hien_tai).strip())
                return [t for t in tham_so], i + 1
            hien_tai.append(c)
        elif c == "," and muc == 1:
            tham_so.append("".join(hien_tai).strip())
            hien_tai = []
        else:
            hien_tai.append(c)
        i += 1
    return None, None

RE_TEMPLATE_PART = re.compile(
    r"get_template_part\(\s*(['\"][^'\"]+['\"]|[^,)]+)"
    r"(?:\s*,\s*(['\"][^'\"]*['\"]|[^,)]+))?")

RE_CHUOI = re.compile(r"^\s*'([^']*)'\s*$|^\s*\"([^\"]*)\"\s*$")


def chuoi_thuan(bieu):
    """Trả chuỗi nếu biểu thức là MỘT literal thuần, ngược lại None.

    Cố ý nghiêm: `'wp_ajax_' . $act` trả None, `$ten` trả None. Đoán ở đây là đúng
    cách sinh ra một cạnh không tồn tại — và một cạnh bịa thì tệ hơn một cạnh thiếu,
    vì cạnh thiếu làm ta thận trọng còn cạnh bịa làm ta tự tin.
    """
    m = RE_CHUOI.match(bieu or "")
    if not m:
        return None
    return m.group(1) if m.group(1) is not None else m.group(2)


def so_nguyen_thuan(bieu):
    b = (bieu or "").strip()
    return int(b) if re.fullmatch(r"-?\d+", b) else None


def giai_require(bieu, danh_sach_file):
    """Phân giải một câu require về file đích. Thô nhưng KHÔNG im lặng.

    Lấy mọi chuỗi trong nháy, nối lại, rồi khớp ĐUÔI đường dẫn với file có thật.
    Khớp nhiều file thì nối hết — thà thừa cạnh còn hơn báo chết oan.
    """
    chuoi = re.findall(r"'([^']*)'|\"([^\"]*)\"", bieu)
    phan = "".join(a or b for a, b in chuoi).strip()
    if not phan:
        return []
    phan = phan.lstrip("./").replace("\\", "/")
    return [f for f in danh_sach_file if f == phan or f.endswith("/" + phan)]


def dung(goc_theme):
    php = {rel(p, goc_theme): doc(p) for p in quet_file(goc_theme, (".php",))}
    ten_file = sorted(php)

    # hàm -> file khai báo
    khai_ham = {}
    for f, s in php.items():
        for h in RE_HAM.findall(bo_script(s)):
            khai_ham.setdefault(h, f)

    nodes = {}
    edges = []
    chua_giai = {
        "require_bien": [],
        "hook_ten_bien": [],
        "callback_bien": [],
        "handle_bien": [],
        "template_part_bien": [],
    }

    def node(nid, loai, **thuoc_tinh):
        if nid not in nodes:
            nodes[nid] = {"id": nid, "loai": loai, **thuoc_tinh}
        return nid

    def canh(tu, den, loai, f, dong, chac_chan=True, ghi_chu=None):
        edges.append({"tu": tu, "den": den, "loai": loai,
                      "nguon": f, "dong": dong, "chac_chan": chac_chan,
                      **({"ghi_chu": ghi_chu} if ghi_chu else {})})

    def so_dong(s, vi_tri):
        return s.count("\n", 0, vi_tri) + 1

    for f, s in php.items():
        node("file:" + f, "file", duong_dan=f, so_dong=len(s.splitlines()))

    for ten, f in khai_ham.items():
        node("ham:" + ten, "ham", khai_o=f)
        canh("file:" + f, "ham:" + ten, "khai_bao", f, None)

    for f, s in php.items():
        sach = bo_ghi_chu_giu_chuoi(s)

        # ── require / include
        for m in RE_NAP.finditer(sach):
            dich = giai_require(m.group(1), ten_file)
            if dich:
                for d in dich:
                    canh("file:" + f, "file:" + d, "require", f, so_dong(sach, m.start()),
                         chac_chan=len(dich) == 1,
                         ghi_chu=None if len(dich) == 1 else "mo ho: khop nhieu file")
            else:
                chua_giai["require_bien"].append(
                    {"file": f, "dong": so_dong(sach, m.start()),
                     "bieu_thuc": m.group(1).strip()[:90]})

        # ── gọi hàm
        khong_chuoi = re.sub(r"'[^']*'|\"[^\"]*\"", " ", bo_script(sach))
        for ten, g in khai_ham.items():
            if g == f:
                continue
            if re.search(r"(?<![A-Za-z0-9_$>])" + re.escape(ten) + r"\s*\(", khong_chuoi):
                canh("file:" + f, "ham:" + ten, "goi", f, None)

        # ── đăng ký hook: ĐÂY là cạnh mà không tool tĩnh nào giải được trọn vẹn
        for m in RE_MO_DANG_KY.finditer(sach):
            ham_dk = m.group(1)
            tham_so, _ = tach_tham_so(sach, m.end() - 1)
            dong = so_dong(sach, m.start())
            if tham_so is None or len(tham_so) < 2:
                chua_giai["callback_bien"].append(
                    {"file": f, "dong": dong, "ham": ham_dk,
                     "bieu_thuc": "KHONG_DOC_DUOC_THAM_SO"})
                continue
            bieu_hook = tham_so[0]
            bieu_cb = tham_so[1]
            bieu_ut = tham_so[2] if len(tham_so) > 2 else None
            ten_hook = chuoi_thuan(bieu_hook)
            ten_cb = chuoi_thuan(bieu_cb)
            uu_tien = so_nguyen_thuan(bieu_ut) if bieu_ut else (10 if ham_dk != "add_shortcode" else None)

            if ten_hook is None:
                chua_giai["hook_ten_bien"].append(
                    {"file": f, "dong": dong, "bieu_thuc": bieu_hook.strip()[:90],
                     "ham": ham_dk})
            if ten_cb is None:
                chua_giai["callback_bien"].append(
                    {"file": f, "dong": dong, "bieu_thuc": bieu_cb.strip()[:90],
                     "ham": ham_dk})
            if ten_hook is None or ten_cb is None:
                continue

            node("hook:" + ten_hook, "hook", ten=ten_hook)
            node("ham:" + ten_cb, "ham", khai_o=khai_ham.get(ten_cb))
            canh("hook:" + ten_hook, "ham:" + ten_cb, "dang_ky", f, dong,
                 ghi_chu=f"{ham_dk} p{uu_tien}" if uu_tien is not None else ham_dk)
            canh("file:" + f, "hook:" + ten_hook, "dang_ky_tu", f, dong)

        # ── phát hook
        for m in RE_PHAT.finditer(sach):
            ten_hook = chuoi_thuan(m.group(2))
            dong = so_dong(sach, m.start())
            if ten_hook is None:
                chua_giai["hook_ten_bien"].append(
                    {"file": f, "dong": dong, "bieu_thuc": m.group(2).strip()[:90],
                     "ham": m.group(1)})
                continue
            node("hook:" + ten_hook, "hook", ten=ten_hook)
            canh("file:" + f, "hook:" + ten_hook, "phat", f, dong, ghi_chu=m.group(1))

        # ── asset handle + dependency
        for m in RE_MO_ENQUEUE.finditer(sach):
            loai_asset = m.group(1)
            tham_so, _ = tach_tham_so(sach, m.end() - 1)
            dong = so_dong(sach, m.start())
            if not tham_so:
                chua_giai["handle_bien"].append(
                    {"file": f, "dong": dong, "bieu_thuc": "KHONG_DOC_DUOC_THAM_SO"})
                continue
            bieu_handle = tham_so[0]
            bieu_deps = tham_so[2] if len(tham_so) > 2 else None
            handle = chuoi_thuan(bieu_handle)
            if handle is None:
                chua_giai["handle_bien"].append(
                    {"file": f, "dong": dong, "bieu_thuc": (bieu_handle or "").strip()[:90]})
                continue
            node("asset:" + handle, "asset", ten=handle, kieu=loai_asset)
            canh("file:" + f, "asset:" + handle, "enqueue", f, dong, ghi_chu=loai_asset)
            for d in re.findall(r"'([^']*)'|\"([^\"]*)\"", bieu_deps or ""):
                ten_dep = d[0] or d[1]
                if ten_dep:
                    node("asset:" + ten_dep, "asset", ten=ten_dep, kieu=loai_asset)
                    canh("asset:" + handle, "asset:" + ten_dep, "phu_thuoc", f, dong)

        # ── template part
        for m in RE_TEMPLATE_PART.finditer(sach):
            dong = so_dong(sach, m.start())
            goc_part = chuoi_thuan(m.group(1))
            hau = chuoi_thuan(m.group(2)) if m.group(2) else None
            if goc_part is None:
                chua_giai["template_part_bien"].append(
                    {"file": f, "dong": dong, "bieu_thuc": m.group(1).strip()[:90]})
                continue
            ung_vien = ([goc_part + "-" + hau + ".php"] if hau else []) + [goc_part + ".php"]
            tim_thay = next((u for u in ung_vien if u in php), None)
            if tim_thay:
                canh("file:" + f, "file:" + tim_thay, "template_part", f, dong)
            else:
                chua_giai["template_part_bien"].append(
                    {"file": f, "dong": dong,
                     "bieu_thuc": goc_part + (("-" + hau) if hau else ""),
                     "ghi_chu": "khong tim thay file dich"})

    tong_chua_giai = sum(len(v) for v in chua_giai.values())
    return {
        "phien_ban": 1,
        "theme": os.path.basename(goc_theme.rstrip("/\\")),
        "nodes": [nodes[k] for k in sorted(nodes)],
        "edges": sorted(edges, key=lambda e: (e["loai"], e["tu"], e["den"], e["dong"] or 0)),
        "dynamic_unresolved": chua_giai,
        "dynamic_unresolved_tong": tong_chua_giai,
    }


def in_ra(g):
    theo_loai = {}
    for n in g["nodes"]:
        theo_loai[n["loai"]] = theo_loai.get(n["loai"], 0) + 1
    canh_loai = {}
    for e in g["edges"]:
        canh_loai[e["loai"]] = canh_loai.get(e["loai"], 0) + 1

    print("=" * 72)
    print(f"CODE NODES — giả thuyết tĩnh cho `{g['theme']}`")
    print("=" * 72)
    print(f"  node: {len(g['nodes'])}   " +
          " · ".join(f"{k} {v}" for k, v in sorted(theo_loai.items())))
    print(f"  cạnh: {len(g['edges'])}   " +
          " · ".join(f"{k} {v}" for k, v in sorted(canh_loai.items())))

    t = g["dynamic_unresolved_tong"]
    print()
    if t == 0:
        print("  dynamic_unresolved = 0")
        print("  Không có cạnh nào bị thiếu vì lý do phân tích tĩnh. Nhưng ĐỪNG đọc con số")
        print("  này thành 'đồ thị đúng': nó chỉ nói 'không có chỗ nào tôi BIẾT là mình mù'.")
        print("  Chốt duy nhất nói được đồ thị có đúng hay không là cong_graph.py, đối chứng")
        print("  với ADN chụp từ WordPress đang chạy.")
    else:
        print(f"  !! dynamic_unresolved = {t} — mỗi mục là một CẠNH BỊ THIẾU")
        for k, v in g["dynamic_unresolved"].items():
            if not v:
                continue
            print(f"     {k}: {len(v)}")
            for m in v[:6]:
                print(f"        {m['file']}:{m.get('dong')}  {m.get('bieu_thuc')}")
            if len(v) > 6:
                print(f"        … và {len(v)-6} mục nữa")
        print("  Còn con số này khác 0 thì mọi kết luận kiểu 'không ai gọi' phải đọc KÈM nó.")
    print("=" * 72)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme", required=True)
    ap.add_argument("--ra", default="", help="ghi graph ra file JSON")
    a = ap.parse_args()

    goc = a.theme.rstrip("/\\")
    if not os.path.isdir(goc):
        print("KHONG_KIEM_DUOC: khong thay thu muc " + goc)
        return 4

    g = dung(goc)
    in_ra(g)
    if a.ra:
        os.makedirs(os.path.dirname(os.path.abspath(a.ra)), exist_ok=True)
        tmp = a.ra + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(g, f, ensure_ascii=False, indent=2)
        os.replace(tmp, a.ra)
        print("đã ghi " + a.ra)
    return 0


if __name__ == "__main__":
    sys.exit(main())
