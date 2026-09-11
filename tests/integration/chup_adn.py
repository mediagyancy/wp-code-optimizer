#!/usr/bin/env python3
"""Chụp ADN của theme fixture ra một file JSON, để `cong_graph.py` đối chứng.

Cố ý là một lớp mỏng, KHÔNG chép lại logic chụp: nó dùng đúng hàm `chup()` của
`tang5.py`. Hai bản chụp khác nhau một chi tiết là hai bản chụp sẽ lệch, và lúc đó
không ai biết lệch vì code đổi hay vì bộ đo đổi.

    python tests/integration/chup_adn.py --ra .wp-it --ra-json .wp-it/adn.json
"""
import argparse
import json
import os
import shutil
import sys

GOC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, GOC)
from tang5 import THEME_SLUG, chup  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ra", required=True, help="thu muc lam viec cua integration test")
    ap.add_argument("--ra-json", required=True, help="file JSON de ghi ADN")
    ap.add_argument("--khong-chep", action="store_true",
                    help="chup theme DANG CO trong site, khong chep lai tu fixture. "
                         "Dung cho ca doi chung nguoc: ben goi da tu dat mot cay theme "
                         "da sua vao site va muon chup DUNG cay do.")
    a = ap.parse_args()

    W = os.path.abspath(a.ra)
    site = os.path.join(W, "site")
    if not os.path.isdir(site):
        print("KHONG_KIEM_DUOC: chua dung WordPress — chay dung_wp.py truoc")
        return 4

    goc_theme = os.path.join(site, "wp-content", "themes", THEME_SLUG)
    if not a.khong_chep:
        if os.path.exists(goc_theme):
            shutil.rmtree(goc_theme)
        shutil.copytree(os.path.join(GOC, "fixture-bien-doi"), goc_theme)
    elif not os.path.isdir(goc_theme):
        print("KHONG_KIEM_DUOC: --khong-chep nhung khong thay theme trong site")
        return 4
    shutil.copy(os.path.join(GOC, "adn-nen.php"), os.path.join(W, "adn-nen.php"))

    adn, loi = chup(W, goc_theme)
    if loi:
        print(loi)
        return 5

    tmp = a.ra_json + ".tmp"
    os.makedirs(os.path.dirname(os.path.abspath(a.ra_json)), exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(adn, f, ensure_ascii=False, indent=2)
    os.replace(tmp, a.ra_json)
    print(f"da ghi {a.ra_json}  ·  hook theme {len(adn['hook_theme'])}"
          f" · file nap {len(adn['file_nap_sau_render'])}"
          f" · chu ky ham {len(adn['chu_ky_ham'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
