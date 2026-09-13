# Luật repo `wp-code-optimizer`

Repo này là **chuẩn** cho các dự án WordPress: mọi dự án WP khác lấy luật từ đây. Nên luật
ở đây không được là lời khuyên — mỗi luật có một phép kiểm chạy trong `tests/`, và luật
nào chưa có phép kiểm thì chưa phải luật.

Luật global ở `~/.claude/CLAUDE.md` vẫn áp (Tier 0: số phải truy được về nguồn, không sửa
trên base lỗi thời, thước phải bắt được ca hỏng đã biết…). File này chỉ thêm luật **của
riêng repo**.

## 1. Tên là hợp đồng — luật ĐẶT TÊN (cứng, có chốt: `tests/check_names.py`)

Mọi tên mà code **phát ra ngoài** — key JSON/dict/array, cờ CLI, mã lý do, exit code, tên file
script — là hợp đồng giữa các script, giữa script và người đọc, và giữa repo này với mọi dự án
WordPress dùng nó. Đổi một tên là **breaking change**: dòng CHANGELOG + đi qua `rename.py`.

Bài học từ bảng Liquid của Haravan (`product.price`, `cart.item_count`, `blog.articles_count`,
filter `truncate(input, characters)`): **một namespace cho mỗi object, tên là danh từ ngắn, hậu
tố có nghĩa cố định, và một bảng tra được bằng mắt cho mọi tên.** Chủ repo chốt 13/09/2026:

| Luật | Đúng | Sai | Vì sao |
|---|---|---|---|
| **Tiếng Anh chuẩn quốc tế**, snake_case | `files_after_render`, `blind_spot_count` | `file_sau_render`, `diem_mu_so` | repo là chuẩn cho các dự án WP; người đọc, tool, và tài liệu WordPress đều nói tiếng Anh. Bản nháp tiếng Việt đã bị bác |
| **Mỗi cụm phải mang nghĩa** — cấm từ đệm | `theme_hooks`, `fire_sequence` | `hook_data`, `tmp_info`, `misc_obj` | `data`/`info`/`tmp`/`obj`/`helper`/`util` không nói gì về nội dung |
| **Cấm tên quá dài**: ≤ 4 cụm, ≤ 24 ký tự | `ignored_count` | `number_of_elements_filtered_as_harmless` | tên dài là mô tả nhét vào định danh; mô tả để ở bảng tham chiếu |
| **Đếm = hậu tố `_count`; tổng = tiền tố `total_`** | `file_count`, `hook_count`, `total_bytes` | `num_files`, `number_of_hooks`, `so_file` | đúng Haravan: `articles_count`, `products_count` |
| **Object trước, thuộc tính sau — lồng** | `counts.static_hooks`, `scripts.queue`, `unresolved.dynamic_hook` | `static_hooks_count_value` | `variant.inventory_quantity`, không phải `variant_inventory_quantity_value` |
| **Boolean: `is_` / `has_` / `can_`** (tên mới) | `has_loader`, `is_certain` | `loader_ok`, `valid` | đọc là biết đó là câu hỏi có/không |
| **Cờ CLI: kebab-case**, mặc định THỬ, ghi thật phải `--write` | `--prefix`, `--against`, `--accept-blind`, `--write` | `--force` | không có `--force` ở đâu trong repo — cổng đóng thì sửa nguyên nhân hoặc khai tường minh |
| **Mã lý do: UPPER_SNAKE, một MỆNH ĐỀ về trạng thái** | `NOT_CHECKABLE`, `NOT_CLEAN`, `GRAPH_UNTRUSTED`, `NOISE_TOO_HIGH` | `ERROR`, `FAILED`, `OK` | mã phải nói **vì đâu** |
| **Thứ tự là dữ liệu thì tài liệu phải nói** | `files_after_render` (bảng ghi: thứ tự nạp thật) | | `theme_hooks` có thứ tự trong bucket là toàn bộ lý do Tầng 5 tồn tại |
| **Bốn nhãn bằng chứng giữ nguyên** | `CONCEPT_PREVIEW` `VISUAL_PASS` `PRODUCTION_VERIFIED` `NOT_TESTED` | | từ vựng có trước luật |

**Bảng tham chiếu `docs/REFERENCE.md` phải phủ MỌI tên** của lane mới — linter đỏ khi thiếu.

**Phiên bản**: `VERSION` ở gốc repo là nguồn duy nhất; mọi `SKILL.md` mang `version:` khớp nó
(`test_install.py` chốt). Cài và cập nhật local **chỉ qua `install.py`** — không `cp -r` tay.

**Nợ cũ**: tên tiếng Việt của skill cũ (`quet_chet.py`, `--tien-to`, `KHONG_KIEM_DUOC`…) khoanh
trong `tests/names-baseline.json`. Ratchet: nợ **không được tăng**; trả nợ thì `--update`.

## 2. Đổi tên — chỉ qua `skills/code-optimize/scripts/rename.py`

Không `sed`, không `replace` tay. Ba cách replace thẳng hỏng **im lặng**: khớp chuỗi con
(`so` → đụng `so_file`), va chạm (tên mới đã tồn tại với nghĩa khác), bỏ sót (chỗ dùng
trong file mình không mở). `rename.py` có chốt cho cả ba: khớp theo ranh giới từ, `đếm(B)
== 0` trước, `đếm(A) == 0` và `đếm(B) == n` sau, `--check` chạy test và **tự phục hồi từng
byte** nếu đỏ (không dùng `git checkout` để phục hồi — trên Windows nó trả CRLF cho file LF).

Cách "A → C độc nhất → test → C → B" bắt được va chạm nhưng **không** bắt được bỏ sót, và
nhân đôi số lần sửa. Không dùng.

## 3. Thước phải bắt được ca hỏng đã biết — và phải có ca đối chứng ngược

Mọi script ghi file phải **từ chối ghi** cho tới khi ca hiệu chuẩn của chính nó đỏ đúng.
Mọi bộ test mới phải có **cả hai chiều**: ca hỏng → đỏ, và **gỡ nguyên nhân → im**. "Cổng
báo 2" mà không chứng minh được nó báo 0 khi phải báo 0 thì con số 2 có thể là trùng hợp.

Ca hiệu chuẩn lấy **nguyên văn ca hỏng lịch sử** khi có, không tự nghĩ biến thể: ca tự nghĩ
chỉ kiểm được cách hỏng người viết đã tưởng tượng ra (`test_preview.py` bắt được lỗ dấu trừ
Unicode chỉ vì dùng đúng dòng sai gốc).

## 4. Fail-closed, không có `--force`

Thiếu công cụ là `NOT_CHECKABLE` và chặn, không đọc thành "không thấy lỗi". Input rỗng là
`NOT_CHECKABLE` và exit khác 0 — repo đã trả giá hai lần cho fail-open (v0.2.0, tái phát
v0.4.0 trong chính code viết ra để chống nó). Cổng đang đóng thì hai đường: sửa nguyên nhân,
hoặc khai tường minh (`--accept-blind N`) và chấp nhận phần đó là `NOT_TESTED`.

## 5. Không hứa thứ chưa đo

Không hứa tốc độ từ ít dòng hơn (OPcache). Không viết "chạy trong CI" khi CI chưa chạy trên
runner. Không nâng nhãn bằng chứng. Mọi con số trong CHANGELOG/README chỉ ra được lệnh nào
đã in ra nó.

## 6. Test tự bảo đảm tiền đề của mình

Bộ integration đã từng xanh **nhờ thứ tự job** (`dna.php` đổi theme và để nguyên,
`test_integration.py` chạy sau thì chụp nhầm theme). Mỗi bộ tự đặt tiền đề bằng
`switch_theme.php`; site vừa dựng thì lượt đầu là lượt lạnh, phải có lượt làm ấm bị bỏ đi.
Chốt riêng tư từng xanh nhờ job `unit` không dựng `.wp-it` — bảo vệ nhờ tình cờ không phải
bảo vệ.

## 7. Sáu dạng code KHÔNG được triển khai — và thước nào bắt được

Sáu "mùi thiết kế" kinh điển (Robert C. Martin). Theo tinh thần §3, mỗi dạng phải trỏ vào
một phép kiểm **đang chạy** trong repo, hoặc ghi thẳng là chưa có thước — không được là
khẩu hiệu.

| Dạng | Biểu hiện | Thước trong repo | Trạng thái |
|---|---|---|---|
| 1. **Cứng nhắc** | một thay đổi nhỏ kéo theo một loạt thay đổi | `rename.py` **in ra số file và số chỗ** phải đụng cho MỘT khái niệm — đó là số đo cứng nhắc; `graph.edges` cho fan-in của từng node | có số đo, **chưa có ngưỡng chặn** |
| 2. **Mong manh** | sửa một chỗ, hỏng nhiều chỗ | **Tầng 5**: sửa một chỗ rồi đo bảy mặt runtime; 6 ca tiêm là 6 kiểu "một chỗ" | có chốt, đã hiệu chuẩn |
| 3. **Bất động** | không tái dùng được ở dự án khác | tên site / đường dẫn máy trong **skill dùng chung**: `kiem_rieng_tu.py` + `tests/rieng-tu.local.txt`. Ca thật 13/09: `ivn_convert_to_webp` nằm trong `wp-corewebvital` của repo public — hàm của một site trong skill của mọi site | có chốt; **danh sách tên là của từng máy** (gitignored) nên CI chỉ kiểm mẫu chung — giới hạn phải biết |
| 4. **Phức tạp không cần thiết** | | `wp_module_size.py`: `functions.php` ≤ 80 LOC thực thi, baseline ratchet cho file cũ; checklist B1 | có chốt cho kích thước; **chưa có** thước độ phức tạp hàm |
| 5. **Lặp lại không cần thiết** | | Ca thật: **ba bản chép** của cùng tài liệu (workspace / repo / `~/.claude`) lệch nhau tới mức repo public dạy công thức sai. Luật: **một nguồn** — skill sống trong repo, cài ra local, không sửa bản cài; `check_names.py` đòi bảng tham chiếu là nguồn duy nhất cho tên | có luật; **chưa có** thước clone code |
| 6. **Khó hiểu** | | §1 luật đặt tên · `docs/REFERENCE.md` · mỗi luật kèm ca hỏng đã trả giá (luật không có lý do là luật người ta lách) | có chốt cho tên; nội dung thì là kỷ luật viết |

## 8. Đối chiếu bộ Clean Code — cái gì đã thành chốt, cái gì chưa

Từ bản tóm tắt Clean Code (viblo). Chỉ liệt kê những mục repo **có lập trường**:

- **Đặt tên có nghĩa · dễ tìm · không nhét kiểu vào tên** → §1, chốt `check_names.py`. Riêng
  "không tiền tố": repo **có** tiền tố/hậu tố có nghĩa (`_count`, `total_`, `is_`/`has_`) — đó là ngữ nghĩa,
  không phải kiểu dữ liệu; Haravan cũng vậy (`first_`, `_count`).
- **Không số trực tiếp, đặt tên cho nó** → `WIDTHS`, `PAGE_TOLERANCE_PX`, `ELEMENT_TOLERANCE_PX`,
  `KNOWN_CASES` là hằng có tên kèm lý do. Chưa có chốt tổng quát.
- **Comment lý do, không comment điều hiển nhiên, xoá code không dùng thay vì comment** →
  toàn bộ repo viết comment về **vì sao** và **ca hỏng**; code chết là việc của
  `wp-code-cleaner`. Comment dày ở đây là chủ ý và đúng loại Clean Code cho phép.
- **Luôn tìm nguyên nhân cốt lõi** → ca lượt-đầu-lạnh: không thêm hook vào danh sách lọc
  (whack-a-mole) mà thêm lượt làm ấm; chốt `test_integration` đỏ vì thứ tự → sửa bằng
  `switch_theme.php`, không sửa thứ tự job.
- **Boy-scout rule** → Fowler *litter-pickup* trong `checklist.md`.
- **Test độc lập · lặp lại được** → §6: bộ integration từng phụ thuộc thứ tự chạy; nay mỗi
  bộ tự đặt tiền đề. **"Mỗi test một thứ"**: bộ test của repo là nhiều `kiem()` trong một
  file — mỗi `kiem()` là một khẳng định có tên, nhưng chúng **không** độc lập với nhau
  trong cùng file (ca [5] cần ca [3] chạy trước). Đây là đánh đổi có chủ ý để chạy được
  không cần framework; ghi nhận, không giả vờ là đã đạt.
- **Không đối số flag** → cờ CLI `--write` (mặc định thử) là giao diện với người, không phải đối số
  hàm; trong hàm thì `chi_trong_nhay=True` ở `mau()` là một flag arg — nhỏ, chấp nhận.
- **Đa hình thay if/else · DI · Demeter · value object** → thuộc code OOP; script của repo
  là thủ tục nhỏ, chưa áp và chưa có nhu cầu. Không giả vờ.

## Trước khi commit

```
python tests/chay_test.py · test_preview.py · test_backup.py · test_clean_gate.py · test_rename.py · test_cheatsheet.py · test_install.py
python tests/kiem_rieng_tu.py
python tests/check_names.py
```
Đụng tới `dna.php`, `tier5.py`, `code_nodes.py`, `graph_gate.py` thì thêm ba bộ
integration (`dung_wp.py --ra .wp-it` rồi `test_integration` · `tier5` · `test_graph_gate`).
