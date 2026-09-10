/* probe đo bố cục — dán NGUYÊN file này vào một công cụ chạy JavaScript trong trang.
 *
 *   · Browser pane của Claude Code:  mcp__Claude_Browser__javascript_tool
 *   · chrome-devtools MCP:           evaluate_script, SAU khi đã `emulate` viewport,
 *                                    bọc trong `() => { ... }` nếu tool đòi function
 *
 * BẮT BUỘC đọc trước khi tin output:
 *
 *   1. Bề rộng viewport lấy từ `documentElement.clientWidth`, KHÔNG lấy từ
 *      `window.innerWidth`. Đây là cả lý do file này tồn tại. Trong giả lập mobile,
 *      `innerWidth` PHÌNH THEO NỘI DUNG: đặt viewport 344px mà nội dung rộng 640px thì nó
 *      báo 640 — đúng bằng bề rộng cuộn. Lấy nó làm số bị trừ thì hiệu triệt tiêu và phép
 *      đo trả về 0 trên một trang tràn 296px, mà số 0 ấy trông y hệt số 0 của một trang
 *      sạch. Đã xảy ra trên CẢ Browser pane lẫn chrome-devtools MCP. `innerWidth` vẫn
 *      được BÁO CÁO ở output để đối chiếu, nhưng không tham gia phép tính nào.
 *
 *      Ràng buộc này có khẳng định canh trong CI (`tests/test_preview.py`), và phép canh
 *      đó nghiêm tới mức KHÔNG cho phép tái hiện công thức sai dưới dạng công thức —
 *      kể cả trong chú thích. Bản verbatim của dòng sai lịch sử sống ở đúng hai nơi: ca
 *      hiệu chuẩn trong file test, và `references/cam-bay-preview.md` mục 1.
 *
 *   2. `viewport = 0` thì KHÔNG kết luận. Ngay sau khi trang nạp, pane có thể chưa có
 *      kích thước. Đã có ca báo "tràn 268px" hoàn toàn sai vì đo lúc ấy. Gặp
 *      `LOI_PHEP_DO` thì đợi một giây rồi đo lại, đừng đọc các số khác.
 *
 *   3. `protocol` phải là `"http:"`. Thấy `"data:"` là đang xem một bản nhúng tĩnh —
 *      JavaScript không chạy, CSS tương đối không nạp, và mọi số đo thuộc về một trang
 *      khác với trang cần đo.
 *
 *   4. Đọc `TRAN_NGANG` TRƯỚC, rồi mới tới `thu_pham_that`. `da_loc_bo_vi_vo_hai` lớn là
 *      BÌNH THƯỜNG với trang có carousel hoặc drawer — con số đó được in ra chính vì nếu
 *      không in thì danh sách thủ phạm rỗng sẽ bị đọc thành "probe bỏ sót".
 *
 * Công thức ở đây được ghim bằng khẳng định chạy trong CI: `scripts/quyet_dinh_tran.py`.
 * Đổi sang `innerWidth` sẽ làm đỏ một test có tên.
 */
(() => {
  const PROBE_VERSION = "wp-preview-builder/1.0.0";

  // Biên ở hai mức KHÁC NHAU, có chủ ý — xem SKILL.md mục 4.
  //   mức trang:   0px, tràn 1px vẫn là tràn (hiệu của hai phép đo nguyên)
  //   mức phần tử: 1px, vì getBoundingClientRect() trả số thực
  const BIEN_PHAN_TU = 1;

  const de = document.documentElement;
  const body = document.body;
  const vw = de.clientWidth;

  if (!vw) {
    return {
      PROBE_VERSION,
      LOI_PHEP_DO: "viewport = 0 — mọi số đo vô nghĩa. Đợi 1 giây rồi đo lại.",
      protocol: location.protocol,
    };
  }

  const scrollWidth = Math.max(de.scrollWidth, body.scrollWidth);
  const tranNgang = Math.max(0, scrollWidth - vw);
  const px = (v) => Math.round(v * 10) / 10;

  const sel = (el) => {
    const id = el.id ? `#${el.id}` : "";
    const cls = (el.className && typeof el.className === "string")
      ? "." + el.className.trim().split(/\s+/).slice(0, 2).join(".")
      : "";
    return `${el.tagName.toLowerCase()}${id}${cls}`.slice(0, 60);
  };

  /* Leo cây tổ tiên tìm khối cắt. Không leo thì mọi slide của carousel đều thành thủ
     phạm — chúng nằm ngoài viewport là đúng thiết kế, vì track bọc ngoài có
     overflow:hidden. Đây là một trong bốn nguồn báo động giả đã làm sai bốn lần. */
  const catBoi = (el) => {
    for (let p = el.parentElement; p && p !== body; p = p.parentElement) {
      const cs = getComputedStyle(p);
      if (/hidden|auto|scroll|clip/.test(cs.overflowX) ||
          /hidden|auto|scroll|clip/.test(cs.overflow)) return sel(p);
    }
    return null;
  };

  const thuPham = [], daLoc = [];
  for (const el of document.querySelectorAll("body *")) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    if (r.right <= vw + BIEN_PHAN_TU && r.left >= -BIEN_PHAN_TU) continue;
    const cs = getComputedStyle(el);
    const cat = catBoi(el);
    const boQuaVi =
      cs.position === "fixed" ? "fixed (drawer/overlay đang đóng)" :
      cs.visibility === "hidden" ? "visibility:hidden" :
      cs.opacity === "0" ? "opacity:0" :
      el.closest("[aria-hidden='true']") ? "aria-hidden" :
      cat ? `bị cắt bởi ${cat}` : null;
    const ghi = { el: sel(el), left: px(r.left), right: px(r.right), w: px(r.width) };
    if (boQuaVi) daLoc.push({ ...ghi, bo_qua_vi: boQuaVi }); else thuPham.push(ghi);
  }
  thuPham.sort((a, b) => b.right - a.right);

  /* Vùng chạm: ngưỡng 40px, nhưng BỎ QUA phần tử tương tác lồng trong một phần tử
     tương tác đã đủ lớn — một icon 20px bên trong một nút 44px không phải lỗi, và
     không bỏ qua thì mọi nút có icon đều bị báo. */
  const TUONG_TAC = "a[href], button, input, select, textarea, [role='button'], [onclick]";
  const vungChamNho = [];
  for (const el of document.querySelectorAll(TUONG_TAC)) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === "hidden" || cs.display === "none") continue;
    const ngoai = el.parentElement && el.parentElement.closest(TUONG_TAC);
    if (ngoai) {
      const or = ngoai.getBoundingClientRect();
      if (or.height >= 40 && or.width >= 40) continue;
    }
    if (r.height < 40 || r.width < 40) {
      vungChamNho.push({ el: sel(el), w: px(r.width), h: px(r.height) });
    }
  }

  /* Cỡ chữ nhỏ nhất: chỉ tính phần tử có text node TRỰC TIẾP. Không lọc thế thì mọi thẻ
     bọc ngoài cũng được tính và kết quả là font-size của thẻ bọc, không phải của chữ. */
  let chuNhoNhat = 99, chuNhoNhatO = "";
  for (const el of document.querySelectorAll("body *")) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    if (getComputedStyle(el).visibility === "hidden") continue;
    if (![...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim())) continue;
    const fs = parseFloat(getComputedStyle(el).fontSize);
    if (fs && fs < chuNhoNhat) { chuNhoNhat = fs; chuNhoNhatO = sel(el); }
  }

  return {
    PROBE_VERSION,
    protocol: location.protocol,
    viewport: vw,
    clientWidth: vw,
    innerWidth: window.innerWidth,   // báo cáo để đối chiếu — KHÔNG dùng để tính
    scrollWidth,
    TRAN_NGANG: tranNgang > 0 ? `${px(tranNgang)}px — LỖI THẬT` : "không",
    tran_ngang_px: px(tranNgang),
    thu_pham_that: thuPham.slice(0, 8),
    da_loc_bo_vi_vo_hai: daLoc.length,
    vi_du_da_loc: daLoc.slice(0, 3),
    chu_nho_nhat: `${chuNhoNhat}px — ${chuNhoNhatO}`,
    vung_cham_duoi_40px: vungChamNho.length,
    vi_du_vung_cham: vungChamNho.slice(0, 5),
    dang_dang_nhap: !!document.querySelector("#wpadminbar, .admin-bar, [data-logged-in='true']"),
  };
})();
