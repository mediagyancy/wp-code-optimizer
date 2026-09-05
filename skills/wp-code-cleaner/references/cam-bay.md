# Cạm bẫy khi dọn code WordPress

Mỗi mục dưới đây là một ca đã thật sự cắn, có bằng chứng. Đọc mục nào thấy giống
tình huống đang gặp; không cần đọc hết một lượt.

**Mục lục**
1. [Tên bị ghép chuỗi — phép quét báo chết nhầm](#1)
2. [Class do JS tự tạo](#2)
3. [Markup do plugin sinh ra lúc chạy](#3)
4. [File admin sở hữu menu — xoá cả file là mất màn hình khác](#4)
5. [Màn hình cài đặt không điều khiển gì — đây là quyết định của chủ site](#5)
6. [Phụ thuộc vào handle của plugin — deregister là chết cả site](#6)
7. [`is_admin()` là chuyện phạm vi, không phải tốc độ](#7)
8. [Endpoint AJAX công khai sống sót sau khi giao diện chết](#8)
9. [Dữ liệu localize không còn ai đọc](#9)
10. [Khối JS chết vẫn để lại tác dụng phụ](#10)
11. [Template chết gọi hàm đã xoá — mìn chờ](#11)
12. [Chú thích lạc hậu sau khi dời code](#12)
13. [Chết theo dây chuyền — phải lặp tới điểm dừng](#13)
14. [Nền lỗi thời: cây git lệch xa host](#14)
15. [Chính việc kiểm làm sập database](#15)
16. [CRLF/LF: FTP chế độ văn bản đổi xuống dòng](#16)
17. [Truy cập thẳng file .php làm lộ đường dẫn máy chủ](#17)
18. [Xoá không hết — phải dò lại từng file](#18)

---

<a id="1"></a>
## 1. Tên bị ghép chuỗi — phép quét báo chết nhầm

**Đã cắn:** một bản cắt CSS bỏ `.kl-the__bac--2` và `.kl-the__bac--3`. Hai class đó
**đang hiện trên trang sản phẩm thật**, nhưng phép quét báo chết vì code sinh chúng
bằng ghép chuỗi:

```php
'kl-the__bac--' . $so_bac
```

Grep tên đầy đủ không bao giờ thấy. Cùng loại: `'is-' . $trang_thai`,
`sprintf('col-%d', $n)`, `$prefix . '__item'`.

**Cách chặn:** một class còn sống nếu tên đầy đủ **hoặc một gốc của nó** (cắt tại
`--` hoặc `__`) xuất hiện trong PHP/JS. `go_css.py` và `quet_chet.py` đã cài luật này.
Giữ thừa vài rule rẻ hơn nhiều so với mất một nhãn đang hiện trên trang.

**Thứ bắt được nó** không phải `php -l`, không phải cân bằng ngoặc, mà là tầng đối
chứng bằng HTML thật. Đó là lý do tầng đó không bỏ được.

---

<a id="2"></a>
## 2. Class do JS tự tạo

`.mytheme-quantity__steppers` bị báo chết vì không có trong markup PHP — nhưng JS dựng
nó bằng `createElement` rồi gán `className`. Trước khi xoá một nhóm class, grep tên nó
trong `assets/js/` chứ không chỉ trong PHP.

---

<a id="3"></a>
## 3. Markup do plugin sinh ra lúc chạy

Phân tích tĩnh chỉ thấy markup theme viết ra. WooCommerce, Contact Form 7, block
editor đều in ra class mà theme không hề nhắc tên. Nếu CSS của theme có rule nhắm vào
`.woocommerce-Price-amount` chẳng hạn, quét tĩnh sẽ báo chết oan.

**Chỉ có một cách biết:** tải HTML thật của các URL công khai rồi so. `doi_chung_live.py`.

---

<a id="4"></a>
## 4. File admin sở hữu menu — xoá cả file là mất màn hình khác

**Đã cắn hụt:** `inc/admin-theme-settings.php` có docblock ghi
*"Theme admin settings — promo banners"*, và toàn bộ nội dung của nó là hai form banner
đã chết. Rất dễ kết luận "xoá cả file".

Nhưng chính file đó:
- `add_menu_page()` đăng ký menu cấp cao **"My Theme"** — nơi các màn hình khác treo vào;
- `add_theme_page()` đăng ký lối vào **Giao diện → Chân trang**;
- hàm render trang của nó gọi `mytheme_render_footer_settings_section()` ở file khác.

Xoá cả file là mất luôn màn hình cài đặt chân trang, mà `php -l` không kêu một tiếng.

**Luật rút ra:** trước khi xoá một file admin, liệt kê những gì nó **đăng ký** —
`add_menu_page`, `add_submenu_page`, `add_theme_page`, `add_meta_boxes`,
`register_setting`, `add_settings_section` — và xem file khác có treo vào không. Mổ
đúng phần chết, giữ phần còn có việc.

---

<a id="5"></a>
## 5. Màn hình cài đặt không điều khiển gì — đây là quyết định của chủ site

**Đã gặp:** màn hình admin cho chọn ảnh, đổi tiêu đề, bấm Lưu — lưu thật vào option.
Nhưng template đọc option đó đã mồ côi từ lâu, trang chủ gọi 8 khối khác. **Sửa xong
bấm Lưu thì trang chủ không đổi gì.**

Cùng họ: một ô "ảnh sóng chân trang" lưu được `footer_wave_id`, có cả hàm đọc nó, mà
không mặt trước nào in ra.

**Đây không phải quyết định kỹ thuật.** Hai hướng cho kết quả trái ngược:
- **A. Xoá hẳn** — bỏ cả phần cài đặt lẫn template. Giao diện giữ nguyên như hiện tại.
- **B. Nối lại** — đưa section trở lại trang. Màn hình admin có tác dụng thật, nhưng
  đây là **thêm section vào trang**, tức đổi giao diện, phải duyệt bố cục.

**Hỏi chủ site, đừng tự chọn.** Trình bày bằng ngôn ngữ đời thường: "anh vào đó đổi
ảnh, bấm Lưu, trang chủ không đổi gì — xoá luôn hay đưa nó trở lại?"

---

<a id="6"></a>
## 6. Phụ thuộc vào handle của plugin — deregister là chết cả site

```php
$deps = array( 'mytheme-google-fonts' );
if ( class_exists( 'WooCommerce' ) ) {
    $deps[] = 'woocommerce-general';   // <- đường chết
    $deps[] = 'woocommerce-layout';
}
wp_enqueue_style( 'main', ..., $deps, ... );
```

WordPress **bỏ qua hoàn toàn** một style khi phụ thuộc của nó chưa được đăng ký. Một
plugin tối ưu gọi `wp_deregister_style('woocommerce-general')` là `main.css` không nạp
và **cả site mất style**, im lặng, không lỗi, không cảnh báo.

Phân biệt cho đúng — đây là chỗ dễ kết luận sai:
- `wp_dequeue_style()` chỉ gỡ khỏi hàng đợi, handle **vẫn đăng ký** → phụ thuộc vẫn
  giải được → **vô hại**;
- `wp_deregister_style()` mới xoá đăng ký → **gây hỏng**.

**Cách sửa giữ nguyên thứ tự nạp:**
```php
foreach ( array( 'woocommerce-general', 'woocommerce-layout' ) as $h ) {
    if ( wp_style_is( $h, 'registered' ) ) {
        $deps[] = $h;
    }
}
```
Đừng bỏ thẳng phụ thuộc: chúng đang giữ cho CSS của theme đứng **sau** CSS plugin. Bỏ
đi là thua specificity ở hàng loạt chỗ.

---

<a id="7"></a>
## 7. `is_admin()` là chuyện phạm vi, không phải tốc độ

Bọc các file chỉ phục vụ wp-admin trong `if ( is_admin() )` là đúng — nhưng **đừng hứa
nó làm trang nhanh hơn**. Với OPcache, chi phí nạp thêm vài trăm dòng PHP gần bằng
không. Nói thật: đây là giảm bề mặt, không phải tối ưu tốc độ. Hứa sai thì lần đo sau
người dùng thấy số không đổi và mất tin vào mọi con số khác.

---

<a id="8"></a>
## 8. Endpoint AJAX công khai sống sót sau khi giao diện chết

Tính năng ghi chú giỏ hàng chết cả chuỗi: ô nhập nằm trong một template-part không ai
gọi, nên hàm ghi session không bao giờ chạy. **Nhưng hai endpoint vẫn đăng ký:**

```php
add_action( 'wp_ajax_mytheme_save_cart_note',        'mytheme_ajax_save_cart_order_note' );
add_action( 'wp_ajax_nopriv_mytheme_save_cart_note', 'mytheme_ajax_save_cart_order_note' );
```

`nopriv` = mở cho cả khách chưa đăng nhập. Một cửa ghi vào session mà không giao diện
nào dùng. Khi dọn, **quét riêng `wp_ajax_nopriv_`, `rest_api_init`, `admin_post_nopriv_`**
— đây là bề mặt tấn công, không chỉ là code thừa.

---

<a id="9"></a>
## 9. Dữ liệu localize không còn ai đọc

`wp_localize_script()` in một object JS vào mọi trang khớp điều kiện. Sau khi xoá khối
JS đọc nó, object vẫn được in — và trong đó có thể có `nonce`, URL admin-ajax, chuỗi
dịch. Quét `wp_localize_script` và `wp_add_inline_script`, đối chiếu tên biến với JS
còn lại.

---

<a id="10"></a>
## 10. Khối JS chết vẫn để lại tác dụng phụ

Một khối "thanh toán nhiều bước" đã bỏ, markup không còn, nhưng hai điều kiện mở cổng
vẫn đúng nên khối vẫn chạy — và nó gắn `document.body.classList.add('...-step-info')`
trên mọi lượt mở trang. Lúc đó chưa CSS nào đọc class ấy nên chưa hại, nhưng ai viết
một rule trùng tên sau này sẽ thấy trang tự đổi hình mà không hiểu vì đâu.

**Đừng chỉ hỏi "khối này có làm gì thấy được không".** Hỏi "nó có ghi gì ra ngoài
không": class trên `body`, biến `window`, cookie, `localStorage`, listener toàn cục.

---

<a id="11"></a>
## 11. Template chết gọi hàm đã xoá — mìn chờ

`template-parts/shop/recently-viewed.php` gọi `mytheme_get_recently_viewed_products()` —
hàm **không còn tồn tại**. File mồ côi nên không ai gọi, không lỗi. Nhưng nếu có ai
`get_template_part` lại nó thì fatal error chứ không phải thiếu một dải.

**Luật thứ tự:** khi gỡ, **nơi tiêu thụ đi trước**. Xoá file gọi hàm trước, rồi mới gỡ
hàm. Làm ngược là để lại một file gọi hàm không tồn tại.

---

<a id="12"></a>
## 12. Chú thích lạc hậu sau khi dời code

Dời một guard `function_exists(...)` lên đầu hàm thì chú thích bên dưới giải thích
guard đó thành sai chỗ. Chú thích sai còn hại hơn không có: người sau tin nó.

Cùng loại rác đã gặp:
- `/* Da bo: */` — chú thích rỗng còn lại sau khi gỡ code, không nói gì cho ai;
- `/* * ...` — thừa một dấu sao, dở dang giữa `/*` và `/**`;
- chú thích ghi "khối mã giảm giá đã bỏ" trong khi JS và CSS của nó vẫn còn.

**Nhưng đừng dọn nhầm.** Các khối chú thích dài ghi lại **một ca hỏng đã trả giá và vì
sao chọn cách hiện tại** là thứ đắt nhất trong file. Giữ. Chỉ dọn chú thích **sai** hoặc
**rỗng**.

---

<a id="13"></a>
## 13. Chết theo dây chuyền — phải lặp tới điểm dừng

Xoá file làm chết thêm hàm ở file khác, gỡ hàm lại làm chết thêm file. Một vòng quét
là không đủ.

Thực tế đã chạy: vòng 1 xoá 20 file → vòng 2 lộ ra 7 hàm mới chết → vòng 3 sạch.

**Lặp `quet_chet.py` cho tới khi cả ba mục đều rỗng.** Chưa rỗng mà dừng là để lại
đúng loại rác vừa mất công dọn.

---

<a id="14"></a>
## 14. Nền lỗi thời: cây git lệch xa host

**Đã cắn:** nhánh `main` đứng ở commit 3 ngày trước, trong khi cây làm việc chứa bản
đang chạy trên host — riêng một file CSS chênh 1.119 dòng, và 20 file đang chạy thật
**chưa từng vào git**. Tách worktree từ `main` lúc đó là dựng lại trên nền không còn
tồn tại.

**Trước khi tách nhánh làm việc, chốt nguyên trạng đã.** Commit bản đang chạy vào một
nhánh mốc rồi mới tách. Và **đừng `git add -A`** — repo WordPress hay có file cấu hình
chứa mật khẩu thật nằm ngoài `.gitignore`; thêm từng đường dẫn cụ thể.

---

<a id="15"></a>
## 15. Chính việc kiểm làm sập database

**Đã cắn:** trong lúc kiểm sau deploy, gọi site khoảng 15–20 lượt bằng URL gắn `?cb=…`
cho "chắc chắn đọc bản mới". Cache-busting ép cache bỏ qua nên **mỗi lượt là một lần
chạy PHP + truy vấn DB đầy đủ**. Host trả:

```
User 'xxx_dbuser' has exceeded the 'max_user_connections' resource (current value: 30)
Error establishing a database connection
```

Không chứng minh được đó là nguyên nhân duy nhất, nhưng chắc chắn góp vào, và đó là
thứ mình kiểm soát được.

**Luật:** dùng URL canonical, mỗi lần một request, có nghỉ giữa các lượt. `?cb=` chỉ
dùng khi thật sự cần hỏi "origin đang có gì", và chỉ **một** lượt. Trang nặng
(bảng giá, danh sách sản phẩm đầy đủ) thì càng phải dè.

---

<a id="16"></a>
## 16. CRLF/LF: FTP chế độ văn bản đổi xuống dòng

File trên host nhẹ hơn bản local đúng bằng số dòng — vì FTP đẩy ở chế độ văn bản, đổi
CRLF thành LF. **Không phải file trượt.** So bằng cách bỏ hết `\r` trước rồi mới đối
chiếu byte.

Ngược lại, khi sửa file thì đọc/ghi **nhị phân** và giữ nguyên EOL sẵn có — nếu không,
diff giả làm mọi phép so với host thành vô nghĩa.

---

<a id="17"></a>
## 17. Truy cập thẳng file .php làm lộ đường dẫn máy chủ

`error_log` trong thư mục theme cho thấy bot gọi thẳng
`/wp-content/themes/x/home.php`. Không có WordPress nên `get_header()` không tồn tại →
fatal error → thông báo lỗi in ra **đường dẫn tuyệt đối trên máy chủ**
(`/home/<tai-khoan-hosting>/public_html/...`).

Nguyên nhân: các template ở gốc theme thiếu `defined( 'ABSPATH' ) || exit;`. Đây không
phải việc của dọn code, nhưng thấy thì ghi lại. Và `error_log` trong thư mục theme nên
được `.gitignore` chặn — nó là log host sinh ra, không phải mã nguồn.

---

<a id="18"></a>
## 18. Xoá không hết — phải dò lại từng file

Giao danh sách 20 file cần xoá, người dùng xoá 19. File sót lại vô hại (không ai
require) nhưng chính nó là file nguy hiểm nhất trong danh sách: bên trong có hook đặt
cookie trên trang được cache công khai.

**Đừng tin "đã xoá xong".** Dò lại từng đường dẫn bằng mã HTTP, kèm đối chứng hai đầu:
một file chắc chắn còn phải ra 200, một tên bịa phải ra 404. `doi_chung_live.py` làm
sẵn việc này.
