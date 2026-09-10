# Quy định làm việc với WordPress — bản hiện hành

> **Bối cảnh cho người đọc lần đầu.** Đây là bộ luật làm việc rút ra từ ba dự án
> WordPress sản xuất. Phần quy trình chung trùng phần lớn với `skills/wp-delivery/SKILL.md`
> trong repo này — đọc một trong hai là đủ; file này có thêm phần responsive và ghi chú
> vì sao mỗi luật ra đời.
>
> Tài liệu có nhắc vài skill KHÔNG kèm trong repo (`wordpress-ops`, `responsive-check`)
> vì chúng thuộc bộ nội bộ khác. Chỗ nào nhắc tới chúng, đọc như mô tả quy trình,
> đừng đi tìm file.

> Xuất ngày 01/09/2026 20:56 từ cấu hình đang chạy trên máy.
> Đây là **ảnh chụp**, không phải bản gốc. Bản gốc là các file skill và `CLAUDE.md` trong repo;
> sửa ở đây không có tác dụng gì.

## Bộ luật gồm những gì

| Lớp | Nguồn | Áp cho |
|---|---|---|
| Quy trình chung | skill `wp-delivery` | mọi dự án có WordPress |
| Luật riêng từng site | `CLAUDE.md` trong repo | site đó, và **thắng** luật chung khi mâu thuẫn |
| Sửa nội dung qua REST | skill `wordpress-ops` | site làm việc qua API |
| Tốc độ, LiteSpeed | skill `wp-corewebvital` | site cần tối ưu CWV |
| Responsive | skill `responsive-check` | mọi dự án, không riêng WordPress |

Ba repo WordPress đều có dòng bắt buộc ở đầu `CLAUDE.md`: chưa gọi skill `wp-delivery` thì
chưa được ghi file.



---

# PHẦN I — Quy trình chung (skill `wp-delivery`)

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

Thứ tự bắt buộc: **đọc → backup → ghi ra file tạm cùng thư mục → kiểm (`php -l`, đếm ngoặc CSS,
độ dài > 0) → đổi tên đè lên → đọc lại so hash.**

`php -l` không bắt được lỗi nạp runtime: gọi hàm plugin trước khi plugin sẵn sàng, `require` hai lần,
trùng tên hàm/class, hoặc hook sai thời điểm. Với file boot/loader: ưu tiên `require_once`, guard
dependency bằng `function_exists`/`class_exists`, nạp tại hook phù hợp, rồi smoke-test ít nhất một
URL có chức năng và một URL không có chức năng đó.

---

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
python ~/.claude/skills/wp-delivery/scripts/wp_freshness.py \
  --site https://SITE --theme THEME_SLUG --local "ĐƯỜNG/DẪN/THEME"
```

Tự dò asset công khai từ trang chủ, tải về so hash với bản local (đã bỏ khác biệt CRLF/LF),
in version theme lộ ra qua `?ver=`. Thoát 0 = khớp, 1 = có lệch, 2 = không so được.
**Không kiểm được file PHP** — server không cho tải `.php`.

### 2. Ghi file an toàn

```python
sys.path.insert(0, os.path.expanduser("~/.claude/skills/wp-delivery/scripts"))
from wp_safe_write import safe_write
safe_write("theme/functions.php", noi_dung_moi)   # backup → tạm → php -l → đổi tên → so hash
```

Từ chối ghi khi nội dung rỗng hoặc không qua `php -l` / cân bằng ngoặc, và **file gốc còn nguyên**.
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

### 3. Canh URL trọng yếu

```bash
python ~/.claude/skills/wp-delivery/scripts/wp_urlwatch.py scripts/sites/*.json --quiet
```

Mỗi URL kèm **chuỗi mốc phải có mặt** — HTTP 200 không đủ, trang vẫn 200 khi nút thêm vào giỏ
đã biến mất. Cấu hình từng dự án nằm trong `scripts/sites/`. Thoát 1 khi có vấn đề, nên cắm thẳng
vào cron được. `--quiet` chỉ in khi có lỗi.

**Chọn mốc cho đúng:** lấy chuỗi từ HTML thật, đừng gõ theo trí nhớ. Hai lần đầu chạy đều báo
động giả vì mốc sai — số điện thoại trong HTML viết liền không dấu cách, và trang giỏ hàng dùng
chữ khác khi giỏ rỗng. Mốc tốt là **class của theme** (`theme-a-cart-page`) vì mất class nghĩa là
template hoặc CSS đã gãy thật.

## Tài liệu đầy đủ

- [`docs/KINH-NGHIEM-WORDPRESS.md`](KINH-NGHIEM-WORDPRESS.md) — bài học phân theo 12 nhóm, kèm bằng chứng
- `DE-XUAT-GIAI-PHAP-WORDPRESS.md` (ghi chép nội bộ, không kèm trong repo) — kiến trúc v3 và lộ trình


---

# PHẦN II — Luật riêng từng site

Đã tách sang `LUAT-RIENG-TUNG-SITE.md` (riêng tư — có tên site và tên theme thật).
Bản đầy đủ và mới nhất của mỗi site luôn là `CLAUDE.md` trong repo của chính site đó.

Nhờ tách, phần còn lại của tài liệu này không nêu đích danh dự án nào và dùng lại
được cho site mới.

# PHẦN III — Luật responsive (skill `responsive-check`)

# Responsive — luật nền

Rút từ các phiên làm việc thật trên ba dự án A, B và C, email template và dashboard.
Mỗi mục đều có ca đã xảy ra chống lưng.

## Bề rộng phải kiểm

| Bề rộng | Là gì | Vì sao có trong danh sách |
|---|---|---|
| **344** | Galaxy Z Fold 6 màn ngoài | **Màn khó nhất có thật của người dùng Việt**, không phải giả định |
| 375 | iPhone tiêu chuẩn | mốc phổ thông |
| 768 | tablet dọc | nơi layout hay gãy giữa chừng |
| 1280 | laptop | |
| 1440 | desktop rộng | |
| 280 | ép cạn | chỉ dùng khi cần biết giới hạn chịu đựng |

**Đừng mặc định 375 là hẹp nhất.** Hỏi thiết bị thật của người dùng trước. Khách sỉ tra giá
giữa ca bếp, tài xế tra gara bên đường — họ dùng máy gập, máy cũ, màn hẹp.

## Phép đo: chỉ một con số quyết định

```
tràn ngang = max(documentElement.scrollWidth, body.scrollWidth) − documentElement.clientWidth
```

Lớn hơn 0 mới là lỗi. **"Nhìn ổn" không phải bằng chứng, và ảnh chụp cũng không.**

> **Sửa 10/09/2026 — bản trước của chính dòng này lấy `window.innerWidth` làm số bị trừ,
> và đó là một phép đo SAI đã được chứng minh bằng số.** Trong giả lập mobile,
> `window.innerWidth` phình theo nội dung: đặt viewport 344px mà nội dung rộng 640px thì
> nó báo 640, đúng bằng bề rộng cuộn — nên hiệu triệt tiêu và phép đo trả về **0** trên
> một trang tràn **296px**. Số 0 ấy trông y hệt số 0 của một trang sạch. Xảy ra trên cả
> Browser pane lẫn `chrome-devtools` MCP, nên không chữa được bằng cách đổi công cụ.
>
> **Cấm dùng `window.innerWidth` để tính** trong mọi script đo layout; vẫn được báo cáo
> giá trị của nó để đối chiếu. Ràng buộc này nay có khẳng định chạy trong CI —
> `skills/wp-preview-builder/scripts/quyet_dinh_tran.py` giữ cả hai công thức và bắt buộc
> phải tồn tại một ca mà chúng cho kết quả khác nhau. Quay về `innerWidth` sẽ làm đỏ một
> test có tên.

Hai biên **khác nhau** có chủ ý: ở mức **trang** không có biên (tràn 1px vẫn là tràn); ở
mức **phần tử** có biên 1px, vì `getBoundingClientRect()` trả số thực và không có biên
thì mọi trang đều có thủ phạm ảo ở đúng mép phải. Hệ quả phải nói ra: một trang có thể
báo tràn 0.4px ở mức trang mà **không liệt được phần tử nào** — đó là làm tròn, không
phải bỏ sót.

### Bốn nguồn báo động giả — phải lọc, nếu không phép đo mất giá trị

Đây là phần khó nhất, và đã sai bốn lần:

| Nguồn | Vì sao vô hại | Nhận biết |
|---|---|---|
| Drawer / menu mobile đang đóng | `position: fixed`, đẩy ra ngoài màn | 48 phần tử "chọc ra ngoài" từng đều thuộc loại này |
| Slide của carousel | nằm trong track `overflow: hidden` | tổ tiên có `overflow` ẩn/cuộn |
| Phần tử ẩn | không chiếm chỗ thật | `visibility:hidden`, `opacity:0`, `aria-hidden` |
| Viewport = 0 lúc đo | số đo vô nghĩa | từng báo "tràn 268px" hoàn toàn sai |

Script `scripts/probe.js` đã lọc cả bốn, và **in ra số phần tử đã lọc** để không ai tưởng
nó bỏ sót. Dán script đó vào `javascript_tool` của Browser pane sau khi resize.

## Nguyên nhân gốc gần như luôn là một con số cứng

| Triệu chứng | Thủ phạm thật | Sửa |
|---|---|---|
| Chữ bị phóng to trên mobile | `container: 600px` cứng → tràn → trình duyệt tự phóng | `width: 100%` — sửa tràn thì chữ tự đúng |
| Chip/thẻ bị đẩy ra ngoài | hàng ngang cố định `120px` | cho xuống dòng |
| Hero tràn trên màn gập | không wrap | `flex-wrap` |

**Chữ to trên mobile thường không phải lỗi `font-size`.** Nó là hệ quả. Chữa gốc trước.

## Breakpoint theo nội dung, không theo tên có sẵn

Ca thật: chữ ẩn bằng `hidden sm:inline`, mà `sm:` của Tailwind là **640px** — chẳng liên quan
gì tới bề rộng mà thanh tìm kiếm thật sự gãy. Chọn breakpoint bằng cách **thu dần cho tới khi
nội dung gãy**, rồi đặt mốc ở đó.

## Một nguồn cho cả hai màn

Ca thật: thanh tìm kiếm mobile gọi chung component với desktop → **sửa một chỗ được cả hai**.
Dựng hai nhánh song song cho desktop và mobile thì chúng sẽ lệch nhau sau vài lần sửa, và
lệch âm thầm.

## Nghiệm thu phải gồm trạng thái, không chỉ bề rộng

- nội dung **rỗng** (giỏ trống, chưa có kết quả, danh mục chưa có bài)
- nội dung **dài bất thường** (tên sản phẩm 3 dòng, địa chỉ dài)
- **đang tải** và **lỗi**
- tương phản đo được (≥ 4.5:1 cho chữ thường)
- cỡ chữ nhỏ nhất đang hiển thị
- vùng chạm ≥ 40px — nhưng **chỉ tính phần tử tương tác thật**; icon 20px nằm trong nút 44px
  không phải lỗi

## Luật báo cáo lỗi giao diện

**Mỗi lỗi phải nói rõ: có sẵn từ trước hay do lần sửa này gây ra.** Đây là câu hỏi hay gặp
nhất, và trả lời sai một lần là mất tin cậy.

Cách trả lời: đo trên bản **chưa sửa** để đối chứng. Ca thật — `bodyOverflowX = 101` được
chứng minh là lỗi drawer **có sẵn trên production**, tách bạch khỏi thanh thống kê vừa thêm.

Và như mọi phần khác: **bản xem trước tĩnh không phải bằng chứng layout**. Không có CSS thật,
không có dữ liệu thật, không có plugin. Chỉ đo trên trang chạy thật mới được gọi là đã kiểm.

## Cách chạy

```
1. mở trang bằng Browser pane
2. resize_window về từng bề rộng: 344 → 375 → 768 → 1280 → 1440
3. dán scripts/probe.js vào javascript_tool
4. đọc TRAN_NGANG trước, rồi mới xét thu_pham_that
5. xong thì resize_window preset "desktop" để trả lại
```

Đọc kết quả: `TRAN_NGANG: "không"` mà `thu_pham_that` rỗng thì trang sạch ở bề rộng đó.
`da_loc_bo_vi_vo_hai` cho biết bao nhiêu phần tử nằm ngoài màn nhưng không gây hại — con số
này lớn là bình thường với trang có carousel hoặc drawer.


---

# PHẦN IV — Công cụ đi kèm

Nằm trong `~/.claude/skills/wp-delivery/scripts/`, chỉ dùng thư viện chuẩn Python.

| Script | Làm gì | Mã thoát |
|---|---|---|
| `wp_freshness.py` | So bản local với bản đang chạy trên host: tải asset công khai, so hash sau khi chuẩn hoá xuống dòng, đọc version theme trong HTML. **Không kiểm được file PHP** vì server không cho tải `.php` | 0 khớp · 1 có lệch · 2 không so được |
| `wp_safe_write.py` | Ghi file không để lại trạng thái nửa vời: backup → file tạm → kiểm tĩnh → đổi tên nguyên tử → đọc lại so hash | 0 ghi xong và kiểm tĩnh sạch · 1 kiểm tĩnh fail · 2 thiếu công cụ kiểm bắt buộc |
| `wp_urlwatch.py` | Canh URL trọng yếu theo **chuỗi mốc phải có mặt** — HTTP 200 không đủ | 0 sạch · 1 có vấn đề · 2 cấu hình sai |

`~/.claude/skills/responsive-check/scripts/probe.js` — đo responsive qua Browser pane, trả về
tràn ngang thật, danh sách thủ phạm **đã lọc bốn nguồn báo động giả**, cỡ chữ nhỏ nhất, vùng chạm nhỏ.

## Ba điều bộ luật này chưa có

Ghi ra để không ai tưởng đã được bảo vệ:

1. **Chưa có luật cấm `functions.php` thành bãi chứa code.** Hiện chỉ có luật ghi file đó cho an
   toàn và đẩy đúng thứ tự — tức dạy cách nhét code vào cho khéo, chưa hỏi nó có nên nằm đó không.
2. **Chưa có WPCS, PHPStan, hay chạy test** trong cổng kiểm. Mới chỉ có `php -l` và đếm ngoặc CSS.
3. **Chưa có luật về kích cỡ module** — không có gì ngăn việc dựng thừa class cho một tính năng nhỏ.
