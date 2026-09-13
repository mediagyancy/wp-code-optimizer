# Bảng tham chiếu — mọi tên mà code phát ra ngoài

Một namespace cho mỗi object, như bảng Liquid của Haravan (`product.price`, `cart.item_count`).
Mỗi mục: **tên** · kiểu · mô tả · ví dụ. Chữ **có thứ tự** nghĩa là thứ tự phần tử là dữ liệu —
sort nó là xoá tín hiệu. Bảng này bị `tests/kiem_ten.py` canh: thiếu một tên của lane mới là đỏ.

Luật đặt tên ở `CLAUDE.md` §1. Ký hiệu: `[]` danh sách · `{}` object · `?` boolean.

---

## `graph` — đồ thị giả thuyết tĩnh · `code_nodes.py --theme <cây> --ra graph.json`

| Tên | Kiểu | Mô tả | Ví dụ |
|---|---|---|---|
| `phien_ban` | int | phiên bản schema của file JSON này; đổi cấu trúc thì tăng | `1` |
| `theme` | str | tên thư mục theme (basename) | `"fixture-bien-doi"` |
| `nut` | `[]{}` | mọi node, **sort theo `id`** để hai lần chạy ra cùng thứ tự | |
| `nut[].id` | str | `<loai>:<tên>` — `file:inc/hook-a.php`, `ham:fxb_gia`, `hook:init`, `asset:fxb-main` | |
| `nut[].loai` | str | `file` · `ham` · `hook` · `asset` | |
| `nut[].duong_dan` | str | chỉ `file`: đường dẫn tương đối, `/` | `"inc/hook-a.php"` |
| `nut[].so_dong` | int | chỉ `file`: số dòng | `41` |
| `nut[].khai_o` | str? | chỉ `ham`: file khai báo; `null` nếu chỉ thấy tên trong `add_action` mà không thấy `function` | |
| `nut[].ten` | str | chỉ `hook`/`asset`: tên hook hoặc handle | `"wp_enqueue_scripts"` |
| `nut[].kieu` | str | chỉ `asset`: `script` · `style` | |
| `canh` | `[]{}` | mọi cạnh, **sort theo (loai, tu, den, dong)** | |
| `canh[].tu` `canh[].den` | str | id node đầu / cuối | |
| `canh[].loai` | str | `require` · `goi` · `khai_bao` · `dang_ky` (hook→callback) · `dang_ky_tu` (file→hook) · `phat` (do_action/apply_filters) · `enqueue` · `phu_thuoc` (handle→dep) · `template_part` | |
| `canh[].nguon` | str | file chứa dòng sinh ra cạnh | |
| `canh[].dong` | int? | dòng trong `nguon`; `null` với cạnh suy ra (khai_bao, goi) | |
| `canh[].chac_chan` | bool | `false` khi `require` khớp nhiều file (mơ hồ, nối hết — thà thừa còn hơn báo chết oan) | |
| `canh[].ghi_chu` | str? | với `dang_ky`: `"add_action p10"` — hàm đăng ký + priority; với `enqueue`: `script`/`style` | |
| `chua_giai` | `{}` | **vùng mù tự khai**: cạnh không phân giải được, đếm chứ không đoán | |
| `chua_giai.require_bien[]` | | `require $f;`, require dựng bằng biến/vòng lặp | |
| `chua_giai.hook_ten_bien[]` | | `add_action( $ten, … )`, `do_action( 'wp_ajax_' . $x )` | |
| `chua_giai.callback_bien[]` | | `add_action( 'init', 'fxb_' . 'dong_b' )`, `array( $this, $m )` | |
| `chua_giai.handle_bien[]` | | `wp_enqueue_style( $handle, … )` | |
| `chua_giai.template_part_bien[]` | | `get_template_part( $slug )` hoặc không tìm thấy file đích | |
| `chua_giai.*[].file` `.dong` `.bieu_thuc` `.ham` `.ghi_chu` | | vị trí + 90 ký tự đầu của biểu thức + hàm gọi | |
| `so_chua_giai` | int | tổng các mục trên. **Khác 0 thì mọi kết luận "không ai gọi" phải đọc kèm nó** | `2` |
| `KHONG_DOC_DUOC_THAM_SO` | mã | `bieu_thuc` khi ngoặc của lời gọi không cân bằng (heredoc…) — nói không đọc được, không đoán | |

CLI: `--theme` cây theme (bắt buộc) · `--ra` ghi JSON.

---

## `adn` — dấu vân tay runtime · `adn-nen.php [--theme-slug=X]` (chạy trong `.wp-it`)

| Tên | Kiểu | Mô tả | Ví dụ |
|---|---|---|---|
| `phien_ban` | int | schema | `1` |
| `moi_truong` | `{}` | `php` · `wp` · `woo` (`"co"`/`"khong"`) · `theme_slug` | `{"php":"8.4.24","wp":"7.1","woo":"co"}` |
| `file_nap_truoc_render` | `[]str` | file theme đã nạp sau bootstrap + `functions.php`, **có thứ tự nạp thật** (`get_included_files`, `array_unique` giữ lần đầu) | |
| `file_nap_sau_render` | `[]str` | như trên, sau khi render — thêm template, template-part | |
| `hook_theme` | `[]{}` | mọi callback của theme trong `$wp_filter`; tên hook sort, **trong một hook: priority tăng dần, cùng priority theo thứ tự đăng ký** — thứ tự này là toàn bộ lý do Tầng 5 tồn tại | |
| `hook_theme[].hook` | str | tên hook | `"init"` |
| `hook_theme[].uu_tien` | int | priority | `20` |
| `hook_theme[].thu_tu` | int | vị trí trong bucket cùng priority, từ 1 | |
| `hook_theme[].callback` | str | `ten_ham` · `Lop::method` · `Lop->method` · `Closure@file:dòng` (ổn định giữa hai lần chạy — không dùng `spl_object_hash`) | |
| `hook_theme[].file` `.dong` | | nơi khai báo callback, qua Reflection; `KHONG_PHAN_CHIEU_DUOC` nếu không phản chiếu được | |
| `hook_theme[].so_tham_so` | int? | `accepted_args` | |
| `so_hook` | int | tổng callback đã đăng ký của **cả site** (core + plugin + theme) | `2472` |
| `chuoi_fire` | `[]str` | mọi hook đã fire trong giai đoạn render, qua meta-hook `all`, **đúng thứ tự thực thi** | |
| `scripts` `styles` | `{}` | registry, chỉ phần mang thông tin — không dump 300 handle của core | |
| `scripts.queue` | `[]str` | handle **thực sự** enqueue, **có thứ tự** | |
| `scripts.theme[]` | `[]{}` | handle có `src` trỏ vào theme: `handle` · `deps[]` · `src` (bỏ host) · `ver` · `extra[]` | |
| `chu_ky_ham` | `[]{}` | hàm do theme khai báo, sort theo tên: `ten` · `file` · `dong` · `tham_so[]` | |
| `chu_ky_ham[].tham_so[]` | `[]{}` | **có thứ tự**: `ten` · `mac_dinh` (`var_export`, `KHONG_CO` nếu không có, `KHONG_DOC_DUOC` nếu không đọc được) · `bat_buoc?` · `kieu` | |
| `html_tho` | str | HTML **thô**, không mask — mask ở phía Python, có lý do, trong version control | |
| `do_dai_html` | int | `strlen(html_tho)` | `23577` |
| `loi` | mã | chỉ khi thất bại: `CAN_CHAY_LAI` (vừa `switch_theme`, `functions.php` mới chưa nạp trong cùng request — chạy lại) · `THEME_KHONG_KHOP` | |
| `theme_moi` `giai_thich` `yeu_cau` `thuc_te` | str | đi kèm `loi` | |

CLI: `--theme-slug` đổi theme kích hoạt trước khi chụp (fail-closed nếu sau đó không khớp) · `--giai-doan` (chỉ `render`).

---

## `graph_trust` — cổng graph · `cong_graph.py --graph g.json --adn adn.json [--ra trust.json] [--chap-nhan-mu N]`

| Tên | Kiểu | Mô tả |
|---|---|---|
| `phien_ban` `theme` `moi_truong` | | như trên |
| `dem` | `{}` | `hook_tinh` · `hook_runtime` · `file_tinh` · `file_runtime` · `asset_tinh` · `asset_runtime` · `chua_giai` — số phần tử mỗi mặt, mỗi bên |
| `chi_runtime_co` | `{}` | **chiều chí mạng**: có ở runtime mà đồ thị tĩnh không thấy → node trông mồ côi nhưng đang chạy. `hook[]` là `[hook, uu_tien, callback]`; `file[]`, `asset[]` là chuỗi |
| `chi_tinh_co` | `{}` | chiều nhẹ hơn: tĩnh nói có mà runtime không có — họ lỗi `TAT_AM_THAM` |
| `so_vung_mu` | int | tổng `chi_runtime_co` |
| `so_noi_qua` | int | tổng `chi_tinh_co` |
| `GRAPH_DANG_TIN` | mã | 0 vùng mù — **chỉ với tập URL đã chụp** |
| `GRAPH_DANG_TIN_CO_DIEU_KIEN` | mã | có vùng mù nhưng đã khai `--chap-nhan-mu` đủ; các node đó là `NOT_TESTED` |
| `GRAPH_KHONG_DANG_TIN` | mã | exit **9** — không tối ưu trên nền này |
| `dang_ky` | | loại cạnh được đọc từ `graph.canh` để lấy `(hook, priority, callback)` |

Cạnh so **theo tập**, không theo thứ tự — thứ tự là việc của Tầng 5.

---

## `gate` — cổng clean · `cong_clean.py --theme <cây> --backup <dir> [--loader functions.php] [--tien-to fx_] [--ra gate.json]`

| Tên | Kiểu | Mô tả |
|---|---|---|
| `phien_ban` `theme` | | |
| `dieu_kien` | `{}bool` | `co_loader` · `require_khong_phan_giai` (==0) · `file_chet` (rỗng) · `hook_khong_nap` (rỗng) · `ham_chet` (rỗng) · `backup_ton_tai` · `cay_khop_backup` |
| `chan` | `[]str` | lý do đóng: `CHUA_CLEAN:<điều kiện>` hoặc `KHONG_CO_DUONG_LUI:<điều kiện>` |
| `mo` | bool | `chan` rỗng |
| `CHUA_CLEAN` | mã | exit **7** — chạy `wp-code-cleaner` tới khi `quet_chet.py` ra rỗng |
| `KHONG_CO_DUONG_LUI` | mã | exit **8** — chưa có backup, hoặc cây đã trôi khỏi backup |
| `CONG_MO` | mã | exit 0 — nhưng là kết luận **tĩnh**; cổng graph đối chứng ngay sau |

`--tien-to`: tiền tố hàm, ngăn bằng phẩy, truyền thẳng cho `quet_chet.py`. `--loader`: file nạp chính.

---

## `manifest` — backup toàn cây · `sao_luu.py luu|kiem|phuc_hoi`

| Tên | Kiểu | Mô tả |
|---|---|---|
| `phien_ban` | int | schema manifest |
| `thoi_diem` | str | ISO-8601 lúc `luu` |
| `nguon` | str | cây gốc, `/` |
| `bo_qua` | `[]str` | thư mục đã bỏ (mặc định `.git`) |
| `so_file` | int | số file trong backup |
| `tong_byte` | int | tổng byte |
| `file` | `{}` | `đường/dẫn → {sha256, byte}` |
| `them` `thieu` `khac` | `[]str` | kết quả `kiem`: file có ở cây mà không có trong manifest · ngược lại · hash khác |
| `DA_LUU` | mã | `luu` xong, đã tự so bản chép với bản gốc |
| `KIEM` `KHOP` | mã | `kiem`: header và kết luận 0 lệch |
| `THU` `PHUC_HOI` | mã | `phuc_hoi` chỉ thử (mặc định) · đã phục hồi và **tự `kiem` lại** |
| `TU_CHOI` | mã | exit 3: backup đã có nội dung · cây đích không rỗng (cần `--de-len`) |
| `HONG` | mã | exit 5: bản chép khác gốc · backup **không tự nhất quán** · cây phục hồi không khớp |
| `luu` `kiem` `phuc_hoi` | lệnh con | |

CLI: `--nguon` · `--ra` · `--bo-qua` · `--tu` · `--so-voi` · `--bo-cr` (**chỉ** cho `kiem` khi so local với bản tải từ host — CRLF/LF; test chứng minh nó không che được thay đổi nội dung) · `--den` · `--ghi` · `--de-len`.

---

## `tang5` — thước tương đương hành vi · `tang5.py --ra .wp-it`

Bảy **mặt** (key trong dict lệch): `nap` (file nạp, có thứ tự) · `hook` (`hook_theme`, có thứ tự) · `fire` (`chuoi_fire` sau lọc noise) · `asset` (`script_queue` `script_theme` `style_queue` `style_theme`) · `chu_ky` (chữ ký hàm) · `html` (toàn văn sau mask) · `sanitise` (**tĩnh**: điểm đọc superglobal → hàm bọc ngoài; mặt duy nhất không cần WordPress).

| Tên | Kiểu | Mô tả |
|---|---|---|
| `nonce` | mask | token động được mask trong `html` — mỗi mask phải có lý do trong code |
| `bien` `khong_tinh` | | điểm đọc superglobal: có biến trung gian / không tính (đã có sanitise) |
| `ma` `ten` `file` `cu` `moi` `cho_doi` | | một **ca tiêm** (`CA_TIEM`): mã · tên · file sửa · chuỗi cũ (phải xuất hiện **đúng 1 lần**) · chuỗi mới · mặt dự đoán bắt |
| `bat` `dat` | | kết quả một ca: mặt đã bắt · có bắt được không |
| `NOISE_QUA_LON` | mã | exit 6 — hai lượt không đổi code đã lệch; **phép đo chưa dùng được**, không phải "gần đúng" |
| `THUOC_CHUA_HIEU_CHUAN` | mã | exit 7 — mốc `cu` không tìm thấy hoặc xuất hiện ≠ 1 lần |
| `KHONG_CHUP_DUOC` | mã | exit 5 — `switch_theme` không ổn định sau 3 lần |
| `CAN_CHAY_LAI` | mã | từ `adn-nen.php`, `tang5` tự chạy lại |

Giao thức: **một lượt làm ấm bị bỏ** → hai lượt baseline (đo noise) → tiêm từng ca → so với baseline. `chup_adn.py --ra .wp-it --ra-json f.json [--khong-chep]` chụp một lượt ra file (`--khong-chep`: chụp cây **đang có** trong site, cho ca đối chứng ngược). `doi_theme.php --theme-slug=X` đặt theme kích hoạt, in `{truoc, sau, doi?}` hoặc `loi`.

---

## `probe` — đo bố cục trong trang · `wp-preview-builder/scripts/probe.js`

| Tên | Kiểu | Mô tả |
|---|---|---|
| `PHIEN_BAN_PROBE` | str | `"wp-preview-builder/1.0.0"` |
| `protocol` | str | phải là `"http:"`; `"data:"` là bản nhúng tĩnh, số đo thuộc trang khác |
| `viewport` | int | `documentElement.clientWidth` — **cơ sở của mọi phép tính** |
| `clientWidth` `innerWidth` `scrollWidth` | int | báo cáo **nguyên văn** tên trình duyệt để đối chiếu DevTools; `innerWidth` không tham gia phép tính nào |
| `TRAN_NGANG` | str | `"296px — LỖI THẬT"` hoặc `"không"`. Mức trang: **biên 0**, tràn 1px vẫn là tràn |
| `tran_ngang_px` | number | cùng giá trị, dạng số |
| `thu_pham_that[]` | `[]{}` | tối đa 8, sort `right` giảm: `el` · `left` · `right` · `w`. Mức phần tử: **biên 1px** (số thực) |
| `da_loc_bo_vi_vo_hai` | int | số phần tử đã lọc — in ra để danh sách rỗng không bị đọc là "bỏ sót"; lớn là bình thường với carousel/drawer |
| `vi_du_da_loc[]` | | 3 ví dụ kèm `bo_qua_vi`: `fixed` · `visibility:hidden` · `opacity:0` · `aria-hidden` · `bị cắt bởi <selector>` |
| `chu_nho_nhat` | str | `"12px — p.fxb-gia"`, chỉ tính phần tử có text node trực tiếp |
| `vung_cham_duoi_40px` | int | phần tử tương tác < 40px, **bỏ** phần tử lồng trong một phần tử tương tác đã ≥ 40×40 |
| `vi_du_vung_cham[]` | | 5 ví dụ: `el` · `w` · `h` |
| `dang_dang_nhap` | bool | thấy `#wpadminbar` — số đo đang có admin bar |
| `LOI_PHEP_DO` | mã | `viewport = 0` — **không kết luận**, đợi 1s đo lại |

`quyet_dinh_tran.py` (hàm quyết định, chạy trong CI không cần trình duyệt): `BE_RONG` = (344, 375, 768, 1280, 1440) · `BE_RONG_THEM` = (280,) · `BIEN_TRANG_PX` = 0 · `BIEN_PHAN_TU_PX` = 1 · `CA_LICH_SU[]` với `ten` · `client_width` · `inner_width` · `scroll_width` · `tran_dung` · `tran_cong_thuc_cu` · `ghi_chu` — ca 296px là nguyên văn ca hỏng 02/09/2026. `THUOC_CHUA_HIEU_CHUAN` khi bộ hiệu chuẩn không phân biệt được hai công thức.

---

## `doi_ten` — đổi tên an toàn · `doi_ten.py --cu A --moi B [--goc .] [--chi-trong-nhay] [--ghi] [--backup D] [--kiem "<lệnh>"]`

| Cờ | Mô tả |
|---|---|
| `--cu` `--moi` | tên cũ / mới |
| `--goc` | thư mục quét (mặc định `.`) |
| `--chi-trong-nhay` | chỉ đổi dạng `"A"`/`'A'` — key JSON, mã lý do; `print(A)` giữ nguyên |
| `--ghi` | đổi thật; mặc định chỉ thử và in mọi `file:dòng` sẽ đụng |
| `--backup` | thư mục do `sao_luu.py luu` tạo, cho cây không phải git; cây git thì phải **sạch** |
| `--kiem` | lệnh chạy sau khi đổi, lặp được; exit ≠ 0 → **phục hồi từng byte** từ snapshot |

Mã: `VA_CHAM` (tên mới đã tồn tại, exit 3) · `TU_CHOI` (cây bẩn / không có gì để đổi) · `CHOT_SAU_LECH` (exit 5, đã phục hồi) · `KIEM_DO` (exit 6, đã phục hồi).

---

## Exit code chung

| Exit | Nghĩa | Ở đâu |
|---|---|---|
| 0 | xong / cổng mở | mọi script |
| 1 | có lệch / có hỏng | `kiem`, bộ test |
| 2 | `THUOC_CHUA_HIEU_CHUAN` | `quyet_dinh_tran.py`, `kiem_ten.py` |
| 3 | `TU_CHOI` / `VA_CHAM` | `sao_luu.py`, `doi_ten.py` |
| 4 | `KHONG_KIEM_DUOC` — thiếu input/công cụ | mọi script |
| 5 | backup hỏng / chốt sau lệch / không chụp được | `sao_luu.py`, `doi_ten.py`, `tang5.py` |
| 6 | `NOISE_QUA_LON` / `KIEM_DO` | `tang5.py`, `doi_ten.py` |
| 7 | `CHUA_CLEAN` / mốc tiêm không hợp lệ | `cong_clean.py`, `tang5.py` |
| 8 | `KHONG_CO_DUONG_LUI` | `cong_clean.py` |
| 9 | `GRAPH_KHONG_DANG_TIN` | `cong_graph.py` |
| 75 / 76 | `CAN_CHAY_LAI` / `THEME_KHONG_KHOP` | `adn-nen.php` |
