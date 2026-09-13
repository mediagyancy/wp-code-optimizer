#!/usr/bin/env python3
"""CHEATSHEET — bảng tra mọi tên mà MỘT DỰ ÁN phát ra ngoài, kiểu bảng Liquid của Haravan.

Việc thật sự là gì
------------------
Một theme/plugin WordPress "phát ra ngoài" nhiều thứ hơn người viết nhớ: hàm có tiền tố,
hook tự phát (`do_action('myp_after_render')`), shortcode, hằng, key option, handle asset,
route REST, action AJAX, template part. Không có bảng thì người sau đọc code để đoán, và
đoán sai ở đúng chỗ đắt nhất — key option đổi tên là mất cài đặt, hook đổi tên là plugin
con im lặng ngừng chạy. Bảng này là HỢP ĐỒNG của dự án, sinh từ code, không viết tay.

Ba luật của script:

  1. **Chỉ ghi nhận literal thuần.** `apply_filters( 'myp_' . $x )` không được đoán thành
     một tên; nó đi vào `unresolved` và được ĐẾM. Cạnh bịa tệ hơn cạnh thiếu.
  2. **Docblock chỉ tính khi đứng NGAY TRÊN.** Docblock đầu file rồi tới `defined(...)`
     rồi tới `function` — docblock đó là của file, không phải của hàm. Hàm không có mô tả
     thì `documented: false` và cộng vào `undocumented_count`: bảng cũng là thước đo nợ tài
     liệu, không phải chỉ là danh sách.
  3. **Từ chối ghi khi chưa hiệu chuẩn.** Trước khi ghi bất kỳ file nào, script chạy chính
     nó trên một đoạn mã có sẵn ca đúng và ca mồi (hàm trong `<script>`, docblock cách hàm
     bằng code, hook tên động). Bắt sai một ca là `UNCALIBRATED`, exit 2, không ghi gì.

Phủ: PHP (WordPress) + Python (cờ argparse — để bảng này chạy được trên chính repo công cụ).
KHÔNG phủ: JavaScript, class/method PHP (chỉ hàm top-level), CSS class.

    python cheatsheet.py --root <dự án> [--prefix myp_,myp-] --out cheatsheet.json
    python cheatsheet.py --root <dự án> --md CHEATSHEET.md --html cheatsheet.html

Exit: 0 xong · 2 UNCALIBRATED · 4 NOT_CHECKABLE (không có file để quét / thiếu template HTML).
"""
import argparse
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

VERSION = 1
SKIP_DIRS = ("node_modules", "vendor", ".git", "__pycache__", ".wp-it", "_backup")
# Tên file template theo WordPress template hierarchy — chỉ tên gốc, không kèm biến thể `-slug`.
TEMPLATE_NAMES = ("index", "front-page", "home", "single", "page", "archive", "category",
                  "tag", "taxonomy", "author", "date", "search", "404", "attachment",
                  "singular", "header", "footer", "sidebar", "comments", "searchform",
                  "woocommerce", "functions", "style")
RE_STRING = re.compile(r"^\s*'((?:[^'\\]|\\.)*)'\s*$|^\s*\"((?:[^\"\\]|\\.)*)\"\s*$")
# Docblock chỉ hợp lệ khi giữa `*/` và `function` toàn khoảng trắng, và bên trong không có
# `*/` khác — `.*?` lazy sẽ nuốt luôn code giữa hai docblock, đó là ca mồi số 2.
RE_FUNC = re.compile(
    r"(?:/\*\*(?P<doc>(?:(?!\*/).)*)\*/[ \t]*\n[ \t]*)?"
    r"^[ \t]*function[ \t]+(?P<name>[A-Za-z_][A-Za-z0-9_]*)[ \t]*(?=\()", re.M | re.S)
RE_EMIT_OPEN = re.compile(r"\b(do_action|apply_filters|do_action_ref_array|apply_filters_ref_array)\s*(?=\()")
RE_REG_OPEN = re.compile(r"\b(add_action|add_filter|add_shortcode)\s*(?=\()")
RE_DEFINE_OPEN = re.compile(r"\bdefine\s*(?=\()")
RE_OPTION_OPEN = re.compile(
    r"\b(get_option|update_option|add_option|delete_option|get_theme_mod|set_theme_mod|"
    r"get_site_option|update_site_option)\s*(?=\()")
RE_ASSET_OPEN = re.compile(r"\bwp_(?:enqueue|register)_(script|style)\s*(?=\()")
RE_REST_OPEN = re.compile(r"\bregister_rest_route\s*(?=\()")
RE_PART_OPEN = re.compile(r"\bget_template_part\s*(?=\()")
RE_LINE_COMMENT = re.compile(r"^[ \t]*(?://|#)[ \t]?(.*)$")
RE_PY_ARG = re.compile(r"\.add_argument\s*(?=\()")
RE_PY_SUB = re.compile(r"\.add_parser\s*(?=\()")
OPTION_READS = ("get_option", "get_theme_mod", "get_site_option")


# ── đọc file ───────────────────────────────────────────────────────────────────────────

def read(p):
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()


def rel(p, root):
    return os.path.relpath(p, root).replace(os.sep, "/")


def walk(root, exts):
    out = []
    for dp, dn, fn in os.walk(root):
        dn[:] = sorted(d for d in dn if d not in SKIP_DIRS)
        for f in sorted(fn):
            if f.endswith(exts):
                out.append(os.path.join(dp, f))
    return out


def strip_script(s):
    """Bỏ khối <script> — không bỏ thì `function x(){}` của JavaScript thành hàm PHP (ca mồi 1)."""
    return re.sub(r"<script\b[^>]*>.*?</script>", lambda m: " " * len(m.group(0)), s, flags=re.S | re.I)


def strip_comments(s):
    """Bỏ comment nhưng GIỮ độ dài (thay bằng khoảng trắng) để số dòng không trôi."""
    s = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), s, flags=re.S)
    s = re.sub(r"(?m)(//|#)[^\n]*$", lambda m: " " * len(m.group(0)), s)
    return s


def line_of(s, i):
    return s.count("\n", 0, i) + 1


def split_args(s, i_open):
    """Tách tham số của lời gọi từ dấu `(` — cân bằng ngoặc, tôn trọng chuỗi.

    Cùng thuật toán với `code_nodes.tach_tham_so`; chép lại để skill này đứng một mình
    (§7.5: hai bản chép là nợ có ghi, không phải nợ giấu). Trả (None, None) khi ngoặc
    không cân — không đọc được thì nói, không đoán.
    """
    if i_open >= len(s) or s[i_open] != "(":
        return None, None
    depth, params, cur, quote, i = 1, [], [], None, i_open + 1
    while i < len(s):
        c = s[i]
        if quote:
            cur.append(c)
            if c == "\\" and i + 1 < len(s):
                cur.append(s[i + 1]); i += 2; continue
            if c == quote:
                quote = None
        elif c in "'\"":
            quote = c; cur.append(c)
        elif c in "([{":
            depth += 1; cur.append(c)
        elif c in ")]}":
            depth -= 1
            if depth == 0:
                params.append("".join(cur).strip())
                return params, i + 1
            cur.append(c)
        elif c == "," and depth == 1:
            params.append("".join(cur).strip()); cur = []
        else:
            cur.append(c)
        i += 1
    return None, None


def literal(expr):
    """Chuỗi nếu biểu thức là MỘT literal thuần; `'a' . $b` và `$x` đều là None."""
    m = RE_STRING.match(expr or "")
    if not m:
        return None
    return m.group(1) if m.group(1) is not None else m.group(2)


def summary_of(doc):
    """Câu đầu của docblock: bỏ `*`, dừng ở dòng trống hoặc thẻ `@`."""
    lines = []
    for ln in doc.splitlines():
        t = ln.strip().lstrip("*").strip()
        if not t and lines:
            break
        if t.startswith("@"):
            break
        if t:
            lines.append(t)
    return " ".join(lines)[:200]


def comment_above(s, i):
    """Comment `//` hoặc docblock nằm NGAY dòng trên vị trí i, nếu có."""
    start = s.rfind("\n", 0, i)
    prev_end = start
    prev_start = s.rfind("\n", 0, prev_end) + 1 if prev_end > 0 else 0
    prev = s[prev_start:prev_end]
    m = RE_LINE_COMMENT.match(prev)
    if m:
        return m.group(1).strip()[:200]
    if prev.strip().endswith("*/"):
        j = s.rfind("/**", 0, prev_end)
        if j >= 0:
            return summary_of(s[j + 3:prev_end].rsplit("*/", 1)[0])
    return ""


def parse_params(params):
    out = []
    for p in params or []:
        p = p.strip()
        if not p:
            continue
        name_m = re.search(r"(\.\.\.)?\$([A-Za-z_][A-Za-z0-9_]*)", p)
        if not name_m:
            continue
        default = None
        if "=" in p[name_m.end():]:
            default = p[name_m.end():].split("=", 1)[1].strip()
        out.append({"name": name_m.group(2), "default": default,
                    "required": default is None and not name_m.group(1)})
    return out


def has_prefix(name, prefixes):
    return not prefixes or any(name.startswith(p) for p in prefixes)


# ── quét PHP ───────────────────────────────────────────────────────────────────────────

def scan_php(path, file, prefixes, sheet, option_index):
    raw = strip_script(read(path))
    code = strip_comments(raw)  # cùng độ dài với raw → chỉ số dùng chung
    unresolved = sheet["unresolved"]

    for m in RE_FUNC.finditer(raw):
        name = m.group("name")
        if not has_prefix(name, prefixes):
            continue
        params, _ = split_args(code, m.end())
        doc = m.group("doc")
        sheet["functions"].append({
            "name": name, "file": file, "line": line_of(raw, m.start("name")),
            "params": parse_params(params) if params is not None else [],
            "summary": summary_of(doc) if doc else "", "documented": bool(doc and summary_of(doc)),
        })

    for m in RE_EMIT_OPEN.finditer(code):
        params, _ = split_args(code, m.end())
        ln = line_of(code, m.start())
        if params is None:
            unresolved["unparsed_call"].append({"file": file, "line": ln, "func": m.group(1)}); continue
        name = literal(params[0]) if params else None
        if name is None:
            unresolved["dynamic_hook"].append({"file": file, "line": ln, "expr": (params[0] if params else "")[:90]}); continue
        sheet["hooks"].append({
            "name": name, "kind": "filter" if "filter" in m.group(1) else "action",
            "file": file, "line": ln, "arg_count": len(params) - 1,
            "summary": comment_above(raw, m.start()),
        })

    for m in RE_REG_OPEN.finditer(code):
        params, _ = split_args(code, m.end())
        ln = line_of(code, m.start())
        if params is None or len(params) < 2:
            unresolved["unparsed_call"].append({"file": file, "line": ln, "func": m.group(1)}); continue
        hook, cb = literal(params[0]), literal(params[1])
        if hook is None:
            unresolved["dynamic_hook"].append({"file": file, "line": ln, "expr": params[0][:90]}); continue
        cb_name = cb if cb is not None else params[1][:90]
        if m.group(1) == "add_shortcode":
            sheet["shortcodes"].append({"tag": hook, "callback": cb_name, "file": file, "line": ln}); continue
        if hook.startswith("wp_ajax_"):
            public = hook.startswith("wp_ajax_nopriv_")
            sheet["ajax"].append({"action": hook.split("nopriv_", 1)[1] if public else hook[len("wp_ajax_"):],
                                  "is_public": public, "callback": cb_name, "file": file, "line": ln})
        pr = params[2].strip() if len(params) > 2 else "10"
        sheet["registrations"].append({"hook": hook, "callback": cb_name,
                                       "priority": int(pr) if re.fullmatch(r"-?\d+", pr) else pr[:40],
                                       "file": file, "line": ln})

    for m in RE_DEFINE_OPEN.finditer(code):
        params, _ = split_args(code, m.end())
        ln = line_of(code, m.start())
        if params is None or not params:
            unresolved["unparsed_call"].append({"file": file, "line": ln, "func": "define"}); continue
        name = literal(params[0])
        if name is None:
            unresolved["dynamic_constant"].append({"file": file, "line": ln, "expr": params[0][:90]}); continue
        if not has_prefix(name, [p.upper().rstrip("_-") for p in prefixes]):
            continue
        val = params[1] if len(params) > 1 else ""
        sheet["constants"].append({"name": name, "value": (literal(val) if literal(val) is not None else val)[:120],
                                   "is_literal": literal(val) is not None, "file": file, "line": ln})

    for m in RE_OPTION_OPEN.finditer(code):
        params, _ = split_args(code, m.end())
        ln = line_of(code, m.start())
        if params is None or not params:
            unresolved["unparsed_call"].append({"file": file, "line": ln, "func": m.group(1)}); continue
        name = literal(params[0])
        if name is None:
            unresolved["dynamic_option"].append({"file": file, "line": ln, "expr": params[0][:90]}); continue
        kind = "theme_mod" if "theme_mod" in m.group(1) else ("site_option" if "site_option" in m.group(1) else "option")
        key = (kind, name)
        o = option_index.setdefault(key, {"name": name, "kind": kind, "read_count": 0, "write_count": 0, "files": []})
        o["read_count" if m.group(1) in OPTION_READS else "write_count"] += 1
        if file not in o["files"]:
            o["files"].append(file)

    for m in RE_ASSET_OPEN.finditer(code):
        params, _ = split_args(code, m.end())
        ln = line_of(code, m.start())
        if params is None or not params:
            unresolved["unparsed_call"].append({"file": file, "line": ln, "func": "wp_enqueue_" + m.group(1)}); continue
        handle = literal(params[0])
        if handle is None:
            unresolved["dynamic_handle"].append({"file": file, "line": ln, "expr": params[0][:90]}); continue
        deps = re.findall(r"'([^']+)'|\"([^\"]+)\"", params[2]) if len(params) > 2 else []
        sheet["assets"].append({"handle": handle, "asset_type": m.group(1),
                                "src": (params[1] if len(params) > 1 else "")[:120],
                                "deps": [a or b for a, b in deps],
                                "ver": (params[3] if len(params) > 3 else "")[:40], "file": file, "line": ln})

    for m in RE_REST_OPEN.finditer(code):
        params, _ = split_args(code, m.end())
        ln = line_of(code, m.start())
        if params is None or len(params) < 2:
            unresolved["unparsed_call"].append({"file": file, "line": ln, "func": "register_rest_route"}); continue
        ns, route = literal(params[0]), literal(params[1])
        if ns is None or route is None:
            unresolved["dynamic_route"].append({"file": file, "line": ln, "expr": (params[0] + ", " + params[1])[:90]}); continue
        sheet["rest_routes"].append({"namespace": ns, "route": route, "file": file, "line": ln})

    for m in RE_PART_OPEN.finditer(code):
        params, _ = split_args(code, m.end())
        ln = line_of(code, m.start())
        if params is None or not params:
            unresolved["unparsed_call"].append({"file": file, "line": ln, "func": "get_template_part"}); continue
        slug = literal(params[0])
        if slug is None:
            unresolved["dynamic_template_part"].append({"file": file, "line": ln, "expr": params[0][:90]}); continue
        name = literal(params[1]) if len(params) > 1 else None
        sheet["template_parts"].append({"slug": slug, "name": name, "file": file, "line": ln})


# ── quét Python (argparse) ────────────────────────────────────────────────────────────

def scan_py(path, file, sheet):
    s = read(path)
    if ".add_argument" not in s and ".add_parser" not in s:
        return
    for m in RE_PY_SUB.finditer(s):
        params, _ = split_args(s, m.end())
        cmd = literal(params[0]) if params else None
        if cmd:
            sheet["cli"].append({"script": file, "command": cmd, "flag": "", "help": _kw(params, "help"), "line": line_of(s, m.start())})
    for m in RE_PY_ARG.finditer(s):
        params, _ = split_args(s, m.end())
        if not params:
            continue
        flags = [literal(p) for p in params if literal(p) is not None and literal(p).startswith("-")]
        if not flags:
            pos = literal(params[0])
            if pos is None:
                sheet["unresolved"]["dynamic_flag"].append({"file": file, "line": line_of(s, m.start()), "expr": params[0][:90]})
                continue
            flags = [pos]
        sheet["cli"].append({"script": file, "command": "", "flag": " / ".join(flags),
                             "help": _kw(params, "help"), "line": line_of(s, m.start())})


def _kw(params, key):
    for p in params or []:
        if p.startswith(key + "="):
            v = literal(p.split("=", 1)[1])
            return (v or "")[:200]
    return ""


# ── dựng bảng ─────────────────────────────────────────────────────────────────────────

def empty_sheet():
    return {
        "version": VERSION, "project": "", "prefix": [],
        "functions": [], "hooks": [], "registrations": [], "shortcodes": [], "ajax": [],
        "constants": [], "options": [], "assets": [], "rest_routes": [], "templates": [],
        "template_parts": [], "cli": [],
        "unresolved": {k: [] for k in ("dynamic_hook", "dynamic_option", "dynamic_handle", "dynamic_constant",
                                       "dynamic_route", "dynamic_template_part", "dynamic_flag", "unparsed_call")},
        "unresolved_count": 0, "counts": {},
    }


def build(root, prefixes):
    sheet = empty_sheet()
    sheet["project"] = os.path.basename(os.path.abspath(root))
    sheet["prefix"] = list(prefixes)
    php = walk(root, (".php",))
    py = walk(root, (".py",))
    if not php and not py:
        return None
    option_index = {}
    for p in php:
        f = rel(p, root)
        scan_php(p, f, prefixes, sheet, option_index)
        base = os.path.basename(f)
        stem = base[:-4]
        if "/" not in f and (stem in TEMPLATE_NAMES or stem.split("-")[0] in TEMPLATE_NAMES):
            sheet["templates"].append({"path": f})
    for p in py:
        scan_py(p, rel(p, root), sheet)
    return finish(sheet, option_index)


def finish(sheet, option_index):
    sheet["options"] = sorted(option_index.values(), key=lambda o: (o["kind"], o["name"]))
    sheet["functions"].sort(key=lambda x: x["name"])
    sheet["hooks"].sort(key=lambda x: (x["name"], x["file"], x["line"]))
    sheet["registrations"].sort(key=lambda x: (x["hook"], x["file"], x["line"]))
    sheet["shortcodes"].sort(key=lambda x: x["tag"])
    sheet["ajax"].sort(key=lambda x: (x["action"], x["is_public"]))
    sheet["constants"].sort(key=lambda x: x["name"])
    sheet["assets"].sort(key=lambda x: (x["asset_type"], x["handle"]))
    sheet["rest_routes"].sort(key=lambda x: (x["namespace"], x["route"]))
    sheet["templates"].sort(key=lambda x: x["path"])
    sheet["template_parts"].sort(key=lambda x: (x["slug"], x["name"] or ""))
    sheet["cli"].sort(key=lambda x: (x["script"], x["line"]))
    sheet["unresolved_count"] = sum(len(v) for v in sheet["unresolved"].values())
    c = {k: len(sheet[k]) for k in ("functions", "hooks", "registrations", "shortcodes", "ajax", "constants",
                                     "options", "assets", "rest_routes", "templates", "template_parts", "cli")}
    c["undocumented"] = sum(1 for f in sheet["functions"] if not f["documented"])
    c["unresolved"] = sheet["unresolved_count"]
    sheet["counts"] = c
    return sheet


# ── hiệu chuẩn: ca đúng và ca mồi, chạy trước mọi lần ghi ─────────────────────────────

CALIBRATION_PHP = r'''<?php
/**
 * Docblock của FILE — không được gán cho hàm bên dưới (ca mồi 2).
 */
defined( 'ABSPATH' ) || exit;
define( 'MYP_VERSION', '1.2.0' );
define( 'MYP_' . $dyn, 1 );

function myp_undocumented( $a, $b = 2 ) { return 1; }

/**
 * Tính giá sau hệ số.
 *
 * @param int $so
 */
function myp_price( $so, $rate = 1.1, ...$rest ) {
	// Cho phép plugin con chỉnh hệ số.
	return apply_filters( 'myp_rate', $rate, $so );
}
add_action( 'init', 'myp_init', 20 );
add_filter( 'myp_' . $x, 'myp_dyn' );
add_shortcode( 'myp_box', 'myp_box_render' );
add_action( 'wp_ajax_myp_save', 'myp_save' );
add_action( 'wp_ajax_nopriv_myp_save', 'myp_save' );
$s = get_option( 'myp_settings', array() );
update_option( 'myp_settings', $s );
$c = get_theme_mod( 'myp_color' );
wp_enqueue_script( 'myp-app', get_template_directory_uri() . '/app.js', array( 'jquery', 'wp-i18n' ), MYP_VERSION, true );
register_rest_route( 'myp/v1', '/items', array( 'methods' => 'GET', 'callback' => 'myp_items' ) );
get_template_part( 'template-parts/card', 'product' );
do_action( 'myp_after_render' );
?>
<script>
function myp_js_decoy() {}   // hàm JavaScript — KHÔNG phải hàm PHP (ca mồi 1)
</script>
'''
CALIBRATION_PY = '''
import argparse
ap = argparse.ArgumentParser()
sub = ap.add_subparsers(dest="cmd")
s = sub.add_parser("save", help="chép toàn cây")
s.add_argument("--source", required=True, help="cây gốc")
s.add_argument("--write", action="store_true")
'''


def calibrate():
    """Trả danh sách lỗi; rỗng là đã hiệu chuẩn. Mỗi khẳng định là một ca có tên."""
    import tempfile
    d = tempfile.mkdtemp(prefix="cheatsheet-cal-")
    with open(os.path.join(d, "functions.php"), "w", encoding="utf-8") as f:
        f.write(CALIBRATION_PHP)
    with open(os.path.join(d, "tool.py"), "w", encoding="utf-8") as f:
        f.write(CALIBRATION_PY)
    sh = build(d, ["myp_", "myp-"])
    errs = []
    def ok(cond, msg):
        if not cond:
            errs.append(msg)
    fn = {f["name"]: f for f in sh["functions"]}
    ok(set(fn) == {"myp_undocumented", "myp_price"}, f"functions: {sorted(fn)} (mồi 1: hàm JS phải bị bỏ)")
    ok(fn.get("myp_undocumented", {}).get("documented") is False, "mồi 2: docblock đầu file không được gán cho hàm")
    ok(fn.get("myp_price", {}).get("summary") == "Tính giá sau hệ số.", f"summary: {fn.get('myp_price', {}).get('summary')!r}")
    ok([p["name"] for p in fn.get("myp_price", {}).get("params", [])] == ["so", "rate", "rest"], "params thứ tự")
    ok(fn.get("myp_price", {}).get("params", [{}])[0].get("required") is True, "params: $so required")
    ok(fn.get("myp_price", {}).get("params", [{}, {}])[1].get("default") == "1.1", "params: default 1.1")
    hooks = {(h["name"], h["kind"]) for h in sh["hooks"]}
    ok(hooks == {("myp_rate", "filter"), ("myp_after_render", "action")}, f"hooks: {hooks}")
    rate = next((h for h in sh["hooks"] if h["name"] == "myp_rate"), {})
    ok(rate.get("arg_count") == 2 and rate.get("summary") == "Cho phép plugin con chỉnh hệ số.", f"hook arg_count/summary: {rate}")
    ok(any(r["hook"] == "init" and r["priority"] == 20 for r in sh["registrations"]), "registration init p20")
    ok([s["tag"] for s in sh["shortcodes"]] == ["myp_box"], "shortcode")
    ok(sorted((a["action"], a["is_public"]) for a in sh["ajax"]) == [("myp_save", False), ("myp_save", True)], f"ajax: {sh['ajax']}")
    ok([c["name"] for c in sh["constants"]] == ["MYP_VERSION"], f"constants: {sh['constants']}")
    opts = {(o["kind"], o["name"]): (o["read_count"], o["write_count"]) for o in sh["options"]}
    ok(opts == {("option", "myp_settings"): (1, 1), ("theme_mod", "myp_color"): (1, 0)}, f"options: {opts}")
    a = sh["assets"][0] if sh["assets"] else {}
    ok(a.get("handle") == "myp-app" and a.get("deps") == ["jquery", "wp-i18n"] and a.get("ver") == "MYP_VERSION", f"asset: {a}")
    ok(sh["rest_routes"] and sh["rest_routes"][0]["namespace"] == "myp/v1" and sh["rest_routes"][0]["route"] == "/items", "rest route")
    ok(sh["template_parts"] and sh["template_parts"][0]["slug"] == "template-parts/card" and sh["template_parts"][0]["name"] == "product", "template part")
    u = sh["unresolved"]
    ok(len(u["dynamic_hook"]) == 1 and len(u["dynamic_constant"]) == 1 and sh["unresolved_count"] == 2, f"unresolved: {sh['unresolved_count']} {u}")
    ok(sh["counts"]["undocumented"] == 1, "undocumented_count")
    cli = {(c["command"], c["flag"]) for c in sh["cli"]}
    ok(cli == {("save", ""), ("", "--source"), ("", "--write")}, f"cli: {cli}")
    ok(next((c["help"] for c in sh["cli"] if c["flag"] == "--source"), "") == "cây gốc", "cli help")
    ok([t["path"] for t in sh["templates"]] == ["functions.php"], f"templates: {sh['templates']}")
    return errs


# ── xuất ──────────────────────────────────────────────────────────────────────────────

def md_escape(s):
    return str(s if s is not None else "").replace("|", "\\|").replace("\n", " ")


def to_markdown(sh):
    L = [f"# Cheatsheet — `{sh['project']}`", "",
         "Sinh từ code bằng `wp-code-cheatsheet/scripts/cheatsheet.py`. Tên trong bảng là **hợp đồng** "
         "của dự án: đổi một tên là breaking change. `unresolved` là những chỗ tên dựng bằng biến — "
         "bảng không đoán, chỉ đếm.", ""]
    c = sh["counts"]
    L += ["| Object | Số mục |", "|---|---|"]
    for k in ("functions", "hooks", "registrations", "shortcodes", "ajax", "constants", "options", "assets",
              "rest_routes", "templates", "template_parts", "cli"):
        if c.get(k):
            L.append(f"| `{k}` | {c[k]} |")
    L += [f"| hàm chưa có mô tả | **{c['undocumented']}** / {c['functions']} |",
          f"| `unresolved` | **{c['unresolved']}** |", ""]
    if sh["functions"]:
        L += ["## `functions` — hàm của dự án", "", "| Tên | Tham số | Mô tả | Ở đâu |", "|---|---|---|---|"]
        for f in sh["functions"]:
            ps = ", ".join(("$" + p["name"] + (" = " + p["default"] if p["default"] is not None else "")) for p in f["params"])
            L.append(f"| `{f['name']}` | `{md_escape(ps)}` | {md_escape(f['summary']) or '_NO_DOC_'} | `{f['file']}:{f['line']}` |")
        L.append("")
    if sh["hooks"]:
        L += ["## `hooks` — hook dự án tự phát (plugin con móc vào đây)", "", "| Tên | Loại | Số tham số | Mô tả | Ở đâu |", "|---|---|---|---|---|"]
        for h in sh["hooks"]:
            L.append(f"| `{h['name']}` | {h['kind']} | {h['arg_count']} | {md_escape(h['summary']) or '_NO_DOC_'} | `{h['file']}:{h['line']}` |")
        L.append("")
    if sh["registrations"]:
        L += ["## `registrations` — callback đăng ký vào hook", "", "| Hook | Callback | Priority | Ở đâu |", "|---|---|---|---|"]
        for r in sh["registrations"]:
            L.append(f"| `{r['hook']}` | `{md_escape(r['callback'])}` | {r['priority']} | `{r['file']}:{r['line']}` |")
        L.append("")
    if sh["shortcodes"]:
        L += ["## `shortcodes`", "", "| Tag | Callback | Ở đâu |", "|---|---|---|"]
        L += [f"| `[{s['tag']}]` | `{md_escape(s['callback'])}` | `{s['file']}:{s['line']}` |" for s in sh["shortcodes"]] + [""]
    if sh["ajax"]:
        L += ["## `ajax` — action AJAX", "", "| Action | Khách vãng lai | Callback | Ở đâu |", "|---|---|---|---|"]
        L += [f"| `{a['action']}` | {'có (nopriv)' if a['is_public'] else 'không'} | `{md_escape(a['callback'])}` | `{a['file']}:{a['line']}` |" for a in sh["ajax"]] + [""]
    if sh["rest_routes"]:
        L += ["## `rest_routes`", "", "| Namespace | Route | Ở đâu |", "|---|---|---|"]
        L += [f"| `{r['namespace']}` | `{r['route']}` | `{r['file']}:{r['line']}` |" for r in sh["rest_routes"]] + [""]
    if sh["constants"]:
        L += ["## `constants`", "", "| Tên | Giá trị | Ở đâu |", "|---|---|---|"]
        L += [f"| `{k['name']}` | `{md_escape(k['value'])}`{'' if k['is_literal'] else ' (biểu thức)'} | `{k['file']}:{k['line']}` |" for k in sh["constants"]] + [""]
    if sh["options"]:
        L += ["## `options` — key lưu trong database (đổi tên là MẤT cài đặt)", "", "| Key | Loại | Đọc | Ghi | File |", "|---|---|---|---|---|"]
        L += [f"| `{o['name']}` | {o['kind']} | {o['read_count']} | {o['write_count']} | {', '.join('`' + f + '`' for f in o['files'])} |" for o in sh["options"]] + [""]
    if sh["assets"]:
        L += ["## `assets` — handle script/style", "", "| Handle | Loại | Phụ thuộc | Version | Ở đâu |", "|---|---|---|---|---|"]
        L += [f"| `{a['handle']}` | {a['asset_type']} | {', '.join('`' + d + '`' for d in a['deps']) or '—'} | `{md_escape(a['ver']) or '—'}` | `{a['file']}:{a['line']}` |" for a in sh["assets"]] + [""]
    if sh["templates"] or sh["template_parts"]:
        L += ["## `templates` · `template_parts`", ""]
        L += [f"- `{t['path']}`" for t in sh["templates"]]
        L += [f"- `get_template_part('{p['slug']}'{', ' + repr(p['name']) if p['name'] else ''})` — `{p['file']}:{p['line']}`" for p in sh["template_parts"]]
        L.append("")
    if sh["cli"]:
        L += ["## `cli` — cờ dòng lệnh (argparse)", "", "| Script | Lệnh con | Cờ | Mô tả |", "|---|---|---|---|"]
        L += [f"| `{c['script']}` | {('`' + c['command'] + '`') if c['command'] else ''} | {('`' + md_escape(c['flag']) + '`') if c['flag'] else ''} | {md_escape(c['help'])} |" for c in sh["cli"]] + [""]
    if sh["unresolved_count"]:
        L += [f"## `unresolved` — {sh['unresolved_count']} chỗ tên dựng bằng biến, bảng KHÔNG đoán", ""]
        for k, items in sh["unresolved"].items():
            for it in items:
                L.append(f"- `{k}` — `{it['file']}:{it['line']}` `{md_escape(it.get('expr', it.get('func', '')))}`")
        L.append("")
    return "\n".join(L)


def to_html(sh, template_path):
    tpl = read(template_path)
    data = json.dumps(sh, ensure_ascii=False).replace("</", "<\\/")
    return tpl.replace("__PROJECT__", sh["project"]).replace("__DATA__", data)


def write_text(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser(description="Bảng tra mọi tên một dự án phát ra ngoài.")
    ap.add_argument("--root", required=True, help="thư mục dự án (theme/plugin/repo)")
    ap.add_argument("--prefix", default="", help="tiền tố hàm/hằng/handle, ngăn bằng phẩy; rỗng = lấy hết")
    ap.add_argument("--out", help="ghi JSON")
    ap.add_argument("--md", help="ghi Markdown")
    ap.add_argument("--html", help="ghi HTML tự chứa (lọc, bấm mở)")
    a = ap.parse_args()
    prefixes = [p.strip() for p in a.prefix.split(",") if p.strip()]

    errs = calibrate()
    if errs:
        print("UNCALIBRATED — chính script chưa bắt đúng ca hiệu chuẩn, KHÔNG ghi gì:")
        for e in errs:
            print("   · " + e)
        return 2

    if not os.path.isdir(a.root):
        print(f"NOT_CHECKABLE: không có thư mục {a.root}")
        return 4
    sh = build(a.root, prefixes)
    if sh is None:
        print(f"NOT_CHECKABLE: không có file .php/.py nào trong {a.root}")
        return 4
    tpl = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cheatsheet_template.html")
    if a.html and not os.path.exists(tpl):
        print(f"NOT_CHECKABLE: thiếu {tpl}")
        return 4

    c = sh["counts"]
    print(f"CHEATSHEET  {sh['project']}  prefix={prefixes or 'tất cả'}")
    for k, v in c.items():
        if v or k in ("undocumented", "unresolved"):
            print(f"  {k:16s} {v}")
    if a.out:
        write_text(a.out, json.dumps(sh, ensure_ascii=False, indent=1) + "\n"); print(f"  -> {a.out}")
    if a.md:
        write_text(a.md, to_markdown(sh)); print(f"  -> {a.md}")
    if a.html:
        write_text(a.html, to_html(sh, tpl)); print(f"  -> {a.html}")
    if c["unresolved"]:
        print(f"  unresolved = {c['unresolved']}: bảng KHÔNG đoán tên dựng bằng biến — đọc mục unresolved trước khi tin bảng là đủ.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
