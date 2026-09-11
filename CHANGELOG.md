# Nhật ký thay đổi

Theo [Semantic Versioning](https://semver.org/lang/vi/). Trước `1.0.0`, API dòng lệnh
và định dạng output còn có thể đổi.

---

## [0.5.0] — 2026-09-10

Hai lane mới, và một lỗi trong chính tài liệu của repo.

### Thêm — Tầng 5: thước cho phép BIẾN ĐỔI, không phải cho phép xoá

Bốn tầng cũ sinh ra để chứng minh một phép XOÁ là an toàn, và ba trong bốn tầng được
tham số hoá bằng MỘT DANH SÁCH ĐÃ XOÁ. Phép viết lại không có danh sách đó nên tập
truy vấn rỗng, nên chúng **PASS RỖNG** — đúng hình dạng input đã gây ra lỗi fail-open ở
v0.2.0 và tái phát ở v0.4.0. Tầng 2 thì bị vô hiệu hoá bằng định nghĩa: chốt mạnh nhất
của nó là "rule còn lại phải NGUYÊN VĂN như cũ".

`tests/integration/adn-nen.php` + `tests/integration/tang5.py` chụp bề mặt quan sát được
trước và sau rồi đòi hiệu bằng rỗng, trên bảy mặt: file nạp (có thứ tự) · hook (priority
+ thứ tự trong bucket + callback) · chuỗi fire · hàng đợi asset · chữ ký hàm kèm giá trị
mặc định · HTML toàn văn · và một mặt TĨNH đọc điểm truy cập superglobal. Mặt tĩnh phải
có vì ca "mất lời gọi sanitise" không để lại dấu runtime nào trên request không mang
tham số đó.

Noise được **đo**, không đoán: chụp bản không đổi hai lượt trước, lệch giữa hai lượt là
noise của chính phép đo và bị trừ đi.

Đo trên WordPress 7.1 + WooCommerce thật: noise 0 trên cả bảy mặt, **6/6 ca tiêm bị
bắt**, và 6/6 bị bắt bởi đúng mặt đã dự đoán TRƯỚC khi chạy.

Hai vùng mù chỉ lộ ra nhờ ca hiệu chuẩn:

- Lượt đầu báo `NOISE_QUA_LON` ở mặt `fire`, lệch từ ký tự 3523 — lượt sau đọc option từ
  cache còn ấm nên không fire lại `pre_option_*`. Đã lọc họ hook option/transient/cache.
  **Đánh đổi khai báo rõ:** mặt `fire` nay không trả lời được "có đổi tập option được đọc
  hay không".
- Ca "đảo chiều điều kiện" ban đầu KHÔNG mặt nào bắt, và lỗi nằm ở **chính phép đo**: bộ
  chụp `require wp-load.php` rồi gọi thẳng `index.php`, bỏ qua giai đoạn `wp()` nơi hook
  `wp` fire. Callback bị đảo chiều không chạy ở cả hai bản nên hiệu rỗng giả tạo.

### Thêm — code nodes + cổng graph

`skills/code-optimize/scripts/code_nodes.py` dựng đồ thị có KIỂU (node: file · hàm ·
hook · handle asset; cạnh: require · goi · khai_bao · dang_ky · phat · enqueue ·
phu_thuoc · template_part). Đặt **cạnh** `quet_chet.py` chứ không sửa nó: `quet_chet.py`
có 13 khẳng định đang dựa vào, và nó trả lời câu khác — "cái gì chết", không phải "cái gì
nối với cái gì". Nó cũng dựng một đồ thị nội bộ nhưng chỉ file→file, không có cạnh hook,
và nó **bỏ** đồ thị đi.

`cong_graph.py` là cổng trung thực: đồ thị tĩnh là **giả thuyết**, ADN runtime là thứ phủ
định hay xác nhận nó. Hai chiều lệch không đối xứng, lấy nguyên tinh thần của
`test_integration.py`: "runtime có mà tĩnh không thấy" là **chí mạng** (node trông mồ côi
nhưng đang chạy), "tĩnh nói có mà runtime không có" là họ lỗi `TAT_AM_THAM`. Fail-closed,
exit 9, muốn đi tiếp phải khai số bằng `--chap-nhan-mu`.

Hiệu chuẩn bằng fixture `inc/hook-dong.php`: một hook tên biến, một callback ghép chuỗi —
hai dạng phổ biến nhất trong WordPress thật. 18 khẳng định, trong đó phép kiểm mạnh nhất
là **ca đối chứng ngược**: gỡ đúng file sinh ra hai cạnh động rồi đòi cổng về 0.

### Thêm — backup toàn cây + phục hồi ĐÃ DIỄN TẬP

Trước `skills/code-optimize/scripts/sao_luu.py`, repo có **0 dòng code phục hồi** và **0
khẳng định test** về backup — trong khi bộ test đã 38 khẳng định. `wp_safe_write.py` ghi
`.bak` cạnh từng file, tức không có mốc thời điểm nhất quán của cả cây. Một đường lùi chưa
từng chạy là một đoạn văn.

Ba lệnh: `luu` (chép toàn cây + manifest SHA-256 từng file, tự so bản chép với bản gốc
trước khi nhận), `kiem` (drift: THÊM / THIẾU / KHÁC), `phuc_hoi` (mặc định thử; `--ghi`
mới phục hồi thật; từ chối backup không tự nhất quán; tự so byte cây vừa dựng với manifest
— "đã copy xong" không phải "đã phục hồi xong").

23 khẳng định, ba phần, và phần ba là phần duy nhất đáng tin: hiệu chuẩn `kiem` trên ba
kiểu hỏng cố ý · làm hỏng một file **bên trong** backup và đòi `phuc_hoi` từ chối ·
**xoá hẳn cây nguồn** rồi phục hồi chỉ từ backup, so byte với bản gốc giữ riêng — 0 lệch.

`--bo-cr` chỉ dành cho `kiem` khi so local với bản tải từ host (CRLF/LF từng làm
`checkout.css` lệch đúng 1.049 byte = 1.049 dòng); test chứng minh nó **không** che được
thay đổi nội dung thật.

### Thêm — cổng clean, và skill `code-optimize`

`cong_clean.py` là cổng [0] của `/code-optimize`, fail-closed, hai điều kiện: `quet_chet.py`
quét lại phải ra **rỗng** (định nghĩa xong của chính cleaner — "lặp tới khi rỗng"), và có
backup toàn cây **khớp** cây hiện tại. Thiếu một là chặn: exit 7 `CHUA_CLEAN` hoặc exit 8
`KHONG_CO_DUONG_LUI`, và **gọi tên** đúng xác còn sót. 19 khẳng định, kể cả ca đối chứng
ngược: gieo một file mồ côi vào cây đã mở được, cổng phải đóng lại và gọi tên file đó.

`skills/code-optimize/SKILL.md` là điểm vào: pipeline bảy bước với bốn cổng, thứ tự bắt
buộc, không có `--force`. Lane biến đổi theo Mikado Method (mục tiêu → thử → vẽ graph →
**hoàn tác** → lặp → hiện thực ngược), vì đó là phương pháp có hoàn tác gắn sẵn và graph
là artefact duy nhất. `references/checklist.md`: mỗi cổng mang `because`, **không cổng nào
viện dẫn "WordPress best practice"** — thẩm quyền đó không tồn tại (Plugin Handbook tự
tuyên bố cố tình không kê đơn; Theme Handbook không có một dòng về kiến trúc PHP; core để
ngỏ ticket PSR-4 autoloader nhiều năm). Chỉ số duy nhất được phép hứa, có số đo:
`--classmap-authoritative`, 176ms → 99ms, và chỉ khi đích có Composer autoloader.

Skill này **không hứa "tinh gọn"**. Thước đếm dòng thưởng cho việc xoá thứ đắt nhất —
chú thích kể lại ca hỏng, vòng giữ thứ tự nạp, guard `ABSPATH`.

### Thêm — skill `wp-preview-builder`

Gom kinh nghiệm dựng và nghiệm thu bản xem trước thành luật, mỗi luật kèm ca hỏng đã trả
giá. Tám cạm bẫy trong `references/cam-bay-preview.md`, và cả tám đều cho ra **âm tính
giả** — không cái nào làm tool báo lỗi, chúng làm tool báo *sạch*.

### Sửa — tài liệu của repo đang dạy đúng phép đo sinh ra âm tính giả

`docs/QUY-DINH-CLAUDE-WORDPRESS.md` in công thức tràn ngang lấy `window.innerWidth` làm
số bị trừ. Trong giả lập mobile, `innerWidth` phình theo nội dung: viewport 344px với nội
dung rộng 640px thì nó báo 640, đúng bằng bề rộng cuộn, nên hiệu triệt tiêu và phép đo
trả **0** trên một trang tràn **296px**. Số 0 đó trông y hệt trang sạch.
`docs/KINH-NGHIEM-WORDPRESS.md` còn tệ hơn một bậc: tiêu chí so sánh lỗi thời, và chỉ một
bề rộng 375px. Danh sách bề rộng ở phần "cách chạy" thiếu mốc 1440 dù bảng phía trên có.

Nay công thức được ghim bằng khẳng định trong bộ test (khai báo trong file CI; nhánh này chưa push nên chưa chạy trên runner)
(`skills/wp-preview-builder/scripts/quyet_dinh_tran.py` + `tests/test_preview.py`, 29
khẳng định): cả hai công thức được giữ lại, và bộ hiệu chuẩn bắt buộc phải tồn tại một ca
mà chúng cho kết quả khác nhau — bộ nào không phân biệt được thì không kiểm gì cả.

Hai lỗ trong chính phép canh đó, tìm ra nhờ ca hiệu chuẩn dùng **nguyên văn** dòng sai
lịch sử thay vì một biến thể tự nghĩ: dòng sai gốc viết bằng dấu trừ Unicode `−`
(U+2212) nên regex chỉ khớp `-` ASCII sẽ mù trước đúng dòng nó sinh ra để chặn; và dạng
**so sánh** `scrollWidth == innerWidth` không có dấu trừ nào nên thoát hết các mẫu ban đầu.

### Sửa — bộ integration cũ xanh nhờ thứ tự chạy

`adn-nen.php --theme-slug` gọi `switch_theme()` và để nguyên — đúng thiết kế, vì nó cần
theme đó ở request kế. Hệ quả: chạy `test_cong_graph.py` rồi `test_integration.py` thì bộ
sau chụp nhầm `fixture-bien-doi`, `fxt-bac--1` không còn trong HTML, và khẳng định "class
ghép chuỗi được giữ" **đỏ**. CI xanh chỉ vì thứ tự job tình cờ đúng.

Nay mỗi bộ tự bảo đảm tiền đề của mình bằng `doi_theme.php` trước khi chụp, và
`test_integration.py` có thêm một khẳng định: theme đang chụp đúng là theme của nó. Chạy
bốn bộ theo thứ tự đảo ngược để chứng minh: xanh hết.

Phép sửa này lộ thêm một nguồn noise cho Tầng 5: hook `query` của `$wpdb` fire ở lượt A
(ngay sau đổi theme, cache vừa flush, đọc `site_option` từ DB) mà không fire ở lượt B
(đọc từ cache). Cùng họ với noise option/transient, cùng cách xử lý, và cùng đánh đổi khai
báo: mặt `fire` không trả lời "có đổi số truy vấn DB không".

### Sửa — chốt riêng tư xanh nhờ may

`tests/kiem_rieng_tu.py` quét cả `.wp-it/`, nên hễ ai chạy tầng integration ở máy là nó
đỏ **462 dòng** email tác giả trong core WordPress. CI vẫn xanh, nhưng xanh **nhờ may**:
chốt chạy ở job `unit`, mà job `unit` không dựng `.wp-it`. Bảo vệ thật chỉ tồn tại do
tình cờ hai job tách nhau — và 462 báo động sai thì không ai đọc tới dòng 463.

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
