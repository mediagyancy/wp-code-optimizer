# Kinh nghiệm code web trên WordPress — tổng hợp toàn bộ dự án

> **Bối cảnh cho người đọc lần đầu.** Đây là tổng hợp bài học rút ra từ ba dự án
> WordPress thật đang chạy sản xuất, gọi là Dự án A, B và C. Tên site và tên theme
> đã được thay bằng nhãn chung — mọi bài học, con số và ca hỏng đều giữ nguyên.
> Mỗi mục gắn với một lần đã trả giá thật, không phải lý thuyết.

Nguồn: toàn bộ 697 transcript trong `~/.claude/projects` (23 dự án), 3 tài liệu đã đúc kết
(`wordpress-ops/SKILL.md`, `wordpress-ops/reference/patterns.md`, `wp-corewebvital/SKILL.md`), và tài liệu
deploy trong repo. Ba dự án WordPress thật: **Dự án A** (WooCommerce, theme `theme-a`), **Dự án B** (WooCommerce, theme `theme-b`),
**Dự án C** (Elementor + Rank Math). Mỗi bài học dưới đây gắn với một lần đã trả giá thật.

---

## A. MƯỜI RỦI RO CHẾT NGƯỜI — xếp theo thiệt hại

| # | Sự cố đã xảy ra | Nhóm | Thiệt hại | Chốt chặn |
|---|---|---|---|---|
| 1 | **Giá hiển thị ≠ giá tính tiền** (Dự án A): bảng giá và WooCommerce đi hai đường tính bậc thang khác nhau | Code + DB | Khách bị tính sai tiền | Một hàm tính giá duy nhất; giao diện gọi đúng hàm mà checkout gọi |
| 2 | **`functions.php` bị xoá trắng 0 byte** (Dự án A 29/08): script mở file mode ghi rồi lỗi trước khi kịp ghi | Code + Ops | Site chết trắng | Ghi file tạm rồi `rename`; không mở file sống ở mode `w` |
| 3 | **Upload FTP sai thứ tự** (Dự án A): `functions.php` lên trước `inc/` → màn hình trắng; lên sau file sửa → trang thanh toán chết | Ops | Sập site / sập checkout | Ba đợt cứng: file mới → `functions.php` → file sửa đè |
| 4 | **1.314 ảnh chết cùng lúc** (Gara): 195/320 bài nhúng ảnh `googleusercontent.com` copy từ Google Docs, Google xoá link | Media | Không khôi phục được | Quét host ảnh ngoài ngay ngày đầu dự án |
| 5 | **Sửa 299 bài, trang thật vẫn sai** (Gara): nội dung nằm ở `_elementor_data`, widget chân trang, reusable block | Kiến trúc | Báo cáo "299/299 xong" sai hoàn toàn | Quét đủ bốn nguồn phát nội dung (mục B) |
| 6 | **Mật khẩu SMTP plaintext trong theme** (Dự án B `inc/sendmail.php`, tài khoản của khách hàng cũ) | Bảo mật | Lộ credential | Secret chỉ nằm trong `wp-config.php` |
| 7 | **PDF chưa được phép nằm public** (Gara): `/wp-content/uploads/*.pdf` public bất kể post là draft | Bảo mật | Rò tài liệu | Chưa cleared thì đừng upload vào Media Library |
| 8 | **Schema khai sai tỉnh** (Gara): JSON-LD ghi gara ở TP.HCM thay vì Đồng Nai, 2 block trùng, 3 địa chỉ khác nhau, chưa từng chạy | SEO | Local business mất nền vị trí | Kiểm bằng Rich Results; một fact sai ở gốc sai trên mọi trang sinh sau |
| 9 | **WooCommerce chèn nguyên trang mặc định tiếng Anh** (Dự án B): theme `theme-b` không khai `add_theme_support('woocommerce')` → unsupported theme compatibility mode, áp cho **≥100 sản phẩm** | Code + UI | Toàn bộ trang sản phẩm hỏng | Khai theme support hoặc override template trong `woocommerce/` |
| 10 | **Rank Math meta ghi qua REST bị nuốt im lặng**: trả HTTP 200, response chỉ `{"footnotes":""}` | Plugin | Tưởng đã ghi, thực tế không | `register_post_meta` ở `init` priority 20; đọc lại xác minh |

---

## B. KIẾN TRÚC & NGUỒN SỰ THẬT — nhóm sai nhiều nhất

**Câu hỏi số một trước mọi phép sửa: trang này hiển thị nội dung TỪ ĐÂU?**

| Trang dựng bằng | Nội dung thật nằm ở | Sửa `content.raw` có tác dụng? |
|---|---|---|
| Gutenberg / editor | `content.raw` (`?context=edit`) | Có |
| **Elementor** | meta `_elementor_data` (JSON) | **Không** |
| Divi | meta `_et_pb_*` | Không |
| WPBakery | `content.raw` chứa shortcode | Có, cẩn thận shortcode |
| ACF | field riêng trong database | Không — và sửa tay vô nghĩa: biên tập viên gõ lại là hỏng |

**Bốn nguồn phát nội dung, phải quét cả bốn** (thiếu một là báo cáo sai):
thân bài → `_elementor_data` (20–30% số trang, thường là trang dựng kỹ nhất) →
widget/sidebar/footer (`wp/v2/widgets?context=edit`, ảnh hưởng **mọi trang cùng lúc**) →
reusable block (`wp/v2/blocks`).

**Hai nguồn sự thật, dùng đúng chỗ — chỗ dễ lẫn nhất:**

- Đo **nội dung / internal link** → đọc từ CMS (`content.raw`), không parse HTML đã render.
  Lọc boilerplate theo tần suất sai đúng ở ca quan trọng nhất: từng kết luận "toàn site 0 link
  contextual", đo lại bằng API ra **219/308**.
- Đo **cấu trúc điều hướng / inventory công khai** → phải **crawl HTML**, không tin REST API.
  API cho biết *database có gì*, không cho biết *website thực sự là gì*. Dự án B có 4 danh mục công khai
  mà WooCommerce API không trả về, và có hai cách biểu diễn sản phẩm song song (116 WooCommerce
  product + WordPress post đóng vai sản phẩm dưới `/san-pham/`). **Lỗi này lặp 4 lần**, mỗi lần
  đẻ ra một issue giả ("32 sản phẩm mồ côi", "money page 239 clicks / 0 sản phẩm").

---

## C. CODE / PHP THEME

- **Không bao giờ mở file sống ở mode ghi.** Ghi file tạm rồi đổi tên (xem A#2).
- **`get_template_part()` không truyền biến cục bộ** — lỗi hợp đồng API, không phải lỗi cú pháp.
  Script tự viết chỉ đếm cân bằng ngoặc không bắt được loại lỗi này.
- **Nhánh `else` hay bị mất khi viết lại template**: `products.php` gốc có
  `else: get_template_part('content','none')` → bỏ mất thì **danh mục rỗng là trang câm**.
- **Hàm phụ thuộc file khác phải có chắn `function_exists()`**: template gọi hàm của
  `tiered-pricing.php` khi file chưa nạp → **trang danh mục trắng màn, sập cả shop**.
- **Đừng tự chế lại hàm lõi**: từng thay bộ lọc gốc bằng `wpautop() + wp_kses_post()` — sai cả hai đầu.
- **Nguồn là ACF/database thì phải cưỡng chế bằng code**, sửa tay một chuỗi là lần sau hỏng lại.
- **Version theme là công cụ nghiệm thu deploy.** Bump mỗi lần đẩy; thấy số cũ (`1.15.1` thay vì
  `1.17.1`) nghĩa là `functions.php` trượt — dừng, đừng đi tiếp.
- **`update_post_meta` trả `false` khi giá trị không đổi** — không phải lỗi; muốn biết thì đọc lại.
- **`register_rest_route` gọi hai lần cho cùng route** (GET, POST riêng) thì lần sau ghi đè lần trước.
  Khai một route với mảng nhiều endpoint.
- **KSES chạy TRƯỚC hook của bạn.** `WP_REST_Server::dispatch()` gọi `sanitize_params()` trước
  callback → hook `rest_pre_insert_*` nhận bản đã bị bóc. Mô tả danh mục bị gắn cứng
  `sanitize_callback => wp_filter_kses` ở tầng REST **và** `wp_filter_kses` còn bám ở tầng
  `wp_update_term()` — phải gỡ cả hai tầng, đổi sang `wp_kses_post`.
- **Windows/tiếng Việt**: `sys.stdout.reconfigure(encoding="utf-8")` đầu mọi script Python
  (console cp1252 sẽ crash). Heredoc bash vỡ với văn bản tiếng Việt — ghi file bằng công cụ ghi file.
- **Chuẩn hoá dấu ở cả hai vế** khi so khớp; `đ`/`Đ` phải thay tay vì `NFD` không tách.
  `_elementor_data` lưu unicode escape (`âng`) → parse JSON, sửa trên cây, không sửa trên text.
- **Thẻ HTML cắt ngang chuỗi cần thay** (`P. Phước Tân,</b><b> TP. Biên Hoà`) khiến regex liền mạch
  trượt dù từng mảnh đều khớp. Chẩn đoán: tách regex ra từng mảnh. Xử lý: thay mảnh ngắn chắc chắn
  liền mạch, hoặc nối bằng `(?:\s|&nbsp;|<[^>]*>)*` **kèm assert cân bằng thẻ trước/sau**.
- **`wp_strip_all_tags()` gỡ thẻ nhưng không giải mã thực thể HTML**, trong khi `wc_price()` chèn
  `&nbsp;` giữa số và `₫` — lỗi thật, ảnh hưởng 9 chỗ trong theme Dự án A.
- **`add_permastruct('<taxonomy>', '%<taxonomy>%')` chiếm gốc tên miền thì nuốt mọi trang tĩnh**
  (Dự án A 02/09/2026, mu-plugin đổi cấu trúc URL): rule taxonomy được chèn vào bảng
  rewrite **trước** rule của trang, mà WordPress chỉ tự bật `use_verbose_page_rules` cho `%category%`
  của core, không bật cho permastruct do plugin thêm → mọi URL một đoạn (`/bao-gia/`, `/gio-hang/`,
  `/thanh-toan/`, `/lien-he/`…) bị đọc thành "term tên X", không có term thì **404 tám trang tĩnh và
  mọi URL sản phẩm**. Cách đúng: `add_rewrite_rule('^([^/]+)/?$', …, 'bottom')` + filter `term_link`.
  `php -l`, PHPCS, PHPStan đều im lặng — **phép kiểm duy nhất bắt được**: sau mỗi thay đổi rewrite,
  mở 3 trang tĩnh bất kỳ trên host bằng `curl` có `?cb=`.

---

## D. UI (CSS & giao diện)

- **Specificity của theme cũ là kẻ thù giấu mặt.** Nút submit CF7 ra xanh dương `#0d61ad` vì rule cũ
  `form .fieldbox input.wpcf7-submit` (0,2,2) thắng selector mới (0,2,1) — chỉ lộ khi đo trên trang
  có nạp `main.css` thật, đọc file nguồn không thấy.
- **Preview HTML tĩnh không phải WordPress**: không plugin, không Rank Math, không WooCommerce —
  về nguyên tắc không thể thấy lớp lỗi đó. Nghiệm thu phải trên site thật.
- **CSS phải suy biến an toàn**: nếu `checkout.css` không tải được thì trang chỉ nên "xếp dọc hơi xấu",
  không vỡ nát — giới hạn `display:contents` bằng selector có điều kiện.
- **Class đang ăn nhờ style thiết kế cũ là mìn chờ** — ghi lại, đừng đợi nó tự nổ.
- **Kiểm bằng số**: `scrollWidth == innerWidth` ở 375px (không tràn ngang), tương phản đo được,
  đếm ngoặc mở/đóng của file CSS (194/194).
- **CSS inline trong PHP vẫn bị cache** — không purge thì thấy màu cũ và tưởng code hỏng.
- **File CSS lệch byte chưa chắc hỏng**: local CRLF vs host LF — `checkout.css` lệch đúng 1.049 byte
  = đúng 1.049 dòng.
- **"Trên máy đẹp, lên host lệch" luôn là đứt một mắt trong chuỗi này**:
  `template → DOM class → CSS file → style handle → điều kiện enqueue → file có trong gói deploy → cache đã purge`.
  Sáu kiểu đứt hay gặp: chưa `wp_enqueue_style`; enqueue sai điều kiện template; sai URI
  parent/child theme; file không nằm trong gói upload; CSS có tải nhưng bị specificity đè;
  cache còn giữ bản cũ.
- **Kiểm asset bằng runtime, và queue thôi thì chưa đủ.** `wp_styles()->queue` chỉ chứng minh
  WordPress *định* nạp trên URL đang kiểm — nó không thấy CSS được `@import` hay bundle vào file
  khác. Đủ bằng chứng cần ba thứ: handle có trong queue của URL dự kiến **hoặc** được bundle vào
  asset đang tải · file tải **200** trên trang · **content hash khớp** bản vừa đẩy.

---

## E. UX (luồng người dùng — chỗ mất tiền thật)

- **Form là đường sống của lead.** Thêm form mà không đọc `functions.php` trước: nếu site bắt buộc
  reCAPTCHA thì mọi lead qua trang đó rơi im lặng. Phải gửi thử thật một lần.
- **Đừng gỡ input mà WooCommerce cần đọc**: bỏ radio `shipping_method[0]` khỏi giao diện → bấm Đặt
  hàng bị chặn "chưa chọn phương thức vận chuyển", **không đặt được đơn**.
- **Giao diện phải "nói thật" thay vì im lặng tính sai**: 8 mặt hàng thiếu quy đổi kg → cảnh báo vàng.
  Hiển thị giá sai tệ hơn không hiện giá.
- **Danh mục rỗng phải có trạng thái rỗng**, không được câm.
- **404 sạch**: `add_filter('do_redirect_guess_404_permalink','__return_false')` để WordPress không
  đoán mò về trang khác.
- **Xoá danh mục thì kiểm menu/widget còn trỏ tới không**; "Chưa phân loại" là danh mục mặc định
  WooCommerce, xoá sẽ lỗi.
- **Trạng thái vận hành phải hiện trong wp-admin**: dải vàng/xanh/đỏ cho SMTP kèm nguyên văn lỗi máy
  chủ và nút "Gửi thử" — người vận hành tự chẩn được, không phải hỏi vòng.

---

## F. PLUGIN

- **Plugin SEO không lộ meta ra REST.** Rank Math: `POST {"meta":…}` trả 200 nhưng bỏ qua.
  Đường `/rankmath/v1/updateMeta` thường **bị WAF chặn 403** (endpoint từng có lỗ hổng leo thang
  đặc quyền) — trả HTML 403 chứ không phải JSON, đừng mất thời gian ở đó. Cách mở: cài Code Snippets
  → `register_post_meta` ở `init` **priority 20** (sau khi Rank Math đăng ký, nếu không bị ghi đè).
  `rank_math_robots` lưu dạng **mảng**; khai `string` thì nhận payload rồi bỏ giá trị.
- **Cửa mở bằng plugin là cửa có thể bị đóng**: Code Snippets nằm trong tay wp-admin, ai tắt nhầm là
  mất quyền ghi SEO. Cài plugin lên production là việc hướng ra ngoài — **xin duyệt trước**.
- **Wordfence Login Security có tuỳ chọn chặn Application Password** → 401. Nhưng lần đó thủ phạm
  thật là **username điền nhầm**: ghi tên của Application Password thay vì tên đăng nhập WordPress.
  Đừng đổ oan cho firewall trước khi kiểm username.
- **Hai plugin cùng in schema** (Rank Math + saswp) → `Organization`/`LocalBusiness` trùng; dọn xong
  mà cài thêm plugin schema thứ hai là tái diễn ngay.
- **Thay plugin bằng code khi rẻ hơn**: lightbox → `<dialog>` + 30 dòng JS (−80KB), slider → CSS
  scroll-snap, social share → URL native (−50KB).
- **Không gỡ plugin khi chưa hỏi nó đang dùng ở trang nào.**
- **Thứ gì WooCommerce đã có ô trong giao diện thì đặt ở đó, đừng nhét vào code.**

---

## G. DATABASE & DỮ LIỆU

- **Draft giữ nguyên dữ liệu trong `wp_posts`** — hỏng thì publish lại, đường lùi rẻ nhất.
- **WooCommerce chỉ đếm sản phẩm đã publish** — số đếm danh mục thấp không phải lỗi.
- **Dữ liệu bẩn sinh giá sai**: 2 SKU có giá tạ **cao hơn** giá sỉ (Tim Gà: sỉ 25.000₫, tạ 50.000₫).
  Chỗ sửa thật là **bắt buộc điền `rate` khi tạo/sửa sản phẩm** — chặn từ khâu nhập, đừng vá ở giao diện.
- **Hằng số kinh doanh phải sửa đồng thời ở lõi tính tiền và ở chữ hiển thị**
  (`SOLUS_TIER_QTY_TA` + bảng giá) — lệch là khách thấy một đằng, tính một nẻo.
- **Object cache gây đọc nhầm**: cùng một trường trả hai giá trị khác nhau tuỳ đường đọc. Nghi ngờ thì
  đối chiếu bằng `wp/v2`, không tin endpoint tự viết.
- **Duplicate content là rủi ro dữ liệu**: 63 trang tỉnh nội dung na ná, 16 mô tả sản phẩm
  copy-paste → Google gộp canonical, loãng lực.

---

## H. CACHE & HIỆU NĂNG (LiteSpeed / CWV)

Kết quả thật Dự án B 27/04: 2.177KB → 1.506KB (−31%), FCP 926ms → 410ms (−56%), CrUX pass toàn bộ.

- **Cache MISS là thủ phạm số 1 của TTFB.** Khi HIT, TTFB chỉ **22ms**.
- **`x-litespeed-cache: hit/miss` là cách rẻ nhất tách "deploy hỏng" khỏi "cache giữ bản cũ"** —
  hai lỗi trông giống hệt nhau trên trình duyệt, cách xử lý hoàn toàn khác.
- **Thêm `?cb=…` để né cache là tự làm hỏng phép đo**: LiteSpeed coi là URL mới → mọi request miss,
  phải chạy PHP → số đo sai.
- **Sửa xong phải Purge All**, không thì người khác tưởng bạn làm hỏng.
- **Không bao giờ bật**: `optm-css_async` (FOUC), `optm-js_defer ≥ 1` (vỡ inline jQuery),
  `optm-qs_rm` (kẹt CSS cũ), `optm-html_min` (vỡ template literal trong inline script),
  `util-instant_click` (**cực nguy với WooCommerce** — hover preload URL add-to-cart),
  `media-placeholder_resp`, `optm-ggfonts_rm` khi chưa self-host font.
- **Không dùng dịch vụ bên thứ ba** (QUIC.cloud, Cloudflare CDN): self-host WebP + `.htaccess`
  auto-serve, self-host font woff2 kèm subset `vietnamese`.
- **Không lazy-load ảnh LCP**; bật `media-add_missing_sizes` để chống CLS.
- **`ob_start` viết lại toàn bộ HTML gây TBT +300ms** — dùng `wp_dequeue` theo hook, priority 100
  (sau khi plugin enqueue).
- **Field data (CrUX p75) mới là cái Google xếp hạng**; lab PSI lệch ±20 điểm mỗi lần chạy — lấy
  trung vị 3+ lần.
- Dequeue thực tế ở Dự án B: bỏ `swiper.js` trùng (312KB), dequeue dashicons cho khách chưa đăng nhập
  (~35KB chặn render ở `<head>`), gỡ CSS Gutenberg khi theme classic (toàn site chỉ 1 class
  `wp-block-image`).

---

## I. SEO & SCHEMA

- **Schema sai một fact ở gốc thì sai trên mọi trang sinh sau.** Kiểm địa chỉ, loại hình
  (`AutoRepair`), và kiểm xem nó **có từng chạy không** — đoạn schema của Gara chưa bao giờ hoạt động.
- **Giá trong schema lệch giá hiển thị → Google bỏ luôn rich result.** Một template schema áp cho mọi
  danh mục sẽ gán cùng một giá cho các sản phẩm khác hẳn nhau.
- **hreflang tự sinh có thể hỏng nặng**: Dự án B khai `vi-KH`, `vi-LA` trỏ sang **trang sản phẩm khác**,
  `x-default` về homepage. (Thẻ `alternate → /wp-json/wp/v2/categories/269` thì **vô hại** — link REST
  mặc định, từng bị xếp nhầm vào nhóm lỗi.)
- **Đổi RDFa → JSON-LD**: sai cú pháp thì mất dải breadcrumb hiển thị, **không mất thứ hạng** — biết
  mức thiệt hại trước khi quyết.
- **Sitemap**: submit sai tên (`sitemap.index.xml`) nằm lại trong GSC ở trạng thái Couldn't fetch;
  `rank_math_robots = ["noindex","nofollow"]` khiến Rank Math tự loại trang khỏi sitemap — nghiệm thu
  bằng cách đếm `<loc>` trước/sau.
- **`noindex` toàn site thì gắn schema NAP cũng vô nghĩa.**
- **Giữ nguyên URL khi viết lại nội dung** để không mất traffic cũ.
- **Quota Search Console ~10 URL/ngày**: URL đưa tay thì luôn gửi; quét sitemap thì bỏ bài đã gửi OK.

---

## J. BẢO MẬT & BÍ MẬT

- **Secret chỉ nằm ở `wp-config.php`.** Đã gặp SMTP password plaintext trong theme Dự án B
  (`inc/sendmail.php:137`, sót từ dự án khách hàng khác) → phải **đổi mật khẩu**, không chỉ xoá code.
- **File cấu hình đặt trong `wp-content/` là rủi ro**: host không chạy PHP ở đó thì nội dung lộ ra internet.
- **Đừng nhận mật khẩu của khách.** Key đọc từ file, không in ra màn hình.
- **`/wp-content/uploads/` luôn public** bất kể post là draft.
- **WAF chặn có chọn lọc**: đọc qua được, ghi bị chặn. Dấu hiệu: trả HTML thay vì JSON.
- **Backup phải là bản đang chạy trên host**, không phải bản local — file PHP không tải được qua trình
  duyệt nên không đối chiếu được; ai đó sửa thẳng trên hosting là bản local mất phần đó.

---

## K. DEPLOY & VẬN HÀNH

- **Thứ tự upload có tính sống chết** (Dự án A, 3 đợt): ① file mới (site không đổi gì) →
  ② `functions.php` (bật các file `inc/`) → ③ file sửa đè (giao diện mới hiện ra).
- **Giữa đợt ② và ③ site vẫn đang phục vụ khách bằng template cũ.** Nên logic mới đưa lên ở
  đợt ② **phải tương thích ngược với template cũ**. Nếu loader mới đòi template mới thì khoảng
  giữa hai đợt chính là khoảng site hỏng — không ai chờ sẵn để bấm tiếp trong vài giây.
- **Gỡ thì đi ngược chiều thêm.** Thêm: file mới → loader → consumer. Gỡ: ① sửa consumer để
  ngừng gọi → ② gỡ `require`/hook trong loader → ③ xoá file cũ sau cùng. Dùng nhầm chiều là tự
  tạo khoảng consumer gọi một hàm không còn tồn tại — fatal error trên trang thật.
- **Backup phải phủ mọi file bị ghi đè ở mọi đợt**, không chỉ file của đợt cuối.
- **Rollback theo từng đợt, không lùi cả cục** — mỗi đợt ghi rõ khôi phục file nào.
- **Kéo nguyên khối thư mục theme**, đứng ở `wp-content/themes/` mà kéo `theme-a`. Kéo nhầm thư
  mục đóng gói → host mọc ra `themes/1-file-moi/`. "Select All → Move" trong File Manager cũng chọn
  cả thư mục con → lồng thư mục.
- **Kiểm bản trên server có khớp bản local trước khi sửa** — repo còn `functions.php` sửa dở chưa
  commit, deploy đè lên base lỗi thời là hỏng việc.
- **Cùng số version không có nghĩa cùng nội dung**: local và host cùng ghi `1.17.1` nhưng `main.css`
  lệch 1.492 ký tự (3 khối `.theme-a-featured-cat-card`) — deploy sẽ mang theo thay đổi trang chủ chưa
  từng lên. Biết trước để lúc nghiệm thu còn mở trang chủ ra xem.
- **Bài lớn (46KB HTML + 52 ảnh) thì paste qua wp-admin an toàn hơn tái tạo qua API.**
- **Dry-run → backup → ghi → đọc lại xác minh TRÊN TRANG THẬT.** Ghi đâu đọc đó thì luôn khớp — đó
  chính là cách báo cáo sai ra đời.
- **Có đường lùi trước khi sửa**: git backup theme, thư mục `REVERT-<ngày>/` chứa đúng file tải từ
  site, dùng draft thay vì xoá.

---

## L. KỶ LUẬT ĐO LƯỜNG & BÁO CÁO (áp cho mọi nhóm trên)

1. **Quét toàn bộ, không quét mẫu rồi nói như toàn bộ.** Từng báo "đã xoá sạch địa chỉ cũ" sau khi
   quét 71/320 URL; thực tế còn 216 bài.
2. **Số 0 phải nghi ngờ phép đo trước.** `heading elementor: 0` là do bộ lọc URL chặn nhầm cả chuỗi.
3. **Phép thay chuỗi không khớp phải báo ngay**, không im lặng trượt qua.
4. **Xác minh trên trang thật**, không trên trường vừa ghi.
5. **Đừng kết luận "không có ô nào trong wp-admin"** khi thực tế là "có ô, nhưng thiếu lựa chọn".
6. **Nói rõ vùng mù**: không có WordPress/WooCommerce ở máy local thì lỗi runtime `WC()->cart` chưa
   kiểm được — ghi ra, đừng ngầm bỏ qua.
7. **Bốn nhãn xác minh, không được nâng cấp lẫn nhau:**
   `CONCEPT_PREVIEW` (xem trên HTML tĩnh — không có WordPress, không plugin, **không phải bằng
   chứng layout**) · `VISUAL_PASS` (đã xem trên WordPress thật, đúng URL, đủ plugin và dữ liệu) ·
   `PRODUCTION_VERIFIED` (đã xem trên canonical URL sau khi purge) · `NOT_TESTED` (không thử thật
   được — không đặt được đơn, không có quyền; ghi rõ chứ đừng im lặng nâng thành PASS).
8. **Đọc kết quả sau deploy theo ba cột** — origin / canonical / asset:
   mới·mới·mới = đạt · mới·**cũ**·bất kỳ = cache công khai còn cũ, purge · mới·mới·**cũ** =
   version asset không đổi, sửa `?ver=` · cũ·cũ·cũ = deploy chưa lên.
9. **Local không mô phỏng được bốn thứ**, phải kiểm lại sau deploy: LiteSpeed (cache/purge),
   WAF (chặn có chọn lọc đường ghi), mail server thật, và cấu hình riêng của hosting.
   "Đã pass local" không miễn trừ bốn thứ này.
10. **Mã thoát đọc sau dấu `|` là mã của lệnh CUỐI, không phải của lệnh mình quan tâm.**
    `cong-cu --check 2>&1 | tail -3; echo "exit=$?"` in ra mã thoát của `tail` — luôn bằng 0 —
    nên một công cụ vừa báo lỗi và thoát 3 vẫn được đọc thành "sạch". Ngày 02/09/2026 cái bẫy
    này cắn **hai phiên độc lập trong cùng một buổi**; một trong hai đã kịp dựng nguyên một
    cảnh báo sai trên nền con số đó rồi nhắn sang hai phiên khác, suýt thành luật. Cách chặn:
    hứng ra file rồi mới đọc (`cmd > out.txt 2>&1; echo $?`), hoặc `${PIPESTATUS[0]}`. Cùng họ
    với bẫy này: `head`/`grep` cắt output tạo vùng mù, và `-ErrorAction SilentlyContinue` giấu
    lỗi nhưng vẫn đổi mã thoát. **Trước khi tin một mã thoát, hỏi: mã này của lệnh nào?**

---

## M. LÀM VIỆC ĐA PHIÊN — nhiều phiên Claude trên cùng một repo

Ca gốc: **Dự án A 02/09/2026 — 5 phiên Claude Code cùng trỏ vào một thư mục, cùng nhánh
`main`, một cây làm việc duy nhất.** Đo được: 35 file bẩn trộn ít nhất 4 tính năng, ghi
trong cùng 10 phút; ba trong năm phiên tự tắt giữa chừng để lại việc mồ côi.

- **Cây giao hàng và cây làm việc phải là hai thứ khác nhau.** Deploy WordPress là kéo
  nguyên khối thư mục theme lên FTP, nên một cây chứa 4 tính năng dở dang thì **không thể
  giao A mà không mang theo B, C, D**. Đây là lỗi kiến trúc quy trình, không phải lỗi thao
  tác. Một tính năng = một nhánh = một worktree = một phiên; repo gốc đứng ở nhánh chính và
  chỉ dùng để đóng gói.
- **"Cây chuẩn duy nhất" là một cái bẫy ngôn ngữ.** Luật cũ viết "cây chuẩn duy nhất được
  **sửa**" — mọi phiên hiểu đúng nghĩa đen và cùng sửa vào đó. Phải viết: duy nhất được
  **đóng gói**.
- **Chỗ va chạm là file cột sống, không phải file tính năng.** Trong theme WP đó là
  `functions.php` (danh sách `require_once`) và `inc/enqueue.php` (danh sách nạp asset).
  Quy ước: mỗi tính năng chỉ **nối thêm** một dòng hoặc một khối của mình, không viết lại
  file. Ở ca 02/09, hai phiên cùng ghi một vùng `enqueue.php` làm chú thích của khối này
  trôi lên nằm trên khối kia — **`php -l` vẫn báo sạch**, không phép kiểm cú pháp nào bắt được.
- **Số hiệu phiên bản không thuộc về tính năng nào.** Hai phiên cùng bump
  `SOLUS_THEME_VERSION` lên `1.23.0` trong cùng một file. Bump một lần ở cây giao hàng lúc
  đóng gói.
- **Nhắn tin giữa các phiên KHÔNG phải hàng rào.** Phiên mới sinh ra liên tục và không biết
  lời dặn nói với phiên cũ; trong 30 phút gỡ rối, danh sách phiên đổi ba lần. Hàng rào phải
  nằm ở tầng công cụ (hook chặn ghi); lời nhắn chỉ để phối hợp.
- **Trước khi tách một cây bẩn, commit nguyên trạng vào nhánh cứu hộ.** Ba phiên tắt giữa
  chừng trong lúc gỡ — việc của họ còn lại được đúng là nhờ commit đó.
- **Tách xong thì dựng lại từ nhánh chính sạch, đừng vá lên bản đã trộn.** Ráp file cột sống
  từ bản sạch cộng đúng khối của mình. Cẩn thận mốc chèn: chuỗi
  `class_exists( 'WooCommerce' ) && is_product()` xuất hiện **hai lần** trong `enqueue.php`
  — chèn nhầm lần thứ nhất là hỏng ngầm mà lint không thấy. **Đếm số lần khớp trước khi chèn.**

**Ba thứ trong repo âm thầm phá việc đa phiên** — đều đã cắn ở Dự án A 02/09:

| Thứ | Triệu chứng | Vì sao nguy |
|---|---|---|
| `.gitignore` chặn cả thư mục `plugins/` | 9 file nguồn plugin **tự viết** không có trong git | `git status` không thấy → backup dựng từ `git status` cũng bỏ sót → không còn bản sao nào ngoài đĩa |
| File chứa secret **không** nằm trong `.gitignore` | một file cấu hình mang credential thật đang ở trạng thái untracked | một lệnh `git add -A` là secret vào lịch sử repo có remote. Kiểm bằng `git check-ignore` chứ **đừng đoán theo tên file**: file trông đáng ngờ nhất có khi chỉ chứa placeholder, còn file trông vô hại lại giữ giá trị thật |
| Thiếu `.gitattributes` | `functions.php` hiện 65/64 dòng đổi, thay đổi thật chỉ **2/1** | mỗi phiên ghi một kiểu EOL → diff giả, conflict giả, và mọi phép so lệch với host thành vô nghĩa |

Cùng ngày, một cổng chất lượng bị **kết luận sai hai lần liên tiếp** — và cả hai lần đều là
lỗi đọc, không phải lỗi công cụ. Đáng ghi lại vì kiểu sai này lặp ở mọi dự án.

- Lần một: một phiên báo sang "cấu hình trỏ thư mục chết nên quét 0 file mà vẫn thoát mã 0",
  và câu đó được **chép thẳng vào tài liệu mà chưa ai tự đo**. Đo lại: chạy trần thoát **3**
  (PHPCS) và **1** (PHPStan), in rõ "path does not exist". Fail-closed, không hề có PASS giả.
- Lần hai: sửa xong lại kết luận "cổng chưa từng chạy được", dựa trên hai số đo **đúng** —
  repo không có `vendor/`, công cụ không nằm trên PATH. Nhưng bộ công cụ cố ý đặt **ngoài**
  repo để `vendor/` không đi theo lên host; truyền đường dẫn file cụ thể thì nó quét bình
  thường. Hai số đo đúng vẫn đẻ ra một kết luận sai vì thiếu một mảnh bối cảnh.

Rút ra ba điều. **Số nhận từ phiên khác phải truy về lệnh của chính mình** — trong việc đa
phiên, tin lời phiên bạn là đường ngắn nhất để một điều sai thành luật. **Trước khi tuyên bố
một công cụ "không chạy được", hãy chạy thử nó** — vắng mặt ở chỗ mình tìm không phải là bằng
chứng vắng mặt. Và **cổng hỏng kiểu fail-closed thì đỡ nguy hơn cổng hỏng kiểu im lặng**: cái
đáng sợ là lệnh chạy trần rồi có người đọc mã thoát khác 0 thành "chắc nó bỏ qua".

## N. KIỂM TRA NHANH TRƯỚC KHI ĐỘNG VÀO MỘT SITE

```
[ ] Trang cần sửa dựng bằng gì? (_elementor_edit_mode / class elementor-element / ACF)
[ ] Bao nhiêu trang dùng page builder? (đếm trước khi sửa hàng loạt)
[ ] Widget + reusable block có khai NAP/CTA riêng không?
[ ] Ảnh trỏ ra host ngoài? (googleusercontent, imgur, dropbox)
[ ] Theme có add_theme_support('woocommerce') không?
[ ] Secret nào đang nằm trong theme? (grep password/smtp/api_key)
[ ] REST /users/me?context=edit trả capabilities chưa? (username = tên đăng nhập, không phải tên app password)
[ ] Rank Math meta đã lộ qua REST chưa? (meta chỉ có footnotes = chưa)
[ ] x-litespeed-cache hit hay miss? Purge bằng đường nào?
[ ] Bản local có khớp bản host không? (tải theme từ FTP về đối chiếu)
[ ] Đường lùi là gì? (backup lấy từ host, không phải backup local)
[ ] Có mấy phiên Claude đang mở trên repo này? (ListAgents) — nhiều hơn 1 thì phải có worktree riêng
[ ] Cây đang đứng có phải cây giao hàng không? (git worktree list) — cây giao hàng thì KHÔNG được sửa
[ ] git status còn bẩn mấy file, thuộc mấy tính năng? — quá 1 tính năng là phải tách trước khi sửa tiếp
[ ] .gitignore có nuốt mất code mình tự viết không? (git check-ignore trên plugin/mu-plugin của mình)
[ ] Secret nào đang untracked mà KHÔNG bị ignore? (git status --porcelain, soi tên có smtp/env/pass)
```
