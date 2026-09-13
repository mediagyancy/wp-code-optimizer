# Reference — mọi tên mà code phát ra ngoài

Một namespace cho mỗi object, như bảng Liquid của Haravan (`product.price`, `cart.item_count`).
Mỗi mục: **tên** · kiểu · mô tả · ví dụ. Chữ **có thứ tự** nghĩa là thứ tự phần tử là dữ liệu —
sort nó là xoá tín hiệu. Bảng này bị `tests/check_names.py` canh: thiếu một tên của lane mới là đỏ.

Luật đặt tên ở `CLAUDE.md` §1: tiếng Anh, ngắn, mỗi cụm mang nghĩa. Ký hiệu: `[]` danh sách ·
`{}` object · `?` boolean.

---

## `graph` — đồ thị giả thuyết tĩnh · `code_nodes.py --theme <dir> --out graph.json`

| Tên | Kiểu | Mô tả | Ví dụ |
|---|---|---|---|
| `version` | int | phiên bản schema của file JSON; đổi cấu trúc thì tăng | `1` |
| `theme` | str | tên thư mục theme (basename) | `"fixture-bien-doi"` |
| `nodes` | `[]{}` | mọi node, **sort theo `id`** để hai lần chạy ra cùng thứ tự | |
| `nodes[].id` | str | `<kind>:<name>` — `file:inc/hook-a.php`, `func:fxb_gia`, `hook:init`, `asset:fxb-main` | |
| `nodes[].kind` | str | `file` · `func` · `hook` · `asset` | |
| `nodes[].path` | str | chỉ `file`: đường dẫn tương đối, `/` | `"inc/hook-a.php"` |
| `nodes[].line_count` | int | chỉ `file`: số dòng | `41` |
| `nodes[].declared_in` | str? | chỉ `func`: file khai báo; `null` nếu chỉ thấy tên trong `add_action` mà không thấy `function` | |
| `nodes[].name` | str | chỉ `hook`/`asset`: tên hook hoặc handle | `"wp_enqueue_scripts"` |
| `nodes[].asset_type` | str | chỉ `asset`: `script` · `style` | |
| `edges` | `[]{}` | mọi cạnh, **sort theo (kind, from, to, line)** | |
| `edges[].from` `edges[].to` | str | id node đầu / cuối | |
| `edges[].kind` | str | `require` · `calls` · `declares` · `registration` (hook→callback) · `registers` (file→hook) · `emits` (do_action/apply_filters) · `enqueue` · `depends_on` (handle→dep) · `template_part` | |
| `edges[].source` | str | file chứa dòng sinh ra cạnh | |
| `edges[].line` | int? | dòng trong `source`; `null` với cạnh suy ra (`declares`, `calls`) | |
| `edges[].certain` | bool | `false` khi `require` khớp nhiều file (mơ hồ, nối hết — thà thừa còn hơn báo chết oan) | |
| `edges[].note` | str? | với `registration`: `"add_action p10"` — hàm đăng ký + priority; với `enqueue`: `script`/`style` | |
| `unresolved` | `{}` | **vùng mù tự khai**: cạnh không phân giải được, đếm chứ không đoán | |
| `unresolved.dynamic_require[]` | | `require $f;`, require dựng bằng biến/vòng lặp | |
| `unresolved.dynamic_hook[]` | | `add_action( $name, … )`, `do_action( 'wp_ajax_' . $x )` | |
| `unresolved.dynamic_callback[]` | | `add_action( 'init', 'fxb_' . 'dong_b' )`, `array( $this, $m )` | |
| `unresolved.dynamic_handle[]` | | `wp_enqueue_style( $handle, … )` | |
| `unresolved.dynamic_template_part[]` | | `get_template_part( $slug )` hoặc không tìm thấy file đích | |
| `unresolved.*[].file` `.line` `.expr` `.func` `.note` | | vị trí + 90 ký tự đầu của biểu thức + hàm gọi | |
| `unresolved_count` | int | tổng các mục trên. **Khác 0 thì mọi kết luận "không ai gọi" phải đọc kèm nó** | `2` |
| `UNPARSED_ARGS` | code | `expr` khi ngoặc của lời gọi không cân bằng (heredoc…) — nói không đọc được, không đoán | |

CLI: `--theme` cây theme (bắt buộc) · `--out` ghi JSON.

---

## `dna` — dấu vân tay runtime · `php dna.php [--theme-slug=X] [--phase=render]` (chạy trong `.wp-it`)

| Tên | Kiểu | Mô tả | Ví dụ |
|---|---|---|---|
| `version` | int | schema | `1` |
| `env` | `{}` | `php` · `wp` · `woo` (`"co"`/`"khong"`) · `theme_slug` | `{"php":"8.4.24","wp":"7.1","woo":"co"}` |
| `files_before_render` | `[]str` | file theme đã nạp sau bootstrap + `functions.php`, **có thứ tự nạp thật** (`get_included_files`, `array_unique` giữ lần đầu) | |
| `files_after_render` | `[]str` | như trên, sau khi render — thêm template, template-part | |
| `theme_hooks` | `[]{}` | mọi callback của theme trong `$wp_filter`; tên hook sort, **trong một hook: priority tăng dần, cùng priority theo thứ tự đăng ký** — thứ tự này là toàn bộ lý do Tầng 5 tồn tại | |
| `theme_hooks[].hook` | str | tên hook | `"init"` |
| `theme_hooks[].priority` | int | priority | `20` |
| `theme_hooks[].order` | int | vị trí trong bucket cùng priority, từ 1 | |
| `theme_hooks[].callback` | str | `func_name` · `Class::method` · `Class->method` · `Closure@file:line` (ổn định giữa hai lần chạy — không dùng `spl_object_hash`) | |
| `theme_hooks[].file` `.line` | | nơi khai báo callback, qua Reflection; `NOT_REFLECTABLE` nếu không phản chiếu được | |
| `theme_hooks[].accepted_args` | int? | `accepted_args` | |
| `hook_count` | int | tổng callback đã đăng ký của **cả site** (core + plugin + theme) | `2472` |
| `fire_sequence` | `[]str` | mọi hook đã fire trong giai đoạn render, qua meta-hook `all`, **đúng thứ tự thực thi** | |
| `scripts` `styles` | `{}` | registry, chỉ phần mang thông tin — không dump 300 handle của core | |
| `scripts.queue` | `[]str` | handle **thực sự** enqueue, **có thứ tự** | |
| `scripts.theme[]` | `[]{}` | handle có `src` trỏ vào theme: `handle` · `deps[]` · `src` (bỏ host) · `ver` · `extra[]` | |
| `signatures` | `[]{}` | hàm do theme khai báo, sort theo tên: `name` · `file` · `line` · `params[]` | |
| `signatures[].params[]` | `[]{}` | **có thứ tự**: `name` · `default` (`var_export`; `NO_DEFAULT`; `UNREADABLE`) · `required?` · `type` | |
| `html_raw` | str | HTML **thô**, không mask — mask ở phía Python, có lý do, trong version control | |
| `html_length` | int | `strlen(html_raw)` | `23577` |
| `error` | code | chỉ khi thất bại: `RERUN_NEEDED` (vừa `switch_theme`, `functions.php` mới chưa nạp trong cùng request — chạy lại, exit 75) · `THEME_MISMATCH` (exit 76) | |
| `new_theme` `explain` `requested` `actual` | str | đi kèm `error` | |

CLI: `--theme-slug` đổi theme kích hoạt trước khi chụp (fail-closed nếu sau đó không khớp) · `--phase` (chỉ `render`).

---

## `graph_trust` — cổng graph · `graph_gate.py --graph g.json --dna dna.json [--out trust.json] [--accept-blind N]`

| Tên | Kiểu | Mô tả |
|---|---|---|
| `version` `theme` `env` | | như trên |
| `counts` | `{}` | `static_hooks` · `runtime_hooks` · `static_files` · `runtime_files` · `static_assets` · `runtime_assets` · `unresolved` — số phần tử mỗi mặt, mỗi bên |
| `runtime_only` | `{}` | **chiều chí mạng**: có ở runtime mà đồ thị tĩnh không thấy → node trông mồ côi nhưng đang chạy. `hook[]` là `[hook, priority, callback]`; `file[]`, `asset[]` là chuỗi |
| `static_only` | `{}` | chiều nhẹ hơn: tĩnh nói có mà runtime không có — họ lỗi `SILENT_OFF` |
| `blind_spot_count` | int | tổng `runtime_only` |
| `overclaim_count` | int | tổng `static_only` |
| `GRAPH_TRUSTED` | code | 0 vùng mù — **chỉ với tập URL đã chụp** |
| `GRAPH_TRUSTED_CAVEATS` | code | có vùng mù nhưng đã khai `--accept-blind` đủ; các node đó là `NOT_TESTED` |
| `GRAPH_UNTRUSTED` | code | exit **9** — không tối ưu trên nền này |
| `registration` | | loại cạnh được đọc từ `graph.edges` để lấy `(hook, priority, callback)` |

Cạnh so **theo tập**, không theo thứ tự — thứ tự là việc của Tầng 5.

---

## `gate` — cổng clean · `clean_gate.py --theme <dir> --backup <dir> [--loader functions.php] [--prefix fx_] [--out gate.json]`

| Tên | Kiểu | Mô tả |
|---|---|---|
| `version` `theme` | | |
| `conditions` | `{}bool` | `has_loader` · `unresolved_requires` (==0) · `dead_files` (rỗng) · `unloaded_hooks` (rỗng) · `dead_functions` (rỗng) · `backup_exists` · `tree_matches_backup` |
| `blockers` | `[]str` | lý do đóng: `NOT_CLEAN:<condition>` hoặc `NO_ROLLBACK:<condition>` |
| `open` | bool | `blockers` rỗng |
| `NOT_CLEAN` | code | exit **7** — chạy `wp-code-cleaner` tới khi `quet_chet.py` ra rỗng |
| `NO_ROLLBACK` | code | exit **8** — chưa có backup, hoặc cây đã trôi khỏi backup |
| `GATE_OPEN` | code | exit 0 — nhưng là kết luận **tĩnh**; cổng graph đối chứng ngay sau |

`--prefix`: tiền tố hàm, ngăn bằng phẩy, truyền thẳng cho `quet_chet.py`. `--loader`: file nạp chính.

---

## `manifest` — backup toàn cây · `backup.py save|check|restore`

| Tên | Kiểu | Mô tả |
|---|---|---|
| `version` | int | schema manifest |
| `created_at` | str | ISO-8601 lúc `save` |
| `source` | str | cây gốc, `/` |
| `excluded` | `[]str` | thư mục đã bỏ (mặc định `.git`) |
| `file_count` | int | số file trong backup |
| `total_bytes` | int | tổng byte |
| `file` | `{}` | `path → {sha256, byte}` |
| `added` `missing` `changed` | `[]str` | kết quả `check`: file có ở cây mà không có trong manifest · ngược lại · hash khác |
| `SAVED` | code | `save` xong, đã tự so bản chép với bản gốc |
| `CHECK` `MATCH` | code | `check`: header và kết luận 0 lệch |
| `DRY_RUN` `RESTORED` | code | `restore` chỉ thử (mặc định) · đã phục hồi và **tự `check` lại** |
| `REFUSED` | code | exit 3: backup đã có nội dung · cây đích không rỗng (cần `--overwrite`) |
| `BROKEN` | code | exit 5: bản chép khác gốc · backup **không tự nhất quán** · cây phục hồi không khớp |
| `save` `check` `restore` | lệnh con | |

CLI: `--source` · `--out` · `--exclude` · `--from` · `--against` · `--ignore-cr` (**chỉ** cho `check` khi so local với bản tải từ host — CRLF/LF; test chứng minh nó không che được thay đổi nội dung) · `--to` · `--write` · `--overwrite`.

---

## `tier5` — thước tương đương hành vi · `tier5.py --workdir .wp-it`

Bảy **mặt** (key trong dict lệch): `files` (file nạp, có thứ tự) · `hooks` (`theme_hooks`, có thứ tự) · `fires` (`fire_sequence` sau lọc noise) · `assets` (`script_queue` `theme_scripts` `style_queue` `theme_styles`) · `signatures` (chữ ký hàm) · `html` (toàn văn sau mask) · `sanitizers` (**tĩnh**: điểm đọc superglobal → hàm bọc ngoài; mặt duy nhất không cần WordPress).

| Tên | Kiểu | Mô tả |
|---|---|---|
| `nonce` | mask | token động được mask trong `html` — mỗi mask phải có lý do trong code |
| `indirect` `skipped` | | điểm đọc superglobal: có biến trung gian / không tính (đã có sanitizer) |
| `case_id` `name` `file` `old` `new` `expect` | | một **ca tiêm** (`INJECTIONS`): mã · tên · file sửa · chuỗi cũ (phải xuất hiện **đúng 1 lần**) · chuỗi mới · mặt dự đoán bắt |
| `caught` `passed` | | kết quả một ca: mặt đã bắt · có bắt được không |
| `NOISE_TOO_HIGH` | code | exit 6 — hai lượt không đổi code đã lệch; **phép đo chưa dùng được**, không phải "gần đúng" |
| `UNCALIBRATED` | code | exit 7 — mốc `old` không tìm thấy hoặc xuất hiện ≠ 1 lần |
| `CAPTURE_FAILED` | code | exit 5 — `switch_theme` không ổn định sau 3 lần |
| `RERUN_NEEDED` | code | từ `dna.php`, `tier5` tự chạy lại |
| `FIRE_NOISE` `SANITIZERS` `NOT_SANITIZER` `SUPERGLOBALS` `THEME_SLUG` | hằng | họ hook bị lọc khỏi `fires` · hàm sanitize được nhận · đánh dấu hàm không phải sanitizer · siêu toàn cục quét · theme fixture |

Giao thức: **một lượt làm ấm bị bỏ** → hai lượt baseline (đo noise) → tiêm từng ca → so với baseline. `capture_dna.py --workdir .wp-it --out f.json [--no-copy]` chụp một lượt ra file (`--no-copy`: chụp cây **đang có** trong site, cho ca đối chứng ngược). `switch_theme.php --theme-slug=X` đặt theme kích hoạt, in `{before, after, switched?}` hoặc `error`.

---

## `probe` — đo bố cục trong trang · `wp-preview-builder/scripts/probe.js`

| Tên | Kiểu | Mô tả |
|---|---|---|
| `PROBE_VERSION` | str | `"wp-preview-builder/1.0.0"` |
| `protocol` | str | phải là `"http:"`; `"data:"` là bản nhúng tĩnh, số đo thuộc trang khác |
| `viewport` | int | `documentElement.clientWidth` — **cơ sở của mọi phép tính** |
| `clientWidth` `innerWidth` `scrollWidth` | int | báo cáo **nguyên văn** tên trình duyệt để đối chiếu DevTools; `innerWidth` không tham gia phép tính nào |
| `OVERFLOW_STATUS` | str | `"296px — LỖI THẬT"` hoặc `"không"`. Mức trang: **biên 0**, tràn 1px vẫn là tràn |
| `overflow_px` | number | cùng giá trị, dạng số |
| `offenders[]` | `[]{}` | tối đa 8, sort `right` giảm: `el` · `left` · `right` · `w`. Mức phần tử: **biên 1px** (số thực) |
| `ignored_count` | int | số phần tử đã lọc — in ra để danh sách rỗng không bị đọc là "bỏ sót"; lớn là bình thường với carousel/drawer |
| `ignored_samples[]` | | 3 ví dụ kèm `reason`: `fixed` · `visibility:hidden` · `opacity:0` · `aria-hidden` · `bị cắt bởi <selector>` |
| `min_font` | str | `"12px — p.fxb-gia"`, chỉ tính phần tử có text node trực tiếp |
| `small_targets` | int | phần tử tương tác < 40px, **bỏ** phần tử lồng trong một phần tử tương tác đã ≥ 40×40 |
| `small_target_samples[]` | | 5 ví dụ: `el` · `w` · `h` |
| `logged_in` | bool | thấy `#wpadminbar` — số đo đang có admin bar |
| `MEASURE_ERROR` | code | `viewport = 0` — **không kết luận**, đợi 1s đo lại |

`overflow_rule.py` (hàm quyết định, chạy trong CI không cần trình duyệt): `WIDTHS` = (344, 375, 768, 1280, 1440) · `EXTRA_WIDTHS` = (280,) · `PAGE_TOLERANCE_PX` = 0 · `ELEMENT_TOLERANCE_PX` = 1 · `KNOWN_CASES[]` với `name` · `client_width` · `inner_width` · `scroll_width` · `expected` · `old_formula` · `note` — ca 296px là nguyên văn ca hỏng 02/09/2026. `UNCALIBRATED` khi bộ hiệu chuẩn không phân biệt được hai công thức.

---

## `rename` — đổi tên an toàn · `rename.py --old A --new B [--root .] [--quoted-only] [--write] [--backup D] [--merge] [--check "<cmd>"]`

| Cờ | Mô tả |
|---|---|
| `--old` `--new` | tên cũ / mới |
| `--root` | thư mục quét (mặc định `.`) |
| `--quoted-only` | chỉ đổi dạng `"A"`/`'A'` — key JSON, mã lý do; `print(A)` giữ nguyên |
| `--write` | đổi thật; mặc định chỉ thử và in mọi `file:line` sẽ đụng |
| `--backup` | thư mục do `backup.py save` tạo, cho cây không phải git; cây git thì phải **sạch** |
| `--merge` | cho phép tên mới **đã tồn tại** (gộp có chủ ý); chốt sau đổi thành `count(B) == n + count(B) trước` |
| `--check` | lệnh chạy sau khi đổi, lặp được; exit ≠ 0 → **phục hồi từng byte** từ snapshot |

Mã: `NAME_COLLISION` (tên mới đã tồn tại, exit 3) · `REFUSED` (cây bẩn / không có gì để đổi) · `POSTCHECK_MISMATCH` (exit 5, đã phục hồi) · `CHECK_FAILED` (exit 6, đã phục hồi) · `NOT_CHECKABLE` (exit 4). Hằng: `SKIP_DIRS` (thư mục không quét, kể cả fixture) · `EXTENSIONS`.

---

## Hằng nội bộ của `code_nodes.py`

`RE_REQUIRE` · `RE_FUNC` · `RE_HOOK_OPEN` · `RE_EMIT` · `RE_ENQUEUE_OPEN` · `RE_TEMPLATE_PART` · `RE_STRING` — regex tìm **điểm mở** của từng lời gọi; tham số thì tách bằng cân bằng ngoặc, không bằng regex. `SKIP_DIRS`.

---

## Exit code chung

| Exit | Nghĩa | Ở đâu |
|---|---|---|
| 0 | xong / cổng mở | mọi script |
| 1 | có lệch / có hỏng | `check`, bộ test |
| 2 | `UNCALIBRATED` | `overflow_rule.py`, `check_names.py` |
| 3 | `REFUSED` / `NAME_COLLISION` | `backup.py`, `rename.py` |
| 4 | `NOT_CHECKABLE` — thiếu input/công cụ | mọi script |
| 5 | backup hỏng / chốt sau lệch / không chụp được | `backup.py`, `rename.py`, `tier5.py` |
| 6 | `NOISE_TOO_HIGH` / `CHECK_FAILED` | `tier5.py`, `rename.py` |
| 7 | `NOT_CLEAN` / mốc tiêm không hợp lệ | `clean_gate.py`, `tier5.py` |
| 8 | `NO_ROLLBACK` | `clean_gate.py` |
| 9 | `GRAPH_UNTRUSTED` | `graph_gate.py` |
| 75 / 76 | `RERUN_NEEDED` / `THEME_MISMATCH` | `dna.php` |
