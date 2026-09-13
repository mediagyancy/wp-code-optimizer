#!/usr/bin/env python3
"""CHECK NAMES — luật đặt tên của repo là luật CỨNG, và đây là chốt giữ nó.

Luật (CLAUDE.md §1), do chủ repo chốt ngày 13/09/2026, đảo ngược bản nháp trước đó:

  · Tên phát ra ngoài — key JSON/dict/array, cờ CLI, mã lý do, tên file script — bằng
    **tiếng Anh chuẩn quốc tế**, snake_case (cờ: kebab-case, mã: UPPER_SNAKE).
  · Mỗi cụm trong tên phải **mang nghĩa**: cấm từ đệm (`data`, `info`, `tmp`, `obj`,
    `misc`, `helper`, `util`, `foo`…).
  · **Cấm tên quá dài**: tối đa 4 cụm và 24 ký tự (không tính `--`).
  · Đếm = hậu tố `_count` (Haravan: `articles_count`), tổng = tiền tố `total_`.
    Cấm `num_`, `number_of_`, `n_`.
  · Object trước, thuộc tính sau — lồng (`counts.static_hooks`) thay vì xếp tiền tố.
  · Mã lý do là một MỆNH ĐỀ về trạng thái (`NOT_CHECKABLE`, `GRAPH_UNTRUSTED`), không
    phải `ERROR`/`FAILED`/`OK`.

Bản nháp trước chọn tiếng Việt không dấu — sai, và chủ repo đã bác. File này thay
`check_names.py`; baseline nợ đảo chiều: tên tiếng Việt cũ là nợ, khoanh trong
`tests/names-baseline.json`, ratchet chỉ được giảm.

Tự hiệu chuẩn trước khi tin: gieo ca hỏng đã biết, chốt phải bắt; gieo ca đúng, chốt
phải im. Không đạt thì UNCALIBRATED và không kiểm gì cả.

    python tests/check_names.py            # kiểm
    python tests/check_names.py --update   # ghi lại baseline sau khi TRẢ nợ
"""
import argparse
import io
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
BASELINE = os.path.join(ROOT, "names-baseline.json")
REFERENCE = os.path.join(REPO, "docs", "REFERENCE.md")

# Lane mới: nợ = 0 và bảng tham chiếu phải phủ hết.
NEW_LANE = (
    "skills/code-optimize/scripts",
    "skills/wp-preview-builder/scripts",
    "skills/wp-code-cheatsheet/scripts",
    "tests/integration/dna.php",
    "tests/integration/tier5.py",
    "tests/integration/capture_dna.py",
    "tests/integration/switch_theme.php",
)

MAX_TOKENS = 4
MAX_CHARS = 24

# Âm tiết tiếng Việt không dấu đã/đang xuất hiện trong tên của repo. Cố ý loại những âm
# tiết trùng từ tiếng Anh hợp lệ (`hang`, `loc`, `bat`, `ten`, `den`, `man`, `may`, `tin`,
# `van`, `no`, `on`, `am`, `an`, `do`, `in`, `me`, `to`, `go`) để không báo sai tên Anh.
# Mỗi âm tiết mang tiền tố `z` và được bỏ khi nạp — để rename.py (quét theo ranh giới từ)
# không đổi được chính danh sách này. Batch 13/09 đã đổi `bo_qua`→`excluded` NGAY TRONG
# danh sách, khiến linter gọi `excluded`, `note`, `required` là tiếng Việt.
VIETNAMESE = {w[1:] for w in """
znap zchua zgiai ztong zvung zmu znoi zqua zchi ztinh znguon zdong zghi zchu zky zham zbien
zthu zpham zthat zda zbo zvi zvo zhai zdang znhap zcho zdoi zcu zmoi zdat zma zkiem zluu
zphuc zhoi zthem zthieu zkhac zkhong zduoc zchay zlai ztran zngang znho znhat zcham zduoi
zdau zsau ztruoc zgia ztri zmac zdinh zbuoc zuu ztien zthuc zte zyeu zcau zsach zgoc zcay
zra zvao ztoi zgioi zhan zmo zta zket zlech zdem znut zcanh zkhai zphat zphu zthuoc zmau
zdung zsai zhieu zchuan zchot zcong zdieu zkien zchan zluat zso zphien zban ztruong ztheo
ztu znhan zbang zchung zbai zxoa zquet zchet zung zvien znen zsu zduong zdan zxac zminh
zbao zcap zgiu znguyen zkhoi ztam zlam zlan zluot zde zlen znghi zlop ztim zrieng ztap zhop
zqua zgop zdoi ztheme_slug
""".split()}

FILLER = {"data", "info", "tmp", "temp", "obj", "misc", "stuff", "thing", "things", "helper",
          "util", "utils", "foo", "bar", "baz", "var", "val", "generic"}

RE_KEY_PY_PHP = re.compile(r"""(?:(?<=[{,(])\s*|(?m:^)[ \t]*)["']([A-Za-z_][A-Za-z0-9_-]*)["']\s*(?::|=>)(?!=)""")
RE_KEY_JS = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(?!:)", re.M)
RE_FLAG = re.compile(r"""add_argument\(\s*["'](--[A-Za-z0-9-]+)["']""")
RE_CODE = re.compile(r"""["']([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)(?=["'\s:—])""")

# Tên KHÔNG do repo đặt: superglobal PHP, header HTTP, khoá WordPress, thuộc tính trình duyệt
FOREIGN = {
    "HTTP_HOST", "SERVER_NAME", "REQUEST_METHOD", "REQUEST_URI", "SCRIPT_NAME",
    "PYTHONIOENCODING", "function", "accepted_args", "callbacks", "__main__",
    "Content-Type", "User-Agent", "Accept-Encoding", "GLOBALS",
    "post_type", "posts_per_page", "DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST",
    "clientWidth", "innerWidth", "scrollWidth",
    # Cờ của script PHP đọc qua $argv (`--theme-slug=`, `--phase=`): kebab-case là đúng cho cờ.
    "theme-slug", "phase",
}
# Bốn nhãn bằng chứng có trước luật, giữ nguyên.
EVIDENCE_LABELS = {"CONCEPT_PREVIEW", "VISUAL_PASS", "PRODUCTION_VERIFIED", "NOT_TESTED",
                   "RUNTIME_NOT_TESTED"}


def rel(p):
    return os.path.relpath(p, REPO).replace(os.sep, "/")


def in_new_lane(r):
    return any(r == x or r.startswith(x + "/") for x in NEW_LANE)


def tokens_of(name):
    return [t for t in re.split(r"[_-]+", name.lower()) if t]


def violations(name, kind):
    """Danh sách lý do vi phạm của MỘT tên. Rỗng = hợp lệ."""
    out = []
    body = name.lstrip("-") if kind == "flag" else name
    if kind == "flag":
        if not re.fullmatch(r"[a-z][a-z0-9]*(-[a-z0-9]+)*", body):
            out.append("flag must be lowercase kebab-case")
    elif kind == "code":
        if not re.fullmatch(r"[A-Z][A-Z0-9]*(_[A-Z0-9]+)+", name):
            out.append("reason code must be UPPER_SNAKE")
    else:
        if re.fullmatch(r"[A-Z][A-Z0-9]*(_[A-Z0-9]+)+", name):
            return violations(name, "code")     # key viết HOA là mã lý do đặt làm key
        if not re.fullmatch(r"[a-z][a-z0-9]*(_[a-z0-9]+)*", name):
            out.append("key must be lowercase snake_case")
    if name in EVIDENCE_LABELS:
        return out
    toks = tokens_of(body)
    vi = [t for t in toks if t in VIETNAMESE]
    if vi:
        out.append("Vietnamese: " + ",".join(vi))
    fill = [t for t in toks if t in FILLER]
    if fill:
        out.append("filler word: " + ",".join(fill))
    if len(toks) > MAX_TOKENS or len(body) > MAX_CHARS:
        out.append(f"too long ({len(toks)} tokens, {len(body)} chars; max {MAX_TOKENS}/{MAX_CHARS})")
    if toks and toks[0] in ("num", "n", "number") or toks[:2] == ["number", "of"]:
        out.append("counts use suffix _count, totals use prefix total_")
    return out


def strip_comments(s, ext):
    def blank(m):
        return re.sub(r"[^\n]", " ", m.group(0))
    if ext == ".py":
        s = re.sub(r"(?m)^[ \t]*#.*$", blank, s)
        s = re.sub(r'"""[\s\S]*?"""', blank, s)
    else:
        s = re.sub(r"/\*[\s\S]*?\*/", blank, s)
        s = re.sub(r"(?m)(?<![:\\])//.*$", blank, s)
    return s


def scan_text(s, ext=".py"):
    """Trả danh sách (name, kind, line) tìm thấy trong một chuỗi mã nguồn."""
    s = strip_comments(s, ext)
    out = []

    def line_of(i):
        return s.count("\n", 0, i) + 1

    if ext in (".py", ".php"):
        for m in RE_KEY_PY_PHP.finditer(s):
            k = m.group(1)
            if k in FOREIGN or k.startswith("--"):
                continue
            out.append((k, "key", line_of(m.start())))
    if ext == ".js":
        for m in RE_KEY_JS.finditer(s):
            k = m.group(1)
            if k in FOREIGN or k in ("const", "let", "var", "return", "case", "default"):
                continue
            out.append((k, "key", line_of(m.start())))
    if ext == ".py":
        for m in RE_FLAG.finditer(s):
            out.append((m.group(1), "flag", line_of(m.start())))
    for m in RE_CODE.finditer(s):
        k = m.group(1)
        if k in FOREIGN:
            continue
        out.append((k, "code", line_of(m.start())))
    return out


def scan_file(p):
    return scan_text(io.open(p, encoding="utf-8", errors="replace").read(), os.path.splitext(p)[1])


def list_files():
    out = []
    for top in ("skills", "tests"):
        for dp, dn, fn in os.walk(os.path.join(REPO, top)):
            dn[:] = [d for d in dn if d not in ("__pycache__", "fixture-theme", "fixture-bien-doi",
                                                 ".wp-it", "fixtures")]
            for f in fn:
                if f.endswith((".py", ".php", ".js")) and f != os.path.basename(__file__):
                    out.append(os.path.join(dp, f))
    return sorted(out)


def names_in_reference(text):
    """Mọi token tên bên trong bất kỳ cặp backtick nào — bảng viết kiểu Haravan
    (`nodes[].kind`, `--out graph.json`, `{sha256, bytes}`), tên không cần đứng một mình."""
    out = set()
    for span in re.findall(r"`([^`]+)`", text):
        out.update(re.findall(r"(?<![A-Za-z0-9_-])(--?[A-Za-z][A-Za-z0-9_-]*|[A-Za-z_][A-Za-z0-9_]*)", span))
    return out


def calibrate():
    # Ca hỏng ghép bằng phép cộng chuỗi để rename.py (quét theo ranh giới từ) KHÔNG đổi
    # chúng sang tên Anh — batch 13/09 đã làm đúng thế và biến bộ hiệu chuẩn thành vô nghĩa.
    V = lambda *parts: "_".join(parts)
    bad = [
        (V("file", "nap", "sau", "render"), "key"), (V("so", "file"), "key"),
        (V("KHONG", "KIEM", "DUOC"), "code"), ("--" + "tien-to", "flag"),
        (V("chua", "giai"), "key"), (V("hook", "tong", "so"), "key"),
        ("camelCase", "key"), (V("tmp", "data"), "key"), (V("number", "of", "files"), "key"),
        (V("ignored", "because", "harmless", "elements"), "key"), ("--" + "chap-nhan-mu", "flag"),
    ]
    good = [
        ("files_after_render", "key"), ("file_count", "key"), ("NOT_CHECKABLE", "code"),
        ("--prefix", "flag"), ("unresolved", "key"), ("total_bytes", "key"), ("sha256", "key"),
        ("PROBE_VERSION", "code"), ("STATIC_CHECKS_PASSED", "code"), ("--write-baseline", "flag"),
        ("GRAPH_UNTRUSTED", "code"), ("MEASURE_ERROR", "key"), ("NOT_TESTED", "code"),
        ("theme_hooks", "key"), ("accepted_args", "key"),
    ]
    for n, k in bad:
        if not violations(n, k):
            return False, f"did not catch known-bad: {n}"
    for n, k in good:
        if violations(n, k):
            return False, f"false alarm on known-good: {n} -> {violations(n, k)}"
    if [t for t, k, _ in scan_text('if os.name != "nt":\n    pass') if k == "key"]:
        return False, 'scanned `!= "nt":` as a key'
    found = [t for t, k, _ in scan_text('d = {"file_count": 1,\n     "total_bytes": 2}') if k == "key"]
    if found != ["file_count", "total_bytes"]:
        return False, "missed keys in dict literal: " + str(found)
    ref = names_in_reference("| `counts.static_hooks` | | `--graph g.json` | `{sha256, bytes}` |")
    if not {"static_hooks", "--graph", "sha256", "bytes"} <= ref:
        return False, "reference parser missed Haravan-style names: " + str(sorted(ref))
    if "blind_spot_count" in ref:
        return False, "reference parser reports a name that is not there"
    return True, ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--update", action="store_true", help="rewrite the debt baseline")
    a = ap.parse_args()

    ok, why = calibrate()
    if not ok:
        print("UNCALIBRATED: " + why)
        return 2

    baseline = json.load(io.open(BASELINE, encoding="utf-8")) if os.path.isfile(BASELINE) else {}
    ref_text = io.open(REFERENCE, encoding="utf-8").read() if os.path.isfile(REFERENCE) else ""
    ref_names = names_in_reference(ref_text)

    bad_by_file, missing_ref, seen = {}, {}, set()
    for p in list_files():
        r = rel(p)
        for name, kind, line in scan_file(p):
            seen.add(name)
            v = violations(name, kind)
            if v:
                bad_by_file.setdefault(r, []).append((name, kind, line, "; ".join(v)))
            if in_new_lane(r) and name not in ref_names and not v:
                missing_ref.setdefault(r, []).append(name)

    counts = {f: len(v) for f, v in bad_by_file.items()}
    red = []
    for f, n in sorted(counts.items()):
        allowed = baseline.get(f, 0)
        if n > allowed:
            red.append((f, n, allowed, "DEBT GREW"))
        elif n < allowed and not a.update:
            red.append((f, n, allowed, "debt shrank but baseline not updated — run --update"))
    for f, allowed in sorted(baseline.items()):
        if f not in counts and allowed > 0 and not a.update:
            red.append((f, 0, allowed, "debt reached 0 but baseline not updated"))

    print("=" * 72)
    print("CHECK NAMES — rule: CLAUDE.md §1 · reference: docs/REFERENCE.md")
    print("=" * 72)
    total_bad, total_debt = sum(counts.values()), sum(baseline.values())
    print(f"  names scanned: {len(seen)} · violations now: {total_bad} · debt allowed: {total_debt}")

    if red:
        print("\nRATCHET RED:")
        for f, n, allowed, why in red:
            print(f"  {f}: {n} violations, allowed {allowed} — {why}")
            for name, kind, line, v in bad_by_file.get(f, [])[:8]:
                print(f"       :{line}  {name}  [{kind}]  {v}")
    if missing_ref:
        print("\nREFERENCE MISSING NAMES (new lane must be fully covered):")
        for f, names in sorted(missing_ref.items()):
            u = sorted(set(names))
            print(f"  {f}: {len(u)} — " + ", ".join(u[:12]) + (" …" if len(u) > 12 else ""))

    if a.update:
        with io.open(BASELINE + ".tmp", "w", encoding="utf-8", newline="\n") as f:
            json.dump(dict(sorted(counts.items())), f, ensure_ascii=False, indent=2)
        os.replace(BASELINE + ".tmp", BASELINE)
        print(f"\nBASELINE WRITTEN: {len(counts)} files, {total_bad} violations recorded as debt")
        return 0

    new_lane_bad = sum(n for f, n in counts.items() if in_new_lane(f))
    if not red and not missing_ref:
        print(f"\n  new lane: {new_lane_bad} violations (must be 0) · legacy: debt did not grow")
        print("=" * 72)
        return 0 if new_lane_bad == 0 else 1
    print("=" * 72)
    return 1


if __name__ == "__main__":
    sys.exit(main())
