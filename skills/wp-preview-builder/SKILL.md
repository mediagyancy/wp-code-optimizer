---
name: wp-preview-builder
description: >-
  Dựng bản xem trước UI / prototype HTML rồi NGHIỆM THU nó bằng số, không bằng mắt. Dùng skill
  này bất cứ khi nào người dùng nói tới: dựng preview, xem trước giao diện, làm prototype, mockup
  HTML, "mở file này lên xem", "xem thử cái này trông thế nào", dựng bản demo một section, kiểm
  responsive, đo tràn ngang, "trên mobile bị lỗi", "chữ to quá trên điện thoại", kiểm ở 344/375/
  768/1280/1440, hoặc cần chứng minh một thay đổi giao diện không làm vỡ bố cục. Cũng dùng khi
  phải trả lời "lỗi này có sẵn từ trước hay do lần sửa này", và khi cần biết một bản xem trước
  đáng tin tới mức nào. KHÔNG dùng cho việc chọn phong cách thiết kế hay sinh ảnh mockup, không
  dùng cho tối ưu Core Web Vitals (đã có wp-corewebvital), không dùng cho deploy (wp-delivery).
---

# Dựng bản xem trước, rồi chứng minh nó là bằng chứng

## Việc thật sự là gì

Dựng một bản xem trước thì dễ: một file HTML, mở ra, nhìn. **Phần khó, và phần duy nhất
đáng tiền, là biết thứ mình đang nhìn có phải bằng chứng hay không.** Một bản xem trước
có thể trông hoàn hảo trong khi JavaScript chưa bao giờ chạy, CSS thật chưa bao giờ nạp,
và phép đo đang trả về số của một viewport khác với viewport mình tưởng.

Ba câu chi phối mọi bước dưới đây:

1. **"Nhìn ổn" không phải bằng chứng, và ảnh chụp cũng không.** Ảnh là bằng chứng *nhìn*
   và bắt buộc phải có — nhưng nó **không thay số**. Mọi kết luận responsive là một con
   số đọc từ probe, kèm ảnh cùng bề rộng đó.
2. **Thước chưa hiệu chuẩn thì mọi PASS đều là `NOT_TESTED`.** Phép đo tràn ngang ở đây
   đã từng trả **0** trên một trang tràn **296px**. Xem `references/cam-bay-preview.md`
   mục 1 trước khi tin bất kỳ con số nào.
3. **Bản xem trước tĩnh không chứng minh layout.** Không có CSS thật, dữ liệu thật,
   plugin thật thì cái được chứng minh chỉ là bố cục cô lập. Đó là `CONCEPT_PREVIEW`, và
   nó **không được nâng** thành "đã kiểm".

Nếu repo có `CLAUDE.md`/`AGENTS.md`, đọc trước — luật repo thắng skill này.

## Bốn nhãn, không được nâng cấp lẫn nhau

Đây là thứ phải gắn vào mọi phát biểu về một bản xem trước. Không gắn nhãn thì người
đọc mặc định hiểu là mức cao nhất, và đó là nơi lòng tin bị vay mượn.

| Nhãn | Đã chứng minh được gì | Chưa chứng minh được gì |
|---|---|---|
| `CONCEPT_PREVIEW` | bố cục cô lập, trong một file tự chứa | integration, specificity CSS, dữ liệu thật |
| `VISUAL_PASS` | đã xem trên hệ thật, đúng URL, đủ plugin và dữ liệu | hành vi sau khi purge cache, bề mặt cần đăng nhập |
| `PRODUCTION_VERIFIED` | đã xem trên canonical URL sau khi purge cache | bề mặt cần giỏ hàng, luồng nghiệp vụ |
| `NOT_TESTED` | — | nói rõ vì sao chưa thử được, đừng để trống |

## 1. Trước khi dựng — chốt bề mặt, và hỏi thiết bị thật

**Hỏi người dùng màn hẹp nhất họ thật sự dùng.** Đừng mặc định 375 là hẹp nhất. Bộ mốc
mặc định ở đây là **344 / 375 / 768 / 1280 / 1440**, và 344 có lý do cụ thể: màn ngoài
Galaxy Z Fold 6, màn hẹp nhất có thật trong tay người dùng Việt. Thêm **280** chỉ khi
cần biết giới hạn chịu đựng, không tính vào nghiệm thu.

**Chốt xem bản này sẽ là loại bằng chứng nào** trước khi dựng, vì nó quyết định cách
dựng. Muốn `CONCEPT_PREVIEW` thì một file tự chứa là đủ. Muốn `VISUAL_PASS` thì phải
dựng trên hệ thật — một file HTML rời **không bao giờ** lên được mức đó, bất kể nó
giống thật đến đâu.

## 2. Dựng — nội dung quyết định bản xem trước có dùng được hay không

**Dựng đủ trạng thái, không chỉ trạng thái đẹp.** Bố cục chỉ vỡ ở trạng thái xấu, nên
một bản xem trước chỉ có dữ liệu vừa đẹp là một bản xem trước chưa hỏi câu nào khó:

- **rỗng** — không có bản ghi nào;
- **dài bất thường** — tên sản phẩm 120 ký tự không dấu cách, tiêu đề 3 dòng;
- **đang tải** và **lỗi**;
- **số lớn** — giá 9 chữ số, `1.234.567.890 ₫` (tiếng Việt dài hơn tiếng Anh ~30%).

**Một nguồn cho cả hai màn.** Không dựng hai nhánh song song desktop/mobile — chúng
lệch âm thầm, và lúc lệch thì không ai biết nhánh nào là đúng.

**Chọn breakpoint bằng cách thu dần cho tới khi nội dung gãy**, không theo tên có sẵn.
`sm:` của Tailwind là 640px và chẳng liên quan gì tới bề rộng mà thanh tìm kiếm của
anh thật sự gãy — đã có ca ẩn chữ bằng `hidden sm:inline` đặt mốc sai hẳn chỗ.

**Tự chứa hay nhiều file?** Quy tắc: tự chứa khi bản xem trước chỉ cần chứng minh bố
cục; nhiều file khi phải dùng **đúng** file CSS/JS production. Nhiều file thì asset
tham chiếu `../` ra ngoài thư mục gốc server sẽ bị **403**, và lúc đó trang vẫn hiện
nhưng **thiếu CSS** — rồi vẫn đo ra số. Thấy trang trông trơ thì kiểm 403 trước khi
kết luận gì về layout, và chạy lại với thư mục gốc cao hơn.

## 3. Mở — chỉ có MỘT đường cho trang sống

**`http://127.0.0.1`. Không phải `file://`.** Đây không phải sở thích; bốn bề mặt đã
được đo và ba trong bốn cho ra thứ KHÔNG phải trang sống — xem
`references/cam-bay-preview.md` mục 2 để biết từng bề mặt ra cái gì.

Ngay sau khi mở, **kiểm `location.protocol` phải là `"http:"`**. Thấy `"data:"` hoặc
thấy báo "No site is open in this tab" là đang nhìn một thứ không chạy JavaScript.

Mở bằng server tĩnh cục bộ, chỉ lắng nghe 127.0.0.1, chỉ GET/HEAD, không phục vụ ra
ngoài thư mục gốc. Server báo **port thật** trong output — dùng đúng số đó, **đừng
đoán**, vì port bận thì nó tự lên port kế tiếp.

Trong môi trường Claude Code: pane chưa mở thì gọi `navigate` **đứng một mình** (lúc đó
`tabs_create` và gộp lệnh sẽ lỗi). **Không dùng Claude-in-Chrome để đo co giãn** —
`resize_window` của nó không đổi viewport.

## 4. Đo — một công thức, và nó không phải công thức ai cũng viết

```
tràn ngang = max(documentElement.scrollWidth, body.scrollWidth) − documentElement.clientWidth
```

**Cấm dùng `window.innerWidth`** ở bất kỳ script đo layout nào. Lý do là một con số:
công thức dùng `innerWidth` trả về **0** trên ca tràn **296px** đã biết, vì trong giả
lập mobile `innerWidth` phình theo nội dung nên hai số cùng phình và phép trừ triệt
tiêu. Ràng buộc này được ghim bằng khẳng định trong bộ test — khai báo trong file CI, chưa chạy trên runner:
`scripts/quyet_dinh_tran.py`. Muốn quay về `innerWidth` thì phải làm đỏ một test có tên.

**Hai biên khác nhau, và phải biết là chúng khác nhau:**

| Mức | Biên | Vì sao |
|---|---|---|
| trang | **0px** — tràn 1px vẫn là tràn | hiệu của hai phép đo nguyên, không có chỗ cho làm tròn |
| phần tử | **1px** | `getBoundingClientRect()` trả số thực; không có biên thì mọi trang đều có thủ phạm ảo ở mép |

Hệ quả phải nói ra: một trang có thể báo tràn 0.4px ở mức trang mà **không liệt được
phần tử nào** — đó là làm tròn, không phải bỏ sót.

**Lọc bốn nguồn báo động giả, và IN RA số đã lọc.** Bốn nguồn này đã làm sai bốn lần:
drawer `position:fixed` đang đóng · slide trong track `overflow:hidden` · phần tử ẩn
(`visibility:hidden` / `opacity:0` / `aria-hidden`) · viewport = 0 lúc đo. Lọc mà không
in số đã lọc thì người đọc tưởng probe bỏ sót; không lọc thì ra dương tính giả hàng loạt.

**Thứ tự đọc kết quả:** con số tràn ngang trước → rồi mới tới danh sách thủ phạm. Số
phần tử "đã lọc vì vô hại" lớn là **bình thường** với trang có carousel hoặc drawer.

**Viewport = 0 thì KHÔNG kết luận.** Đợi một giây rồi đo lại. Đã có ca báo "tràn 268px"
hoàn toàn sai chỉ vì đo lúc viewport chưa sẵn sàng.

Trên `chrome-devtools` MCP: dùng `emulate` chứ **không** `resize_page` — `resize_page`
đổi cửa sổ hệ điều hành và Chrome không xuống dưới ~500px, nên yêu cầu 344px **im lặng**
bị kẹp lại thành 500px rồi vẫn trả số. Và `emulate` phải chạy **TRƯỚC** khi trace.

Đo xong thì trả viewport về desktop.

## 5. Nghiệm thu — bảng số, và một câu bắt buộc

| bề rộng | tràn ngang | thủ phạm đầu tiên | chữ nhỏ nhất | vùng chạm < 40px |
|---|---|---|---|---|
| 344 | | | | |
| 375 | | | | |
| 768 | | | | |
| 1280 | | | | |
| 1440 | | | | |

Kèm ảnh chụp mỗi bề rộng. Và mỗi lỗi giao diện phải trả lời:

> **Lỗi này có sẵn từ trước, hay do lần sửa này?**

Cách duy nhất trả lời là **đo bản chưa sửa để đối chứng**. Đã có ca `bodyOverflowX = 101`
phải tách bạch đúng câu này — nó là lỗi drawer có sẵn trên production, không phải do
phần vừa thêm. Trả lời sai câu này một lần là mất lòng tin cho mọi lần sau.

**Ngoài trục ngang**, nghiệm thu còn gồm: tương phản ≥ 4.5:1, cỡ chữ nhỏ nhất, vùng chạm
≥ 40px — nhưng **chỉ tính phần tử tương tác thật**, và bỏ qua phần tử tương tác lồng
trong một phần tử đã ≥ 40×40 (icon 20px trong nút 44px không phải lỗi).

**Chữ to bất thường trên mobile thường không phải lỗi `font-size`** mà là hệ quả của
tràn: một số cứng ở đâu đó đẩy layout rộng ra rồi trình duyệt phóng chữ theo. Chữa gốc
trước, đừng chữa `font-size`.

## 6. Giao cho người dùng

Bản xem trước mà người dùng phải tự mở trình duyệt, tự dán đường dẫn là **chưa giao**.
Đưa đường bấm được: một khối lệnh mở đúng chỗ, hoặc một Artifact nếu đó là báo cáo
nhiều mục. Và nếu trang đã nằm trên `127.0.0.1` thì nói rõ nó **sống tới khi nào** —
server tự tắt sau một khoảng không ai dùng.

## Skill này KHÔNG làm

- **Chọn phong cách thiết kế.** Đó là việc của các skill design; skill này lo phần dựng
  và nghiệm thu, không lo thẩm mỹ.
- **Sinh ảnh mockup.** Ảnh không đo được.
- **Tối ưu Core Web Vitals** — `wp-corewebvital`. Và lưu ý `lighthouse_audit` của
  chrome-devtools MCP **không có phần performance**, nên chạy nó rồi tưởng đã đo CWV là
  một bước nhầm hay gặp.
- **Render PHP/template engine.** Server tĩnh chỉ phục vụ file tĩnh. Cần PHP thật thì
  phải dựng trên hệ thật, và lúc đó nhãn cao nhất đạt được là `VISUAL_PASS` trở lên.
- **Hứa tốc độ chưa đo.** Xem `wp-code-cleaner` về cùng kỷ luật này.

## File trong skill

| File | Đọc khi nào |
|---|---|
| `references/cam-bay-preview.md` | trước khi tin bất kỳ con số nào — các ca hỏng kèm số đo thật |
| `scripts/quyet_dinh_tran.py` | công thức tràn ngang, tách khỏi trình duyệt để CI ghim được |
| `scripts/probe.js` | probe chạy trong trang: tràn ngang, thủ phạm, chữ nhỏ nhất, vùng chạm |
