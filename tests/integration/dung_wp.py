#!/usr/bin/env python3
"""Dựng một WordPress + WooCommerce chạy được, để lấy SỰ THẬT NỀN.

Không cần MySQL và không cần Docker: dùng plugin sqlite-database-integration
chính thức của WordPress.org làm drop-in database. Chỉ cần PHP CLI có
pdo_sqlite (Linux thường có sẵn; Windows thì DLL nằm sẵn trong thư mục ext,
script tự bật).

    python tests/integration/dung_wp.py --ra <thư-mục-làm-việc>

Tải một lần rồi dùng lại: có sẵn thì bỏ qua bước tải.
"""
import argparse
import io
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GOC = os.path.dirname(os.path.abspath(__file__))

TAI = [
    ("wordpress.zip", "https://wordpress.org/latest.zip"),
    ("woocommerce.zip", "https://downloads.wordpress.org/plugin/woocommerce.zip"),
    ("sqlite.zip", "https://downloads.wordpress.org/plugin/sqlite-database-integration.zip"),
]

WP_CONFIG = """<?php
/* wp-config cho integration test — SQLite, không cần MySQL. */
define( 'DB_NAME', 'wpit' );
define( 'DB_USER', '' );
define( 'DB_PASSWORD', '' );
define( 'DB_HOST', 'localhost' );
define( 'DB_CHARSET', 'utf8' );
define( 'DB_COLLATE', '' );
define( 'AUTH_KEY', 'it-a' );        define( 'SECURE_AUTH_KEY', 'it-b' );
define( 'LOGGED_IN_KEY', 'it-c' );   define( 'NONCE_KEY', 'it-d' );
define( 'AUTH_SALT', 'it-e' );       define( 'SECURE_AUTH_SALT', 'it-f' );
define( 'LOGGED_IN_SALT', 'it-g' );  define( 'NONCE_SALT', 'it-h' );
$table_prefix = 'wp_';
define( 'WP_DEBUG', true );
define( 'WP_DEBUG_DISPLAY', false );
define( 'WP_HOME', 'http://localhost:8899' );
define( 'WP_SITEURL', 'http://localhost:8899' );
define( 'DISABLE_WP_CRON', true );
if ( ! defined( 'ABSPATH' ) ) { define( 'ABSPATH', __DIR__ . '/' ); }
require_once ABSPATH . 'wp-settings.php';
"""


def php_args():
    """Trên Windows, pdo_sqlite thường có DLL nhưng bị tắt trong php.ini — tự bật."""
    ra = ["-d", "memory_limit=512M"]
    co = subprocess.run(["php", "-r", 'echo extension_loaded("pdo_sqlite") ? "1" : "0";'],
                        capture_output=True, text=True).stdout.strip()
    if co == "1":
        return ra
    ext = subprocess.run(["php", "-r", 'echo ini_get("extension_dir");'],
                         capture_output=True, text=True).stdout.strip()
    for ten in ("php_pdo_sqlite.dll", "php_sqlite3.dll"):
        p = os.path.join(ext, ten)
        if os.path.exists(p):
            ra += ["-d", "extension=" + p]
    return ra


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ra", required=True, help="thư mục làm việc")
    ap.add_argument("--lam-lai", action="store_true", help="xoá và dựng lại từ đầu")
    a = ap.parse_args()

    W = os.path.abspath(a.ra).replace("\\", "/")
    tai_dir = os.path.join(W, "tai")
    site = os.path.join(W, "site")
    if a.lam_lai and os.path.exists(site):
        shutil.rmtree(site, ignore_errors=True)
    os.makedirs(tai_dir, exist_ok=True)

    for ten, url in TAI:
        p = os.path.join(tai_dir, ten)
        if os.path.exists(p) and os.path.getsize(p) > 1000:
            print(f"  có sẵn  {ten}")
            continue
        print(f"  tải     {ten} …", flush=True)
        urllib.request.urlretrieve(url, p)
        print(f"          {os.path.getsize(p)/1048576:.1f} MB")

    if not os.path.exists(site):
        with zipfile.ZipFile(os.path.join(tai_dir, "wordpress.zip")) as z:
            z.extractall(W)
        os.rename(os.path.join(W, "wordpress"), site)
        pl = os.path.join(site, "wp-content", "plugins")
        for ten in ("woocommerce.zip", "sqlite.zip"):
            with zipfile.ZipFile(os.path.join(tai_dir, ten)) as z:
                z.extractall(pl)
        print("  giải nén xong")

    # drop-in database
    sq = os.path.join(site, "wp-content", "plugins", "sqlite-database-integration")
    dbp = os.path.join(site, "wp-content", "db.php")
    src = os.path.join(sq, "db.copy")
    if os.path.exists(src):
        s = io.open(src, encoding="utf-8", errors="replace").read()
        s = s.replace("{SQLITE_IMPLEMENTATION_FOLDER_PATH}", sq.replace("\\", "/"))
        io.open(dbp, "w", encoding="utf-8").write(s)

    io.open(os.path.join(site, "wp-config.php"), "w", encoding="utf-8").write(WP_CONFIG)

    # theme fixture
    dich = os.path.join(site, "wp-content", "themes", "fixture-theme")
    if os.path.exists(dich):
        shutil.rmtree(dich)
    shutil.copytree(os.path.join(GOC, "fixture-theme"), dich)

    for f in ("cai-wp.php", "su-that-nen.php"):
        shutil.copy(os.path.join(GOC, f), os.path.join(W, f))

    r = subprocess.run(["php"] + php_args() + [os.path.join(W, "cai-wp.php")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    for l in (r.stdout or "").splitlines():
        if l.strip() and not l.lstrip().startswith("<"):
            print("  " + l.strip())
    if "class_exists: co" not in (r.stdout or ""):
        print((r.stdout or "")[-1200:])
        print((r.stderr or "")[-600:])
        sys.exit("KHÔNG dựng được WordPress+WooCommerce")
    print("\nWordPress + WooCommerce sẵn sàng:", W)
    return 0


if __name__ == "__main__":
    sys.exit(main())
