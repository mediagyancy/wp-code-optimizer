---
name: wp-corewebvital
preamble-tier: 3
version: 2.1.0
description: |
  Core Web Vitals optimization for WordPress sites on LiteSpeed server with LiteSpeed Cache plugin.
  Ưu tiên an toàn: chỉ dùng setting rollback được và KHÔNG phụ thuộc dịch vụ bên thứ ba (QUIC.cloud, Cloudflare CDN, online image opt).
  7-phase workflow: audit → LiteSpeed safe preset → plugin dequeue → image WebP self-host → CSS/JS optimize → font self-host → verify.
  v2.1.0: đo lab tại chỗ bằng chrome-devtools MCP (LCP/CLS/LCP-breakdown + insight có estimated savings,
  page weight trên cache nguội, quét lỗi console) thay cho việc bảo người dùng tự mở PageSpeed.
  Based on real sprint results: Dự án B -31% page weight, FCP -56%, all CWV pass.
  Use when asked to "optimize core web vitals", "tối ưu CWV", "speed up WordPress", "tune LiteSpeed", "fix PageSpeed score".
voice-triggers:
  - core web vitals
  - optimize wordpress
  - tối ưu tốc độ
  - pagespeed
  - litespeed cache
  - cwv
  - page speed
  - web vitals
  - tối ưu cwv
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
  - Glob
  - Grep
  - Agent
  - AskUserQuestion
  - WebSearch
  - WebFetch
  # Đo lab tại chỗ (từ v2.1.0) — thiếu nhóm này thì Step 0.3 không chạy được
  - mcp__chrome-devtools__new_page
  - mcp__chrome-devtools__navigate_page
  - mcp__chrome-devtools__close_page
  - mcp__chrome-devtools__list_pages
  - mcp__chrome-devtools__emulate
  - mcp__chrome-devtools__performance_start_trace
  - mcp__chrome-devtools__performance_stop_trace
  - mcp__chrome-devtools__performance_analyze_insight
  - mcp__chrome-devtools__list_network_requests
  - mcp__chrome-devtools__list_console_messages
  - mcp__chrome-devtools__evaluate_script
  - mcp__chrome-devtools__take_screenshot
---

# CWV-WP: Core Web Vitals Optimization for WordPress + LiteSpeed

> **Proven results:** Dự án B sprint 2026-04-27 — 2177KB → 1506KB (-31%), FCP 926ms → 410ms (-56%), all CrUX field metrics PASS.

> **Ưu tiên an toàn:** Mọi optimization phải rollback được. KHÔNG bao giờ enable setting có thể break inline JS, FOUC, CLS regression, hay cache poisoning. KHÔNG dùng dịch vụ bên thứ 3 (QUIC.cloud, Cloudflare CDN, online CCSS/UCSS service).

---


> ## Mức chắc chắn — đọc trước khi làm theo bất cứ bước nào
>
> Không có setting nào "an toàn 100%". Câu đó từng nằm ở đầu tài liệu này và nó sai:
> an toàn hay không phụ thuộc plugin đang cài, theme, phiên bản LiteSpeed và cấu hình
> hosting của TỪNG site. Nên mỗi bước dưới đây mang một nhãn:
>
> | Nhãn | Nghĩa | Phải làm gì |
> |---|---|---|
> | `AN-TOAN-CAO` | Chưa gặp ca hỏng nào trên các site đã thử; rollback bằng cách tắt lại setting | kiểm 5 loại trang sau khi bật |
> | `CAN-KIEM` | Đúng với cấu hình thường gặp, nhưng có cấu hình làm nó hỏng | đọc phần "hỏng khi nào" ngay dưới bước đó, rồi tự kiểm |
> | `RUI-RO` | Có thể làm hỏng chức năng đang chạy | chỉ làm khi hiểu rõ, và kiểm bằng thao tác thật |
>
> Không nhãn nào là "khỏi kiểm". Sau mỗi phase, mở đủ 5 loại trang và **đặt thử một
> đơn** nếu là site bán hàng.


## CRITICAL RULES

1. **SAFE-first, không nguy hiểm.** Không bao giờ enable: `optm-css_async`, `optm-js_defer ≥ 1`, `optm-qs_rm`, `optm-ggfonts_rm` (trừ khi đã self-host fonts), `optm-html_min`, `util-instant_click` (đặc biệt với WooCommerce), `media-placeholder_resp`. Mọi setting này có thể break site theo cách khó debug.
2. **KHÔNG dịch vụ bên thứ 3.** Không dùng QUIC.cloud (UCSS, CCSS, VPI, Image Opt), Cloudflare CDN, online image services. Tất cả tối ưu phải self-host hoặc native.
3. **Field data first, lab score second — nhưng lab phải là lab TÁI LẬP ĐƯỢC.** CrUX p75 (LCP, INP, CLS, TTFB) mới là cái Google rank. Điểm PSI dao động ±20 mỗi run nên đừng chase. Từ v2.1.0, lab được đo bằng `performance_start_trace` với throttle **cố định** (mobile 412×915, CPU 4x, Slow 4G) — ổn định hơn PSI nhiều và so trước/sau được, nhưng vẫn là lab: nó **không** thay thế field data để kết luận thắng thua.
4. **Audit before code.** Chạy Day 0 protocol đủ. Discover ALL instances của một pattern trước khi fix bất kỳ. Batch deploys.
5. **Confirm with user before deploying.** Present ROI-ranked optimization list. User pick scope.
6. **Don't break tracking (Google Ads), forms (CF7), WooCommerce, or SEO.** Hard constraints.

---

## PHASE 0 — Day 0 Audit (ALWAYS RUN FIRST)

Trước khi viết bất kỳ optimization code nào, hoàn thành audit này.

### Step 0.1 — Confirm site URL

```
AskUserQuestion: "URL website cần tối ưu? (VD: https://example.com)"
```

### Step 0.2 — Server stack diagnostics

```bash
URL="<user-provided-url>"
echo "=== SERVER HEADERS ==="
curl -sI "$URL" | grep -iE "server:|x-powered-by|x-litespeed|cf-ray|x-cache"

echo "=== HTTP VERSION ==="
curl -sI --http2 "$URL" 2>&1 | head -1

echo "=== LITESPEED CACHE STATUS ==="
curl -sI "$URL" | grep -i "x-litespeed-cache"

echo "=== HTML SIZE ==="
curl -s "$URL" -o /tmp/cwv-audit.html
wc -c < /tmp/cwv-audit.html
```

### Step 0.3 — Đo lab TẠI CHỖ bằng chrome-devtools MCP (không phải mở PageSpeed bằng tay)

> Từ v2.1.0. Trước đây bước này bảo người dùng tự mở `pagespeed.web.dev` rồi đọc hộ —
> Claude không có số nào của riêng mình, không lặp lại được, không so được trước/sau.
> MCP `chrome-devtools` (đã cấu hình sẵn trong `~/.claude.json`) cho đo thẳng.

**Thứ tự bắt buộc — sai thứ tự là số vô nghĩa:**

```
1. new_page   { url: "<URL>" }                          → lấy pageId
2. emulate    { pageId, viewport: "412x915x2.625,mobile,touch",
                cpuThrottlingRate: 4, networkConditions: "Slow 4G" }
3. performance_start_trace { pageId, reload: true, autoStop: true }
4. performance_analyze_insight { pageId, insightSetId: "NAVIGATION_0",
                                 insightName: "<tên từ danh sách trả về ở bước 3>" }
```

`emulate` phải chạy **trước** trace. `reload: true` để trace bắt được cả quá trình tải.
Bỏ throttle thì đo trên máy dev mạnh + cáp quang, ra số đẹp không liên quan gì tới điện
thoại của khách.

Bước 3 trả về thẳng: `LCP`, **LCP breakdown** (TTFB / render delay), `CLS`, danh sách insight
kèm **estimated savings**, và một dòng quan trọng: `Metrics (field / real users)` — nếu trang
có trong CrUX thì field data hiện ngay ở đây, khỏi mở PageSpeed.

Ca thật (du-an-b.example, 09/09/2026, mobile 4x CPU + Slow 4G):

```
LCP: 2530 ms   ← LCP breakdown: TTFB 661 ms + Render delay 1869 ms
CLS: 0.00
Metrics (field / real users): n/a – no data for this page in CrUX
DocumentLatency → estimated savings: FCP 559 ms, LCP 559 ms
  · The request was not redirected: PASSED
  · Server responded quickly: FAILED     ← 661 ms > ngưỡng 600 ms
  · Compression was applied: PASSED      (content-encoding: br, protocol h3)
LCP element: H1.du-an-b-hero-title — là CHỮ, không tải từ mạng
```

**Đọc ca này cho đúng, vì nó dạy cách chọn phase:** LCP element là **text**, nên tối ưu ảnh
(Phase 3) *không* kéo LCP xuống được. 1869 ms render delay mới là chỗ mất, tức Phase 1 (TTFB)
và Phase 4 (CSS chặn render) mới là hai phase đáng làm. Không có bước đo này thì rất dễ đổ
công vào Phase 3 rồi tự hỏi vì sao số không nhúc nhích.

**Bốn cái bẫy đã trả giá, phải biết trước khi tin số:**

| Bẫy | Sự thật đo được | Làm gì |
|---|---|---|
| `lighthouse_audit` tưởng có điểm performance | Mô tả tool ghi rõ **"This excludes performance"** — nó chỉ có a11y/SEO/best-practices | Muốn CWV thì dùng `performance_start_trace`, không dùng `lighthouse_audit` |
| Đo page weight bằng `transferSize` | Trên tab đã ghé qua: **57/60 resource có `transferSize = 0`**, `deliveryType: cache` 43 cái → tổng ra **4 KB**, sai hoàn toàn | Đo trên tab **cache nguội** (xem 0.3b) |
| Cộng `transferSize` của bên thứ ba | Cross-origin không gửi `Timing-Allow-Origin` thì mọi trường size = 0. Ca Dự án B: 16–17 resource ngoài vẫn bằng 0 dù đã tải nguội | Báo cáo dạng "≥ X KB, còn N resource bên thứ ba không đo được từ JS" — đừng gộp im lặng |
| Kiểm `x-litespeed-cache` qua MCP | MCP **che giá trị header**: hiện `x-litespeed-cache: <redacted>` | Cache hit vẫn phải kiểm bằng `curl -sI` (Phase 1.5) |

### Step 0.3b — Page weight bằng số thật (cache nguội)

`new_page` với `isolatedContext` cho một context sạch, **cache rỗng** — đây là điều kiện
duy nhất khiến `transferSize` có nghĩa.

```
new_page { url: "<URL>", isolatedContext: "cwv-cold", background: true }
```

rồi `evaluate_script` với:

```js
() => {
  const r = performance.getEntriesByType("resource");
  const nav = performance.getEntriesByType("navigation")[0];
  const host = location.host;
  const sum = (a, k) => Math.round(a.reduce((s, e) => s + (e[k] || 0), 0) / 1024);
  const same = r.filter(e => new URL(e.name).host === host);
  const cross = r.filter(e => new URL(e.name).host !== host);
  const delivery = {};
  for (const e of r) { const d = e.deliveryType || "(network)"; delivery[d] = (delivery[d] || 0) + 1; }
  return {
    tong_request: r.length + 1,
    docKB: Math.round((nav?.transferSize || 0) / 1024),
    cung_host: { n: same.length, transferKB: sum(same, "transferSize") },
    khac_host: { n: cross.length, transferKB: sum(cross, "transferSize"),
                 khong_do_duoc: cross.filter(e => !e.transferSize).length },
    deliveryType: delivery,           // phải là {"(network)": N} — có "cache" là số hỏng
    tenMienNgoai: [...new Set(r.map(e => new URL(e.name).host))].filter(h => h !== host)
  };
}
```

**Đọc `deliveryType` TRƯỚC mọi con số khác.** Thấy `cache` xuất hiện là phép đo hỏng, phải
mở context mới. Ca Dự án B cold: `{"(network)": 66}` và `{"(network)": 67}` ở hai lần chạy —
doc 28 KB + cùng host 644 KB + khác host 38 KB, còn 16–17 resource bên thứ ba không đo được
→ báo cáo trung thực là **≥ 710 KB**, không phải "710 KB".

**Chạy tối thiểu hai lần.** Phần cùng host rất ổn định (644 KB cả hai lần), nhưng script
quảng cáo/analytics tải không đều: cùng trang, cùng điều kiện, hai lần cho **9 rồi 11 domain
ngoài**. Chênh lệch bên thứ ba giữa trước/sau sprint mà nhỏ hơn biên độ này thì là nhiễu,
không phải cải thiện.

`tenMienNgoai` thay luôn cho `grep` HTML ở Step 0.4: nó bắt được cả domain do JS chèn động,
thứ mà grep trên HTML thô không thấy. Ca Dự án B có `use.fontawesome.com` (Phase 5/6 xử lý),
cụm Google Ads/Analytics (giữ, theo Phase 6.1), và vài domain khác — trong đó
`traffic2479.com` và `images.dmca.com` không nằm trong bảng phân loại Phase 6.1, tức là
**bảng đó chưa đủ**: gặp domain lạ thì hỏi người dùng "cái này của ai, dùng làm gì" trước
khi xếp KEEP hay REMOVE, đừng tự đoán.

### Step 0.3c — CrUX field data (khi trace báo "no data")

Nếu dòng `Metrics (field / real users)` ở bước 3 nói `n/a`, mở
`https://pagespeed.web.dev/analysis?url=$URL` → section **"Discover what your real users are experiencing"**.

| Metric | Good | Needs improvement | Poor |
|--------|-----:|------------------:|-----:|
| LCP    | ≤2.5s | 2.5–4.0s | >4.0s |
| INP    | ≤200ms | 200–500ms | >500ms |
| CLS    | ≤0.1 | 0.1–0.25 | >0.25 |
| TTFB   | ≤800ms | 800ms–1.8s | >1.8s |

**XÁC ĐỊNH metric nào đang FAILING.** Đó là target. Mọi metric khác là secondary.

### Step 0.4 — Resource inventory

```bash
echo "=== PLUGINS WITH FRONTEND ASSETS ==="
grep -oE '/wp-content/plugins/[^/"]+' /tmp/cwv-audit.html | sort | uniq -c | sort -rn

echo "=== EXTERNAL DEPENDENCIES ==="
DOMAIN=$(echo "$URL" | grep -oP '://[^/]+' | sed 's|://||')
grep -oE 'https?://[^"'"'"' ]+' /tmp/cwv-audit.html | grep -v "$DOMAIN" | sort -u
```

### Step 0.5 — Bottleneck prioritization

Build ROI table → present top 3 cho user → confirm scope.

---

## PHASE 1 — LiteSpeed Cache: preset khởi điểm (KHÔNG phải preset an toàn tuyệt đối)

**Target metric:** TTFB, FCP, cache hit rate
**Impact:** HIGH — server response time là foundation
**Risk:** LOW — preset đã loại bỏ mọi setting nguy hiểm

### 1.1 — Apply preset có sẵn

✅ **Use the prepared safe preset:** `skills/wp-corewebvital/presets/lscwp-safe-basic.data`

```
AskUserQuestion: "Em sẽ apply preset khởi điểm. Có 3 cách:
A) Em copy file vào Downloads cho anh import qua WP Admin → LiteSpeed Cache → Toolbox → Import
B) Anh có SSH access — em dùng wp-cli để apply
C) Em hướng dẫn anh chỉnh manual từng setting"
```

Sau khi apply: **Toolbox → Purge All**.

### 1.2 — Settings preset BẬT (mỗi mục có nhãn mức chắc chắn)

| Group | Settings | Why safe |
|-------|----------|----------|
| Page Cache | `cache`, `cache-priv`, `cache-rest`, `cache-browser` | Foundation — không break gì |
| TTL | `cache-ttl_pub: 7d`, `cache-ttl_browser: 30d` | Browser TTL ngắn hơn 1 năm để tránh cache poisoning |
| Drop QS | `cache-drop_qs: [fbclid,gclid,utm*,...]` | Tracking params không nên trong cache key |
| Minify | `optm-css_min`, `optm-js_min` | Generally safe (KHÔNG bật `optm-html_min` — có thể break inline JS) |
| Emoji | `optm-emoji_rm: true` | Save 46KB, không break gì |
| Lazy Load | `media-lazy`, `media-iframe_lazy`, `media-add_missing_sizes` | Chống CLS, giảm initial load |
| Heartbeat | `misc-heartbeat_*: 120s` | Throttle giảm tải server |
| Font display | `optm-css_font_display: swap` | Chống FOIT (chữ trắng) |

### 1.3 — Settings preset TẮT (vì NGUY HIỂM)

| Setting | Risk |
|---------|------|
| `optm-css_async` | Cần Critical CSS service → fail silently → FOUC |
| `optm-js_defer` (≥ 1) | Có thể break inline scripts gọi jQuery/document.write |
| `optm-qs_rm` | Strip ?ver= → user stuck CSS cũ sau update |
| `optm-ggfonts_rm` | FOIT nếu chưa self-host fonts |
| `optm-html_min` | Strip whitespace trong inline `<script>` → break template literals/comments |
| `util-instant_click` | Hover preload → side-effect với add-to-cart URLs (DANGEROUS với WooCommerce) |
| `media-placeholder_resp` | Inject SVG vào mọi `<img>` → conflict với theme CSS |
| `optm-css_comb`, `optm-js_comb` | HTTP/2 multiplexing tốt hơn combine |
| `cache-mobile` (với responsive theme) | Wastes storage cho HTML giống nhau |

### 1.4 — Settings preset TẮT (vì DỊCH VỤ BÊN 3)

| Setting | Service phụ thuộc |
|---------|-------------------|
| `optm-ucss`, `optm-ccss_per_url` | QUIC.cloud (Critical CSS service) |
| `media-vpi` | QUIC.cloud (Viewport Images) |
| `img_optm-auto` | QUIC.cloud (Image Optimization) |
| `cdn-quic` | QUIC.cloud CDN |
| `cdn-cloudflare` | Cloudflare API |
| `optm-localize` | Tự host external scripts (cần manual setup) |
| `crawler` | Có thể bị shared hosting chặn — bật manual nếu cần |
| `object` (Object Cache) | Cần Redis/Memcached + credentials |

### 1.5 — Verify

```bash
curl -sI "$URL" | grep -i "x-litespeed-cache"
# Expect: x-litespeed-cache: hit (sau khi browse vài lần để warm cache)
```

---

## PHASE 2 — Plugin Audit & Conditional Dequeue

**Target metric:** Page weight, request count
**Impact:** HIGH — typically -200KB to -400KB

### 2.1 — Identify plugin bloat

```bash
echo "=== PLUGIN ASSET COUNT ==="
grep -oE '/wp-content/plugins/[^/"]+' /tmp/cwv-audit.html | sort | uniq -c | sort -rn

echo "=== LARGEST PLUGIN JS ==="
grep -oE '/wp-content/plugins/[^"'"'"' ]+\.js' /tmp/cwv-audit.html | sort -u
```

### 2.2 — Classify mỗi plugin

| Action | Khi nào |
|--------|---------|
| 🔴 REMOVE | Plugin replaceable bằng <50 lines theme code |
| 🟡 CONDITIONAL | Plugin chỉ cần trên specific pages → dequeue elsewhere |
| 🟢 KEEP | Essential, loads efficiently |

Common high-ROI replacements:
- **Lightbox plugins** (easy-fancybox): Replace bằng `<dialog>` + 30 lines JS (-80KB)
- **Slider plugins**: Replace bằng CSS scroll-snap
- **Social share plugins**: Replace bằng native share URLs (-50KB+)
- **Font plugins**: Self-host fonts

### 2.3 — Conditional dequeue pattern

```php
add_action('wp_enqueue_scripts', function() {
    global $post;
    
    // WooCommerce: chỉ load trên shop pages
    if (function_exists('is_woocommerce') && !is_woocommerce() && !is_cart() && !is_checkout() && !is_account_page()) {
        wp_dequeue_style('woocommerce-general');
        wp_dequeue_style('woocommerce-layout');
        wp_dequeue_style('woocommerce-smallscreen');
        wp_dequeue_style('wc-blocks-style');
        wp_dequeue_script('wc-add-to-cart');
        wp_dequeue_script('wc-cart-fragments');
        /* [CAN-KIEM] Hỏng khi nào: fragments là thứ cập nhật mini-cart bằng AJAX.
           Gỡ nó ngoài các trang Woo chuẩn sẽ làm mini-cart / widget giỏ hàng /
           shortcode [woocommerce_cart] trên TRANG CHỦ hoặc trang tĩnh ngừng cập
           nhật số lượng sau khi thêm hàng. Trước khi bật: tìm mọi nơi có mini-cart
           ngoài trang Woo, và thêm chúng vào điều kiện loại trừ. Kiểm bằng cách
           thêm một món rồi xem số trên biểu tượng giỏ có đổi không. */
    }
    
    // Plugin chỉ load khi có shortcode
    if (is_a($post, 'WP_Post') && !has_shortcode($post->post_content, 'dflip')) {
        wp_dequeue_style('dflip-css');
        wp_dequeue_script('dflip-script');
    }
    
    // Contact Form 7: chỉ trên page có form
    if (is_a($post, 'WP_Post') && !has_shortcode($post->post_content, 'contact-form-7')) {
        wp_dequeue_style('contact-form-7');
        wp_dequeue_script('contact-form-7');
    }
}, 100); // Priority 100 = AFTER plugins enqueue
```

### 2.4 — URL-based blocking (belt-and-suspenders)

Cho stubborn plugins re-enqueue lại:

```php
add_action('template_redirect', function() {
    ob_start(function($html) {
        $block_patterns = [
            // 'animate.css',
            // 'unwanted-plugin-handle',
        ];
        foreach ($block_patterns as $pattern) {
            $html = preg_replace(
                '#<(link|script)[^>]*' . preg_quote($pattern, '#') . '[^>]*>(\s*</script>)?#i',
                '', $html
            );
        }
        return $html;
    });
});
```

---

## PHASE 3 — Image Optimization (Self-hosted WebP, KHÔNG QUIC.cloud)

**Target metric:** LCP, page weight
**Impact:** HIGH — typically -40% to -60% image bytes
**Self-host only — no QUIC.cloud/external service.**

### 3.1 — Bulk WebP conversion script

Create `tools/convert-uploads-to-webp.php` trong theme:

```php
<?php
/**
 * Bulk convert uploads to WebP. Run once via WP-CLI.
 * Usage: wp eval-file wp-content/themes/<theme>/tools/convert-uploads-to-webp.php
 */
if (!defined('ABSPATH')) require_once dirname(__FILE__, 5) . '/wp-load.php';
if (!current_user_can('manage_options') && php_sapi_name() !== 'cli') die('Admin only');

$upload_dir = wp_upload_dir()['basedir'];
$iterator = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($upload_dir));
$converted = 0; $skipped = 0; $errors = 0;

foreach ($iterator as $file) {
    if (!$file->isFile()) continue;
    $ext = strtolower($file->getExtension());
    if (!in_array($ext, ['jpg', 'jpeg', 'png'])) continue;
    
    $webp_path = $file->getPathname() . '.webp';
    if (file_exists($webp_path)) { $skipped++; continue; }
    
    $img = ($ext === 'png')
        ? @imagecreatefrompng($file->getPathname())
        : @imagecreatefromjpeg($file->getPathname());
    if (!$img) { $errors++; continue; }
    
    if ($ext === 'png') {
        imagepalettetotruecolor($img);
        imagealphablending($img, true);
        imagesavealpha($img, true);
    }
    
    if (imagewebp($img, $webp_path, 82)) {
        if (filesize($webp_path) >= filesize($file->getPathname())) {
            unlink($webp_path); $skipped++;
        } else {
            $converted++;
        }
    } else { $errors++; }
    imagedestroy($img);
}
echo "Converted: $converted | Skipped: $skipped | Errors: $errors\n";
```

### 3.2 — Auto-convert on upload

Add to `functions.php`:

```php
add_filter('wp_generate_attachment_metadata', function($metadata, $attachment_id) {
    $file = get_attached_file($attachment_id);
    if (!$file) return $metadata;
    $ext = strtolower(pathinfo($file, PATHINFO_EXTENSION));
    if (!in_array($ext, ['jpg', 'jpeg', 'png'])) return $metadata;
    
    mytheme_convert_to_webp($file);
    
    $upload_dir = dirname($file);
    if (!empty($metadata['sizes'])) {
        foreach ($metadata['sizes'] as $size) {
            mytheme_convert_to_webp($upload_dir . '/' . $size['file']);
        }
    }
    return $metadata;
}, 10, 2);

function mytheme_convert_to_webp($file_path) {
    if (!file_exists($file_path)) return;
    $webp_path = $file_path . '.webp';
    if (file_exists($webp_path)) return;
    
    $ext = strtolower(pathinfo($file_path, PATHINFO_EXTENSION));
    $img = ($ext === 'png') ? @imagecreatefrompng($file_path) : @imagecreatefromjpeg($file_path);
    if (!$img) return;
    
    if ($ext === 'png') {
        imagepalettetotruecolor($img);
        imagealphablending($img, true);
        imagesavealpha($img, true);
    }
    imagewebp($img, $webp_path, 82);
    imagedestroy($img);
    
    if (file_exists($webp_path) && filesize($webp_path) >= filesize($file_path)) {
        unlink($webp_path);
    }
}
```

### 3.3 — .htaccess WebP auto-serve

Add vào `/public_html/.htaccess` BEFORE WordPress rewrite rules:

```apache
# BEGIN WebP auto-serve
<IfModule mod_rewrite.c>
  RewriteEngine On
  RewriteCond %{HTTP_ACCEPT} image/webp
  RewriteCond %{REQUEST_URI} \/wp-content\/uploads\/
  RewriteCond %{REQUEST_FILENAME} \.(jpe?g|png)$
  RewriteCond %{REQUEST_FILENAME}\.webp -f
  RewriteRule ^(.+)\.(jpe?g|png)$ $1.$2.webp [T=image/webp,L]
</IfModule>
<IfModule mod_headers.c>
  <FilesMatch "\.(jpe?g|png)\.webp$">
    Header set Content-Type "image/webp"
    Header append Vary "Accept"
  </FilesMatch>
</IfModule>
# END WebP auto-serve
```

### 3.4 — Verify

```bash
curl -sI -H "Accept: image/webp" "$URL/wp-content/uploads/<image>.png" | grep -i content-type
# Expect: content-type: image/webp
```

---

## PHASE 4 — CSS/JS Theme-level Optimization

**Target metric:** FCP, TBT
**Impact:** MEDIUM — -20% to -30%

### 4.1 — Defer non-critical CSS (an toàn, không qua LiteSpeed async)

```php
add_action('wp_enqueue_scripts', function() {
    // Defer Font Awesome bằng media trick (không cần CCSS service)
    add_filter('style_loader_tag', function($html, $handle) {
        $defer_handles = ['font-awesome', 'swiper-css'];
        if (in_array($handle, $defer_handles)) {
            return str_replace("media='all'", "media='print' onload=\"this.media='all'\"", $html);
        }
        return $html;
    }, 10, 2);
}, 100);
```

### 4.2 — Remove unused CSS/JS

```php
add_action('wp_enqueue_scripts', function() {
    // Remove Gutenberg block CSS nếu là classic theme
    /* [RUI-RO] Hỏng khi nào: classic theme KHÔNG có nghĩa là nội dung không có
       block. Bài viết soạn bằng Gutenberg vẫn sinh ra markup block (columns,
       gallery, buttons, group) và mất wp-block-library là mất style của chúng —
       lỗi hiện ở GIỮA BÀI, không hiện ở trang chủ, nên rất dễ không ai thấy.
       Chỉ bật khi đã kiểm: mở vài bài viết dài nhất và một trang có gallery. */
    wp_dequeue_style('wp-block-library');
    wp_dequeue_style('wp-block-library-theme');
    wp_dequeue_style('global-styles');
    
    // Remove wp-embed nếu không dùng oEmbed
    wp_deregister_script('wp-embed');
}, 100);

// Remove WP emoji (LiteSpeed cũng làm, đây là backup)
remove_action('wp_head', 'print_emoji_detection_script', 7);
remove_action('wp_print_styles', 'print_emoji_styles');
```

---

## PHASE 5 — Font Self-hosting (KHÔNG dùng Google Fonts external)

**Target metric:** FCP, LCP (loại bỏ external DNS lookups)
**Impact:** MEDIUM — -30KB + eliminates 2 external domains

### 5.1 — Download fonts

1. Identify fonts đang load từ Google Fonts
2. Download từ [google-webfonts-helper](https://gwfh.mranftl.com/)
3. Chỉ lấy `woff2` (modern browsers all support)
4. Include `latin` + language-specific subset (e.g., `vietnamese`)

### 5.2 — Self-host trong theme

Place `.woff2` files trong `assets/fonts/` và add:

```php
add_action('wp_head', function() {
    ?>
    <style>
    @font-face {
        font-family: 'Your Font';
        src: url('<?php echo get_template_directory_uri(); ?>/assets/fonts/your-font-latin.woff2') format('woff2');
        font-weight: 100 900;
        font-style: normal;
        font-display: swap;
        unicode-range: U+0000-00FF;
    }
    @font-face {
        font-family: 'Your Font';
        src: url('<?php echo get_template_directory_uri(); ?>/assets/fonts/your-font-vietnamese.woff2') format('woff2');
        font-weight: 100 900;
        font-style: normal;
        font-display: swap;
        unicode-range: U+0102-0103, U+0110-0111, U+0128-0129, U+0168-0169, U+01A0-01A1, U+01AF-01B0, U+1EA0-1EF9, U+20AB;
    }
    </style>
    <?php
}, 1);
```

### 5.3 — Remove Google Fonts

```php
add_action('wp_enqueue_scripts', function() {
    wp_dequeue_style('google-fonts');
    // Add other Google Fonts handles cụ thể
}, 100);

// Belt-and-suspenders: block trong HTML output
add_action('template_redirect', function() {
    ob_start(function($html) {
        return preg_replace('#<link[^>]*fonts\.googleapis\.com[^>]*>#i', '', $html);
    });
});
```

**Sau Phase 5 xong:** Có thể an toàn enable `optm-ggfonts_rm: true` trong LiteSpeed như layer thứ 3 backup.

---

## PHASE 6 — External Dependency Audit

**Target metric:** TTFB (DNS lookups), TBT (3rd-party scripts)
**Impact:** MEDIUM-HIGH — mỗi external domain = 50-200ms DNS+connect

### 6.1 — Classify external dependencies

| Dependency | Action |
|-----------|--------|
| Google Ads (gtag/GTM) | KEEP — revenue tracking |
| Google Analytics | KEEP nhưng consolidate với GTM nếu có |
| Facebook SDK | REMOVE nếu không dùng FB Login/Share |
| Instagram embed | REMOVE nếu không embed IG posts |
| Google Fonts | REMOVE — replaced by self-host (Phase 5) |
| QUIC.cloud | REMOVE — replaced by self-host WebP (Phase 3) |
| Font Awesome CDN | SELF-HOST hoặc subset to used icons only |

### 6.2 — DNS prefetch các externals còn lại

```php
add_action('wp_head', function() {
    $domains = [
        'www.googletagmanager.com',
        'www.google-analytics.com',
    ];
    foreach ($domains as $domain) {
        echo '<link rel="dns-prefetch" href="//' . $domain . '">' . "\n";
        echo '<link rel="preconnect" href="https://' . $domain . '" crossorigin>' . "\n";
    }
}, 0);
```

---

## PHASE 7 — Verification & Monitoring

### 7.1 — Post-optimization verification

**Phần curl — những thứ MCP không đo được** (giá trị header bị MCP che):

```bash
URL="<site-url>"

echo "=== 1. CACHE HIT ==="
curl -sI "$URL" | grep -i "x-litespeed-cache"

echo "=== 2. WEBP SERVING ==="
curl -sI -H "Accept: image/webp" "$URL/wp-content/uploads/<image>.png" | grep -i content-type

echo "=== 3. HTML DOC SIZE (chỉ tài liệu, KHÔNG phải page weight) ==="
curl -s "$URL" -o /tmp/cwv-final.html
wc -c < /tmp/cwv-final.html
```

> Bước 3 chỉ là kích thước **file HTML**. Bảng EXPECTED RESULTS bên dưới nói "page weight
> 2-3 MB → 1-1.5 MB" — con số đó **không** đo được bằng `wc -c`. Page weight thật lấy từ
> phần MCP ngay dưới.

**Phần MCP — trước/sau bằng cùng một phép đo.** Chạy lại **nguyên xi** Step 0.3 và 0.3b
(cùng viewport, cùng `cpuThrottlingRate: 4`, cùng `networkConditions: "Slow 4G"`, cùng
`isolatedContext` cho phần cân nặng). Khác điều kiện thì hai lần đo không so được với nhau.

Lập bảng đối chiếu:

| Chỉ số | Trước | Sau | Nguồn |
|---|---|---|---|
| LCP (lab, mobile throttled) | | | `performance_start_trace` |
| LCP breakdown: TTFB / render delay | | | trace |
| CLS | | | trace |
| Page weight (cold, cùng host) | | | `evaluate_script` trên tab `isolatedContext` |
| Số resource bên thứ ba không đo được | | | cùng script — **phải ghi ra, đừng giấu** |
| Số domain ngoài | | | `tenMienNgoai` |
| Insight có `estimated savings` lớn nhất | | | `performance_analyze_insight` |

**Lỗi JS — bước mới, bắt buộc.** Dequeue ở Phase 2 và 4 là nơi hay làm vỡ script phụ thuộc
nhau, mà bảng smoke test bằng mắt thì không thấy:

```
list_console_messages { pageId, types: ["error", "warn"], pageSize: 20 }
```

Ca thật (du-an-b.example, 09/09/2026): trang chủ đang có `Uncaught ReferenceError: wp is not
defined` — dấu hiệu điển hình của một script gọi global `wp` (wp-util / wp-i18n) sau khi
dependency của nó bị gỡ hoặc bị defer. Đây đúng là loại hỏng mà Phase 2/4 gây ra, và bản
skill trước **không có bước nào bắt được nó**.

So `list_console_messages` trước và sau: lỗi mới xuất hiện = regression do chính sprint này
gây ra, phải sửa hoặc rollback, không được ghi vào phần "đã biết".

### 7.2 — Smoke test checklist

- [ ] Homepage — loads, images visible, slider works
- [ ] Product page — WooCommerce styles load, add-to-cart works
- [ ] News/blog page — content renders, images load
- [ ] Contact page — form submits successfully
- [ ] Mobile — responsive layout intact
- [ ] Language switcher — gtranslate works
- [ ] Admin panel — WP admin loads normally
- [ ] **Console sạch** — `list_console_messages` không có lỗi MỚI so với bản trước sprint

### 7.3 — Theo dõi field data (KHÔNG phải 24–48 giờ)

> **Đừng kết luận field data sau 24–48 giờ.** CrUX và Search Console báo cáo theo
> **cửa sổ cuốn 28 ngày**, nên sau hai ngày thì thay đổi của bạn mới chiếm khoảng
> 2/28 dữ liệu — con số nhìn thấy gần như vẫn là con số của bản cũ. Đọc sớm rồi kết
> luận là cách tự lừa mình theo cả hai hướng: tưởng đã cải thiện, hoặc tưởng đã hỏng.
>
> Mốc đọc hợp lý:
> · **ngay sau deploy** — kiểm chức năng, không phải kiểm tốc độ
> · **lab (PSI/Lighthouse)** — thấy được ngay, nhưng dao động ±20 điểm mỗi lần chạy
> · **field data** — nhìn xu hướng từ khoảng ngày thứ 7, và chỉ kết luận sau 28 ngày


```
1. https://pagespeed.web.dev/analysis?url=<URL>
   → Section "Discover what your real users are experiencing"
   → All 4 metrics phải FAST (xanh)

2. Google Search Console → Experience → Core Web Vitals
   → Tất cả pages phải show "Good"
```

---

## QUICK REFERENCE — WHAT TO ENABLE / DISABLE

### ✅ Settings AN TOÀN — preset đã bật sẵn

| Setting | Value | Why safe |
|---------|-------|----------|
| `cache` | true | Foundation — không break |
| `cache-priv` | true | Private cache cho logged-in |
| `cache-rest` | true | Cache REST API |
| `cache-browser` | true | Browser cache |
| `cache-ttl_browser` | 2592000 (30 ngày) | Ngắn hơn 1 năm để tránh cache poisoning |
| `optm-css_min` | true | Minify CSS — generally safe |
| `optm-js_min` | true | Minify JS — generally safe |
| `optm-emoji_rm` | true | Save 46KB |
| `optm-css_font_display` | "swap" | Chống FOIT |
| `media-lazy` | true | Lazy load images |
| `media-iframe_lazy` | true | Lazy load iframes |
| `media-add_missing_sizes` | true | Chống CLS |
| `misc-heartbeat_*` | true (120s) | Throttle giảm tải |

### ❌ Settings NGUY HIỂM — preset đã tắt, KHÔNG bật

| Setting | Risk | When OK to enable |
|---------|------|-------------------|
| `optm-css_async` | FOUC trắng vài giây nếu CCSS fail | Không bao giờ (cần QUIC.cloud) |
| `optm-js_defer` ≥ 1 | Break inline scripts gọi jQuery | Sau test exhaustive trên staging |
| `optm-qs_rm` | User stuck CSS cũ sau update | Không bao giờ với browser TTL dài |
| `optm-ggfonts_rm` | FOIT nếu chưa self-host | Chỉ sau Phase 5 done |
| `optm-html_min` | Strip whitespace inline JS | Không bao giờ với theme có inline `<script>` |
| `util-instant_click` | Side-effect add-to-cart | KHÔNG BAO GIỜ với WooCommerce |
| `media-placeholder_resp` | Inject SVG mọi `<img>` | Không cần — lazy load đã đủ |
| `optm-css_comb` / `optm-js_comb` | HTTP/2 multiplexing tốt hơn | Chỉ HTTP/1.1 servers |
| `cache-mobile` | Wastes storage | Chỉ với theme HTML khác cho mobile |

### ❌ Settings DỊCH VỤ BÊN 3 — preset đã tắt, KHÔNG bật

| Setting | 3rd-party service |
|---------|-------------------|
| `optm-ucss` | QUIC.cloud |
| `optm-ccss_per_url` | QUIC.cloud (Critical CSS) |
| `media-vpi` | QUIC.cloud (Viewport Images) |
| `img_optm-auto` | QUIC.cloud (Image Opt) |
| `cdn-quic` | QUIC.cloud CDN |
| `cdn-cloudflare` | Cloudflare API |

### ⚠️ Settings PHỤ THUỘC HOSTING — bật manual nếu phù hợp

| Setting | Condition |
|---------|-----------|
| `object` (Object Cache) | Hosting có Redis/Memcached + credentials |
| `crawler` | Hosting cho phép (shared hosting có thể chặn) |
| `cdn` | Có CDN setup riêng (BunnyCDN, KeyCDN, etc.) |

---

## EXPECTED RESULTS (based on Dự án B benchmark)

| Metric | Trước | Sau | Improvement |
|--------|------:|----:|-------------|
| Page weight (mobile) | 2-3 MB | 1-1.5 MB | -30% to -50% |
| Requests | 70-100 | 40-65 | -20 to -35 |
| FCP | 1.5-3s | 0.4-1.5s | -50% |
| LCP | 2.5-4s | 1.5-2.5s | -30% |
| TTFB | 1-3s | 0.3-0.8s | -60% (with Object Cache) |
| PSI Mobile | 30-55 | 60-85 | +25-30 pts |
| PSI Desktop | 55-75 | 80-95 | +20-25 pts |

---

## ANTI-PATTERNS (lessons từ real sprints)

1. **❌ Bật setting "vì có vẻ improve performance"** → Không hiểu rõ → break site khó debug. Chỉ bật khi hiểu cả benefit lẫn risk.
2. **❌ Dùng QUIC.cloud / Cloudflare CDN "vì miễn phí"** → External dependency, có downtime, có thể bị block ở VN, lock-in vào ecosystem. Self-host always.
3. **❌ Chase PSI lab score** → Lab scores vary ±20 points per run. Chỉ CrUX field data matters cho ranking.
4. **❌ CSS/JS combine trên HTTP/2** → Combining defeats multiplexing. Only combine on HTTP/1.1.
5. **❌ Lazy-load LCP image** → Hero/banner image phải load eagerly. Add class vào `media-lazy_cls_exc`.
6. **❌ ob_start global HTML rewriting** → Causes TBT regression (300ms+). Use wp_enqueue/dequeue hooks instead.
7. **❌ Enable UCSS/CCSS without QUIC.cloud setup** → Strips CSS it thinks is unused → above-fold styles missing → FOUC.
8. **❌ Delete plugins without confirming usage** → Always ask user "Plugin X đang dùng ở page nào?" trước khi remove.
9. **❌ Single-run PSI for regression detection** → Always median of 3+ runs.
10. **❌ Deploy optimizations one-by-one** → Batch changes, max 3 deploys per sprint.
11. **❌ Skip Day 0 audit** → Cost: 3-5 hours debugging missed cases later.
12. **❌ `util-instant_click` trên WooCommerce site** → Hover trigger add-to-cart link → cart pollution.
13. **❌ `optm-html_min` với theme có inline `<script>`** → Strip whitespace có thể vỡ template literals.
14. **❌ `optm-qs_rm` + `cache-ttl_browser` 1 năm** → User stuck CSS cũ tới 1 năm sau update.
15. **❌ Đo page weight bằng `transferSize` trên tab đã ghé qua** → cache làm `transferSize = 0`. Đo thật 09/09/2026 trên du-an-b.example: **57/60 resource bằng 0**, tổng ra **4 KB** trong khi trang thật ≥ 710 KB. Luôn đo trên `isolatedContext` và **đọc `deliveryType` trước** — thấy `cache` là số hỏng.
16. **❌ Gộp im lặng cân nặng bên thứ ba** → cross-origin không có `Timing-Allow-Origin` thì mọi trường size = 0. Ca Dự án B: 16 resource ngoài không đo được ngay cả khi cache nguội. Báo cáo phải ghi "≥ X KB, N resource không đo được", không được làm tròn thành một con số gọn.
17. **❌ Dùng `lighthouse_audit` để lấy điểm performance** → mô tả tool ghi rõ **"This excludes performance"**. Nó chỉ trả a11y / SEO / best-practices. CWV phải lấy từ `performance_start_trace`.
18. **❌ Trace mà quên `emulate` trước** → đo trên máy dev mạnh + mạng nhanh, LCP đẹp giả. Luôn `emulate` (mobile viewport + CPU 4x + Slow 4G) **trước** khi `performance_start_trace`.
19. **❌ So trước/sau với điều kiện đo khác nhau** → đổi viewport hoặc mức throttle giữa hai lần đo thì phần trăm cải thiện là số bịa. Ghi lại đúng tham số `emulate` cùng với mỗi lần đo.
20. **❌ Nghiệm thu sprint mà không xem console** → dequeue ở Phase 2/4 làm vỡ script phụ thuộc, mắt thường không thấy. Ca thật: `Uncaught ReferenceError: wp is not defined` trên trang chủ Dự án B.

---

## RELATED FILES

- 📄 Preset SAFE BASIC: `skills/wp-corewebvital/presets/lscwp-safe-basic.data`
  **Preset này xuất từ LiteSpeed Cache 7.8.1.** Bản LSCWP khác có thể đổi mặc định của
  một số khoá — đáng chú ý là `cache-page_login` (cache trang đăng nhập), trong preset
  này đang BẬT. Sau khi import, mở lại từng nhóm setting đối chiếu với tài liệu của
  đúng phiên bản đang cài, rồi test site. Import xong coi như đã an toàn là sai.
- 📖 Preset README: `skills/wp-corewebvital/presets/README.md`
- 🗒️ Dự án B sprint reference: `(báo cáo nội bộ, không kèm trong repo)`
- 🗒️ Dự án B landscape: `(báo cáo nội bộ, không kèm trong repo)`
- 🗒️ Day 0 protocol: `(báo cáo nội bộ, không kèm trong repo)`

---

## COMPLETION

Khi tất cả phases done:
1. Save final PSI data vào `.gstack/benchmark-reports/`
2. Update landscape doc (`.gstack/audit/`) với current state
3. Tạo verification checklist; nói rõ mốc field data là 28 ngày, không phải 24–48h
4. Đợi CrUX data confirm trước khi declare victory
