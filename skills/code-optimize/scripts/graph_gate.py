#!/usr/bin/env python3
"""CỔNG GRAPH — đối chứng đồ thị TĨNH với ADN chụp từ WordPress đang chạy.

Đây là cổng trung thực của cả lane tối ưu, và nó tồn tại vì một lý do rất cụ thể:
**một đồ thị sai mà tự tin thì tệ hơn không có đồ thị.** Không có đồ thị thì người ta
thận trọng. Có một đồ thị sai thì người ta xoá code đang chạy với cảm giác đã kiểm.

Nên ở đây đồ thị tĩnh không được coi là sự thật. Nó là GIẢ THUYẾT, và ADN runtime là
thứ phủ định hoặc xác nhận nó. Khoảng lệch giữa hai bên được IN RA thành số, không
được làm tròn thành "đồ thị đúng".

Hai chiều lệch, và chúng KHÔNG đối xứng
---------------------------------------
Lấy nguyên tinh thần bất đối xứng mà `tests/integration/test_integration.py` đã dựng
cho bộ quét, vì lý do ở đây y hệt:

  · **CHỈ RUNTIME CÓ** — tĩnh mù. Đây là chiều CHÍ MẠNG. Một cạnh thật mà đồ thị không
    thấy nghĩa là node ở đầu cạnh đó trông như mồ côi. Tin theo là xoá code đang chạy.
  · **CHỈ TĨNH CÓ** — tĩnh nói quá. Đây là chiều NHẸ HƠN nhưng vẫn phải báo: nó làm
    người ta tưởng một thứ đang được nối trong khi thực tế không, nên tưởng một tính
    năng đang chạy trong khi nó đã chết im lặng. Đúng họ lỗi `SILENT_OFF` mà
    `doi_chung_live.py --loader` đã phải thêm ở v0.4.0.

FAIL-CLOSED. Có cạnh ở chiều chí mạng thì thoát khác 0 với `GRAPH_UNTRUSTED`.
Không có khái niệm "gần đúng". Repo này đã trả giá hai lần cho fail-open — một lần ở
v0.2.0 và một lần TÁI PHÁT trong chính code viết ra để chống nó ở v0.4.0 — nên mặc
định ở đây là chặn, và muốn đi tiếp thì phải khai số vùng mù một cách tường minh.

    python graph_gate.py --graph graph.json --dna adn.json [--out trust.json]
                         [--accept-blind N]
"""
import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def doc_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────────────────────
# MẶT 1 — cạnh đăng ký hook
# ─────────────────────────────────────────────────────────────────────────────
def static_hooks(g):
    """(hook, priority, callback) từ cạnh `registration` của đồ thị tĩnh."""
    ra = set()
    for e in g["edges"]:
        if e["kind"] != "registration":
            continue
        hook = e["from"].split(":", 1)[1]
        cb = e["to"].split(":", 1)[1]
        ghi = e.get("note") or ""
        priority = None
        for phan in ghi.split():
            if phan.startswith("p") and phan[1:].lstrip("-").isdigit():
                priority = int(phan[1:])
        ra.add((hook, priority, cb))
    return ra


def runtime_hooks(adn):
    """(hook, priority, callback) từ ADN. Bỏ phần thứ tự — cổng này hỏi CÓ/KHÔNG, không hỏi thứ tự.

    Thứ tự là việc của Tầng 5 (`tier5.py`), không phải của cổng này. Gộp hai câu hỏi
    vào một phép kiểm là cách chắc nhất để không trả lời được câu nào.
    """
    return {(h["hook"], h["priority"], h["callback"]) for h in adn["theme_hooks"]}


# ─────────────────────────────────────────────────────────────────────────────
# MẶT 2 — file thực sự được nạp
# ─────────────────────────────────────────────────────────────────────────────
def file_tinh_toi_duoc(g):
    """Tập file mà đồ thị tĩnh cho là tới được, lần theo `require` và `template_part`.

    Gốc lấy đúng như `quet_chet.py`: file nạp chính, cộng MỌI template ở thư mục gốc
    theme (WordPress chọn template từ đó), cộng override trong `woocommerce/`.
    """
    canh = {}
    moi_file = set()
    for n in g["nodes"]:
        if n["kind"] == "file":
            moi_file.add(n["path"])
            canh.setdefault(n["path"], set())
    for e in g["edges"]:
        if e["kind"] in ("require", "template_part"):
            canh.setdefault(e["from"].split(":", 1)[1], set()).add(e["to"].split(":", 1)[1])

    goc = {f for f in moi_file if "/" not in f or f.startswith("woocommerce/")}
    goc |= {"functions.php"} & moi_file

    thay, ngan = set(), list(goc)
    while ngan:
        f = ngan.pop()
        if f in thay:
            continue
        thay.add(f)
        ngan.extend(canh.get(f, set()) - thay)
    return thay


# ─────────────────────────────────────────────────────────────────────────────
# MẶT 3 — handle asset do theme đăng ký
# ─────────────────────────────────────────────────────────────────────────────
def static_assets(g):
    return {e["to"].split(":", 1)[1] for e in g["edges"] if e["kind"] == "enqueue"}


def runtime_assets(adn):
    ra = set()
    for nhom in ("scripts", "styles"):
        for m in adn[nhom]["theme"]:
            ra.add(m["handle"])
    return ra


def de_ghi(bo):
    """Đưa một tập về dạng JSON ghi được, thứ tự ổn định để diff giữa hai lần chạy có nghĩa."""
    return [list(x) if isinstance(x, tuple) else x for x in sorted(bo, key=str)]


def in_nhom(ten, chi_mieu_ta, muc, bo, gioi_han=10):
    print(f"\n  {muc}  {ten}: {len(bo)}")
    if chi_mieu_ta:
        print(f"        {chi_mieu_ta}")
    for x in sorted(bo, key=lambda v: str(v))[:gioi_han]:
        print(f"        · {x}")
    if len(bo) > gioi_han:
        print(f"        … và {len(bo) - gioi_han} mục nữa")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--graph", required=True, help="JSON do code_nodes.py ghi")
    ap.add_argument("--dna", required=True, help="JSON do dna.php chụp")
    ap.add_argument("--out", default="", help="ghi graph-trust.json")
    ap.add_argument("--accept-blind", type=int, default=0,
                    help="so vung mu DA KHAI va chap nhan; khac 0 thi phai giai trinh")
    a = ap.parse_args()

    for p in (a.graph, a.dna):
        if not os.path.isfile(p):
            print("NOT_CHECKABLE: khong thay " + p)
            return 4

    g = doc_json(a.graph)
    adn = doc_json(a.dna)

    ht, hr = static_hooks(g), runtime_hooks(adn)
    ft, fr = file_tinh_toi_duoc(g), set(adn["files_after_render"])
    at, ar = static_assets(g), runtime_assets(adn)

    chi_mu = {
        "hook": hr - ht,
        "file": fr - ft,
        "assets": ar - at,
    }
    static_only = {
        "hook": ht - hr,
        "file": ft - fr,
        "assets": at - ar,
    }
    tong_mu = sum(len(v) for v in chi_mu.values())
    overclaim_count = sum(len(v) for v in static_only.values())

    print("=" * 72)
    print("CỔNG GRAPH — giả thuyết tĩnh đối chứng ADN runtime")
    print("=" * 72)
    print(f"  theme: {g['theme']}   ·   môi trường: PHP {adn['env']['php']} · "
          f"WP {adn['env']['wp']} · Woo {adn['env']['woo']}")
    print(f"  cạnh hook   tĩnh {len(ht):4d}  runtime {len(hr):4d}")
    print(f"  file nạp    tĩnh {len(ft):4d}  runtime {len(fr):4d}")
    print(f"  handle asset tĩnh {len(at):3d}  runtime {len(ar):4d}")
    print(f"  unresolved mà chính đồ thị tĩnh tự khai: {g['unresolved_count']}")

    if tong_mu:
        print("\n" + "-" * 72)
        print("CHIỀU CHÍ MẠNG — runtime CÓ mà đồ thị tĩnh KHÔNG THẤY")
        print("Mỗi cạnh ở đây là một node trông như mồ côi nhưng đang chạy thật.")
        print("-" * 72)
        for ten, bo in chi_mu.items():
            if bo:
                in_nhom(ten, "tin theo đồ thị tĩnh ở đây là xoá code đang chạy", "!!", bo)

    if overclaim_count:
        print("\n" + "-" * 72)
        print("CHIỀU NHẸ HƠN — đồ thị tĩnh NÓI CÓ mà runtime KHÔNG CÓ")
        print("Không chí mạng, nhưng đây là họ lỗi SILENT_OFF: nhìn code tưởng tính năng")
        print("đang chạy, thực tế không. Phải xử lý, đừng để nguyên.")
        print("-" * 72)
        for ten, bo in static_only.items():
            if bo:
                in_nhom(ten, None, " ·", bo)

    ket_qua = {
        "version": 1,
        "theme": g["theme"],
        "env": adn["env"],
        "counts": {
            "static_hooks": len(ht), "runtime_hooks": len(hr),
            "static_files": len(ft), "runtime_files": len(fr),
            "static_assets": len(at), "runtime_assets": len(ar),
            "unresolved": g["unresolved_count"],
        },
        "runtime_only": {k: de_ghi(v) for k, v in chi_mu.items()},
        "static_only": {k: de_ghi(v) for k, v in static_only.items()},
        "blind_spot_count": tong_mu,
        "overclaim_count": overclaim_count,
    }
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        tmp = a.out + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(ket_qua, f, ensure_ascii=False, indent=2)
        os.replace(tmp, a.out)
        print("\nđã ghi " + a.out)

    print("\n" + "=" * 72)
    if tong_mu == 0:
        print("GRAPH_TRUSTED — 0 vùng mù ở chiều chí mạng.")
        print("Đọc cho đúng: điều này chỉ đúng VỚI TẬP URL và giai đoạn đã chụp. Bề mặt cần")
        print("đăng nhập, cần giỏ có hàng, hay luồng AJAX/REST chưa được chụp thì vẫn là")
        print("NOT_TESTED — đồ thị không được coi là đã kiểm ở những chỗ đó.")
        print("=" * 72)
        return 0

    if tong_mu <= a.accept_blind:
        print(f"GRAPH_TRUSTED_CAVEATS — {tong_mu} vùng mù, đã khai và chấp nhận "
              f"(--accept-blind {a.accept_blind}).")
        print("Mỗi vùng mù là một cạnh đồ thị không có. Mọi kết luận kiểu 'không ai gọi'")
        print("ở gần những node đó là NOT_TESTED.")
        print("=" * 72)
        return 0

    print(f"GRAPH_UNTRUSTED — {tong_mu} vùng mù ở chiều chí mạng, "
          f"chỉ chấp nhận {a.accept_blind}.")
    print("Không tối ưu trên nền này. Hai đường đi tiếp, không có đường thứ ba:")
    print("  · mở rộng đồ thị tĩnh để giải được những cạnh trên; hoặc")
    print("  · khai tường minh bằng --accept-blind và ghi rõ những node nào thành NOT_TESTED.")
    print("=" * 72)
    return 9


if __name__ == "__main__":
    sys.exit(main())
