---
name: wp-code-cleaner
description: >-
  Soát và dọn code chết trong theme/plugin WordPress một cách CHỨNG MINH ĐƯỢC — tìm file
  mồ côi, hàm không ai gọi, CSS/JS không còn markup nào dùng, màn hình cài đặt không điều
  khiển gì, rồi gỡ theo đợt kèm bốn tầng xác minh trên site thật. Dùng skill này bất cứ khi
  nào người dùng nói tới: audit code, soát code, dọn code, code thừa, code chết, code rác,
  file mồ côi, hàm không ai gọi, CSS/JS không dùng, "code phình", "code chồng chéo", refactor
  theme, tinh gọn theme, giảm dung lượng CSS/JS, "tại sao trang tải chậm", hoặc đưa ra một
  file như functions.php và bảo xem có gì thừa không. Cũng dùng khi cần chứng minh một phép
  xoá code không làm hỏng gì, hoặc khi đã lỡ xoá và cần kiểm lại. KHÔNG dùng cho việc viết
  tính năng mới, sửa giao diện, hay tối ưu hiệu năng thuần (LiteSpeed, ảnh, CDN).
---

# Dọn code WordPress mà chứng minh được

## Việc thật sự là gì

Tìm code chết thì dễ — grep vài lượt là ra một danh sách dài. **Phần khó, và phần duy
nhất đáng tiền, là chứng minh xoá nó đi không làm hỏng gì.** Trên một site đang bán
hàng, một phép xoá sai không hiện ra ngay: nó nằm im tới lúc có khách vào đúng trang đó.

Nên skill này dành phần lớn công sức cho **thước đo**, không cho việc xoá. Ba câu chi
phối mọi bước:

1. **Thước chưa hiệu chuẩn thì mọi PASS đều là `NOT_TESTED`.** Trước khi tin một phép
   kiểm, cho nó chạy qua đúng ca hỏng mà nó phải bắt. Ca hỏng cũng PASS = thước mù.
2. **Phân tích tĩnh mù trước markup sinh ra lúc chạy.** Grep không thấy tên ghép chuỗi,
   không thấy class do JS tạo, không thấy HTML do plugin in ra. Luôn đối chứng bằng HTML
   thật trước khi xoá.
3. **Chết theo dây chuyền.** Xoá file làm chết thêm hàm, gỡ hàm làm chết thêm file. Lặp
   tới khi quét ra rỗng, không dừng ở vòng một.

Nếu repo có `CLAUDE.md`/`AGENTS.md`, đọc trước — luật repo thắng skill này. Nếu môi
trường có skill `wp-delivery`, dùng nó cho phần deploy; skill này lo phần soát và gỡ.

## Trước khi động vào gì

**Chốt nền.** Cây git rất hay lệch xa host — đã gặp ca `main` đứng ở commit 3 ngày
trước trong khi cây làm việc chứa bản đang chạy, và 20 file đang chạy thật chưa từng vào
git. Tách nhánh từ nền lỗi thời là dựng lại trên thứ không tồn tại. Đối chiếu với host
trước (hash asset công khai + version lộ ra trong HTML), commit nguyên trạng nếu cần, rồi
mới tách nhánh làm việc.

**Chốt phạm vi.** Chỉ có thư mục theme thì kết luận cũng chỉ tới đó: "đã soát theme; chưa
soát plugin và database". Đừng nói "đã audit toàn site".

**Hỏi có backup chưa** nếu sắp đụng production. Với site đang chạy, bản tải từ FTP là
đường lùi duy nhất cho file PHP — chúng không tải được qua trình duyệt nên không có cách
đối chiếu nào khác.

## Quy trình

### 1. Quét — chỉ đọc, chưa sửa gì

```bash
python scripts/quet_chet.py --theme "đường/dẫn/theme" --tien-to mytheme_,mg_
```

Trả về ba mục: file không có đường nào dẫn tới · hàm không ai gọi · class CSS **nghi**
chết. Mục 3 chỉ là nghi ngờ, đừng xoá theo nó khi chưa qua tầng 3.

Rồi soát thêm bằng mắt những thứ script không thấy:

- **`functions.php` (hoặc file nạp chính)** — nó chỉ được chứa guard, hằng số nền,
  `require_once`, và một lời gọi khởi động. Có `add_action` của tính năng, truy vấn,
  AJAX handler, logic giá/giỏ trong đó là đặt sai chỗ. Mục tiêu ≤ 80 dòng thực thi.
- **file `inc/` có trên đĩa mà loader không require** — hoặc là tính năng đang tắt mà
  không ai biết, hoặc là rác. Cả hai đều phải xử lý, không để nguyên.
- **`wp_ajax_nopriv_`, `rest_api_init`, `admin_post_nopriv_`** — endpoint công khai sống
  sót sau khi giao diện chết là bề mặt tấn công, không chỉ code thừa.
- **`wp_localize_script`** — đối chiếu tên biến với JS còn lại.
- **màn hình cài đặt admin** — chúng ghi option nào, và mặt trước nào đọc option đó?
- **điều kiện `enqueue`** — cùng một câu hỏi lặp lại ở nhiều khối là dấu vết của việc mỗi
  lần góp ý lại chèn thêm một đoạn.
- **phụ thuộc style/script vào handle của plugin** — xem `references/cam-bay.md` mục 6,
  đây là đường chết cả site.

### 2. Báo cáo trước khi xoá — và hỏi những gì không phải việc của mình

Đưa danh sách kèm **bằng chứng cho từng mục** (lệnh nào, dòng nào), phân theo mức:
mất chức năng · nguy cơ · code chết · kém gọn · tốc độ. Ghi rõ phần **chưa kiểm được**.

Ba loại phải hỏi chủ site, không tự quyết:
- **màn hình cài đặt không điều khiển gì** — xoá hẳn hay nối section trở lại? Hai hướng
  cho kết quả trái ngược nhau (`cam-bay.md` mục 5);
- **tính năng có vẻ tắt nhầm** — bật lại hay bỏ hẳn?
- **bất cứ thứ gì đổi giao diện.** Dọn code thì giao diện phải **không đổi gì**. Nếu một
  phép dọn làm đổi giao diện, nó không còn là dọn code.

### 3. Gỡ theo đợt — đi NGƯỢC chiều với lúc thêm

Thêm logic thì: file mới → loader → file sửa đè. **Gỡ logic thì ngược lại:**

| Đợt | Làm gì | Vì sao thứ tự này |
|---|---|---|
| 1 | **nơi tiêu thụ** ngừng gọi (JS, CSS, template gọi hàm) | file cung cấp vẫn còn, chưa ai hụt |
| 2 | **loader** gỡ `require`/hook | các file vừa hết người gọi |
| 3 | **xoá file** | không còn ai nhắc tên |

Làm ngược = có khoảng thời gian consumer gọi hàm không còn tồn tại → fatal error. Và
**giữa hai đợt site vẫn phải chạy được** — đó là điều kiện để tách đợt.

Mỗi đợt: sửa → chạy đủ bốn tầng xác minh → đóng gói → deploy → xác minh trên host →
mới sang đợt sau. Người dùng chọn gộp hay tách; mặc định tách, vì gộp thì lúc hỏng
không biết hỏng vì đợt nào.

**Công cụ gỡ** (cả hai tự hiệu chuẩn trước khi ghi, không qua thì dừng chứ không ghi):

```bash
python scripts/go_ham.py --json ke-hoach.json --thu    # chạy thử trước
python scripts/go_css.py --theme "..." --css assets/css/main.css --thu
```

Sau mỗi lần gỡ, **quét lại** (`quet_chet.py`). Lặp tới khi rỗng.

### 4. Xác minh — bốn tầng, đọc `references/xac-minh.md` để làm cho đúng

| Tầng | Hỏi gì | Bắt được cái gì |
|---|---|---|
| 1 | thứ vừa xoá còn ai gọi? thứ phải còn có còn không? | cắt hụt và cắt lố |
| 2 | cú pháp sạch? rule còn lại có **nguyên văn** như cũ? vi phạm có tăng? | sửa nhầm nội dung |
| 3 | class/mốc vừa xoá còn trên **HTML thật** không? | markup do plugin sinh ra |
| 4 | **computed style** từng phần tử có y hệt trước không? | rule bị cắt tuy class còn |

```bash
python scripts/doi_chung_live.py --url-file urls.txt --css-cu cu.css --css-moi moi.css
python scripts/dung_so_computed.py --site https://... --css-cu ... --css-moi ... \
    --duong-dan-css wp-content/themes/x/assets/css/main.css --url ... --ra ./xem
```

Tầng 4 dựng ra một thư mục cần static server. Trong Claude Code: thêm một mục vào
`.claude/launch.json` rồi `preview_start` — **đừng chạy server bằng Bash**.

### 5. Sau deploy

- purge cache, rồi xem `?ver` trong HTML đã đổi chưa;
- mở **mỗi loại trang một cái** — mỗi loại nạp một bộ asset khác nhau, đó là chỗ lỗi
  enqueue lộ ra;
- **dò lại từng file trong danh sách xoá bằng mã HTTP**, kèm đối chứng hai đầu. Đã có ca
  giao 20 file, người dùng xoá 19;
- bề mặt cần đăng nhập hoặc cần giỏ có hàng thì phải thao tác tay. Với site bán hàng,
  phép kiểm cuối cùng luôn là **đặt thử một đơn**.

## Cách kiểm không được làm sập site

Đừng gọi site nhiều lượt bằng URL gắn `?cb=…`. Cache-busting ép cache bỏ qua nên mỗi
lượt là một lần chạy PHP + truy vấn DB đầy đủ. Đã có ca chính việc kiểm làm host hết
sạch kết nối MySQL (`max_user_connections`) ngay giữa lúc đang kiểm — xem
`cam-bay.md` mục 15. Dùng URL canonical, mỗi lần một request, có nghỉ giữa các lượt.

## Báo cáo

Với báo cáo dài (từ ~10 mục trở lên) hoặc bảng đối chiếu, dựng **Artifact** thay vì đổ
markdown vào khung chat — người đọc cần bấm được, tick được, chia sẻ được.

Mỗi mục phải có: **bằng chứng** (lệnh nào, dòng nào) · **việc cần làm** · **nhãn** nếu
là suy luận chứ không phải đo được. Cuối báo cáo luôn có mục **chưa kiểm được**, nói rõ
tại sao.

Không hứa cái chưa đo. `is_admin()` không làm trang nhanh hơn (OPcache); nói nó giảm
phạm vi thì đúng, nói nó tăng tốc thì sai và lần đo sau sẽ lộ.

## File trong skill

| File | Đọc khi nào |
|---|---|
| `references/cam-bay.md` | 18 cạm bẫy đã cắn thật, có mục lục — đọc mục giống tình huống đang gặp |
| `references/xac-minh.md` | trước khi tin bất kỳ phép kiểm nào; giải thích vì sao đếm tổng là mù |
| `scripts/quet_chet.py` | quét file/hàm/class chết — chỉ đọc |
| `scripts/go_ham.py` | gỡ hàm PHP an toàn, tự hiệu chuẩn bằng `php -l` |
| `scripts/go_css.py` | gỡ rule và vế selector chết, ba chốt cấu trúc |
| `scripts/doi_chung_live.py` | tầng 3 — đối chứng bằng HTML thật, và dò file đã xoá chưa |
| `scripts/dung_so_computed.py` | tầng 4 — dựng bộ so computed style |

Mọi script chạy bằng thư viện chuẩn Python, không cài thêm gì. Script nào ghi file cũng
theo lối **tạm → kiểm → đổi tên**, và từ chối ghi khi chưa qua hiệu chuẩn.
