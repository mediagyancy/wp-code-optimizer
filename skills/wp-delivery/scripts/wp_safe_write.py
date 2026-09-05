#!/usr/bin/env python3
"""Ghi file nguồn WordPress mà không có trạng thái nửa vời.

Vì sao tồn tại: một script từng mở functions.php ở chế độ ghi rồi lỗi trước khi
kịp ghi. Mở mode "w" cắt trắng file NGAY LẬP TỨC, nên nội dung mất sạch và site
chết trắng. File này làm đúng thứ tự an toàn:

    đọc → backup → ghi ra file tạm cùng thư mục → kiểm tĩnh → đổi tên đè → đọc lại so hash

Đổi tên là thao tác nguyên tử: hoặc file cũ nguyên vẹn, hoặc file mới hoàn chỉnh.

PHẠM VI BẢO ĐẢM — đọc kỹ trước khi tin kết quả:

    Script này chỉ chứng minh được HAI điều: file đã ghi nguyên tử, và bản mới
    qua được các phép kiểm TĨNH (không rỗng, `php -l` hoặc cân bằng ngoặc, hash
    sau ghi khớp).

    Nó KHÔNG chứng minh gì về hành vi lúc chạy. `php -l` không bắt được: gọi hàm
    plugin trước khi plugin sẵn sàng, `require` hai lần, trùng tên hàm/class,
    hook sai thời điểm, hay thứ tự nạp sai. Những lỗi đó chỉ lộ ra khi WordPress
    thật sự chạy file.

    Vì vậy exit code 0 có nghĩa "ghi xong và kiểm tĩnh không phát hiện lỗi".
    Nó KHÔNG có nghĩa "an toàn để deploy", càng không phải PRODUCTION_VERIFIED.

Dùng như thư viện:
    from wp_safe_write import safe_write
    safe_write("theme/inc/pricing.php", noi_dung_moi)
    safe_write("theme/inc/bootstrap.php", noi_dung_moi, loader=True)   # nạp file khác

Dùng như lệnh (đọc nội dung mới từ stdin):
    cat moi.php | python wp_safe_write.py theme/functions.php
    cat moi.php | python wp_safe_write.py --loader theme/inc/bootstrap.php
    python wp_safe_write.py --check theme/functions.php     # chỉ kiểm, không ghi
"""
import hashlib, os, shutil, subprocess, sys, time

sys.stdout.reconfigure(encoding="utf-8")

# Hai tên này là loader theo định nghĩa của WordPress, không phải phỏng đoán.
# Mọi file nạp-file-khác khác phải do người gọi khai bằng loader=True / --loader:
# đoán bootstrap từ tên file sẽ vừa sót vừa báo nhầm.
KNOWN_LOADERS = {"functions.php", "wp-config.php"}


class UnsafeWrite(Exception):
    """Bản mới không qua được phép kiểm tĩnh. File gốc còn nguyên."""


class RequiredCheckUnavailable(Exception):
    """Loại file này CÓ phép kiểm bắt buộc, nhưng phép kiểm đó không chạy được.

    Fail-closed: thà không ghi còn hơn ghi mù. Nếu máy thiếu `php`, việc ghi
    functions.php mà không có `php -l` chính là đường đưa lỗi cú pháp vào file
    sống — đúng thứ script này sinh ra để chặn.
    """


# Đuôi file → tên phép kiểm BẮT BUỘC. Có tên ở đây mà không chạy được → từ chối ghi.
# Đuôi không có trong bảng → không có phép kiểm nào được quy định → cho ghi, báo SKIPPED.
REQUIRED_CHECKS = {".php": "php -l"}


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def check_php(path):
    php = shutil.which("php")
    if not php:
        return None, "không có PHP trên máy — chưa chạy được php -l"
    r = subprocess.run([php, "-l", path], capture_output=True, text=True)
    if r.returncode == 0:
        # Không in lại đường dẫn: phép kiểm chạy trên file TẠM, in ra dễ tưởng kiểm nhầm file.
        return True, "php -l không thấy lỗi cú pháp"
    # Khi lỗi thì giữ nguyên văn (có số dòng), chỉ bỏ tên file tạm cho đỡ rối.
    err = (r.stdout + r.stderr).strip().replace(path, os.path.basename(path).split(".tmp-")[0])
    return False, err


def _strip_noise(t, css):
    """Bỏ comment và chuỗi để ngoặc nằm trong đó không bị đếm nhầm."""
    out, i, n = [], 0, len(t)
    while i < n:
        c = t[i]
        if c == "/" and i + 1 < n and t[i + 1] == "*":
            j = t.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if not css and c == "/" and i + 1 < n and t[i + 1] == "/":
            j = t.find("\n", i)
            i = n if j < 0 else j
            continue
        if c in "\"'":
            q, i = c, i + 1
            while i < n and t[i] != q:
                i += 2 if t[i] == "\\" else 1
            i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


def check_braces(path, css=False):
    """Kiểm CẤU TRÚC ngoặc, không chỉ đếm tổng.

    ĐÃ TRẢ GIÁ (01/09/2026): một bản vá CSS cắt nhầm mốc kết thúc khối media —
    lấy dấu } đóng của một rule thay vì dấu } đóng của cả @media. Khối media bị
    nhét vào giữa một media khác, và toàn bộ CSS phía sau rơi vào trong nó nên
    chỉ áp ở màn hẹp; ở desktop cả một section mất sạch style. Tổng ngoặc vẫn
    243/243 vì chỗ này thiếu một dấu đóng thì chỗ kia thừa đúng một dấu —
    **cân bằng giả**. Đếm tổng là phép kiểm mù trước đúng loại lỗi mà việc
    cắt-dán chuỗi hay gây ra nhất.

    Ba chốt thay cho một:
      1. tổng { = tổng }
      2. độ sâu không bao giờ âm  → bắt dấu } mồ côi giữa file
      3. (CSS) không có at-rule nào nằm trong khối khác → bắt khối media bị nuốt

    Chốt 3 chỉ áp cho CSS và có thể tắt bằng biến môi trường
    WP_ALLOW_NESTED_AT=1 nếu dự án dùng CSS Nesting thật.
    """
    raw = open(path, encoding="utf-8", errors="replace").read()
    t = _strip_noise(raw, css)
    o, c = t.count("{"), t.count("}")
    if o != c:
        return False, f"lệch ngoặc: {o} mở / {c} đóng"

    allow_nested = os.environ.get("WP_ALLOW_NESTED_AT") == "1"
    depth, line = 0, 1
    nested_at = []
    for k, ch in enumerate(t):
        if ch == "\n":
            line += 1
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                return False, f"dấu }} mồ côi ở dòng ~{line} (đóng nhiều hơn mở)"
        elif css and ch == "@" and depth > 0 and not allow_nested:
            word = t[k:k + 10].split("{")[0].strip().lower()
            if word.startswith(("@media", "@supports", "@layer", "@container")):
                nested_at.append(line)
    if depth != 0:
        return False, f"còn {depth} khối chưa đóng ở cuối file"
    if nested_at:
        return False, (f"at-rule lồng trong khối khác ở dòng ~{nested_at[:3]} — "
                       "thường là dấu hiệu một @media bị thiếu dấu đóng và nuốt phần sau "
                       "(đặt WP_ALLOW_NESTED_AT=1 nếu dự án dùng CSS Nesting thật)")
    return True, f"{o} cặp ngoặc cân · không có dấu đóng mồ côi · không có at-rule bị nuốt"


def verify(path, as_ext=None):
    """Kiểm nội dung của `path`, chọn phép kiểm theo `as_ext`.

    `as_ext` tồn tại vì ta kiểm trên file TẠM (đuôi .tmp-1234) trong khi phép kiểm
    phải theo đuôi của file ĐÍCH. Bỏ tham số này là mọi phép kiểm im lặng bị bỏ qua —
    đã mắc đúng lỗi đó một lần.

    Trả về (trạng thái, mô tả) với trạng thái là một trong bốn:
        "pass"        — phép kiểm chạy và không thấy lỗi
        "fail"        — phép kiểm chạy và thấy lỗi
        "unavailable" — loại file này CÓ phép kiểm bắt buộc nhưng không chạy được
        "no_checker"  — không có phép kiểm nào được quy định cho loại file này

    Hai trạng thái cuối khác nhau về bản chất và phải xử lý khác nhau:
    "unavailable" là vùng mù ở chỗ ta đã biết là nguy hiểm → từ chối ghi.
    "no_checker" là loại file ta chưa quy định phép kiểm → cho ghi, nói rõ là chưa kiểm.
    """
    ext = (as_ext or os.path.splitext(path)[1]).lower()
    if ext == ".php":
        ok, msg = check_php(path)
        if ok is None:
            return "unavailable", msg
        return ("pass" if ok else "fail"), msg
    if ext in (".css", ".js", ".scss"):
        ok, msg = check_braces(path, css=ext in (".css", ".scss"))
        return ("pass" if ok else "fail"), msg
    return "no_checker", f"chưa quy định phép kiểm tĩnh cho đuôi {ext or '(trống)'}"


def _report(path, nbytes, state, msg, is_loader, bak):
    """In trạng thái. Mỗi dòng nói đúng một điều đã hoặc chưa được chứng minh."""
    print(f"WRITE_OK                — {path} ({nbytes} byte), ghi nguyên tử qua file tạm")
    if bak:
        print(f"                          backup: {bak}")
    if state == "pass":
        print(f"STATIC_CHECKS_PASSED    — không rỗng · {msg} · hash sau ghi khớp")
    else:
        print(f"STATIC_CHECKS_SKIPPED   — không rỗng · hash sau ghi khớp · {msg}")
        print("                          (loại file này chưa có phép kiểm nào được quy định)")
    print("RUNTIME_NOT_TESTED      — chưa kiểm thứ tự nạp, dependency, hook, trùng tên hàm,")
    print("                          hay bất kỳ hành vi nào của WordPress lúc chạy")
    if is_loader:
        print()
        print("  ╔═══════════════════════════════════════════════════════════════════════╗")
        print("  ║  FILE NÀY NẠP FILE KHÁC — hỏng là hỏng toàn site, không hỏng một trang ║")
        print("  ╚═══════════════════════════════════════════════════════════════════════╝")
        print("  Lên trước các file nó nạp → màn hình trắng.")
        print("  Lên sau file dùng nó      → chết riêng bề mặt dùng chức năng đó.")
    print("NEXT                    — sau khi deploy, tự tay smoke-test:")
    print("                          · một URL CHẠY chức năng vừa đụng")
    print("                          · một URL ĐỐI CHỨNG không dùng chức năng đó")
    print("                          Chưa chạy hai URL đó thì trạng thái vẫn là RUNTIME_NOT_TESTED.")


def safe_write(path, content, backup_dir=None, encoding="utf-8", loader=False, quiet=False):
    """Ghi an toàn. Trả về đường dẫn bản backup (None nếu file trước đó chưa tồn tại).

    loader=True: file này nạp file khác (bootstrap, require, autoload) → in cảnh báo
    runtime nổi bật. `functions.php` và `wp-config.php` tự bật cờ này.

    Ném UnsafeWrite và KHÔNG đụng file gốc nếu nội dung mới rỗng, hoặc bản mới
    không qua được phép kiểm tĩnh.
    """
    if isinstance(content, str):
        content = content.encode(encoding)
    if not content.strip():
        raise UnsafeWrite("nội dung mới rỗng — từ chối ghi (đây đúng là cách file bị xoá trắng)")

    path = os.path.abspath(path)
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    is_loader = loader or os.path.basename(path).lower() in KNOWN_LOADERS

    bak = None
    if os.path.exists(path):
        old = open(path, "rb").read()
        stamp = time.strftime("%Y%m%d-%H%M%S")
        bdir = backup_dir or os.path.join(d, "_backup")
        os.makedirs(bdir, exist_ok=True)
        bak = os.path.join(bdir, f"{os.path.basename(path)}.{stamp}")
        with open(bak, "wb") as f:
            f.write(old)
        if _sha(old) == _sha(content):
            if not quiet:
                print(f"NO_CHANGE               — {path} giữ nguyên, nội dung không đổi")
            return bak

    tmp = path + f".tmp-{os.getpid()}"
    with open(tmp, "wb") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())

    # kiểm trên file tạm, chưa đụng gì tới file thật
    ext = os.path.splitext(path)[1].lower()
    state, msg = verify(tmp, as_ext=ext)
    if state == "fail":
        os.unlink(tmp)
        raise UnsafeWrite(f"kiểm tĩnh KHÔNG QUA, file gốc còn nguyên: {msg}")
    if state == "unavailable":
        os.unlink(tmp)
        raise RequiredCheckUnavailable(
            f"{REQUIRED_CHECKS.get(ext, 'phép kiểm bắt buộc')} — {msg}")

    os.replace(tmp, path)   # nguyên tử

    back = open(path, "rb").read()
    if _sha(back) != _sha(content):
        raise UnsafeWrite("đọc lại không khớp nội dung vừa ghi — kiểm tay ngay")

    if not quiet:
        _report(path, len(content), state, msg, is_loader, bak)
    return bak


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    if args[0] == "--check":
        rc = 0
        for p in args[1:]:
            state, msg = verify(p)
            if state == "pass":
                print(f"STATIC_CHECKS_PASSED        {p} — {msg}")
            elif state == "fail":
                print(f"STATIC_CHECKS_FAILED        {p} — {msg}")
                rc = max(rc, 1)
            elif state == "unavailable":
                need = REQUIRED_CHECKS.get(os.path.splitext(p)[1].lower(), "phép kiểm bắt buộc")
                print(f"REQUIRED_CHECK_UNAVAILABLE  {p} — {need}: {msg}")
                print(f"                            → file loại này KHÔNG được ghi khi thiếu {need}")
                rc = max(rc, 2)
            else:
                print(f"STATIC_CHECKS_SKIPPED       {p} — {msg}")
        print("RUNTIME_NOT_TESTED          — phép kiểm này không chạy WordPress")
        return rc
    loader = "--loader" in args
    rest = [a for a in args if not a.startswith("--")]
    if not rest:
        print("Thiếu đường dẫn file đích.")
        return 2
    data = sys.stdin.buffer.read()
    try:
        safe_write(rest[0], data, loader=loader)
    except RequiredCheckUnavailable as e:
        print(f"WRITE_REFUSED               — không ghi vì không kiểm được, file gốc còn nguyên")
        print(f"REQUIRED_CHECK_UNAVAILABLE  — {e}")
        print( "                              Cài PHP rồi chạy lại. Ghi file PHP mà không có")
        print( "                              php -l chính là đường đưa lỗi cú pháp vào file sống.")
        return 2
    except UnsafeWrite as e:
        print(f"WRITE_REFUSED               — {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
