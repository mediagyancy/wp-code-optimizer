# Nhật ký thay đổi

Theo [Semantic Versioning](https://semver.org/lang/vi/). Trước `1.0.0`, API dòng lệnh
và định dạng output còn có thể đổi.

---

## [0.5.0] — 2026-09-12

Đúc kết một tuần làm việc dày trên một site WooCommerce thật (05–12/09) vào kho kiến thức
và skill `wp-delivery`. Mọi bài học gắn với một commit / con số đã trả giá; tên site và
định danh đã ẩn danh như phần còn lại của repo.

### Thêm — bài học mới trong `docs/KINH-NGHIEM-WORDPRESS.md`

Rải vào các nhóm D, E, F, G, H, K, L, M:

- **WooCommerce lõi** — công tắc "ẩn hàng hết" lọc bằng thẻ `outofstock` có thể chưa gán
  (lọc bằng `_stock_status`); đếm danh mục bằng `wc_get_products` xoá bài toán cha+con gấp
  đôi; mô tả sản phẩm thường không đi qua `the_content()` → bám `woocommerce_product_get_description`.
- **Khoá transient phải bám version theme** — DOC/GHI/XOÁ cùng một khoá, nếu không bề mặt
  lệch âm thầm sau đợt chỉ đổi cách tính.
- **CSS** — đè bằng lớp phạm vi phải khai lại MỌI thuộc tính (thắng specificity chưa đủ);
  màn cực hẹp 280–330px phải đo trên site thật, "phần tử vượt viewport" không bắt được chữ
  cắt trong nút.
- **Đổi slug trang là migration** — không có auto-redirect, phải tự 301.
- **Làm tròn giá ở cửa đọc phía khách**, không ở getter dùng chung với lúc lưu; tròn đơn giá
  trước khi nhân số lượng.
- **Nhập dữ liệu hàng loạt** — ô trống ≠ xoá; đọc mọi hàng tiêu đề + ánh xạ cột do người
  nhập chốt; "0đ" = miễn phí; ngưỡng phép soát hiệu chuẩn trên file thật.
- **Kỷ luật đo** — "đọc lại chính cái mình vừa bấm" đẻ ra giả thuyết sai và deploy thừa
  (deploy không phải phép chẩn đoán); danh sách đang sắp xếp; công cụ quản trị nội bộ ba trụ.
- **Đa phiên** — tag cứu hộ phải có chú thích (`git tag -a`) mới được `push.followTags` đẩy;
  ba lỗ hook gác cổng chỉ lộ khi dựng ca dương; bản tải FTP thiếu thư mục → git tưởng xoá file.

### Thêm — skill `wp-delivery`

- Mục **"Nhiều worktree cùng deploy"**: sổ chiếm chỗ dùng chung qua `.git`, cổng deploy tám
  phép kiểm (ca banner "file sống trên host mà `main` không có"), và bài học "đo nhầm câu hỏi".
- Hai script **`wp_deploy_gate.py`** và **`wp_lock.py`** (genericize từ bản dùng thật): cổng
  deploy liên worktree + sổ chiếm chỗ/nhật ký. Version-constant dò theo mẫu `*_THEME_VERSION`,
  không gắn cứng một theme.
- Các bài học vận hành mới rải vào "Kiểm đúng runtime state", "Giữ pipeline WordPress", "Sửa
  dữ liệu hàng loạt", "Một luật nghiệp vụ nhiều bề mặt", "Kiểm nối asset", "Môi trường thử",
  "Đổi schema/meta/option".

---

## [0.4.0] — 2026-09-05

Thêm một phép kiểm mà cả ba tầng cũ đều mù, sau khi một phiên khác báo về đúng loại
hỏng đó đang xảy ra trên production.

### Thêm — dò loader trên host

`doi_chung_live.py --loader ... --ung-vien-file ...` so danh sách `require` trong loader
với các file `inc/*.php` THỰC SỰ có trên host, và báo hai chiều:

- **TẮT ÂM THẦM** — file có trên host (HTTP 200) mà loader không require. Tính năng
  không chạy, `php -l` sạch, không một dòng lỗi; guard `function_exists()` làm nó suy
  biến êm. Ca thật đã gặp: thiếu một dòng require → option rỗng → trang chủ rơi về nội
  dung demo, mà không có gì báo.
- **THIẾU FILE** — loader require mà host trả 404 → fatal ở mọi lượt truy cập.

Vì sao mọi phép quét chỉ đọc cây local đều mù trước ca thứ nhất: file đó có thể chưa
từng được commit vào nhánh chính. Nó tồn tại trên host và trong một nhánh tính năng,
nhưng nhánh chính không hề biết. Vì vậy danh sách ứng viên phải gom từ **mọi ref git**,
không chỉ nhánh hiện tại — script in sẵn lệnh, kèm cảnh báo `git ls-tree` chỉ nhận MỘT
tree-ish nên phải lặp qua từng ref (truyền nhiều ref là nó trả về rỗng).

### Sửa — fail-open tái phát trong chính code mới

Lần chạy đầu của phép kiểm trên báo "(khớp)" trong khi nó dò **0 file**, vì lệnh gom ứng
viên sai. Đúng cái fail-open đã sửa ở v0.2.0, tái phát trong code viết để chống nó. Nay
danh sách ứng viên rỗng là `KHONG_KIEM_DUOC` và thoát khác 0.

Và một lỗi nữa lộ ra khi viết test: sau khi in `KHONG_KIEM_DUOC`, script **vẫn in tiếp
"(khớp)"** — hai câu mâu thuẫn trong cùng một output.

Bộ test lên **38 khẳng định**, hai cái mới đều đã hiệu chuẩn ngược: gỡ chốt fail-closed
ra thì test đỏ đúng chỗ, lắp lại thì xanh.

---

## [0.3.0] — 2026-09-05

Bổ sung đúng thứ mà v0.2.0 tự khai là khoảng trống lớn nhất: **integration test trên
WordPress + WooCommerce thật**. Không còn mục nào trong bảng trạng thái ghi CHƯA TEST.

### Thêm — tầng integration

`tests/integration/` tải WordPress và WooCommerce từ wordpress.org, cài trên drop-in
**SQLite** (không cần MySQL, không cần Docker — chỉ cần PHP CLI có `pdo_sqlite`; trên
Windows script tự bật DLL có sẵn), kích hoạt một theme fixture rồi hỏi thẳng WordPress
ba câu mà phân tích tĩnh chỉ đoán được:

| Hỏi WordPress | Bằng gì |
|---|---|
| file theme nào THỰC SỰ được nạp | `get_included_files()` |
| class nào THỰC SỰ render ra | HTML thật của trang |
| hook nào THỰC SỰ đăng ký | `$wp_filter` |

**13 khẳng định**, trong đó hai chiều cố ý **không** đối xứng:
· *"tool báo chết mà WordPress có nạp"* → **hỏng nặng**, tin theo là xoá code đang chạy;
· *"WordPress không nạp mà tool bỏ sót"* → chỉ là tiếc, không mất gì.

Vòng hai chứng minh luật chết theo dây chuyền bằng chính sự thật nền: tool **giữ** CSS mà
tên class còn xuất hiện trong một template mồ côi, và chỉ xoá sau khi file đó bị xoá —
đúng lý do quy trình bắt xoá file trước rồi mới quét lại.

Theme fixture cài sẵn các ca thật: năm dạng `require`, một `require` chỉ chạy khi
WooCommerce bật, một file có `add_action` mà **không ai nạp**, một template-part mồ côi,
và một class ghép chuỗi `fxt-bac--<?php echo $n ?>`.

### Thêm — CI

Job `integration` chạy trên Ubuntu với PHP 8.2, có cache bản tải. Job `unit` giữ nguyên
ma trận Ubuntu + Windows × Python 3.9/3.12.

### Sửa

- Chốt riêng tư báo động giả trên các tên miền RFC 2606/6761 dành riêng cho ví dụ
  (`.test` `.example` `.invalid` `.localhost`). Chúng không bao giờ là địa chỉ thật, nên
  báo động ở đó chỉ dạy người ta bỏ qua cảnh báo — và cảnh báo bị bỏ qua vài lần là cảnh
  báo đã chết. Đã hiệu chuẩn: email thật vẫn bị bắt (5/5 ca).

### Vẫn chưa phủ — nói rõ, không giấu

Theme dùng autoload PSR-4 hay `spl_autoload_register`; `require` dựng trong vòng lặp;
page builder sinh markup từ JSON lưu trong database; multisite.

---

## [0.2.0] — 2026-09-05

Bản này sinh ra từ một lượt soát ngoài tìm được **ba lỗi P0** trong chính bộ công cụ
đi rao giảng về kỷ luật kiểm thử. Ba lỗi đó lọt qua vì mọi ca hiệu chuẩn đều do chính
người viết tự nghĩ ra — tức là chỉ kiểm được những cách hỏng đã nghĩ tới. Bản này sửa
lỗi, và thêm bộ test + CI để lần sau không phải trông vào trí tưởng tượng của một người.

### Sửa lỗi chặn (P0)

- **`go_css.py` ghi ra CSS hỏng mà vẫn báo PASS.** Selector tách bằng `split(",")` nên
  không hiểu dấu phẩy trong `:is()` `:not()` `:where()` `:has()` và trong `[attr="a,b"]`.
  `.x:is(.foo,.bar){…}` bị cắt thành `.bar){…}` — sai cú pháp — mà phép kiểm chỉ đếm
  ngoặc nhọn nên vẫn cân bằng, và script **đã thực sự ghi đè file nguồn**.
  Nay: tách theo độ sâu, thêm chốt "mỗi vế phải cân bằng `()` `[]`", và
  **mặc định chỉ chạy thử — phải truyền `--ghi` mới ghi**.
- **`doi_chung_live.py` fail-open.** Chạy không tham số nào vẫn in "Sạch ở tầng này"
  và thoát 0 — "chưa kiểm gì" trông y hệt "đã kiểm và sạch". Nay trả `KHONG_KIEM_DUOC`,
  nói rõ thiếu tham số nào, và thoát 2.
- **`quet_chet.py` kết luận sai về file chết, cả hai chiều.** Tham số `--loader` được
  nhận nhưng không dùng, và đồ thị không đi theo cạnh `require`/`include`. Hậu quả: một
  file chỉ khai hằng số rồi được `require_once` bị báo chết oan; ngược lại, luật "có
  `add_action` là điểm vào" khiến một file **không ai nạp** lại được coi là sống.
  Nay: điểm vào là loader + template gốc theme + override WooCommerce, và đồ thị đi
  theo `require`/`include`. Thêm **mục 2 mới: file đăng ký hook nhưng không được nạp** —
  đây là loại nguy hiểm nhất, nhìn code tưởng tính năng đang chạy mà thực ra không.

### Sửa lỗi khác, đều do bộ test mới bắt được

- `quet_chet.py` đếm hàm JavaScript trong `<script>` của file PHP như hàm PHP → báo
  "không ai gọi" → dụ người dùng xoá code đang chạy.
- Regex require thiếu chốt cuối từ nên khớp cả chữ `required` trong HTML và
  `'required' => false` trong mảng PHP: một theme thật ra 25 câu "không phân giải
  được", 24 trong đó là khớp nhầm.
- Luật bảo vệ tên ghép chuỗi **hỏng ngay tại chỗ nó sinh ra để bảo vệ**: markup ghi
  `fx-bac--<?php … ?>` thì sau gốc `fx-bac` là dấu `-`, mà lookahead lại chặn đúng ký
  tự đó — nên gốc không bao giờ khớp và `.fx-bac--2` vẫn bị xoá.
- Tên class chỉ được **nhắc trong chú thích** vẫn được tính là markup, nên câu
  `/* class .x đã bỏ */` giữ cho `.x` sống mãi.
- Chú thích đứng ngay trên một rule bị tính là một phần của selector, nên
  `/* ghi chú */ @media print { … }` không được nhận ra là at-rule và cả khối đi lọt.
- Chốt "at-rule nằm trong khối khác" quá rộng: `@media` lồng `@supports` là CSS hợp lệ.
  Nay chỉ chặn at-rule nằm trong một **style rule** — đó mới là dấu hiệu khối bị nuốt.

### Thêm

- `tests/` — bộ test chạy bằng thư viện chuẩn, **36 khẳng định**, kèm fixture PHP
  (bảy dạng `require`, `get_template_part` có/không hậu tố, JS nhúng trong PHP, bẫy
  `required`) và fixture CSS (`:is` `:not` `:where` `:has`, `[attr="a,b"]`, `@layer`,
  `@media` lồng `@supports`, `content:"}{"`, tên ghép chuỗi).
- `tests/kiem_rieng_tu.py` — chốt chặn dữ liệu riêng lọt vào repo công khai. Tên khách
  để ở `tests/rieng-tu.local.txt` (đã gitignore), không hardcode vào repo.
- CI GitHub Actions: **Ubuntu + Windows** × Python 3.9 và 3.12.
- Nhãn mức chắc chắn `AN-TOAN-CAO` / `CAN-KIEM` / `RUI-RO` trong skill CWV.

### Đổi

- Bỏ mọi tuyên bố **"an toàn 100%"** và **"Mục 1 và 2 đáng tin"**. Thay bằng điều kiện
  cụ thể: `quet_chet.py` nay in ra ngay đầu output "loader có tìm thấy không" và "bao
  nhiêu câu require không phân giải được", và nói rõ mục 1 chỉ đáng tin khi cả hai đạt.
- `wp_quality.py` không còn đường dẫn công cụ viết cứng: đọc `WP_QUALITY_TOOLS`, không
  có thì tìm trong `PATH`.
- Skill CWV: cảnh báo cụ thể "hỏng khi nào" cho `wc-cart-fragments` và
  `wp-block-library`; ghi rõ preset xuất từ LSCWP 7.8.1 và `cache-page_login` đang bật,
  phải đối chiếu lại với phiên bản đang cài.
- **Sửa một sai về phương pháp đo:** tài liệu cũ bảo đánh giá field data sau 24–48 giờ.
  CrUX báo cáo theo **cửa sổ cuốn 28 ngày**, nên sau hai ngày thay đổi mới chiếm ~2/28
  dữ liệu. Nay: xu hướng nhìn từ ngày thứ 7, kết luận sau 28 ngày.

### Chưa có — nói rõ để không ai tưởng đã có

- **Không có integration test WordPress + WooCommerce.** Bộ test hiện tại chạy trên
  fixture tĩnh; nó chứng minh bộ phân tích đọc đúng cú pháp, **không** chứng minh hành
  vi đúng trên một WordPress đang chạy với plugin thật. Đây là khoảng trống lớn nhất.
- Chưa thử trên theme dùng autoload PSR-4, `spl_autoload_register`, hay require trong
  vòng lặp — cả ba đều nằm ngoài tầm phân tích tĩnh hiện tại.
- Chưa thử trên CSS dùng cú pháp lồng gốc (CSS Nesting) hay `@container` nhiều tầng.

---

## [0.1.0] — 2026-09-05

Bản đầu: ba skill `wp-delivery`, `wp-code-cleaner`, `wp-corewebvital`, cùng hai tài
liệu bài học trong `docs/`.
