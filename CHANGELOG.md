# Nhật ký thay đổi

Theo [Semantic Versioning](https://semver.org/lang/vi/). Trước `1.0.0`, API dòng lệnh
và định dạng output còn có thể đổi.

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
