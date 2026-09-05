# Xác minh: bốn tầng, và kỷ luật hiệu chuẩn

Xoá code là phần dễ. Phần khó — và phần đáng tiền — là **chứng minh xoá không hỏng gì**.
File này nói cách chứng minh.

---

## Nguyên tắc gốc: thước chưa hiệu chuẩn thì mọi PASS đều là NOT_TESTED

Trước khi tin bất kỳ phép kiểm nào, cho nó chạy qua **đúng ca hỏng mà nó phải bắt**.
Nếu ca hỏng cũng PASS thì phép kiểm đang mù, và mọi số đẹp nó đưa ra đều vô nghĩa —
tệ hơn là không kiểm, vì nó tạo cảm giác an toàn.

Điều này nghe hiển nhiên. Thực tế nó bị vi phạm liên tục, vì ca hiệu chuẩn dễ dựng
quá yếu. Hai lần đã xảy ra:

**Lần 1 — ca hiệu chuẩn quá yếu.** Định kiểm phép cắt hàm PHP bằng cách dựng bản "cắt
hụt một dòng" rồi bắt `php -l` phải FAIL. Nhưng `php -l` **PASS**. Lý do: dòng cuối
vùng cắt là một dòng trống, bỏ hụt nó chẳng sai cú pháp gì. Ca hỏng phải là **bỏ lại
một dấu `}` mồ côi** — cắt tới trước dấu đóng thân hàm — thì mới chắc chắn sai.

**Lần 2 — chính thước đo hỏng.** Dựng bộ so computed style bằng cách thay link CSS
trong HTML thật thành `href="/main-moi.css"`. Nhưng thẻ `<base href="https://site/">`
kéo đường dẫn tương đối đó về `https://site/main-moi.css` → **404** → không stylesheet
nào của theme tải được. Hai bản trông giống hệt nhau, phép so vui vẻ báo **"0 phần tử
lệch"**, và con số đó hoàn toàn vô nghĩa. Bắt được nhờ ca hiệu chuẩn: bản cố ý xoá một
rule đang dùng cũng ra 0 — lúc đó mới lộ.

**Rút ra:** ca hiệu chuẩn phải là **ca hỏng thật của đúng loại lỗi đang sợ**, không
phải một biến thể cho có. Và với thước chạy trong trình duyệt, kiểm luôn xem
`document.styleSheets` có file của mình với số rule > 0 không.

---

## Vì sao đếm tổng là phép kiểm mù

Cắt file bằng cắt-dán chuỗi sinh ra một loại hỏng **không làm lệch tổng ngoặc**: cắt
nhầm mốc kết thúc thì chỗ này thiếu một dấu đóng, chỗ kia thừa đúng một dấu — **cân
bằng giả**. Tổng vẫn 243/243.

Đã trả giá: một bản vá CSS cắt tới dấu `}` đóng của một *rule* thay vì dấu `}` đóng
của cả `@media`. Khối media bị nhét vào giữa một media khác, **toàn bộ CSS phía sau
rơi vào trong nó** nên chỉ áp ở màn hẹp — desktop mất sạch style của một section. Mắt
người cũng không thấy, vì phần hỏng nằm ngoài màn hình đang xem.

Ba chốt thay cho một:
1. tổng `{` = tổng `}`
2. **độ sâu không bao giờ âm** → bắt dấu `}` mồ côi giữa file
3. **không at-rule nào nằm trong khối khác** → bắt khối `@media` bị nuốt

`go_css.py` cài đủ ba. Nhớ bỏ comment và nội dung chuỗi trước khi đếm — `content:'}{'`
là hợp lệ.

**Và luôn mở lại bề mặt mình *không* định đụng.** Lỗi loại này hiện ra ở đoạn **đứng
sau** chỗ vừa sửa, không phải ở chỗ vừa sửa.

---

## Đừng cắt theo mốc chuỗi

Mốc hiếm khi duy nhất. Một lần, cùng một mốc `/* ---------- TIN TỨC ---------- */` có
mặt ở **cả khối CSS lẫn khối JS** trong một file, gây hỏng hai lần:
- cắt theo hai mốc, lấy nhầm cặp ngược nhau → slice rỗng → chèn vào giữa mọi ký tự;
- `str.replace(moc, moi + moc)` **không giới hạn số lần** → chèn vào cả hai chỗ; bản
  rơi vào `<script>` giết chết toàn bộ JS của trang.

Cả hai đều lọt qua phép đếm ngoặc.

**Cắt theo cân bằng ngoặc có xử lý chuỗi và comment**, như `go_ham.py` và `go_css.py`
làm. Nếu buộc phải dùng mốc thì mốc phải **duy nhất** — kiểm số lần xuất hiện trước,
ném lỗi nếu khác 1.

---

## Bốn tầng, tầng sau bắt được cái tầng trước bỏ sót

Chạy đủ bốn. Bỏ tầng nào thì nói rõ đã bỏ, đừng im lặng.

### Tầng 1 — Đối chứng hai chiều trên mã nguồn

Hỏi cả hai chiều, vì mỗi chiều bắt một loại lỗi:
- **chiều xuôi:** thứ vừa xoá có còn ai gọi không? (grep tên hàm/hằng số của file đã
  xoá trên **toàn `wp-content`**, không chỉ theme — plugin có thể gọi)
- **chiều ngược:** thứ phải còn có còn không? Chọn sẵn một danh sách hàm/mốc **đang
  sống** rồi đếm lại sau khi cắt. Chiều này bắt được ca cắt lố.

Công cụ: `quet_chet.py`, và grep tay cho danh sách đối chứng.

### Tầng 2 — Cấu trúc và chuẩn code

- `php -l` từng file PHP (hoặc `node --check` cho JS, ba chốt ngoặc cho CSS)
- **Rule còn lại phải NGUYÊN VĂN như bản cũ.** Chuẩn hoá khoảng trắng rồi so tập rule:
  `rule_mới − rule_cũ` phải rỗng. Bắt được sửa nhầm nội dung, gộp nhầm hai rule — thứ
  mà `git diff` giấu đi, vì xoá một khối lớn làm git căn lại hunk và hiện ra hàng trăm
  "dòng thêm" thực ra chỉ là dòng cũ được vẽ lại.
- PHPCS/PHPStan **so trước với sau trên đúng file đã sửa**. Luật là **code mới không
  tạo thêm vi phạm**, không phải làm sạch quá khứ. Với PHPStan quét file rời, phần lớn
  lỗi là nhiễu do không thấy file khác — điều đáng hỏi là *"có lỗi nào nhắc tới tên
  vừa gỡ không"*, chứ không phải tổng số lỗi.

### Tầng 3 — HTML thật của production

Tầng duy nhất nhìn thấy markup do WooCommerce, plugin, shortcode sinh ra lúc chạy.

Lấy HTML của một tập URL công khai đại diện, gom mọi `class="…"`, rồi hỏi: **class hay
mốc nào vừa xoá còn xuất hiện?** Phải là 0.

Chọn URL cho đủ loại trang, không phải cho nhiều: trang chủ · một danh mục · một trang
chi tiết · giỏ hàng · một trang tĩnh · một trang danh sách bài · một trang đặc thù của
site. Mỗi loại nạp một bộ asset khác nhau.

Công cụ: `doi_chung_live.py`.

### Tầng 4 — So computed style trên chính HTML đó

Không hỏi "class còn không" mà hỏi **"từng phần tử có hiển thị y hệt trước không"**.
Bắt được cả ca class vẫn còn nhưng rule định vị nó đã bị cắt.

Cách dựng: HTML thật + `<base href>` để asset khác vẫn tải từ host, thay **đúng một**
dòng link CSS bằng **URL tuyệt đối** về server local, nạp hai bản vào hai iframe cùng
origin, duyệt mọi phần tử, so 25 thuộc tính computed.

Công cụ: `dung_so_computed.py` (đã cài sẵn cả bước tự kiểm CSS có nạp thật không và ca
hiệu chuẩn).

**Con số thực tế đã đạt:** 4.249 phần tử qua 5 trang, 0 lệch — với thước đã được chứng
minh là báo 5 phần tử lệch ở bản cố ý xoá một rule đang dùng.

---

## Bề mặt không kiểm được từ ngoài

Ghi rõ, đừng để trống:
- **trang cần giỏ có hàng** (đặt hàng/thanh toán) — không lấy được qua HTTP trần;
- **trang cần đăng nhập** — wp-admin, tài khoản khách;
- **luồng nghiệp vụ** — gửi form, đặt đơn, email đi.

Những bề mặt này là `NOT_TESTED` cho tới khi có người thao tác tay. Nói thẳng ra và
nói cần làm gì, đừng nâng thầm thành PASS.

Với site bán hàng, phép kiểm cuối cùng luôn là **đặt thử một đơn**, không phải mở trang
xem có hiện không.

---

## Bốn nhãn, không được nâng cấp lẫn nhau

- `CONCEPT_PREVIEW` — chỉ chứng minh bố cục cô lập, không chứng minh integration.
- `VISUAL_PASS` — đã xem trên WordPress thật, đúng URL, đủ plugin và dữ liệu.
- `PRODUCTION_VERIFIED` — đã xem trên canonical URL sau khi purge cache.
- `NOT_TESTED` — không thử thật được. Ghi rõ.

Và trạng thái giao hàng là chuyện khác với nhãn bằng chứng:
`PLANNED` → `LOCAL_VERIFIED` → `PACKAGE_READY` → `UPLOADED_UNVERIFIED` →
`PRODUCTION_VERIFIED`. Từ "xong" đứng một mình không có nghĩa.

---

## Sau deploy: đọc kết quả cho đúng

| Origin | Canonical | Asset | Kết luận |
|---|---|---|---|
| mới | mới | mới | đạt |
| mới | **cũ** | bất kỳ | cache công khai còn cũ → purge |
| mới | mới | **cũ** | version asset không đổi → sửa `?ver=` |
| cũ | cũ | cũ | deploy chưa lên |

`x-litespeed-cache: hit/miss` là cách rẻ nhất tách "deploy hỏng" khỏi "cache giữ bản
cũ" — hai lỗi trông giống hệt nhau trên trình duyệt.

**Về bump version:** nếu đợt dọn không đổi nội dung CSS/JS, bump vẫn khiến trình duyệt
tải lại một lần toàn bộ asset. Vẫn nên bump, vì `?ver` trong HTML là **cách duy nhất
nhìn từ ngoài biết host đang chạy bản nào** — file PHP không tải được qua trình duyệt.
Mất mốc đó thì mọi phép so local ↔ host thành vô nghĩa. Nhưng **nói rõ đánh đổi** cho
người dùng, đừng lặng lẽ.
