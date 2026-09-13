# Luật repo `wp-code-optimizer`

Repo này là **chuẩn** cho các dự án WordPress: mọi dự án WP khác lấy luật từ đây. Nên luật
ở đây không được là lời khuyên — mỗi luật có một phép kiểm chạy trong `tests/`, và luật
nào chưa có phép kiểm thì chưa phải luật.

Luật global ở `~/.claude/CLAUDE.md` vẫn áp (Tier 0: số phải truy được về nguồn, không sửa
trên base lỗi thời, thước phải bắt được ca hỏng đã biết…). File này chỉ thêm luật **của
riêng repo**.

## 1. Tên là hợp đồng — luật ĐẶT TÊN (cứng, có chốt: `tests/kiem_ten.py`)

Mọi tên mà code **phát ra ngoài** — key JSON/dict/array, cờ CLI, mã lý do, exit code — là
hợp đồng giữa các script, giữa script và người đọc, và giữa repo này với dự án dùng nó.
Đổi một tên là **breaking change**: phải có dòng CHANGELOG, và phải đi qua `doi_ten.py`.

Bài học lấy từ bảng tham chiếu Liquid của Haravan (`product.price`, `cart.item_count`,
`blog.comments_enabled?`, filter `truncate(input, characters)`): **một namespace cho mỗi
object, tên là danh từ, tiền tố/hậu tố có nghĩa cố định, và một bảng tra được bằng mắt cho
mọi tên.** Áp vào đây:

| Luật | Đúng | Sai | Vì sao |
|---|---|---|---|
| **Một ngôn ngữ: tiếng Việt không dấu**, snake_case | `file_nap_sau_render`, `so_vung_mu` | `dynamic_unresolved`, `STATIC_CHECKS_PASSED` | repo từng nói hai ngôn ngữ, ba quy ước — người đọc phải đoán mỗi tên thuộc "phe" nào |
| **Danh từ kỹ thuật mượn** chỉ khi repo không có từ Việt đang dùng, và nằm trong allowlist `MUON` của linter | `hook`, `asset`, `handle`, `nonce`, `sha256`, `callback` | `check`, `pass`, `kind`, `size`, `type` | thêm vào allowlist là một quyết định, kèm lý do trong commit; **không** thêm động từ/tính từ |
| **Đếm = tiền tố `so_`; tổng = tiền tố `tong_`** | `so_file`, `so_hook`, `tong_byte` | `hook_tong_so`, `items_count`, `so_luong_file` | một cách đếm, đọc là biết ngay đó là số đếm |
| **Object trước, thuộc tính sau — lồng thay vì xếp tiền tố** | `dem.hook_tinh`, `scripts.queue`, `chua_giai.hook_ten_bien` | `so_hook_tinh_static_count` | Haravan: `variant.inventory_quantity`, không phải `variant_inventory_quantity_value` |
| **Boolean bắt đầu bằng `co_` / `da_` / `la_`** (cho tên mới; tên cũ như `chac_chan`, `bat_buoc` giữ) | `co_loader`, `da_loc_bo_vi_vo_hai`, `la_theme` | `loader_ok`, `valid` | đọc là biết là câu hỏi có/không |
| **Cờ CLI: kebab-case tiếng Việt**, mặc định là THỬ, ghi thật phải `--ghi` | `--tien-to`, `--so-voi`, `--chap-nhan-mu`, `--ghi` | `--write-baseline`, `--skip-tests`, `--force` | không có `--force` ở đâu trong repo — muốn qua cổng đang đóng thì sửa nguyên nhân hoặc khai tường minh |
| **Mã lý do: UPPER_SNAKE tiếng Việt, là một MỆNH ĐỀ về trạng thái** | `KHONG_KIEM_DUOC`, `CHUA_CLEAN`, `GRAPH_KHONG_DANG_TIN`, `NOISE_QUA_LON` | `ERROR`, `FAILED`, `OK` | mã phải nói **vì đâu**, không chỉ nói đỏ/xanh |
| **Thứ tự là dữ liệu thì tài liệu phải nói** — tên không cần hậu tố, nhưng bảng tham chiếu phải ghi "có thứ tự" | `file_nap_sau_render` (bảng ghi: thứ tự nạp thật) | | `hook_theme` có thứ tự trong bucket là toàn bộ lý do Tầng 5 tồn tại |
| **Bốn nhãn bằng chứng giữ nguyên tiếng Anh** — từ vựng có trước luật này | `CONCEPT_PREVIEW` `VISUAL_PASS` `PRODUCTION_VERIFIED` `NOT_TESTED` | | đổi chúng là đổi ngôn ngữ chung của ba site đã dùng |

**Bảng tham chiếu `docs/BANG-THAM-CHIEU.md` phải phủ MỌI tên** của lane mới — linter đỏ khi
thiếu. Bảng thiếu tên là bảng chết dần; bảng của Haravan chỉ có giá trị vì nó đầy đủ.

**Nợ cũ**: `wp-delivery` có 34 tên tiếng Anh, khoanh trong `tests/ten-baseline.json`. Ratchet:
nợ **không được tăng**; trả nợ thì chạy `kiem_ten.py --cap-nhat` để con số không trượt ngược.

## 2. Đổi tên — chỉ qua `skills/code-optimize/scripts/doi_ten.py`

Không `sed`, không `replace` tay. Ba cách replace thẳng hỏng **im lặng**: khớp chuỗi con
(`so` → đụng `so_file`), va chạm (tên mới đã tồn tại với nghĩa khác), bỏ sót (chỗ dùng
trong file mình không mở). `doi_ten.py` có chốt cho cả ba: khớp theo ranh giới từ, `đếm(B)
== 0` trước, `đếm(A) == 0` và `đếm(B) == n` sau, `--kiem` chạy test và **tự phục hồi từng
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

Thiếu công cụ là `KHONG_KIEM_DUOC` và chặn, không đọc thành "không thấy lỗi". Input rỗng là
`KHONG_KIEM_DUOC` và exit khác 0 — repo đã trả giá hai lần cho fail-open (v0.2.0, tái phát
v0.4.0 trong chính code viết ra để chống nó). Cổng đang đóng thì hai đường: sửa nguyên nhân,
hoặc khai tường minh (`--chap-nhan-mu N`) và chấp nhận phần đó là `NOT_TESTED`.

## 5. Không hứa thứ chưa đo

Không hứa tốc độ từ ít dòng hơn (OPcache). Không viết "chạy trong CI" khi CI chưa chạy trên
runner. Không nâng nhãn bằng chứng. Mọi con số trong CHANGELOG/README chỉ ra được lệnh nào
đã in ra nó.

## 6. Test tự bảo đảm tiền đề của mình

Bộ integration đã từng xanh **nhờ thứ tự job** (`adn-nen.php` đổi theme và để nguyên,
`test_integration.py` chạy sau thì chụp nhầm theme). Mỗi bộ tự đặt tiền đề bằng
`doi_theme.php`; site vừa dựng thì lượt đầu là lượt lạnh, phải có lượt làm ấm bị bỏ đi.
Chốt riêng tư từng xanh nhờ job `unit` không dựng `.wp-it` — bảo vệ nhờ tình cờ không phải
bảo vệ.

## Trước khi commit

```
python tests/chay_test.py · test_preview.py · test_sao_luu.py · test_cong_clean.py · test_doi_ten.py
python tests/kiem_rieng_tu.py
python tests/kiem_ten.py
```
Đụng tới `adn-nen.php`, `tang5.py`, `code_nodes.py`, `cong_graph.py` thì thêm ba bộ
integration (`dung_wp.py --ra .wp-it` rồi `test_integration` · `tang5` · `test_cong_graph`).
