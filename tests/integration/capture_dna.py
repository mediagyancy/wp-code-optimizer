#!/usr/bin/env python3
"""Chụp ADN của theme fixture ra một file JSON, để `graph_gate.py` đối chứng.

Cố ý là một lớp mỏng, KHÔNG chép lại logic chụp: nó dùng đúng hàm `chup()` của
`tier5.py`. Hai bản chụp khác nhau một chi tiết là hai bản chụp sẽ lệch, và lúc đó
không ai biết lệch vì code đổi hay vì bộ đo đổi.

    python tests/integration/capture_dna.py --workdir .wp-it --out .wp-it/adn.json
"""
import argparse
import json
import os
import shutil
import sys

GOC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, GOC)
from tier5 import THEME_SLUG, chup  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", required=True, help="thu muc lam viec cua integration test")
    ap.add_argument("--out", required=True, help="file JSON de ghi ADN")
    ap.add_argument("--no-copy", action="store_true",
                    help="chup theme DANG CO trong site, khong chep lai tu fixture. "
                         "Dung cho ca doi chung nguoc: ben goi da tu dat mot cay theme "
                         "da sua vao site va muon chup DUNG cay do.")
    a = ap.parse_args()

    W = os.path.abspath(a.workdir)
    site = os.path.join(W, "site")
    if not os.path.isdir(site):
        print("NOT_CHECKABLE: chua dung WordPress — chay dung_wp.py truoc")
        return 4

    goc_theme = os.path.join(site, "wp-content", "themes", THEME_SLUG)
    if not a.no_copy:
        if os.path.exists(goc_theme):
            shutil.rmtree(goc_theme)
        shutil.copytree(os.path.join(GOC, "fixture-bien-doi"), goc_theme)
    elif not os.path.isdir(goc_theme):
        print("NOT_CHECKABLE: --no-copy nhung khong thay theme trong site")
        return 4
    shutil.copy(os.path.join(GOC, "dna.php"), os.path.join(W, "dna.php"))

    adn, loi = chup(W, goc_theme)
    if loi:
        print(loi)
        return 5

    tmp = a.out + ".tmp"
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(adn, f, ensure_ascii=False, indent=2)
    os.replace(tmp, a.out)
    print(f"da ghi {a.out}  ·  hook theme {len(adn['theme_hooks'])}"
          f" · file nap {len(adn['files_after_render'])}"
          f" · chu ky ham {len(adn['signatures'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
