---
name: wp-delivery
description: |
  Quy trình sửa code, kiểm thử và đưa thay đổi lên site WordPress an toàn.
  Dùng khi sửa theme/child theme/plugin/functions.php, CSS/JS/template, luồng WooCommerce,
  sửa dữ liệu hàng loạt có rủi ro, deploy qua FTP/File Manager, hoặc điều tra tình trạng
  "local đúng nhưng host lệch", cache giữ bản cũ và màn hình trắng sau upload.
  Không dùng thay quy trình biên tập nội dung CMS đơn thuần hoặc tối ưu hiệu năng chuyên sâu.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - AskUserQuestion
---

# Đưa thay đổi lên WordPress mà không làm sập site

Skill này lo **code và deploy**. Nếu được cài trong môi trường hiện tại, hai skill liên quan là:

- `wordpress-ops` — sửa **nội dung** qua REST (Elementor, widget, reusable block, Rank Math, KSES)
- `wp-corewebvital` — **tốc độ** (LiteSpeed, WebP, dequeue)

Nếu repo có `CLAUDE.md` hoặc `AGENTS.md`, đọc nó trước — luật của repo thắng skill này.

## Bước 0: đây có phải dự án WordPress không

```bash
ls wp-config.php wp-content 2>/dev/null            # mã nguồn đầy đủ
ls style.css functions.php 2>/dev/null             # chỉ có thư mục theme
curl -s -o /dev/null -w "%{http_code}" "$SITE/wp-json/"   # site sống
```

Chỉ có thư mục theme thì **phạm vi kết luận cũng chỉ tới đó**: "đã soát theme; chưa soát runtime
và dữ liệu". Không bao giờ nói "đã audit toàn site" khi chưa nhìn thấy plugin và database.

## Chọn tầng — đừng bắt mọi task chạy đủ quy trình

| Tầng | Khi nào | Bắt buộc |
|---|---|---|
| **A** | sửa code nhỏ, một bề mặt, không đổi cấu trúc hay luồng nghiệp vụ | Cổng 1 + xác minh trên trang thật |
| **B** | sửa CSS/template một bề mặt | A + snapshot + kiểm nối asset + purge |
| **C** | chạm tiền, lead, dữ liệu hàng loạt, `functions.php`, plugin | đủ quy trình |

Tầng C mặc định khi đụng: giá, giỏ hàng, thanh toán, form, email, `functions.php`,
`wp-config.php`, plugin, hoặc sửa quá 5 bài.

---

## Cổng 1 — Đúng đích và tươi mới. Không qua cổng này thì chưa được sửa

Trạng thái mặc định là **UNKNOWN**, không phải "chắc là khớp".

Trước khi so file, chốt danh tính phép sửa:

```yaml
target_site: ""          # domain chính xác
environment: ""          # production / staging / local
canonical_source: ""     # cây source DUY NHẤT được phép sửa
deploy_root: ""          # thư mục đích trên host
deployment_method: ""    # FTP / File Manager / CI / khác
live_release: ""         # version/hash đang quan sát được
```

Không suy ra `canonical_source` từ tên thư mục. Nếu có `theme/`, `source code/theme/`, `_upload/`
hoặc nhiều bản tương tự, phải chứng minh bản nào là nguồn chuẩn và bản nào chỉ là build/staging.
Xác nhận domain và tài khoản/kết nối đang trỏ đúng site trước mọi thao tác ghi.

```bash
# 1. bản local đang ở đâu
git -C "$REPO" log -1 --format="%h %s" 2>/dev/null; git -C "$REPO" status --short

# 2. host đang chạy gì — version theme lộ ra trong HTML
curl -s "$SITE" | grep -oE "themes/[^/]+/[^\"']*\?ver=[0-9.]+" | head -5

# 3. so file thật: tải asset từ host rồi diff với local (bỏ khác biệt CRLF/LF)
curl -s "$SITE/wp-content/themes/$THEME/assets/css/main.css" -o /tmp/host.css
diff <(tr -d '\r' < "$LOCAL/assets/css/main.css") <(tr -d '\r' < /tmp/host.css) | head
```

**Đã trả giá:** local và host cùng ghi version `1.17.1` nhưng `main.css` lệch 1.492 ký tự trong
3 khối — deploy lần sau sẽ mang theo thay đổi chưa ai duyệt. Cùng số version **không** có nghĩa
cùng nội dung.

Lệch byte chưa chắc hỏng: local CRLF vs host LF. Một file từng lệch đúng 1.049 byte vì nó có
đúng 1.049 dòng. Luôn chuẩn hoá xuống dòng trước khi so.

**File PHP không tải được qua trình duyệt** → không có cách đối chiếu. Vì vậy backup phải lấy
từ FTP của host, không phải bản local.

---

## Cổng 2 — Khoanh vùng theo tính năng, không theo tên file

Bắt đầu từ mục tiêu nghiệp vụ, truy ngược ra danh sách đầy đủ:

```
dữ liệu  →  hàm tính  →  hook  →  nơi hiển thị  →  AJAX  →  schema  →  URL cần kiểm
```

Hỏi WordPress lúc chạy, đừng đoán từ tên file (WP đăng ký hook bằng chuỗi, chọn template từ
database, plugin lọc lẫn nhau — phân tích tĩnh vừa thiếu vừa nhiễu):

| Muốn biết | Hỏi bằng |
|---|---|
| hook nào đang gắn, priority bao nhiêu | duyệt `$wp_filter['<hook>']` |
| URL này render bằng template nào | log `template_include` |
| trang này nạp asset nào | `wp_styles()->queue`, `wp_scripts()->queue` |
| nội dung hiển thị nằm đâu | meta `_elementor_edit_mode`, `wp/v2/widgets`, `wp/v2/blocks` |
| trang nào thực sự công khai | **crawl HTML**, không đếm bằng REST API |

Câu cuối là bài học đắt nhất: REST API cho biết *database có gì*, không cho biết *website là gì*.
Một site có 4 danh mục công khai mà WooCommerce API không trả về. **Lỗi này lặp 4 lần.**

**Dừng ngay** nếu tìm thấy hai bản cài đặt cùng làm một việc mà chưa biết cái nào đang chạy.

### Trước khi tạo file override

Các file như `taxonomy-*.php`, `archive-*.php`, `single-*.php`, WooCommerce override và template
được chọn từ database có thể che toàn bộ giao diện cũ dù chỉ thêm một file. Trước khi tạo chúng:

1. Ghi lại template đang thắng trên URL thật và đường phân giải tới nó.
2. Liệt kê hook, sidebar, bộ lọc, banner, schema và hành vi cũ sẽ mất hoặc đổi.
3. Chọn rõ **mở rộng**, **thay tại chỗ** hay **thay toàn bộ**; mất chức năng đáng kể thì phải hỏi.
4. Đưa chính danh sách cần giữ vào `invariants` và kiểm lại sau deploy.

### Giữ pipeline WordPress, không tự chế lại

Trước khi thay `the_content()`, `wp_head`, `wp_footer`, shortcode, hook của WooCommerce hay bất kỳ
hàm template nào của core: **liệt kê filter và side effect đang bám vào pipeline đó**. Những hàm này
là điểm nối của hàng chục plugin, không phải hàm tiện ích.

- Không thay `the_content()` bằng `wpautop()` + KSES thủ công khi chưa chứng minh tương đương —
  đã tự chế đúng kiểu đó một lần và **sai cả hai đầu**.
- `get_template_part()` **không kế thừa biến local của caller**. Truyền `$args`, hoặc để template
  tự lấy dữ liệu. Đây là lỗi hợp đồng API, `php -l` không bắt được.
- Sửa xong phải test trên WordPress thật, không phải trên bản dựng tay.

### `functions.php` chỉ là bootstrap — cấm biến thành bãi chứa code

`functions.php` chỉ được chứa: guard `defined('ABSPATH') || exit;` · hằng số nền cần trước
bootstrap · `require_once`/autoload · một lời gọi khởi động.

**Không đặt trực tiếp vào đó:** `add_action`/`add_filter` của tính năng, truy vấn, AJAX/REST
handler, shortcode phức tạp, cron, logic giá/giỏ/checkout của WooCommerce, xử lý form, CSS/JS
inline. Những thứ đó vào file đặt tên theo trách nhiệm trong `inc/`, hoặc vào **site plugin /
mu-plugin** nếu tính năng phải sống sót khi đổi theme.

Mục tiêu: **≤ 80 LOC thực thi**. File mới vượt ngưỡng trả `FUNCTIONS_PHP_TOO_LARGE`.

Số đo thật (01/09/2026): `mytheme/functions.php` **48 LOC — đạt**;
`theme-b/functions.php` **1.218 LOC — vượt 15 lần**.

**Với file legacy đã quá lớn:** không refactor big-bang giữa một task có mục tiêu khác. Nhưng
cũng **không được nhét thêm** — LOC ròng không tăng. Sửa tối thiểu tại chỗ chỉ chấp nhận khi
việc tách làm phình rủi ro, và phải ghi lý do trong Change Manifest.

### Kích cỡ module — chuông báo kiến trúc, không phải trò đếm dòng

| Đối tượng | Mục tiêu | Xem lại | Chặn |
|---|---:|---:|---:|
| `functions.php` | 80 | — | > 80 (file mới) |
| PHP / JS module | 300 | 301–450 | > 450 |
| function / method | 40 | 41–80 | > 80 |
| CSS component | 400 | 401–600 | > 600 |

LOC bỏ dòng trống, comment thuần, vendor, file build, `.min.*`.

**Ngưỡng chỉ là chuông.** Một file 100 dòng giữ ba trách nhiệm vẫn phải tách; một bảng khai báo
dài thuần dữ liệu có thể được miễn khi nói rõ lý do. Và **không được lách bằng cách chẻ ra
`helpers.php`, `misc.php` hay dựng class/trait rỗng nghĩa chỉ để qua số dòng** — đó là làm tệ hơn
mà trông đẹp hơn.

Đo bằng script, không đếm tay:

```bash
# chụp hiện trạng một lần cho mỗi theme, rồi commit file .module-size.json
python skills/wp-delivery/scripts/wp_module_size.py \
  --scan "<theme>" --write-baseline "<theme>/.module-size.json"

# kiểm trước khi ghi hoặc deploy
python skills/wp-delivery/scripts/wp_module_size.py \
  --check "<theme>" --baseline "<theme>/.module-size.json"
```

File **có** trong baseline là legacy: không áp ngưỡng, nhưng phình thêm thì trả `LEGACY_GREW`
và chặn. File **không có** trong baseline là mới: áp ngưỡng chặn. Baseline đã chụp cho
`mytheme` (119 file) và `theme-b` (98 file) ngày 01/09/2026.

### Chọn nơi sở hữu thay đổi

- Nội dung hoặc cấu hình đã có trường trong WordPress/WooCommerce/Rank Math → ưu tiên CMS/API.
- Logic nghiệp vụ dùng qua nhiều bề mặt → đặt ở plugin/site plugin hoặc một module dùng chung.
- Theme chỉ sở hữu phần trình bày đặc thù của theme. Không hard-code một thiết lập mà core/plugin
  đã cho quản trị trong giao diện; hai nguồn cấu hình sẽ lệch nhau và rất khó tháo gỡ.

### Change Manifest — viết trước khi mở editor

```yaml
goal: ""
baseline_release: ""
canonical_source: ""
deploy_root: ""
files_to_change: []
surfaces_to_verify: []   # bề mặt phải kiểm DÙ KHÔNG SỬA
invariants: []
rollback_plan: []
blocking_unknowns: []    # mọi điều chưa rõ có thể đổi kết quả/rủi ro phải được giải quyết
status: "PLANNED"
```

Phát sinh file ngoài danh sách → dừng, khai lại. Phạm vi phình dần là dấu hiệu phép sửa đã lạc.

**Không tự mở rộng sang:** migration/schema, `.env` và mọi secret, cấu hình CI, lockfile, thư mục
vendor/generated. Không xoá, bỏ qua hoặc làm yếu test cũ để đổi một màu xanh giả; được cập nhật
hoặc bổ sung test khi hành vi đã được duyệt thực sự thay đổi. Cần mở rộng phạm vi thì **báo cáo**,
để người dùng quyết.

---

## Ghi file: không bao giờ mở file sống ở chế độ ghi

Mở mode `w` là cắt trắng file ngay lập tức. Script lỗi giữa chừng → file rỗng → site chết.
Đã xảy ra với `functions.php`.

Thứ tự bắt buộc: **đọc → backup → ghi ra file tạm cùng thư mục → kiểm (`php -l`, kiểm cấu trúc
CSS/JS, độ dài > 0) → đổi tên đè lên → đọc lại so hash.**

### Sửa file bằng cắt-dán chuỗi: đếm tổng là phép kiểm mù

Vá file bằng `replace`/slice theo mốc chuỗi là cách nhanh nhất, và cũng là cách dễ cắt nhầm mốc
nhất. Loại hỏng đặc trưng của nó **không làm lệch tổng ngoặc**:

**Đã trả giá (01/09/2026):** một bản vá CSS cắt tới dấu `}` đóng của một *rule* thay vì dấu `}`
đóng của cả `@media`. Khối media bị nhét vào giữa một media khác, **toàn bộ CSS phía sau rơi vào
trong nó** nên chỉ áp ở màn hẹp — desktop mất sạch style của một section. Tổng ngoặc vẫn **243/243**
vì chỗ này thiếu một dấu đóng thì chỗ kia thừa đúng một dấu: **cân bằng giả**. Phép kiểm "đếm ngoặc"
cho lỗi này đi lọt hoàn toàn, và mắt người cũng không thấy vì phần hỏng nằm ngoài màn hình đang xem.

Ba chốt thay cho một, chạy **trước khi ghi**:

1. tổng `{` = tổng `}` (sau khi đã bỏ comment và chuỗi — `content:'}{'` là hợp lệ)
2. **độ sâu không bao giờ âm** → bắt dấu `}` mồ côi giữa file
3. **không at-rule nào nằm trong khối khác** (`@media`/`@supports`/`@layer`/`@container`) → bắt
   khối bị nuốt. Dự án dùng CSS Nesting thật thì đặt `WP_ALLOW_NESTED_AT=1`

`check_braces()` trong `wp_safe_write.py` đã cài đủ ba chốt và **đã được hiệu chuẩn bằng chính ca
hỏng trên**: nó FAIL đúng ca đó dù ngoặc 6/6, và PASS với `content:'}{'`, comment `/* } */`, chuỗi
JS `'}'`. Thước đo nào chưa bắt được ca hỏng đã biết thì mọi PASS từ nó là `NOT_TESTED`.

### Mốc chèn phải DUY NHẤT — dùng `wp_patch.py`, đừng gọi `str.replace` trần

Cùng ngày 02/09/2026, **cùng một mốc** `/* ---------- TIN TỨC ---------- */` gây hỏng **hai lần**,
vì nó có mặt ở CẢ khối CSS lẫn khối JS trong một file:

- **lần 1** — cắt đoạn theo hai mốc, lấy nhầm cặp ngược nhau → slice rỗng → `replace('')` chèn vào
  giữa mọi ký tự; kết quả là media lồng media, toàn bộ CSS phía sau mất tác dụng ở desktop.
- **lần 2** — `str.replace(moc, css + moc)` **không giới hạn số lần** → khối CSS bị chèn vào cả hai
  chỗ; bản rơi vào `<script>` giết chết toàn bộ JS của trang.

Cả hai lần đều lọt qua phép đếm ngoặc. Chốt phải nằm chỗ khác:

```python
import sys, os
sys.path.insert(0, os.path.expanduser("skills/wp-delivery/scripts"))
from wp_patch import thay, chen_truoc, cat_giua, kiem_html, ghi_an_toan

s = thay(s, cu, moi)          # ném lỗi nếu `cu` không xuất hiện ĐÚNG 1 lần
s = chen_truoc(s, moc, khoi)  # ném lỗi nếu `moc` không duy nhất
cat_giua(s, dau, cuoi)        # ném lỗi nếu hai mốc ngược thứ tự
kiem_html(s, 'file.html')     # CSS còn là CSS · JS còn là JS · node --check từng <script>
```

`kiem_html` đã hiệu chuẩn **11 ca**: qua file thật, chặn CSS-lọt-script, @media-lọt-script,
JS-lọt-style, thiếu `}`, thừa `}`, JS vỡ cú pháp, mốc trùng, mốc thiếu, mốc ngược. Hai điều cần nhớ
khi dùng: file **template còn placeholder** (`/*__DATA__*/`) thì gọi `bo_qua_node=True`, và
`<script type="application/ld+json">` được bỏ qua tự động — JSON-LD không phải JS.

**Gắn `kiem_html` vào chính script build**, đừng để nó là bước phải nhớ chạy tay.

Sau khi vá xong, **so lại cái mình không định đụng**: mở đúng bề mặt nằm *phía sau* chỗ vừa sửa
trong file. Lỗi kiểu này luôn hiện ra ở đó chứ không ở chỗ vừa sửa.

`php -l` không bắt được lỗi nạp runtime: gọi hàm plugin trước khi plugin sẵn sàng, `require` hai lần,
trùng tên hàm/class, hoặc hook sai thời điểm. Với file boot/loader: ưu tiên `require_once`, guard
dependency bằng `function_exists`/`class_exists`, nạp tại hook phù hợp, rồi smoke-test ít nhất một
URL có chức năng và một URL không có chức năng đó.

---

## Cổng 3 — Chất lượng code. `php -l` sạch chưa đủ để deploy

Cổng ghi file bảo vệ file khỏi rỗng và lỗi cú pháp. Cổng này bảo vệ code khỏi sai chuẩn
WordPress, sai tương thích PHP và sai kiểu. **Hai cổng không thay nhau.**

```bash
python skills/wp-delivery/scripts/wp_quality.py \
  --repo "<gốc repo>" --files "<đường/dẫn/file/vừa/sửa.php>"
```

**Chạy trên file đang sửa, không chạy toàn theme.** Mã kế thừa có sẵn hàng nghìn vi phạm; quét
toàn bộ chỉ ra một con số làm nản lòng rồi không ai đọc. Luật là **code mới không được tạo thêm
vi phạm**, không phải làm sạch quá khứ.

Mỗi phép kiểm báo **riêng** một trạng thái, không gộp thành một chữ PASS:

| Trạng thái | Nghĩa | Hành vi |
|---|---|---|
| `pass` | đã chạy, sạch trong phạm vi đã khai | đi tiếp |
| `fail` | đã chạy, có lỗi | chặn |
| `unavailable` | thiếu binary hoặc thiếu config | **chặn** — không được đọc thành "không có lỗi" |
| `not_applicable` | không có file thuộc loại đó | ghi rõ lý do |

`unavailable` **fail-closed**. Thiếu PHPStan là `PHPSTAN_UNAVAILABLE`, không phải
`STATIC_CHECKS_PASSED`. Muốn đi tiếp thì cài công cụ, hoặc xin người dùng duyệt ngoại lệ cho
đúng lần đó — ngoại lệ không tự cấp, và không biến phép kiểm thành pass.

### Bộ công cụ (đã cài 01/09/2026)

| Thứ | Ở đâu |
|---|---|
| PHPCS 3.13.6 + WPCS 3.4.1 + PHPCompatibilityWP | `<thư-mục-công-cụ-ngoài-repo>/vendor/bin/` |
| PHPStan 2.2.12 + phpstan-wordpress + WooCommerce stubs | cùng chỗ |
| `phpcs.xml.dist`, `phpstan.neon.dist` | **gốc repo**, không đặt trong theme |

Đặt config ngoài thư mục theme là cố ý: mọi thứ trong theme đều có thể bị kéo lên host, và
`vendor/` 40MB thì không có việc gì trên production.

**PHPStan phải chạy với `--memory-limit=3G`.** Stub WooCommerce nặng, worker vượt mặc định rồi
crash — và PHPStan báo chính cái crash đó thành `Found 1 error`, rất dễ đọc nhầm thành lỗi code.
Wrapper đã xử lý và phân loại nó thành `unavailable` chứ không phải `fail`.

### Hiện trạng đo được (01/09/2026)

| Repo | PHPCS | PHPStan level 5 |
|---|---:|---:|
| Dự án A (`mytheme`) | 232 vi phạm / 37 loại | 146 lỗi |
| Dự án B (`theme-b`) | **4.180 lỗi + 248 cảnh báo** / 64 file | chưa chạy |

Trong 232 vi phạm của Dự án A có **23 lỗi bảo mật thật**: 13 `InputNotSanitized`,
10 `OutputNotEscaped`, cộng 7 `NonceVerification.Missing`. Đây là thứ đáng tiền của cả cổng này.

**Chỉnh cấu hình là để tín hiệu nổi lên, không phải để số nhỏ đi.** Lần chạy đầu ra 884 lỗi,
trong đó 540 chỉ vì khai prefix `mg` (WPCS từ chối prefix dưới 4 ký tự) và 107 vì CRLF của
Windows. Ba con số đó che mất 23 lỗi bảo mật. Đã khai lại prefix theo từng họ thật (`mg_dc`,
`mg_nh`, `mg_smtp`…) và loại nhóm thuần định dạng — **không loại một sniff bảo mật nào**.

## Deploy theo đợt — thứ tự quyết định sống chết

### Dựng gói từ manifest, không tái dùng thư mục upload cũ

Mỗi lần đóng gói, tạo một thư mục rỗng mới rồi chỉ chép `files_to_change` vào đúng cây đích.
So danh sách và hash giữa source với gói trước khi mở thư mục cho người dùng upload. File cần xoá
phải nằm trong **delete list riêng**, không để lẫn trong gói ghi đè. Không tái dùng `_upload/` cũ:
một template override tưởng đã huỷ nhưng còn sót trong đó có thể quay lại host ở lần kéo tiếp theo.

Gói phải cho biết: release nguồn, các đợt theo thứ tự, file mỗi đợt, delete list và rollback tương
ứng. Gói không khớp Change Manifest → không được gọi là sẵn sàng deploy.

### Thêm logic mới

| Đợt | Làm gì | Vì sao |
|---|---|---|
| 0 | backup mọi file sẽ bị ghi đè, ở mọi đợt | không chỉ file của đợt cuối |
| 1 | **file mới** (host chưa có) | chưa ai gọi tới, site không đổi gì |
| 2 | **loader** (`functions.php`) | bật các file vừa lên |
| 3 | **file sửa đè** (template, part) | giao diện mới hiện ra |
| 4 | purge cache | |
| 5 | xác minh canonical | |

**Đã trả giá:** `functions.php` lên **trước** file `inc/` → mỗi lượt truy cập là màn hình trắng.
Lên **sau** file sửa → trang thanh toán chết trong khi các trang khác vẫn chạy, nên rất dễ không
ai phát hiện.

**Điều kiện giữa đợt 2 và 3:** logic mới phải **tương thích ngược với template cũ**. Giữa hai đợt,
site vẫn đang phục vụ khách bằng template cũ.

### Đổi schema/meta/option — giữ đường lùi

Khi đổi tên custom field, option, taxonomy key hoặc cấu trúc dữ liệu: triển khai theo pha
**đọc cũ + mới → ghi song song → deploy consumer đọc mới → xác minh live → mới dọn dữ liệu cũ**.
Không xoá khoá cũ khi code đang chạy trên host vẫn còn đọc nó. Nếu không thể tương thích hai chiều,
coi đó là migration riêng và xin phép, không giấu vào một bản sửa giao diện.

### Gỡ logic cũ — đi ngược chiều

| Đợt | Làm gì |
|---|---|
| 1 | sửa consumer để **ngừng gọi** logic cũ |
| 2 | gỡ `require`/hook trong loader |
| 3 | xoá file cũ **sau cùng** |

Dùng nhầm chiều = có khoảng thời gian consumer gọi hàm không còn tồn tại → fatal error.

### Giao gói cho người dùng upload — giao THƯ MỤC, không giao tên file

Khi người dùng là người tự đẩy file lên host, phần "giao hàng" cũng là một bước của quy trình,
không phải câu nói thêm ở cuối. Người ta không kéo được **tên file in trong khung chat**, cũng
không mở được thẻ file đính kèm. Thứ kéo được chỉ có một: **một thư mục đang mở sẵn trên màn hình**.

Ba việc bắt buộc, làm đủ cả ba:

1. **Xuất ra thư mục cha**, cây bên trong phản chiếu đúng cây đích trên host. Người dùng kéo là
   trúng chỗ, không phải tự dựng lại đường dẫn bằng tay.
2. **Tự mở trình quản lý tệp** tại thư mục đó — đừng bắt người dùng đi tìm:

   ```bash
   explorer.exe "D:/duong/dan/UPLOAD-<ngay>"    # Windows
   open "/duong/dan/UPLOAD-<ngay>"              # macOS
   xdg-open "/duong/dan/UPLOAD-<ngay>"          # Linux
   ```

3. **Nói rõ ba câu**: đứng ở đâu trên host · kéo cái nào · thả vào đâu. Thiếu câu đầu là nguồn gốc
   của lỗi lồng thư mục.

Chọn **cấp kéo** theo chế độ ghi của công cụ, vì hai chế độ cho kết quả trái ngược:

| Công cụ | Thả thư mục trùng tên | Cấp nên kéo |
|---|---|---|
| FTP client (FileZilla, WinSCP) | **merge** — chỉ file trùng tên bị đè | kéo được ở cấp cao: cả thư mục theme vào `themes/` |
| File Manager trên cPanel/DirectAdmin | có thể **replace** cả thư mục | kéo ở **cấp sâu nhất mà đích đã tồn tại** |

Không chắc công cụ nào thì chọn cấp sâu nhất — mất nhiều cú kéo hơn nhưng không có đường nào dẫn
tới xoá trắng một thư mục đang chạy.

Trước khi mở thư mục cho người dùng: `cmp`/hash gói với nguồn, chạy `php -l` trên file PHP **trong
gói** (không phải chỉ trên bản source), và in kích thước từng file. Người dùng nhìn kích thước để
biết mình kéo đúng bản, không phải bản cũ còn sót.

Gói đã mở cho người dùng rồi mà code còn sửa tiếp → **chép đè lại gói và nói rõ đã chép lại**.
Người dùng không có cách nào tự biết thư mục đang mở đã cũ.

### Kéo thả FTP

Đứng ở `wp-content/themes/` mà kéo **nguyên khối thư mục theme**. Kéo nhầm thư mục đóng gói thì
host mọc ra `themes/1-file-moi/`. "Select All → Move" trong File Manager cũng chọn cả thư mục con
và gây lồng thư mục.

Mỗi lần đẩy phải bump đúng **nguồn version mà `wp_enqueue_*` thực sự dùng** (theme version,
constant release hoặc `filemtime`, tuỳ code). Chỉ đổi header theme mà asset vẫn giữ `?ver=` cũ
không có tác dụng. Thấy release/asset version cũ trong HTML nghĩa là file trượt hoặc cache còn cũ,
dừng lại để phân biệt trước khi sửa tiếp.

---

## Kiểm nối asset — chỗ làm layout lệch

Một layout đúng cần cả chuỗi còn nguyên:

```
template → DOM class → CSS file → style handle → điều kiện enqueue → file trong gói deploy → cache đã purge
```

Đứt mắt nào cũng ra cùng triệu chứng "trên máy đẹp, lên host lệch". Ba câu hỏi cho mỗi URL đại diện:

1. **CSS/JS mới có tới được người dùng không?** Phải đạt một trong hai: handle có trong queue của
   URL dự kiến, **hoặc** được `@import`/bundle vào asset đang tải. Không đường nào → orphan, chặn deploy.
2. Có handle trùng, hoặc hai file cùng nội dung nạp hai lần không?
3. File có tải **200** và **content hash khớp** bản vừa đẩy không? Queue chỉ chứng minh WordPress
   *định* nạp; network mới chứng minh nó *đã* nạp.

**Queue không bắt được specificity.** CSS tải đúng vẫn có thể bị rule cũ đè — một nút submit từng
ra màu xanh dương vì rule cũ `(0,2,2)` thắng rule mới `(0,2,1)`. Phải đọc *computed style* của vài
phần tử trọng yếu trên trang thật.

---

## Xác minh 4 tầng — dừng ở tầng 1 là cách báo cáo sai ra đời

| Tầng | Hỏi gì |
|---|---|
| 1. Storage | trường đã ghi đúng chưa |
| 2. Runtime | WordPress/plugin có đọc đúng không (object cache có thể trả bản cũ) |
| 3. Bề mặt công khai | canonical URL hiển thị đúng chưa, đã purge chưa, computed style đúng chưa |
| 4. Hành trình nghiệp vụ | form gửi được, giỏ tính đúng, đơn đặt được |

Từng báo "299/299 thành công, quét lại còn 0" — đúng với trường `content`, nhưng 69 trang Elementor
vẫn hiển thị dữ liệu cũ. **Ghi đâu đọc đó thì luôn khớp.**

### Bốn nhãn, không được nâng cấp lẫn nhau

- `CONCEPT_PREVIEW` — HTML tĩnh; chỉ chứng minh bố cục cô lập, không chứng minh integration WordPress.
- `VISUAL_PASS` — đã xem trên WordPress thật, đúng URL, đủ plugin và dữ liệu.
- `PRODUCTION_VERIFIED` — đã xem trên canonical URL sau khi purge.
- `NOT_TESTED` — không thử thật được. Ghi rõ, **không im lặng nâng thành PASS**.

Nhãn bằng chứng ở trên khác với trạng thái giao hàng. Mỗi lần báo tiến độ phải dùng đúng một trạng
thái: `PLANNED` → `LOCAL_VERIFIED` → `PACKAGE_READY` → `UPLOADED_UNVERIFIED` →
`PRODUCTION_VERIFIED`. Từ "xong" đứng một mình không có nghĩa; phải nói xong ở trạng thái nào.

### Dữ liệu thử không được giả làm dữ liệu thật

Số liệu bịa để xem thử phải được đánh dấu **ngay tại chỗ hiển thị**, không giấu ở chú thích cuối
trang, và không bao giờ dùng để chứng minh production đúng. Khi bản trong file và bản trên site
khác nhau, nói rõ mỗi con số đến từ đâu và cái nào mới hơn — đừng lặng lẽ chọn nguồn thuận tiện.

### Một luật nghiệp vụ, nhiều bề mặt

Giá, điều kiện giao, trạng thái đơn và mọi luật ảnh hưởng tiền/lead phải có **một model chuẩn**.
Lập ma trận cùng một bộ ca qua nơi hiển thị, AJAX, giỏ, checkout, email và dữ liệu lưu. Test ít nhất:
ngay dưới/ngay tại/ngay trên mỗi mốc; thiếu field; giá/bậc bằng nhau; đơn vị không phải kg; giỏ rỗng
và nhiều dòng. Một bề mặt tự cài lại luật bằng JS/PHP riêng là lỗi kiến trúc cho tới khi chứng minh
được nó chỉ trình bày kết quả của model chuẩn.

### Kiểm đúng runtime state

Cùng một URL cho ra kết quả khác nhau tuỳ **trạng thái đo**. Mỗi phép đo phải ghi rõ nó thuộc trạng
thái nào, và before/after phải so **trong cùng một trạng thái**:

| Trạng thái | Đo được gì |
|---|---|
| khách vãng lai, cache miss (nguội) | PHP chạy thật — số xấu nhất, và là số phản ánh khách đầu tiên |
| khách vãng lai, cache hit (ấm) | trải nghiệm của phần lớn người dùng |
| đã đăng nhập / admin | **không đại diện cho ai cả** — bỏ qua cache, nạp thêm thanh admin và script quản trị |

Ba thứ **không được dùng để kết luận trải nghiệm công khai**: DOM đọc trong trình duyệt đang đăng
nhập, plugin debug, và TTFB đo ở trang admin.

Khi cần quy nguồn lỗi, dùng thêm **một URL đối chứng** — trang không dùng chức năng vừa sửa. Đối
chứng hỏng theo nghĩa là lỗi nằm ở tầng chung (loader, cache, hosting); đối chứng còn nguyên nghĩa
là lỗi khu trú đúng chỗ vừa đụng.

### Đọc kết quả sau deploy

| Origin | Canonical | Asset | Kết luận |
|---|---|---|---|
| mới | mới | mới | đạt |
| mới | **cũ** | bất kỳ | cache công khai còn cũ → purge |
| mới | mới | **cũ** | version asset không đổi → sửa `?ver=` |
| cũ | cũ | cũ | deploy chưa lên |

`x-litespeed-cache: hit/miss` là cách rẻ nhất tách "deploy hỏng" khỏi "cache giữ bản cũ" — hai lỗi
trông giống hệt nhau trên trình duyệt. `?cb=…` có thể dùng để hỏi **origin đang có gì**, nhưng vì
server coi đó là URL mới nên không chứng minh khách ở canonical URL đã thấy bản mới. Luôn kiểm cả
origin có cache-busting và canonical không cache-busting; không thay phép đo thứ hai bằng phép đầu.

---

## Môi trường thử — và bốn thứ nó không thay thế được

Không có WordPress chạy được ngoài production thì mọi phép sửa PHP đều là thử trực tiếp trên site
đang bán hàng, và mọi bản xem trước chỉ là `CONCEPT_PREVIEW`.

Local **không** mô phỏng được, phải kiểm lại sau deploy: **LiteSpeed** (cache/purge), **WAF**
(chặn có chọn lọc đường ghi, trả HTML thay vì JSON), **mail server thật**, **cấu hình riêng của
hosting**. "Đã pass local" không miễn trừ bốn thứ này.

Harness cũng là một dụng cụ cần hiệu chuẩn. Trước khi tin số đo responsive/runtime, kiểm nó có dùng
đúng CSS/JS/markup production không, media query đang đọc viewport nào, và có stub nào che lỗi thật
không. Cho một assertion đã biết trước chạy qua harness; nếu thước không đo đúng ca kiểm soát thì
mọi PASS từ nó là `NOT_TESTED`.

---

## Ghi qua REST/API — chốt write-set trước

Trước khi ghi, viết ra hai danh sách: **trường định sửa**, và **trường phải giữ nguyên**. Gửi payload
nhỏ nhất có thể — mỗi trường thừa trong payload là một trường có thể bị ghi đè ngoài ý muốn.

**HTTP 2xx chỉ chứng minh request được nhận.** Nó không chứng minh dữ liệu được áp dụng, cũng không
chứng minh không có ghi kèm ngoài ý muốn. Đã gặp: `POST {"meta": …}` trả 200 nhưng plugin bỏ qua
hoàn toàn, response chỉ có `{"footnotes": ""}`.

Sau khi ghi, đọc lại **ba thứ**: trường đích, trường lẽ ra phải giữ nguyên, và **ít nhất một bề mặt
render**. Thiếu vế thứ hai là cách mất dữ liệu âm thầm — một tool cập nhật meta SEO từng gửi lại
**toàn bộ object**, và phần mô tả đã dán tay bị bức tường KSES bóc sạch trên đường đi.

**Tool nào luôn gửi lại toàn object thì bắt buộc backup + diff before/after trước khi dùng trên
production.** Không có ngoại lệ, kể cả khi "chỉ sửa một trường".

## Sửa dữ liệu hàng loạt

Trước khi ghi: chốt schema/đơn vị/null semantics, inventory nguồn, khoá định danh và quy tắc map;
chạy dry-run để in số sẽ tạo/sửa/bỏ qua/lỗi. Dùng một mẫu/canary khi kết quả chưa được duyệt; nếu
người dùng đã duyệt mẫu và yêu cầu chạy một lần thì vẫn phải giữ log ID trước/sau và đường rollback.

Sau khi ghi, đối chiếu **đếm trước/sau + mẫu biên + bề mặt công khai**. "API trả thành công N lần"
không chứng minh N đối tượng hiển thị đúng, cũng không cho phép tự sửa typo, gộp taxonomy hay điền
giá trị thiếu ngoài quy tắc đã duyệt.

---

## Nhiều tính năng cùng lúc — chốt từng cái

Không cấm làm nhiều tính năng trong một phiên. Cấm để cả phiên biến thành **một khối thay đổi hỗn
hợp chưa chốt**. Mỗi tính năng: checkpoint/commit riêng và có trạng thái riêng. Khi chưa thể deploy
từng cái, xác minh local theo manifest rồi kiểm integration của toàn gói và từng hành trình sau upload.

**Trạng thái nằm trong file và commit, không nằm trong đoạn hội thoại.** Đây là lý do các phiên dài
hay quên quyết định của tính năng làm trước đó.

Hai tính năng cùng chạm một file dùng chung (`functions.php`, CSS toàn cục, hook chung) → khai xung
đột và giải quyết lúc ghép, không phải lúc deploy.

---

## Dừng lại và hỏi khi

- Không chứng minh được local khớp host.
- Có hai bản cài đặt cùng một tính năng, chưa biết cái nào đang chạy.
- Phép sửa cần đụng danh sách cấm.
- Phạm vi file phình lần thứ hai cho cùng một việc.
- Một bề mặt bị ảnh hưởng nhưng không có cách kiểm chứng.
- Kết quả **bằng 0 ngoài dự kiến** hoặc mâu thuẫn với inventory — kiểm tay một mẫu trước khi báo cáo.

## Script có sẵn — chạy được, đã thử trên site thật

Thư mục `scripts/` của skill này. Chỉ dùng thư viện chuẩn, không cài thêm gì.

### 1. Cổng tươi mới

```bash
python skills/wp-delivery/scripts/wp_freshness.py \
  --site https://SITE --theme THEME_SLUG --local "ĐƯỜNG/DẪN/THEME"
```

Tự dò asset công khai từ trang chủ, tải về so hash với bản local (đã bỏ khác biệt CRLF/LF),
in version theme lộ ra qua `?ver=`. Thoát 0 = khớp, 1 = có lệch, 2 = không so được.
**Không kiểm được file PHP** — server không cho tải `.php`.

### 2. Ghi file an toàn

```python
sys.path.insert(0, os.path.expanduser("skills/wp-delivery/scripts"))
from wp_safe_write import safe_write
safe_write("theme/functions.php", noi_dung_moi)   # backup → tạm → php -l → đổi tên → so hash
```

Từ chối ghi khi nội dung rỗng, không qua `php -l`, hoặc **cấu trúc ngoặc hỏng** (lệch tổng · dấu
đóng mồ côi · at-rule bị nuốt — xem "đếm tổng là phép kiểm mù" ở trên), và **file gốc còn nguyên**.
Kiểm nhanh, không ghi: `python wp_safe_write.py --check <file>`.

Output nói đúng phạm vi đã chứng minh — **đọc cả bốn dòng, đừng chỉ nhìn exit code**:

```
WRITE_OK                ghi nguyên tử qua file tạm, có backup
STATIC_CHECKS_PASSED    không rỗng · php -l hoặc cân bằng ngoặc · hash sau ghi khớp
                        (thành STATIC_CHECKS_SKIPPED khi máy không có PHP hoặc đuôi lạ)
RUNTIME_NOT_TESTED      chưa kiểm thứ tự nạp, dependency, hook, trùng tên hàm
NEXT                    sau deploy tự tay chạy 2 URL: một URL dùng chức năng, một URL đối chứng
```

**`exit 0` chỉ có nghĩa "ghi xong, kiểm tĩnh không thấy lỗi".** Không có nghĩa an toàn để deploy,
càng không phải `PRODUCTION_VERIFIED`. `php -l` không bắt được lỗi nạp runtime, nên chừng nào chưa
tự chạy hai URL kia thì trạng thái vẫn là `RUNTIME_NOT_TESTED` — script không bao giờ nói hộ.

`functions.php` và `wp-config.php` tự động in thêm cảnh báo loader (hỏng là hỏng toàn site).
File nạp-file-khác khác thì tự khai bằng `--loader` / `loader=True` — script **không đoán bootstrap
từ tên file**, vì đoán vừa sót vừa báo nhầm.

### 3. Đo kích cỡ module

```bash
python skills/wp-delivery/scripts/wp_module_size.py \
  --check "<theme>" --baseline "<theme>/.module-size.json"
```

Trả `SIZE_CHECKS_PASSED` · `MODULE_TOO_LARGE` · `FUNCTIONS_PHP_TOO_LARGE` · `LEGACY_GREW`
· `REVIEW_ARCHITECTURE`. Thoát 1 khi có file mới vượt ngưỡng hoặc file legacy phình thêm.
Kèm danh sách hàm dài quá 80 LOC, có số dòng để mở thẳng.

### 4. Canh URL trọng yếu

```bash
python skills/wp-delivery/scripts/wp_urlwatch.py scripts/sites/*.json --quiet
```

Mỗi URL kèm **chuỗi mốc phải có mặt** — HTTP 200 không đủ, trang vẫn 200 khi nút thêm vào giỏ
đã biến mất. Cấu hình từng dự án nằm trong `scripts/sites/`. Thoát 1 khi có vấn đề, nên cắm thẳng
vào cron được. `--quiet` chỉ in khi có lỗi.

**Chọn mốc cho đúng:** lấy chuỗi từ HTML thật, đừng gõ theo trí nhớ. Hai lần đầu chạy đều báo
động giả vì mốc sai — số điện thoại trong HTML viết liền không dấu cách, và trang giỏ hàng dùng
chữ khác khi giỏ rỗng. Mốc tốt là **class của theme** (`mytheme-cart-page`) vì mất class nghĩa là
template hoặc CSS đã gãy thật.

## Tài liệu đầy đủ

- `(ghi chép nội bộ, không kèm trong repo)` — bài học phân theo 12 nhóm, kèm bằng chứng
- `(ghi chép nội bộ, không kèm trong repo)` — kiến trúc v3 và lộ trình
