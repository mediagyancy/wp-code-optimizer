---
name: wp-code-cheatsheet
description: >-
  Sinh CHEATSHEET (bảng tra kiểu Liquid của Haravan) cho bất kỳ dự án nào — theme, plugin
  WordPress hay repo script — từ chính code: hàm và chữ ký, hook dự án tự phát, callback đã
  đăng ký, shortcode, action AJAX, route REST, hằng, key option trong database, handle asset,
  template, cờ dòng lệnh. Ra ba định dạng cùng một nguồn: JSON (máy đọc), Markdown (commit
  vào repo), HTML tự chứa (lọc, bấm mở). Dùng skill này khi người dùng nói tới: cheatsheet,
  bảng tra, bảng tham chiếu, "dự án này có những hàm/hook nào", "tài liệu hoá theme", "ai
  móc vào hook nào", "key option tên gì", onboarding người mới vào codebase, hoặc trước khi
  đổi tên bất cứ thứ gì để biết mình sắp phá hợp đồng nào. KHÔNG dùng để tìm code chết
  (wp-code-cleaner), không dùng để vẽ đồ thị phụ thuộc file↔file (code-optimize), không
  dùng cho tài liệu viết tay.
---

# Cheatsheet sinh từ code — hợp đồng của dự án, không phải mô tả của người viết

## Việc thật sự là gì

Một dự án WordPress phát ra ngoài nhiều tên hơn người viết nhớ: hook `do_action('myp_after_render')`
mà plugin con đang móc vào, key `get_option('myp_settings')` đang nằm trong database của mọi
site, shortcode `[myp_box]` đang nằm trong 300 bài viết, handle `myp-app` mà theme con đang
`wp_dequeue_script`. **Đổi một tên trong số đó là breaking change**, và cái đắt nhất là nó
hỏng **im lặng**: hook đổi tên thì plugin con không báo lỗi, chỉ ngừng chạy.

Bảng Liquid của Haravan (`product.price`, `cart.item_count`) hay ở chỗ: **một namespace mỗi
object, mỗi tên một dòng, tra được bằng mắt**. Skill này sinh đúng bảng đó cho dự án của
anh — nhưng **từ code**, không từ trí nhớ. Tài liệu viết tay lệch khỏi code sau lần sửa thứ
ba; bảng sinh lại mỗi lần commit thì không.

Ba câu chi phối mọi bước:

1. **Chỉ ghi nhận literal thuần.** `apply_filters( 'myp_' . $x )` không được đoán thành tên.
   Nó vào `unresolved`, được **đếm**, và số đó in ngay đầu bảng. Muốn bảng phủ hết thì viết
   tên thành literal — đó cũng là lời khuyên đúng cho code.
2. **Docblock chỉ tính khi đứng ngay trên hàm.** Docblock đầu file, rồi `defined('ABSPATH')`,
   rồi `function` — docblock đó là của file. Hàm không mô tả là `NO_DOC` và cộng vào
   `undocumented`: **bảng đồng thời là thước đo nợ tài liệu**, không chỉ là danh sách.
3. **Script từ chối ghi khi chưa hiệu chuẩn.** Trước mỗi lần ghi nó tự chạy trên một đoạn mã
   có ca đúng và ca mồi (hàm JavaScript trong `<script>`, docblock cách hàm bằng code, hook
   tên động). Sai một ca là `UNCALIBRATED`, không ghi gì. Bộ test của repo còn chứng minh bộ
   hiệu chuẩn ấy **đỏ được** khi gỡ một chốt — bộ hiệu chuẩn chưa từng đỏ không chứng minh gì.

Nếu repo có `CLAUDE.md`/`AGENTS.md`, đọc trước — luật repo thắng skill này.

## Quy trình

```bash
# 1. sinh — prefix là tiền tố của dự án (hàm, hằng viết hoa, handle); rỗng thì lấy hết
python scripts/cheatsheet.py --root "đường/dẫn/theme" --prefix mytheme_,mytheme- \
    --out run/cheatsheet.json --md docs/CHEATSHEET.md --html run/cheatsheet.html

# 2. đọc ba dòng đầu của output TRƯỚC khi đọc bảng
#    functions N · undocumented M · unresolved K
```

Đọc bảng theo **thứ tự rủi ro**, không theo thứ tự trong file:

| Đọc trước | Vì sao |
|---|---|
| `options` | key trong **database**. Đổi tên là mất cài đặt của mọi site đang chạy — không có cách lùi bằng code |
| `hooks` | plugin con / theme con đang móc vào. Đổi tên → chúng im lặng ngừng chạy |
| `ajax` có `is_public` · `rest_routes` | bề mặt **công khai**, khách vãng lai gọi được — rà soát sanitizer trước |
| `shortcodes` | nằm trong nội dung đã xuất bản; đổi tên → bài viết hiện tag thô |
| `registrations` | cùng priority thì chạy theo **thứ tự đăng ký** = thứ tự require; đảo là đổi hành vi (Tầng 5 của `code-optimize` đo được) |
| `functions` | chữ ký + giá trị mặc định là hợp đồng; đổi mặc định không đổi HTML nhưng đổi lần gọi sau |
| `unresolved` | những chỗ bảng **không biết** — không đọc mục này thì bảng trông đầy đủ hơn thực tế |

Cam kết bảng vào repo dự án (`docs/CHEATSHEET.md`) và sinh lại trong CI: diff của file đó
chính là danh sách breaking change của mỗi PR.

## Ba định dạng, một nguồn

| File | Cho ai | Ghi chú |
|---|---|---|
| `cheatsheet.json` | máy: linter, so sánh trước/sau đổi tên, `rename.py --check` | schema trong `docs/REFERENCE.md` → `cheatsheet`; mọi danh sách sort, **không** timestamp — hai lần chạy ra cùng byte, diff được |
| `CHEATSHEET.md` | commit vào repo, đọc trong PR | bảng theo object, `_NO_DOC_` đánh dấu nợ |
| `cheatsheet.html` | người mới onboard, chia sẻ | tự chứa, không script ngoài; lọc theo tên/mô tả/file; bấm mở từng dòng. Dòng vàng = nợ (NO_DOC, unresolved, option chỉ đọc chưa thấy ghi, AJAX công khai) |

Mở HTML qua `http://127.0.0.1` (một `python -m http.server` là đủ) — cạm bẫy `file://` của
`wp-preview-builder` áp ở đây y hệt: mở thẳng file thì trang là ảnh tĩnh, JavaScript không chạy.

## Bề mặt KHÔNG phủ — nói ra, đừng để trống

- **JavaScript**: không quét `wp.hooks`, custom event, `window.X`. Bảng chỉ có bề mặt PHP.
- **Class/method PHP**: chỉ hàm top-level. Theme dùng OOP (`add_action('init', [$this, 'x'])`)
  thấy `callback` là nguyên văn biểu thức, không phân giải về method.
- **CSS class**: không phải hợp đồng theo nghĩa này; `wp-code-cleaner` lo phần đó.
- **Tên dựng bằng biến**: đếm ở `unresolved`, không đoán. Đây là giới hạn có chủ ý.
- **Hook của WordPress core** mà dự án *đăng ký vào* (`init`, `wp_head`) nằm ở `registrations`,
  không phải `hooks` — `hooks` chỉ là hook **dự án tự phát**. Đừng đọc nhầm.

## File trong skill

| File | Đọc khi nào |
|---|---|
| `scripts/cheatsheet.py` | mọi lúc — một file, thư viện chuẩn, tự hiệu chuẩn |
| `scripts/cheatsheet_template.html` | khi muốn đổi giao diện HTML; nhận `__PROJECT__` và `__DATA__` |
| `../../docs/REFERENCE.md` → `cheatsheet` | schema JSON, ý nghĩa từng key |
| `../../tests/test_cheatsheet.py` | 30 khẳng định: fixture, đối chứng ngược, tất định, fail-closed, và bộ hiệu chuẩn phải đỏ được |
