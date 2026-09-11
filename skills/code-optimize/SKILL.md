---
name: code-optimize
description: >-
  Tối ưu và tái cấu trúc code theme/plugin WordPress SAU KHI đã dọn code chết — dựng code
  nodes và bản đồ kiến trúc, đối chứng với WordPress đang chạy, áp checklist kiến trúc, rồi
  biến đổi có đường lùi và có thước chứng minh tương đương hành vi. Dùng skill này khi người
  dùng nói tới: tối ưu code, tái cấu trúc, refactor theme, viết lại cho gọn, tách functions.php,
  đưa về module, vẽ kiến trúc code, code graph, code nodes, "code này nối với cái gì", "ai gọi
  hàm này", hook nào đăng ký ở đâu, "sửa xong có chắc không đổi hành vi không", hoặc cần bằng
  chứng một phép biến đổi không làm đổi gì. CHỈ chạy được sau khi wp-code-cleaner đã quét ra
  rỗng và đã có backup toàn cây — cổng đầu tiên tự kiểm điều đó và CHẶN nếu thiếu. KHÔNG dùng
  để xoá code chết (wp-code-cleaner), không dùng cho hiệu năng hạ tầng (wp-corewebvital), không
  dùng để deploy (wp-delivery).
---

# Tối ưu code sau khi dọn — có bản đồ, có đối chứng, có đường lùi

## Việc thật sự là gì

Dọn code chết là phép **XOÁ**: chứng minh nó an toàn là hỏi "thứ bị xoá còn ai gọi không".
Tối ưu là phép **BIẾN ĐỔI**: phải chứng minh hành vi **tương đương**, và đó là bài toán
khó hơn nhiều bậc. Bộ bốn tầng xác minh của `wp-code-cleaner` sinh ra cho phép xoá; đối
mặt sáu lỗi refactor điển hình, **năm trong sáu không tầng nào bắt được** — xem
`references/cam-bay-bien-doi.md` mục 1 để biết vì sao, từng tầng một.

Nên skill này dành phần lớn công sức cho **thước**, không cho việc viết lại. Ba câu chi
phối mọi bước:

1. **Graph tĩnh là GIẢ THUYẾT, runtime là SỰ THẬT.** Không tool tĩnh nào đang được bảo
   trì giải được cạnh `add_action('init','fn')` — đã kiểm bằng cách đọc source của chúng,
   không đọc mô tả. Đồ thị dựng từ text bị đối chứng với ADN chụp từ WordPress đang chạy,
   và khoảng lệch được **in ra**, không được ẩn. Một đồ thị sai mà tự tin tệ hơn không có
   đồ thị: nó làm người ta xoá code đang chạy với cảm giác có cơ sở.
2. **"Code ADN" là dấu vân tay CÓ THỨ TỰ của bề mặt runtime, không phải hash của cấu
   trúc.** Không tồn tại fingerprint bất biến dưới refactor bảo toàn hành vi cho PHP — đó
   là tương đương clone Type-4, ngành tự nhận chưa giải được. Hash thì đổi khi text đổi,
   nên diff của nó không nói gì. Hiệu tập trên bề mặt quan sát được thì nói được: một hook
   biến mất, một file thôi được nạp là tín hiệu thật.
3. **"Tinh gọn" không phải chỉ số, và là proxy có hướng sai.** Ít dòng hơn không làm trang
   nhanh hơn (OPcache). Tệ hơn: thước đếm dòng **thưởng cho việc xoá thứ đắt nhất** — khối
   chú thích kể lại ca hỏng đã trả giá, vòng `wp_style_is()` giữ thứ tự nạp, guard
   `defined('ABSPATH')`. Skill này **không hứa gọn**. Nó hứa: bề mặt hỏng im lặng nhỏ hơn,
   cấu trúc nhìn được, và một con số đo được khi áp dụng được (xem §5).

Nếu repo có `CLAUDE.md`/`AGENTS.md`, đọc trước — luật repo thắng skill này.

## Quy trình — thứ tự là bắt buộc, không được nhảy cóc

```
[0] cổng clean ─► [1] code nodes ─► [2] ADN runtime ─► [3] cổng graph
       │                                                      │
     CHẶN                                                   CHẶN
                                                              ▼
[6] Tầng 5 ◄─── [5] biến đổi (Mikado) ◄─── [4] bản đồ + checklist
     │
   diff ≠ ∅ → LÙI
```

Mỗi cổng là một script **fail-closed**: đóng thì exit khác 0 và nói rõ vì đâu. Không có
cờ `--force`. Muốn đi qua một cổng đang đóng thì sửa nguyên nhân, hoặc khai tường minh số
vùng mù bằng `--chap-nhan-mu` và chấp nhận các node đó là `NOT_TESTED`.

### [0] Cổng clean — `scripts/cong_clean.py`

```bash
python scripts/sao_luu.py luu --nguon "đường/dẫn/theme" --ra "backup/theme-2026-09-10"
python scripts/cong_clean.py --theme "đường/dẫn/theme" --backup "backup/theme-2026-09-10" --tien-to mytheme_
```

Hai điều kiện, thiếu một là chặn: (a) `quet_chet.py` quét lại phải ra **rỗng** — đúng
định nghĩa xong của cleaner, "lặp tới khi rỗng"; (b) có backup toàn cây và cây hiện tại
**khớp** manifest của nó — để nếu hỏng thì bản trong backup đúng là bản đang chạy.

**Backup phải là bản lấy từ HOST qua FTP, không dựng từ git.** Đã có hai ca chứng minh
git thiếu trên đúng loại codebase này: 20 file đang chạy thật chưa từng vào git, và 9
file nguồn bị `.gitignore` chặn — "không còn bản sao nào ngoài đĩa". Tải từ host trước,
rồi `luu`.

Cổng này là kết luận **tĩnh**. Cổng [3] đối chứng nó với runtime.

### [1] Code nodes — `scripts/code_nodes.py`

```bash
python scripts/code_nodes.py --theme "đường/dẫn/theme" --ra "run/graph.json"
```

Node: file · hàm · hook · handle asset. Cạnh có kiểu: `require` · `goi` · `khai_bao` ·
`dang_ky` · `phat` · `enqueue` · `phu_thuoc` · `template_part`. Mọi thứ không phân giải
được — hook tên biến, callback ghép chuỗi, require dựng bằng biến — **đếm vào
`dynamic_unresolved`**, không đoán. Con số đó là thước đo độ tin cậy của chính đồ thị;
nó khác 0 thì mọi kết luận "không ai gọi" phải đọc kèm nó.

Đặt **cạnh** `quet_chet.py`, không sửa nó: `quet_chet.py` trả lời "cái gì chết", file này
trả lời "cái gì nối với cái gì". Hai câu khác nhau.

### [2] ADN runtime — `tests/integration/adn-nen.php`

Boot WordPress + WooCommerce thật (drop-in SQLite, không cần MySQL/Docker), render, rồi
dump **bảy mặt có thứ tự**: file nạp · hook (priority + thứ tự trong bucket + callback →
`file:dòng`) · chuỗi fire · hàng đợi asset · chữ ký hàm kèm giá trị mặc định · HTML toàn
văn · và một mặt **tĩnh** đọc điểm truy cập superglobal kèm hàm sanitise bọc ngoài.

Mặt tĩnh phải có vì ca "mất lời gọi sanitise" **không để lại dấu runtime nào** trên request
không mang tham số đó. Đây là lý do Tầng 5 không thể chỉ gồm các mặt runtime.

**Chụp trên staging clone, không chạm site bán hàng.** Chính phép đo đã từng làm host hết
`max_user_connections` giữa lúc đang kiểm. Mỗi lần một request, có nghỉ, URL canonical,
không `?cb=`.

### [3] Cổng graph — `scripts/cong_graph.py`

```bash
python scripts/cong_graph.py --graph run/graph.json --adn run/adn.json --ra run/graph-trust.json
```

Hai chiều lệch, **không đối xứng** có chủ ý:

| Chiều | Nghĩa | Xử lý |
|---|---|---|
| runtime **có** mà tĩnh không thấy | node trông mồ côi nhưng **đang chạy** | **chí mạng** — exit 9 |
| tĩnh **nói có** mà runtime không có | họ lỗi `TAT_AM_THAM` | báo, phải xử lý |

Cổng đã được hiệu chuẩn bằng fixture cố tình chứa một hook tên biến và một callback ghép
chuỗi: cổng phải gọi đúng tên hai callback ấy, và phải **về 0 khi gỡ file gây ra chúng**.
Chiều thứ hai là phép kiểm mạnh — "cổng báo 2" mà không về 0 khi gỡ nguyên nhân thì có
thể là trùng hợp.

### [4] Bản đồ + checklist

Bản đồ dựng từ `graph.json` + `graph-trust.json` bằng `archify` (đã có trong môi
trường). Checklist ở `references/checklist.md` — mỗi cổng mang `because`, và **không một
cổng nào viện dẫn "WordPress best practice" làm thẩm quyền**, vì thẩm quyền đó không tồn
tại: Plugin Handbook tự tuyên bố "cố tình không kê đơn", Theme Handbook không có một dòng
về kiến trúc PHP, core để ngỏ ticket PSR-4 autoloader nhiều năm.

Xếp hạng việc cần làm theo **bề mặt hỏng im lặng** — endpoint `wp_ajax_nopriv_`/REST công
khai, file có trên đĩa mà loader không require, hook đăng ký trong `__construct` — **cấm
xếp theo số dòng**.

### [5] Biến đổi — theo Mikado Method, có hoàn tác gắn sẵn

Hình dạng quy trình lấy từ Mikado Method (Ellnestam & Brolund), vì nó khớp đúng yêu cầu
"vẽ code node trước khi tối ưu" — và vì nó có bước hoàn tác:

1. **Đặt mục tiêu** — phát biểu trạng thái đích.
2. **Thử** — sửa thật để xem cái gì vỡ. Chỗ vỡ là prerequisite.
3. **Vẽ** — ghi goal + prerequisite vào **Mikado Graph**. Graph là artefact duy nhất.
4. **Hoàn tác** — `sao_luu.py phuc_hoi` về trạng thái chạy được **trước khi** đi xử lý
   prerequisite. Trạng thái vỡ không được tồn tại qua bước kế.
5. Lặp 2–4 tới khi hết prerequisite.
6. **Hiện thực theo thứ tự ngược** — từ lá vào gốc.

Điều này hợp nhất hai thứ tưởng rời nhau: "vẽ code node" và "an toàn trên hết" là **cùng
một cơ chế** — graph là sản phẩm của việc thử-rồi-hoàn-tác, không phải của việc đọc rồi
đoán. Và nó khớp luật cũ của cleaner: gỡ logic thì đi **ngược** chiều với lúc thêm.

Fowler đặt điều kiện loại rất sắc: *"Nếu ai đó nói hệ thống bị hỏng vài ngày trong khi
họ đang refactor, khá chắc họ không đang refactor."* Trạng thái trung gian **phải chạy
được**. Không chạy được thì đó không phải refactor, và Tầng 5 sẽ đỏ.

Ghi file **chỉ qua `wp_safe_write.py`** của `wp-delivery` (atomic: backup → temp → check
→ rename, từ chối output rỗng hoặc sai cú pháp).

### [6] Tầng 5 — `tests/integration/tang5.py`

Chụp ADN trước, biến đổi, chụp sau, **hiệu phải rỗng** trên cả bảy mặt. Noise được **đo**
bằng hai lượt baseline, không đoán: lệch giữa hai lượt không đổi code là noise của chính
phép đo và bị trừ đi. Hai lượt baseline đã khác nhau thì `NOISE_QUA_LON` — phép đo chưa
dùng được, không phải "gần đúng".

Đã hiệu chuẩn trên WordPress 7.1 + WooCommerce thật: **6/6 ca tiêm bị bắt, và bị bắt bởi
đúng mặt đã dự đoán trước khi chạy**. Ca nào không bắt được thì lớp đó là `NOT_TESTED`,
không nâng thầm.

Diff khác rỗng ở một trường không nằm trong danh sách mask đã biện minh → **lùi ngay**
bằng `sao_luu.py phuc_hoi --ghi`, rồi chạy lại Tầng 5 để **chứng minh đã về đúng nền**.
"Đã copy xong" không phải "đã lùi xong".

## Chỉ số được phép hứa — và chỉ khi áp dụng được

Một con số, có nguồn, có cơ chế giải thích được, kiểm lại được tại chỗ:
`composer dump-autoload --classmap-authoritative`. Benchmark từ WordPress developer blog:
**176ms → 99ms (~44%)**, bỏ **916 lần `file_exists()` vô ích mỗi request**; chỉ 349/6.331
plugin (5,5%) đang dùng. Jordi Boggiano, tác giả Composer: *"authoritative autoloading is
the best solution I'd say."*

**Chỉ áp khi đích có Composer autoloader.** Không có thì N/A — không suy diễn sang trường
hợp khác, không thay bằng "gọn hơn".

## Ba loại câu hỏi phải hỏi chủ site, không tự quyết

Kế thừa nguyên từ `wp-code-cleaner`: màn hình cài đặt không điều khiển gì · tính năng có
vẻ tắt nhầm · **bất cứ gì đổi giao diện** — tối ưu code thì giao diện phải **không đổi
gì**; đổi là không còn là tối ưu. Thêm một loại của riêng lane này: **bật PSR-4 hay dùng
classmap** — vì PSR-4 không tương thích với quy ước tên file của WPCS, muốn dùng phải tắt
sniff chính thức. Đó là một quyết định, không phải chi tiết.

## Bề mặt KHÔNG kiểm được — nói ra, đừng để trống

- ADN là **lấy mẫu**: chỉ biết những gì tập URL chạm tới. Trang cần đăng nhập, cần giỏ có
  hàng, luồng gửi form/đặt đơn/email đi là `NOT_TESTED` cho tới khi có người thao tác tay.
  Site bán hàng: phép kiểm cuối vẫn là **đặt thử một đơn**.
- Mặt `fire` đã lọc họ hook `option_*`/`transient_*`/`alloptions` vì cache ấm làm lượt
  sau không fire lại. **Đánh đổi**: mặt này không trả lời "có đổi tập option được đọc không".
- Observable ngoài HTML body: header, redirect, `wp_mail`, ghi option, REST/AJAX.
- **Multisite** chưa phủ.

## File trong skill

| File | Đọc khi nào |
|---|---|
| `references/cam-bay-bien-doi.md` | trước khi tin bất kỳ tầng xác minh nào — vì sao 4 tầng cũ mù trước 5/6 lỗi |
| `references/checklist.md` | ở bước [4] — mỗi cổng mang `because`, không cổng nào viện dẫn thẩm quyền không tồn tại |
| `scripts/cong_clean.py` | cổng [0] — fail-closed |
| `scripts/code_nodes.py` | bước [1] — đồ thị giả thuyết, đếm vùng mù |
| `scripts/cong_graph.py` | cổng [3] — đối chứng tĩnh/runtime, hai chiều không đối xứng |
| `scripts/sao_luu.py` | backup toàn cây + phục hồi **đã diễn tập** (23 khẳng định, kể cả ca nguồn đã mất) |
| `../../tests/integration/adn-nen.php` | bộ chụp ADN |
| `../../tests/integration/tang5.py` | Tầng 5 + 6 ca hiệu chuẩn |

Mọi script dùng thư viện chuẩn Python. Script nào ghi file cũng theo lối **tạm → kiểm →
đổi tên**, mặc định là thử, và từ chối ghi khi chưa qua chốt.
