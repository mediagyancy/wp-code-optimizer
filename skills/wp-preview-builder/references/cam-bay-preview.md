# Cạm bẫy khi dựng và đo bản xem trước

Mỗi mục ở đây là một ca **đã hỏng thật**, kèm con số. Luật không có ca hỏng của nó là
luật người ta sẽ lách, nên số được giữ nguyên.

Đặc điểm chung của cả tám mục, và là lý do chúng đáng chép lại: **chúng đều cho ra
ÂM TÍNH GIẢ**. Không cái nào làm tool báo lỗi ầm ĩ. Chúng làm tool báo *sạch*. Một phép
đo hỏng theo hướng báo lỗi thì người ta đi sửa; hỏng theo hướng báo sạch thì người ta
đóng việc.

---

## 1. `innerWidth` phình theo nội dung — phép đo tràn ngang trả 0 trên ca tràn 296px

**Số đo:** viewport đặt 344px, nội dung rộng 640px. Khi đó
`documentElement.clientWidth = 344` nhưng `window.innerWidth = 640`, và
`scrollWidth = 640`.

Công thức cũ `max(scrollWidth) − innerWidth` = `640 − 640` = **0**.
Công thức đúng `max(scrollWidth) − clientWidth` = `640 − 344` = **296**.

**Vì sao nó là cạm bẫy và không phải một lỗi thường:** số 0 ấy **trông y hệt** số 0 của
một trang sạch. Không có cảnh báo, không có ngoại lệ, không có gì lệch. Phép trừ hai số
cùng phình ra thì triệt tiêu, và kết quả triệt tiêu trông giống kết quả tốt.

Xảy ra trên **cả hai** bề mặt đo: Browser pane và `chrome-devtools` MCP — nên không thể
chữa bằng cách đổi công cụ.

**Luật:** cấm `window.innerWidth` trong mọi script đo layout. Probe vẫn *báo cáo* giá
trị `innerWidth` để đối chiếu, nhưng không dùng nó để tính.

**Đã ghim bằng khẳng định:** `scripts/quyet_dinh_tran.py` giữ cả hai công thức và bắt
buộc phải tồn tại một ca mà chúng cho kết quả khác nhau. Bộ hiệu chuẩn nào không phân
biệt được hai công thức thì không kiểm gì cả — đó là lý do ca 296px nằm trong code chứ
không nằm trong tài liệu.

---

## 2. `file://` trong Browser pane không cho trang sống — bốn bề mặt, ba cái vô dụng

Đã đo từng bề mặt, không suy luận:

| Bề mặt | Kết quả thật |
|---|---|
| Claude-in-Chrome + `navigate file://` | URL bị viết lại thành `https://file:///…` → trang lỗi |
| Browser pane + file **ngoài** project | chỉ ra **ảnh tĩnh**; `javascript_tool` báo "No site is open" |
| Browser pane + file **trong** project | nhúng thành **`data:` URL**; asset tương đối vỡ |
| Browser pane + `http://127.0.0.1` | **trang sống** — `clientWidth = 344` khi resize 344 |

**Vì sao là âm tính giả:** ba bề mặt đầu vẫn *hiện ra một cái gì*. Người xem kết luận
"đã mở xem rồi". Nhưng JavaScript không chạy và CSS tương đối không nạp, nên cái được
xem **không phải** trang cần đo.

**Luật:** chỉ đo qua `http://127.0.0.1`. Ngay sau khi mở, kiểm
`location.protocol === "http:"`.

---

## 3. `resize_page` không xuống dưới ~500px — yêu cầu 344px bị kẹp im lặng

`resize_page` của `chrome-devtools` MCP đổi **cửa sổ hệ điều hành**, và Chrome không cho
cửa sổ hẹp hơn khoảng 500px. Yêu cầu 344px bị kẹp lại thành ~500px — **không có lỗi,
không có cảnh báo**, và probe vẫn trả về một bộ số đầy đủ.

**Vì sao là âm tính giả:** ở 500px trang có thể sạch hoàn toàn trong khi ở 344px nó vỡ.
Báo cáo ghi "đã kiểm 344" mà thực tế chưa bao giờ đo ở 344.

**Luật:** dùng `emulate { viewport: "344x800x1,mobile,touch" }`, không dùng `resize_page`.
Và luôn đọc lại `clientWidth` từ probe để xác nhận viewport đúng là số mình yêu cầu —
đừng tin rằng lệnh resize đã có tác dụng.

---

## 4. Bốn nguồn báo động giả — "đã sai bốn lần"

48 phần tử được báo là "chọc ra ngoài" từng **đều** là drawer `position:fixed` đang
đóng. Một lần khác báo "tràn 268px" **hoàn toàn sai** vì viewport = 0 lúc đo.

Bốn nguồn phải lọc:

1. `position: fixed` — drawer/overlay đang đóng, nằm ngoài viewport là đúng thiết kế;
2. slide/carousel nằm trong track `overflow: hidden` (phải **leo cây tổ tiên** để thấy);
3. phần tử ẩn: `visibility: hidden`, `opacity: 0`, trong `[aria-hidden="true"]`;
4. viewport = 0 — không phải lọc mà là **dừng**, đo lại sau một giây.

**Nhưng lọc mà không in số đã lọc cũng là một cạm bẫy khác:** người đọc thấy danh sách
thủ phạm rỗng thì tưởng probe bỏ sót. Nên phải in ra "đã lọc N phần tử vì vô hại" kèm
vài ví dụ, và nói rõ rằng N lớn là **bình thường** với trang có carousel hoặc drawer.

---

## 5. `transferSize = 0` âm thầm — trang 710KB đo ra 4KB

**Số đo (09/09/2026, trên một site thật):** 57 trong 60 resource có `transferSize = 0`,
trong đó 43 cái có `deliveryType: "cache"`. Cộng lại ra **4 KB** cho một trang thật
**≥ 710 KB**.

Nguyên nhân: resource lấy từ cache, hoặc cross-origin không có `Timing-Allow-Origin`,
thì API trả `transferSize = 0` — không phải lỗi, là đúng đặc tả.

**Vì sao là âm tính giả:** 4 KB là một con số *hợp lệ về hình thức*. Nó cộng được, nó
tròn trịa, nó sai một bậc độ lớn, và không có dấu hiệu nào. Đây đúng là "cân bằng giả
trông y hệt cân bằng thật".

**Luật:** đo page weight phải trên **cache nguội** (`isolatedContext`), và **đọc
`deliveryType` TRƯỚC mọi con số**. Báo dạng *"≥ X KB, còn N resource bên thứ ba không đo
được"* — đừng gộp thành một con số gọn. Có bên thứ ba thì chạy **tối thiểu hai lần**;
cùng một trang cùng điều kiện từng ra 9 rồi 11 domain ngoài.

---

## 6. `lighthouse_audit` không có phần performance

Mô tả tool ghi rõ *"This excludes performance"* — nó trả a11y, SEO, best-practices, và
**không** trả chỉ số hiệu năng.

**Vì sao là âm tính giả:** chạy lighthouse xong, thấy điểm cao, kết luận "đã đo CWV".
Thực tế chưa đo gì về tốc độ.

**Luật:** đo CWV theo đúng thứ tự `new_page` → `emulate` → `performance_start_trace` →
`performance_analyze_insight`. `emulate` **phải** trước trace, nếu không là đang đo trên
máy dev mạnh và mạng nhanh — số đẹp và vô nghĩa.

---

## 7. Preview tĩnh không thấy được lớp lỗi specificity

**Ca thật:** nút submit của form ra màu xanh `#0d61ad` không như thiết kế, vì một rule
cũ `form .fieldbox input.wpcf7-submit` (specificity 0,2,2) thắng selector mới (0,2,1).

**Vì sao là âm tính giả:** trong bản xem trước tĩnh, selector mới thắng vì không có
rule cũ nào ở đó. Bản xem trước hiện **đúng màu thiết kế**. Lỗi chỉ lộ ra khi trang nạp
`main.css` thật. Đọc file nguồn cũng không thấy — phải đo trên trang đã nạp đủ CSS.

**Luật:** bản xem trước tĩnh là `CONCEPT_PREVIEW`. Mọi phát biểu về màu, khoảng cách,
hay thứ tự lớp chỉ lên được `VISUAL_PASS` sau khi đo trên hệ thật với đúng bộ CSS
production.

---

## 8. Mốc breakpoint theo tên thư viện, không theo chỗ gãy thật

`sm:` của Tailwind là **640px**. Bề rộng mà thanh tìm kiếm thật sự gãy là một số khác.
Ẩn chữ bằng `hidden sm:inline` đặt mốc sai hẳn chỗ: ở khoảng giữa hai số, giao diện vừa
mất chữ vừa chưa hết chật.

**Luật:** chọn breakpoint bằng cách **thu dần cho tới khi nội dung gãy**, rồi đặt mốc ở
đó. Tên có sẵn trong thư viện là tiện lợi cú pháp, không phải kết luận về nội dung.

---

## Những chỗ chưa có luật — nói ra để không ai tưởng là đã phủ

- **Trục dọc.** Toàn bộ kỷ luật ở trên là trục ngang. `height: 800` là một hằng số
  không có lý do được ghi lại; chưa có luật nào về fold, về scroll dọc, về chiều cao
  viewport.
- **Tương phản.** Nghiệm thu yêu cầu ≥ 4.5:1 nhưng probe **không đo** tương phản, và
  chưa có công cụ nào được chỉ định.
- **Dark mode / `prefers-color-scheme`.** Không có luật.
- **Hot-reload.** Không có; sửa rồi phải bấm F5. Chưa có luật về nhịp sửa → đo lại.
- **Artifact và widget inline.** Chúng nằm trong phạm vi responsive nhưng server tĩnh
  cục bộ không phục vụ được chúng, nên chưa có đường đo.
