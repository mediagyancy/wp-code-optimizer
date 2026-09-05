# LiteSpeed Cache Preset — Safe Basic

## File: `lscwp-safe-basic.data`

**Triết lý:** Chỉ bật những gì AN TOÀN 100% — bỏ hết mọi setting nguy hiểm và mọi dependency dịch vụ bên thứ 3.

Import qua: **WP Admin → LiteSpeed Cache → Toolbox → Import**

---

## Settings BẬT (an toàn cho mọi WordPress site)

### Page Cache (foundation)
| Setting | Value | Lý do |
|---------|-------|-------|
| `cache` | true | Page cache — foundation của tất cả |
| `cache-priv` | true | Private cache cho logged-in users |
| `cache-rest` | true | Cache REST API |
| `cache-browser` | true | Browser cache (repeat visit) |
| `cache-ttl_pub` | 604800 (7 ngày) | TTL public cache |
| `cache-ttl_browser` | 2592000 (30 ngày) | TTL browser cache — **30 ngày an toàn** thay vì 1 năm |
| `cache-drop_qs` | tracking params | Drop fbclid, gclid, utm*, mc_cid... khỏi cache key |

### Minification (an toàn)
| Setting | Value | Lý do |
|---------|-------|-------|
| `optm-css_min` | true | Minify CSS — giảm 10-20%, an toàn |
| `optm-js_min` | true | Minify JS — an toàn |
| `optm-emoji_rm` | true | Bỏ WP emoji script — tiết kiệm 46KB |

### Lazy Loading (chống CLS + giảm initial load)
| Setting | Value | Lý do |
|---------|-------|-------|
| `media-lazy` | true | Lazy load images |
| `media-iframe_lazy` | true | Lazy load iframes (YouTube...) |
| `media-add_missing_sizes` | true | Auto-add width/height → chống CLS |
| `media-lazy_cls_exc` | logo/hero/banner... | Loại trừ class LCP image |

### Heartbeat throttle (giảm tải server)
| Setting | Value | Lý do |
|---------|-------|-------|
| `misc-heartbeat_front` | true (120s) | Throttle xuống 120s thay vì 60s |
| `misc-heartbeat_back` | true (120s) | Tiết kiệm CPU server |

### Font display
| Setting | Value | Lý do |
|---------|-------|-------|
| `optm-css_font_display` | "swap" | Chống FOIT (chữ trắng vô hình) |

---

## Settings TẮT (vì NGUY HIỂM hoặc cần dịch vụ bên 3)

### Tắt — vì có thể BREAK site
| Setting | Lý do tắt |
|---------|-----------|
| `optm-css_async` | Cần Critical CSS generation → nếu chưa có gây FOUC trắng vài giây |
| `optm-html_min` | Có thể strip whitespace trong inline JS → break template literals / inline comments |
| `media-placeholder_resp` | Inject SVG placeholder vào mọi `<img>` → modify HTML, có thể conflict với theme CSS |
| `optm-js_defer` (= 0) | Defer all JS có thể vỡ inline scripts gọi jQuery |
| `optm-qs_rm` | Strip ?ver= sẽ làm browser stuck CSS cũ sau update |
| `optm-ggfonts_rm` | Chỉ bật SAU khi đã self-host fonts, không thì FOIT |
| `optm-css_comb` / `optm-js_comb` | HTTP/2 — combine làm chậm hơn |
| `util-instant_click` | Preload-on-hover gây side-effect với add-to-cart links (WooCommerce) |
| `optm-noscript_rm` | Giữ lại `<noscript>` cho accessibility |
| `media-lqip` | Thêm requests, không cần thiết với hình thường |

### Tắt — vì PHỤ THUỘC dịch vụ bên 3
| Setting | Dịch vụ phụ thuộc |
|---------|-------------------|
| `optm-ucss` | QUIC.cloud |
| `optm-ccss_per_url` | QUIC.cloud (Critical CSS service) |
| `media-vpi` | QUIC.cloud (Viewport Images) |
| `img_optm-auto` | QUIC.cloud (Image Optimization) |
| `cdn-quic` | QUIC.cloud CDN |
| `cdn-cloudflare` | Cloudflare API |
| `optm-localize` | Tự host external scripts (cần manual setup) |
| `crawler` | Có thể bị shared hosting chặn — bật manual nếu cần |

### Tắt — vì cần config theo site
| Setting | Khi nào bật |
|---------|-------------|
| `object` (Object Cache) | Chỉ bật nếu hosting có Redis/Memcached + có credentials |
| `cdn` | Chỉ bật khi đã setup CDN riêng |
| `cache-mobile` | Chỉ bật nếu theme serve HTML khác cho mobile |

---

## Sau khi import — Việc cần làm

### Bắt buộc
1. **Toolbox → Purge All** sau khi import settings.

### Khuyến nghị (sau 24h theo dõi)
2. **Crawler:** Nếu hosting cho phép, vào Crawler → bật on + nhập URL sitemap.
3. **Object Cache:** Hỏi hosting xem có Redis/Memcached không. Nếu có:
   ```
   object: true
   object-host: <socket path hoặc IP>
   object-port: 0 (socket) hoặc 6379 (TCP)
   ```
4. **Lazy Load Exclusion:** Mở DevTools → tìm CSS class của ảnh hero/logo cụ thể → thêm vào `media-lazy_cls_exc`.

### KHÔNG nên làm trừ khi anh hiểu rõ
- KHÔNG bật `optm-css_async`, `optm-js_defer = 2`, `optm-ggfonts_rm`, `optm-qs_rm` cho đến khi đã test kỹ trên staging.
- KHÔNG enable QUIC.cloud / Cloudflare CDN trừ khi có chiến lược migration cụ thể.

---

## Kỳ vọng sau khi áp dụng

- ✅ Page cache hit rate cao → TTFB giảm
- ✅ HTML/CSS/JS gọn hơn 10-20%
- ✅ Browser cache 30 ngày → repeat visit nhanh
- ✅ Lazy load + missing sizes → chống CLS, giảm initial load
- ✅ Emoji script -46KB
- ✅ Heartbeat throttle giảm tải server
- ⚠️ Không expect đột phá CWV — đây là baseline an toàn. Để tối ưu sâu hơn → cần làm theo skill `/wp-corewebvital` (tự self-host fonts, WebP, conditional dequeue plugin).

## Nếu muốn tối ưu sâu hơn

Đọc `skills/wp-corewebvital/SKILL.md` — 7-phase workflow:
- Phase 3: Self-host WebP (loại bỏ QUIC.cloud Image Opt)
- Phase 5: Self-host fonts (loại bỏ Google Fonts external)
- Sau đó: có thể bật thêm `optm-ggfonts_rm` an toàn vì đã self-host
