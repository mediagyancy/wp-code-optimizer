# Checklist kiến trúc — mỗi cổng mang lý do, không cổng nào viện dẫn thẩm quyền không tồn tại

## Đọc trước: không có chuẩn kiến trúc WordPress có thẩm quyền

Plugin Handbook tự tuyên bố: *"The architecture, or code organization, you choose for your
plugin will likely depend on the size of your plugin"*, và *"there's little benefit in
engineering complex classes"* cho plugin nhỏ. Trang đó liệt kê đúng ba mẫu kiến trúc và
**không một chữ** về singleton, DI, service provider, PSR-4 hay Composer. Theme Handbook mục
advanced-topics **không có một dòng** về kiến trúc code PHP. Core để ngỏ ticket PSR-4
autoloader (#21300, #43979) nhiều năm.

Hệ quả: mọi cổng dưới đây là **quy ước của repo này**, phải tự biện minh bằng `because`, và
**cấm** viện dẫn "WordPress best practice" làm thẩm quyền — một người soát kỹ có quyền bác
lập luận đó, và họ đúng.

Hình thức mỗi cổng lấy từ hai chỗ: *Mechanics* của Fowler (bước nhỏ có thứ tự, mỗi bước kết
ở một trạng thái kiểm được) và `because('<lý do>')` của PHPArkitect.

## Phát biểu cổng cho đúng: BẢO TOÀN, không phải CẢI THIỆN

Một fitness function khẳng định **bảo toàn một đặc tính**, không khẳng định **cải thiện một
proxy**. Phát biểu "tập file nạp, chuỗi hook fire, bản đồ priority, tập handle — KHÔNG ĐỔI"
thì không gian được bằng việc xoá guard hay xoá chú thích. Phát biểu "ít dòng hơn" thì gian
được ngay.

---

## A. Cổng bảo toàn — Tầng 5 đo tự động, diff phải rỗng

| # | Cổng | because |
|---|---|---|
| A1 | Tập file theme được nạp, **theo thứ tự**, không đổi | thứ tự nạp quyết định hàm nào có trước hàm nào; `require` dời chỗ là đổi hành vi dù text y nguyên |
| A2 | Bản đồ `$wp_filter`: (hook, priority, **thứ tự trong bucket**, callback) không đổi | WordPress chạy callback cùng priority theo đúng thứ tự đăng ký; dời hook sang file khác không đổi tập, không đổi markup, nhưng đổi thứ tự chạy — 4 tầng cũ đều mù |
| A3 | Chuỗi hook fire trong giai đoạn render không đổi | bắt `get_template_part` dời điểm trong lifecycle; **đánh đổi đã khai**: họ `option_*`/`transient_*` bị lọc vì cache ấm |
| A4 | Hàng đợi script/style (handle + thứ tự) không đổi | part enqueue style mà dời sang sau `wp_head()` là style không bao giờ ra `<head>` — site không lỗi, không cảnh báo, chỉ mất style |
| A5 | Chữ ký hàm: tên → tham số có thứ tự kèm **giá trị mặc định** không đổi | đổi mặc định `1.1 → 1.2` không đổi một byte HTML khi mọi lời gọi truyền đủ tham số; là quả mìn cho lời gọi sau; trên site bán hàng nghĩa là giá sai |
| A6 | Mỗi điểm đọc `$_GET`/`$_POST`/`$_REQUEST` giữ nguyên hàm sanitise bọc ngoài | mất `esc_html` không để lại dấu runtime nào trên request không mang tham số đó — phải đo **tĩnh** |
| A7 | HTML toàn văn từng loại trang, sau mask đã biện minh, không đổi | so **tập** class thì mù trước đổi thứ tự; phải so toàn văn theo byte. Mỗi mask là một vùng mù bằng cấu trúc nên phải mang lý do |

## B. Cổng cấu trúc — đo trên graph, chấm theo bề mặt hỏng im lặng

| # | Cổng | because |
|---|---|---|
| B1 | `functions.php` chỉ chứa guard, hằng số nền, `require`, và một lời gọi khởi động (≤ 80 dòng thực thi) | `add_action` của tính năng, AJAX handler, logic giá trong file nạp là đặt sai chỗ — luật đã có của cleaner, không phải luật mới |
| B2 | **Không có hook đăng ký trong `__construct`** | điểm hội tụ **duy nhất** của cả hệ sinh thái (10up, Gary Jones, Bright Nucleus, Inpsyde modularity — bốn nguồn độc lập, cùng tên method `run()`): khởi tạo object là hook đã nối ngay, nên không thể assert trạng thái "trước"; vượt quá điểm này thì **không có đồng thuận** |
| B3 | Không có file trong `inc/` nằm trên đĩa mà loader không `require` | họ lỗi `TAT_AM_THAM`: tính năng không chạy, `php -l` sạch, không một dòng lỗi, guard `function_exists` làm nó suy biến êm — `doi_chung_live.py --loader` đã đo được từ v0.4.0 |
| B4 | Mỗi endpoint `wp_ajax_nopriv_*` / `rest_api_init` / `admin_post_nopriv_*` có chủ: biết ai gọi, từ giao diện nào | endpoint công khai sống sót sau khi giao diện chết là **bề mặt tấn công**, không chỉ là code thừa |
| B5 | `dynamic_unresolved` của đồ thị tĩnh được **in ra** cạnh mọi kết luận "không ai gọi" | đồ thị sai mà tự tin tệ hơn không có đồ thị |
| B6 | Không `posts_per_page => -1`; không `post__not_in`; `no_found_rows => true` khi không phân trang; không ghi DB ở trang frontend | luật cứng của 10up, có lý do nghiệp vụ rõ (truy vấn không biên trên bảng lớn) — ghi nguồn là 10up, không ghi là "chuẩn WordPress" |
| B7 | Không Heredoc/Nowdoc trong template | phá late escaping (10up); và phá luôn phép cắt theo cân bằng ngoặc của chính bộ công cụ này |
| B8 | Đổi theme mặc định hoặc tắt functionality plugin **không** gây lỗi | luật decoupling của 10up: "every piece of code should be decoupled and use standard WordPress paradigms (hooks)" |

## C. Hai bẫy refactor giết im lặng — cổng cứng, không có ngoại lệ

| # | Cổng | because |
|---|---|---|
| C1 | Classic theme **không thêm** `templates/*.html` nếu chưa kiểm `locate_block_template()` | từ WP 5.8, block template có specificity bằng hoặc cao hơn sẽ **thắng** template PHP, PHP thành fallback — một classic theme thêm dần file `.html` có thể **âm thầm vô hiệu hoá chính template PHP của nó**. Regression đã ghi: block template của parent theme thắng PHP của child theme (Trac #54515 — chưa xác minh tại nguồn vì Trac trả 403) |
| C2 | Handle có `strategy => 'defer'/'async'` **không** được kèm `wp_add_inline_script()` ở vị trí `after` | verbatim Make Core: *"if a given script handle contains inline scripts in the after position, this script will be assumed to be blocking and any intended strategy such as defer/async will be removed"*. `after` là mặc định. Không có warning. Và nó **lan theo cả cây dependency**: "A handle will never inherit a strategy that is 'more strict' than the one intended" — defer không xuống async, nhưng **lên blocking** |

## D. Autoload — một quyết định, không phải chi tiết

| # | Cổng | because |
|---|---|---|
| D1 | Nếu dùng Composer autoloader: `--classmap-authoritative` | **chỉ số duy nhất có số đo** trong cả checklist: 176ms → 99ms (~44%), bỏ 916 `file_exists()` vô ích mỗi request (WordPress developer blog, issue #468, từ Discussion #457 — không ai phản đối). Jordi Boggiano: *"authoritative autoloading is the best solution I'd say"*. **Chỉ áp khi có Composer autoloader; không có thì N/A, không suy diễn** |
| D2 | Chọn PSR-4 **hay** classmap là câu hỏi cho chủ site | PSR-4 **không tương thích** quy ước tên file `class-ten-class.php` của WPCS; muốn dùng phải tắt sniff chính thức (`strict_class_file_names = false`). Một maintainer đề xuất classmap ngay dưới bài official. Đây là đánh đổi, không phải chi tiết râu ria |

## E. Điều kiện loại — Fowler

- *"Don't refactor unless you think you will recoup your investment later by quicker work."*
  Không có baseline cho "chi phí sửa lần sau" thì không có cách phân biệt refactor thành
  công với refactor làm hỏng. Đo trước, hoặc đừng làm.
- *"If somebody talks about a system being broken for a couple of days while they are
  refactoring, you can be pretty sure they are not refactoring."* (Refactoring Malapropism,
  2004). Trạng thái trung gian **phải chạy được**. Mikado bước 4 — hoàn tác — tồn tại để
  bảo đảm điều này.

## Những gì checklist này KHÔNG chứa

- Không có cổng về **số dòng**. Cố ý. Xem `cam-bay-bien-doi.md` mục 5.
- Không có cổng về **tốc độ** ngoài D1. OPcache làm chi phí nạp PHP gần bằng 0; đòn hiệu
  năng thật của WordPress nằm ở OPcache bật, object cache persistent, và không để inline
  script phá defer — việc của `wp-corewebvital`.
- Không có cổng về **container / DI / service provider**. Không có đồng thuận, và tài liệu
  chính thức không đứng về bên nào. Handbook: "little benefit in engineering complex
  classes" cho plugin nhỏ.
