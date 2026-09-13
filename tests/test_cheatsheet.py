#!/usr/bin/env python3
"""Kiểm `wp-code-cheatsheet/scripts/cheatsheet.py` — bảng sinh từ code phải ĐÚNG code.

Ba nhóm khẳng định, mỗi nhóm hai chiều:
  · bảng ghi đúng những gì fixture có (tên, tham số, giá trị mặc định, priority, vị trí);
  · ca đối chứng ngược: xoá một file khỏi bản chép của fixture → mục của nó BIẾN MẤT, và
    số mục giảm đúng bằng số mục file đó đóng góp — không được "gần đúng";
  · chính bộ hiệu chuẩn của script phải ĐỎ khi ta làm hỏng một chốt (bỏ lọc <script>),
    vì một bộ hiệu chuẩn chưa từng đỏ không chứng minh được gì (§3).
Cộng: output tất định (hai lần chạy ra cùng byte), fail-closed (cây rỗng → exit 4),
Markdown/HTML có chứa đúng tên, và ba định dạng cùng một số đếm.

    python tests/test_cheatsheet.py
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GOC = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(GOC)
SCRIPT = os.path.join(REPO, "skills", "wp-code-cheatsheet", "scripts", "cheatsheet.py")
FX = os.path.join(GOC, "integration", "fixture-bien-doi")

dat, hong = [], []


def kiem(ten, ok, chi_tiet=""):
    (dat if ok else hong).append((ten, chi_tiet))
    print(f"  {'đạt ' if ok else 'HỎNG'}  {ten}" + (f"\n          {chi_tiet}" if not ok else ""))


def chay(*args):
    r = subprocess.run([sys.executable, SCRIPT] + list(args), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def load_module():
    spec = importlib.util.spec_from_file_location("cheatsheet", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    tmp = tempfile.mkdtemp(prefix="cheatsheet-")
    try:
        return run(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run(tmp):
    print("=" * 70)
    print("CHEATSHEET — bảng sinh từ code phải đúng code")
    print("=" * 70)

    print("\n[1] Fixture fixture-bien-doi, prefix fxb_")
    out, md, html = (os.path.join(tmp, f) for f in ("cs.json", "CS.md", "cs.html"))
    ma, ra = chay("--root", FX, "--prefix", "fxb_,fxb-", "--out", out, "--md", md, "--html", html)
    kiem("exit 0", ma == 0, ra[-500:])
    sh = json.load(open(out, encoding="utf-8"))
    fn = {f["name"]: f for f in sh["functions"]}
    kiem("10 hàm fxb_ được liệt kê", len(fn) == 10, sorted(fn))
    g = fn.get("fxb_gia", {})
    kiem("fxb_gia: tham số có thứ tự + mặc định 1.1 + $so bắt buộc",
         [p["name"] for p in g.get("params", [])] == ["so", "ty_le"]
         and g["params"][1]["default"] == "1.1" and g["params"][0]["required"] is True, g)
    kiem("fxb_gia: docblock đầu file KHÔNG bị gán cho hàm (documented=false)", g.get("documented") is False, g)
    kiem("fxb_gia ở inc/tham-so.php:18", (g.get("file"), g.get("line")) == ("inc/tham-so.php", 18), g)
    regs = {(r["hook"], r["callback"], r["priority"]) for r in sh["registrations"]}
    kiem("init p20 đăng ký hai callback fxb_init_a/fxb_init_b",
         {("init", "fxb_init_a", 20), ("init", "fxb_init_b", 20)} <= regs, regs)
    kiem("wp_head p5 fxb_meta_som", ("wp_head", "fxb_meta_som", 5) in regs, regs)
    kiem("callback ghép chuỗi giữ NGUYÊN biểu thức, không đoán",
         any(r["callback"] == "'fxb_' . 'dong_b'" for r in sh["registrations"]), regs)
    kiem("hook tên biến → unresolved.dynamic_hook = 1, unresolved_count = 1",
         len(sh["unresolved"]["dynamic_hook"]) == 1 and sh["unresolved_count"] == 1, sh["unresolved"])
    # Tên hằng của fixture là tiếng Việt có chủ ý (fixture = theme thật giả lập, rename.py
    # không đụng). Đọc thẳng từ define() trong functions.php thay vì chép tên vào đây.
    import re
    fx_src = open(os.path.join(FX, "functions.php"), encoding="utf-8").read()
    defined = dict(re.findall(r"define\( '(\w+)', (.+?) \);", fx_src))
    got = {c["name"]: c for c in sh["constants"]}
    kiem("mọi define() trong functions.php đều có mặt (2 hằng)", set(got) == set(defined) and len(defined) == 2, (sorted(got), sorted(defined)))
    kiem("hằng giá trị '1.0.0' là literal, hằng gọi hàm là biểu thức",
         all(got[n]["is_literal"] == (v.startswith("'")) for n, v in defined.items()), got)
    ver_const = next(n for n, v in defined.items() if v.startswith("'"))
    kiem("asset fxb-main style, ver = tên hằng version",
         any(a["handle"] == "fxb-main" and a["asset_type"] == "style" and a["ver"] == ver_const for a in sh["assets"]),
         sh["assets"])
    kiem("template part template-parts/bo-phan", [p["slug"] for p in sh["template_parts"]] == ["template-parts/bo-phan"], sh["template_parts"])
    kiem("counts khớp danh sách", sh["counts"]["functions"] == len(sh["functions"])
         and sh["counts"]["undocumented"] == sum(1 for f in sh["functions"] if not f["documented"]), sh["counts"])

    print("\n[2] Ba định dạng nói cùng một điều")
    md_s = open(md, encoding="utf-8").read()
    html_s = open(html, encoding="utf-8").read()
    kiem("Markdown có fxb_gia với chữ ký", "`fxb_gia` | `$so, $ty_le = 1.1`" in md_s)
    kiem("Markdown đếm đúng: 10 hàm, unresolved 1", "| `functions` | 10 |" in md_s and "| `unresolved` | **1** |" in md_s)
    kiem("HTML nhúng JSON đầy đủ (không phải bản tóm tắt)", '"fxb_gia"' in html_s and '"unresolved_count": 1'.replace(": ", ":") in html_s.replace(": ", ":"))
    kiem("HTML tự chứa: không script ngoài, có charset", "<script src=" not in html_s and 'charset="utf-8"' in html_s)

    print("\n[3] Tất định: chạy lại ra cùng byte")
    out2 = os.path.join(tmp, "cs2.json"); md2 = os.path.join(tmp, "CS2.md")
    chay("--root", FX, "--prefix", "fxb_,fxb-", "--out", out2, "--md", md2)
    kiem("JSON hai lần giống nhau", open(out, "rb").read() == open(out2, "rb").read())
    kiem("Markdown hai lần giống nhau", open(md, "rb").read() == open(md2, "rb").read())

    print("\n[4] Đối chứng ngược: xoá inc/tham-so.php → fxb_gia biến mất, đếm giảm đúng 1")
    copy = os.path.join(tmp, "fx-copy")
    shutil.copytree(FX, copy)
    os.remove(os.path.join(copy, "inc", "tham-so.php"))
    out3 = os.path.join(tmp, "cs3.json")
    ma, ra = chay("--root", copy, "--prefix", "fxb_,fxb-", "--out", out3)
    sh3 = json.load(open(out3, encoding="utf-8"))
    kiem("fxb_gia không còn", "fxb_gia" not in {f["name"] for f in sh3["functions"]})
    kiem("functions 10 → 9, các mục khác không đổi",
         sh3["counts"]["functions"] == 9 and {k: v for k, v in sh3["counts"].items() if k not in ("functions", "undocumented")}
         == {k: v for k, v in sh["counts"].items() if k not in ("functions", "undocumented")}, (sh["counts"], sh3["counts"]))

    print("\n[5] Fail-closed")
    empty = os.path.join(tmp, "empty"); os.makedirs(empty)
    ma, ra = chay("--root", empty, "--out", os.path.join(tmp, "x.json"))
    kiem("cây không có .php/.py → NOT_CHECKABLE exit 4, không ghi file",
         ma == 4 and "NOT_CHECKABLE" in ra and not os.path.exists(os.path.join(tmp, "x.json")), ra[-300:])
    ma, ra = chay("--root", os.path.join(tmp, "khong-co"), "--out", os.path.join(tmp, "y.json"))
    kiem("thư mục không tồn tại → exit 4", ma == 4, ra[-300:])

    print("\n[6] Bộ hiệu chuẩn của chính script phải ĐỎ khi làm hỏng một chốt")
    m = load_module()
    kiem("nguyên bản: calibrate() rỗng", m.calibrate() == [], m.calibrate())
    goc = m.strip_script
    m.strip_script = lambda s: s  # bỏ lọc <script> → hàm JS lọt vào bảng
    errs = m.strip_script and m.calibrate()
    m.strip_script = goc
    kiem("bỏ lọc <script> → calibrate() đỏ đúng ca 'mồi 1'", any("mồi 1" in e for e in errs), errs)
    goc_re = m.RE_FUNC
    import re
    m.RE_FUNC = re.compile(r"(?:/\*\*(?P<doc>.*?)\*/\s*)?^[ \t]*function[ \t]+(?P<name>[A-Za-z_][A-Za-z0-9_]*)[ \t]*(?=\()", re.M | re.S)
    errs = m.calibrate()
    m.RE_FUNC = goc_re
    kiem("docblock lazy (nuốt code giữa hai docblock) → calibrate() đỏ đúng ca 'mồi 2'", any("mồi 2" in e for e in errs), errs)
    kiem("phục hồi xong, calibrate() lại rỗng", m.calibrate() == [])

    print("\n[7] Python argparse trên chính repo")
    out4 = os.path.join(tmp, "self.json")
    ma, ra = chay("--root", os.path.join(REPO, "skills", "code-optimize", "scripts"), "--out", out4)
    sh4 = json.load(open(out4, encoding="utf-8"))
    cli = {(c["script"], c["command"], c["flag"]) for c in sh4["cli"]}
    kiem("backup.py: ba lệnh con save/check/restore",
         {("backup.py", "save", ""), ("backup.py", "check", ""), ("backup.py", "restore", "")} <= cli, sorted(cli)[:10])
    kiem("rename.py: cờ --old có help", any(c["script"] == "rename.py" and c["flag"] == "--old" and c["help"] for c in sh4["cli"]))

    print("\n" + "=" * 70)
    print(f"đạt {len(dat)} · hỏng {len(hong)}")
    print("=" * 70)
    return 1 if hong else 0


if __name__ == "__main__":
    sys.exit(main())
