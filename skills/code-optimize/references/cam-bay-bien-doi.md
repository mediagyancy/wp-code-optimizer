# Cạm bẫy khi BIẾN ĐỔI code — những chỗ bộ thước của phép XOÁ bị mù

Bốn tầng xác minh của `wp-code-cleaner` là một bộ thước tốt. Chúng chỉ được thiết kế cho
một loại thay đổi: **xoá**. Đem chúng sang phép **biến đổi** thì chúng không sai — chúng
**im lặng**, và im lặng trông giống sạch.

---

## 1. Bốn tầng cũ đối mặt sáu lỗi refactor — bảng đã đo

| Lỗi refactor | T1 | T2 | T3 | T4 | Tầng 5 bắt bằng mặt |
|---|---|---|---|---|---|
| hook dời file → đổi **thứ tự đăng ký** cùng priority | — | — | — | — | `hook` (thứ tự trong bucket) |
| `add_action` đổi **priority** | — | — | — | — | `hook` + `html` |
| hàm tách ra với **giá trị mặc định** khác | — | — | — | — | `chuky` (Reflection) |
| **mất `esc_html`** quanh `$_GET` khi dời | — | một phần, có điều kiện | — | — | `sanit` (tĩnh) |
| `get_template_part` dời sang **sau `wp_head()`** | — | — | — | — | `asset` + `html` |
| điều kiện **đảo chiều** canh một `add_filter` | — | — | — | — | `hook` (cạnh biến mất) |

Năm trong sáu: **không tầng nào**. Từng tầng một, vì sao:

**Tầng 1 và Tầng 3 được tham số hoá bằng một DANH SÁCH ĐÃ XOÁ.** Tầng 3 hỏi "class hay mốc
nào vừa xoá còn xuất hiện? Phải là 0". Phép biến đổi không có danh sách xoá → tập truy vấn
rỗng → **PASS rỗng**. Đây đúng là hình dạng input đã sinh ra lỗi P0 fail-open ở v0.2.0 —
`doi_chung_live.py` "chạy không tham số nào vẫn in 'Sạch ở tầng này' và thoát 0" — và
fail-open ấy **tái phát trong chính code viết ra để chống nó** ở v0.4.0.

**Tầng 2 bị vô hiệu hoá bằng định nghĩa.** Chốt mạnh nhất của nó là "rule còn lại phải
**nguyên văn** như bản cũ". Phép biến đổi phá tiền đề này: văn bản sống sót không còn
nguyên văn. Tầng 2 chỉ còn hai kết cục — đỏ ở mọi lượt (nên sẽ bị nới hoặc tắt), hoặc bị
thay bằng thứ yếu hơn. Và chính repo đã ghi luật: cảnh báo luôn kêu là cảnh báo đã chết.

**Tầng 4 so một HTML với chính nó.** Cơ chế của nó là "thay **đúng một** dòng link CSS
bằng URL tuyệt đối" rồi so computed style của hai iframe. Hai iframe dùng **cùng một
HTML**. Nên nó không thể thấy bất kỳ thay đổi phía PHP nào — với phép biến đổi (thứ làm
đổi output PHP), cấu trúc phép đo vô hiệu, không chỉ thiếu độ phủ.

---

## 2. Hai ca mà CHÍNH PHÉP ĐO đã hỏng — lộ ra nhờ ca hiệu chuẩn

**Ca "đảo chiều điều kiện" ban đầu không mặt nào bắt.** Lỗi không nằm ở fixture. Nó nằm ở
bộ chụp: `require wp-load.php` rồi gọi thẳng `index.php`, **bỏ qua giai đoạn `wp()`** nơi
hook `wp` fire. Callback bị đảo chiều không chạy ở cả hai bản — nên hiệu rỗng giả tạo. Nếu
không có ca tiêm này thì bộ chụp sẽ được tin là đủ trong khi nó bỏ cả một giai đoạn
lifecycle.

**Lượt đầu báo `NOISE_QUA_LON` ở mặt `fire`.** Hai lượt không đổi code ra khác nhau từ ký
tự 3523 — lượt sau đọc option từ cache còn ấm nên không fire lại `pre_option_*`. Đã lọc họ
hook option/transient/cache. **Đánh đổi phải khai rõ:** mặt `fire` nay không trả lời được
"có đổi tập option được đọc hay không". Một mask là một vùng mù bằng cấu trúc; cái này được
ghi lại để không ai tưởng mặt `fire` phủ cả option.

---

## 3. Cạm bẫy của chính việc viết tool — hai lỗi regex, hai hướng hỏng ngược nhau

Khi viết `code_nodes.py`:

- `([^,)]+?)` **lazy** đứng trước một cái đuôi toàn optional khớp đúng **một ký tự**, nên
  handle `'fxb-main'` bị bắt thành dấu `'`. Hậu quả: `dynamic_unresolved` phồng lên 2 vì
  lỗi của chính tool — tức thước đo độ tin cậy của đồ thị bị chính tool làm vô dụng.
- Đổi sang `[^,()]+` **greedy** thì handle đúng, nhưng tham số `src` là
  `get_template_directory_uri() . '...'` có dấu ngoặc nên char class dừng giữa đường và
  mảng dependency **im lặng** không được đọc — cạnh `phu_thuoc` biến mất, và lần này tool
  báo `dynamic_unresolved = 0` **trong khi đang thiếu cạnh**. Hướng này nguy hiểm hơn.

Cách đúng là cách repo đã dùng ở `go_ham.py`/`go_css.py`: **cắt theo cân bằng ngoặc** có
xử lý chuỗi, regex chỉ để tìm điểm mở. Một regex cố bắt cả lời gọi nhiều tham số là một
regex sẽ sai ở tham số thứ hai.

---

## 4. Đồ thị tĩnh tự tin sai — hai dạng phổ biến nhất trong WordPress thật

```php
$ten = 'init';
add_action( $ten, 'fxb_dong_a' );          // tên hook là biến
add_action( 'init', 'fxb_' . 'dong_b' );    // callback ghép chuỗi
```

Đọc text thì không thấy cạnh nào. Runtime thì thấy cả hai trong `$wp_filter`. Không phải ca
nhân tạo: core WordPress dùng đầy họ hook ghép chuỗi — `save_post_{$post_type}`,
`wp_ajax_{$action}`, `woocommerce_*`. Đồ thị tĩnh phải **đếm** chúng vào vùng mù chứ không
đoán — đoán là bịa ra một cạnh, và cạnh bịa tệ hơn cạnh thiếu: cạnh thiếu làm ta thận
trọng, cạnh bịa làm ta tự tin.

Lưu ý kéo theo: với `quet_chet.py`, `fxb_dong_b` trông như **hàm không ai gọi** (tên đầy
đủ không xuất hiện ở đâu ngoài chỗ khai báo). Nếu tin bộ quét tĩnh mà xoá nó thì xoá một
callback đang đăng ký. Đây đúng là lý do cổng graph tồn tại.

---

## 5. "Tinh gọn" thưởng cho việc xoá thứ đắt nhất

Thước đếm dòng cho điểm cao khi bỏ:

- khối chú thích kể lại một ca hỏng đã trả giá và vì sao chọn cách hiện tại — `cam-bay.md`
  của cleaner gọi đây là "thứ đắt nhất trong file";
- vòng `wp_style_is()` giữ thứ tự nạp asset;
- `defined( 'ABSPATH' ) || exit;`;
- guard `function_exists()`.

Với một "checklist kiến trúc hiện đại" tất cả trông như boilerplate xoá được. Đây không
phải proxy yếu, đây là proxy **có hướng sai**. Và chính README của repo đã từ chối hứa tốc
độ từ ít dòng hơn, với lý do OPcache.

---

## 6. Restore là một đoạn văn cho tới khi nó chạy

Trước `sao_luu.py`, repo có **0 dòng code phục hồi**, **0 khẳng định test** về backup, và
`wp-delivery/SKILL.md` có `rollback_plan: []`. `wp_safe_write.py` ghi `.bak` cạnh từng
file — không có mốc thời điểm nhất quán của cả cây.

Bài diễn tập bắt buộc (đã chạy, 23 khẳng định): làm hỏng một bản sao đúng ba kiểu và đòi
`kiem` gọi đúng tên ba file · làm hỏng một file **bên trong** backup và đòi `phuc_hoi` từ
chối · **xoá hẳn cây nguồn** rồi phục hồi chỉ từ backup, so byte với bản gốc giữ riêng —
0 lệch. Ca thứ ba là tình huống thật của một đường lùi: lúc cần nó thì cây gốc đã không còn.
