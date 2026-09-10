#!/usr/bin/env python3
"""Kiểm CỔNG GRAPH: nó có thật sự bắt được vùng mù của đồ thị tĩnh hay không.

Phép kiểm quan trọng nhất ở đây KHÔNG phải "cổng báo 2 vùng mù". Báo đúng số mà không
biết số đó từ đâu ra thì vẫn có thể là trùng hợp. Phép kiểm quan trọng là **ca đối
chứng ngược**: gỡ đúng cái file gây ra vùng mù đi, cổng phải về 0. Hai chiều cùng đúng
mới chứng minh được cổng đang nhìn vào đúng chỗ.

Đây là cùng một kỷ luật mà `xac-minh.md` đã trả giá để học: ca hiệu chuẩn dễ dựng
thường quá yếu. "Cổng báo có lỗi" là ca yếu. "Cổng báo có lỗi, và thôi báo đúng lúc ta
gỡ nguyên nhân" là ca mạnh.

    python tests/integration/test_cong_graph.py --ra .wp-it
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GOC = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(GOC))
SCRIPTS = os.path.join(REPO, "skills", "wp-code-optimize", "scripts")

dat, hong = [], []


def kiem(ten, ok, chi_tiet=""):
    (dat if ok else hong).append((ten, chi_tiet))
    print(f"  {'đạt ' if ok else 'HỎNG'}  {ten}" + (f"\n          {chi_tiet}" if not ok else ""))


def chay(*lenh):
    r = subprocess.run([sys.executable] + list(lenh), capture_output=True, text=True,
                       encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ra", required=True)
    a = ap.parse_args()
    W = os.path.abspath(a.ra)
    if not os.path.isdir(os.path.join(W, "site")):
        print("KHONG_KIEM_DUOC: chua dung WordPress — chay dung_wp.py truoc")
        return 4

    theme_src = os.path.join(GOC, "fixture-bien-doi")
    graph = os.path.join(W, "graph-kiem.json")
    adn = os.path.join(W, "adn-kiem.json")
    trust = os.path.join(W, "trust-kiem.json")

    print("=" * 70)
    print("CỔNG GRAPH — kiểm hai chiều")
    print("=" * 70)

    # ── 1. đồ thị tĩnh tự khai đúng số cạnh nó không giải được
    print("\n[1] Đồ thị tĩnh có TỰ KHAI vùng mù của chính nó không")
    ma, ra = chay(os.path.join(SCRIPTS, "code_nodes.py"), "--theme", theme_src, "--ra", graph)
    kiem("code_nodes.py chạy xong, exit 0", ma == 0, ra[-400:])
    g = json.load(open(graph, encoding="utf-8"))
    kiem("tự khai đúng 2 cạnh không phân giải được",
         g["dynamic_unresolved_tong"] == 2,
         f"tự khai {g['dynamic_unresolved_tong']}, mong 2")
    kiem("một cạnh là HOOK TÊN BIẾN",
         len(g["dynamic_unresolved"]["hook_ten_bien"]) == 1,
         str(g["dynamic_unresolved"]["hook_ten_bien"]))
    kiem("một cạnh là CALLBACK GHÉP CHUỖI",
         len(g["dynamic_unresolved"]["callback_bien"]) == 1,
         str(g["dynamic_unresolved"]["callback_bien"]))
    kiem("cạnh phụ thuộc asset được đọc (deps nằm sau một tham số có dấu ngoặc)",
         any(e["loai"] == "phu_thuoc" for e in g["edges"]),
         "khong co canh phu_thuoc — regex mot phat lai an mat mang deps")

    # ── 2. ADN runtime
    print("\n[2] Chụp ADN từ WordPress đang chạy")
    ma, ra = chay(os.path.join(GOC, "chup_adn.py"), "--ra", W, "--ra-json", adn)
    kiem("chup_adn.py chạy xong, exit 0", ma == 0, ra[-500:])
    if ma != 0:
        return 1

    # ── 3. chiều chí mạng: cổng phải CHẶN
    print("\n[3] Chiều chí mạng — cổng phải CHẶN, không phải cảnh báo")
    ma, ra = chay(os.path.join(SCRIPTS, "cong_graph.py"),
                  "--graph", graph, "--adn", adn, "--ra", trust)
    kiem("exit KHÁC 0 khi có vùng mù (fail-closed)", ma == 9, f"exit={ma}")
    kiem("in ra GRAPH_KHONG_DANG_TIN", "GRAPH_KHONG_DANG_TIN" in ra)
    t = json.load(open(trust, encoding="utf-8"))
    kiem("đếm đúng 2 vùng mù", t["tong_vung_mu"] == 2, f"dem {t['tong_vung_mu']}")
    mu_hook = [x for x in t["chi_runtime_co"]["hook"]]
    kiem("gọi đúng TÊN hai callback mà tĩnh không thấy",
         sorted(x[2] for x in mu_hook) == ["fxb_dong_a", "fxb_dong_b"],
         str(mu_hook))
    kiem("KHÔNG có vùng mù ở mặt file và mặt asset",
         not t["chi_runtime_co"]["file"] and not t["chi_runtime_co"]["asset"],
         f"file={t['chi_runtime_co']['file']} asset={t['chi_runtime_co']['asset']}")

    # ── 4. khai tường minh thì đi tiếp được
    print("\n[4] Khai tường minh số vùng mù thì mới đi tiếp được")
    ma, ra = chay(os.path.join(SCRIPTS, "cong_graph.py"),
                  "--graph", graph, "--adn", adn, "--chap-nhan-mu", "2")
    kiem("exit 0 khi đã khai đúng số", ma == 0, f"exit={ma}")
    kiem("vẫn nói rõ những node đó là NOT_TESTED", "NOT_TESTED" in ra)
    ma, _ = chay(os.path.join(SCRIPTS, "cong_graph.py"),
                 "--graph", graph, "--adn", adn, "--chap-nhan-mu", "1")
    kiem("khai THIẾU một vùng mù thì vẫn chặn", ma == 9, f"exit={ma}")

    # ── 5. CA ĐỐI CHỨNG NGƯỢC — phép kiểm mạnh nhất của file này
    #
    # Gỡ đúng file sinh ra hai cạnh động, rồi đòi cổng về 0. Thiếu bước này thì "cổng
    # báo 2" có thể là một con số đúng vì trùng hợp — ví dụ cổng luôn báo 2 vì một
    # khác biệt hệ thống nào khác giữa tĩnh và runtime.
    print("\n[5] Ca đối chứng ngược — gỡ nguyên nhân thì cổng phải THÔI báo")
    tam = os.path.join(W, "fixture-khong-hook-dong")
    if os.path.exists(tam):
        shutil.rmtree(tam)
    shutil.copytree(theme_src, tam)
    os.remove(os.path.join(tam, "inc", "hook-dong.php"))
    fn = os.path.join(tam, "functions.php")
    s = open(fn, encoding="utf-8").read()
    moc = "require_once FXB_DUONG_DAN . '/inc/hook-dong.php';\n"
    kiem("mốc require của file động xuất hiện đúng 1 lần", s.count(moc) == 1,
         f"xuat hien {s.count(moc)} lan")
    open(fn, "w", encoding="utf-8", newline="").write(s.replace(moc, ""))

    graph2 = os.path.join(W, "graph-khong-dong.json")
    ma, ra = chay(os.path.join(SCRIPTS, "code_nodes.py"), "--theme", tam, "--ra", graph2)
    g2 = json.load(open(graph2, encoding="utf-8"))
    kiem("bỏ file động thì đồ thị tĩnh tự khai 0 vùng mù",
         g2["dynamic_unresolved_tong"] == 0, f"tu khai {g2['dynamic_unresolved_tong']}")

    # Chụp ADN của chính cây đã gỡ file, rồi so — đây mới là đối chứng thật.
    adn2 = os.path.join(W, "adn-khong-dong.json")
    site_theme = os.path.join(W, "site", "wp-content", "themes", "fixture-bien-doi")
    luu = os.path.join(W, "luu-fixture-goc")
    if os.path.exists(luu):
        shutil.rmtree(luu)
    shutil.copytree(site_theme, luu)
    try:
        shutil.rmtree(site_theme)
        shutil.copytree(tam, site_theme)
        ma, ra = chay(os.path.join(GOC, "chup_adn.py"), "--ra", W,
                      "--ra-json", adn2, "--khong-chep")
        if ma != 0:
            kiem("chup duoc ADN cua cay da go file dong", False, ra[-500:])
        else:
            ma, ra = chay(os.path.join(SCRIPTS, "cong_graph.py"),
                          "--graph", graph2, "--adn", adn2)
            kiem("cổng về 0 vùng mù và exit 0 sau khi gỡ nguyên nhân", ma == 0,
                 f"exit={ma}\n{ra[-700:]}")
            kiem("in ra GRAPH_DANG_TIN", "GRAPH_DANG_TIN" in ra)
    finally:
        shutil.rmtree(site_theme, ignore_errors=True)
        shutil.copytree(luu, site_theme)
        shutil.rmtree(luu, ignore_errors=True)

    print("\n" + "=" * 70)
    print(f"đạt {len(dat)} · hỏng {len(hong)}")
    if hong:
        print("\nHỎNG:")
        for t_, c in hong:
            print(f"  · {t_}\n    {c}")
    print("=" * 70)
    return 1 if hong else 0


if __name__ == "__main__":
    sys.exit(main())
