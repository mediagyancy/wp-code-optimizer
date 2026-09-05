# WP Code Optimizer

**Three Claude Code skills for working on live WordPress sites without breaking them:
ship changes safely, clean out dead code, and tune Core Web Vitals.**

> ⚠️ **The skill content is written in Vietnamese.** The scripts, CLI flags and output
> are Vietnamese too. This README is bilingual; everything below the divider is Vietnamese.
> If you don't read Vietnamese, the scripts still work — but the reasoning that makes them
> worth using won't reach you. A translation PR is very welcome.

---

## What this is

These skills were extracted from real work on production WordPress sites — sites that take
orders, where a bad deploy costs money the same afternoon. Every rule in here exists because
something went wrong first. Where a rule came from a specific failure, the failure is written
down next to it, because a rule without its reason is a rule people work around.

Three skills, three moments in the same job:

| Skill | Use it when | Core idea |
|---|---|---|
| **`wp-delivery`** | editing a theme/plugin and shipping it to a live host | Prove local matches host *before* editing. Deploy in ordered batches. Never open a live file in write mode. |
| **`wp-code-cleaner`** | auditing or deleting dead code | Deleting is easy; *proving the deletion broke nothing* is the work. Four verification tiers, each calibrated against a known-bad case. |
| **`wp-corewebvital`** | optimizing Core Web Vitals on LiteSpeed | Safe-first: only settings that can't break the site, no third-party services. |

They compose: audit with `wp-code-cleaner`, ship with `wp-delivery`, then tune speed with
`wp-corewebvital`. But each stands alone.

## The idea worth stealing, even if you never install this

**A check you haven't calibrated is not a check.** Before trusting any test, feed it the
exact failure it's supposed to catch. If the broken case also passes, the tool is blind and
every green result it gives you is worse than no result — it manufactures confidence.

This sounds obvious and gets violated constantly, because the easy calibration case is
usually too weak. Two real examples from the sessions these skills came from:

- A PHP function cutter was "verified" by building a version cut one line short and expecting
  `php -l` to fail. It **passed** — the last line of the cut region was blank, so dropping it
  broke nothing. The real calibration case is leaving an **orphan closing brace**.
- A CSS diff harness loaded a page twice with two stylesheets and compared computed styles.
  It reported *"0 elements differ"* — because a `<base href>` tag turned the relative
  stylesheet URL into a 404 and **neither** version loaded any CSS at all. Caught only
  because the deliberately-broken control case also reported 0.

Every script in this repo refuses to write until its own calibration case fails first.

## Install

Skills live in `~/.claude/skills/`. Clone and symlink, or copy:

```bash
git clone https://github.com/mediagyancy/wp-code-optimizer.git
cp -r wp-code-optimizer/skills/* ~/.claude/skills/
```

Then in Claude Code: `/wp-delivery`, `/wp-code-cleaner`, `/wp-corewebvital`.

Claude also picks them up on its own when you describe a matching task — the `description`
field in each `SKILL.md` is what drives that.

## Requirements

- **Python 3.8+** — standard library only, nothing to install
- **PHP CLI** — for `php -l` syntax checks
- **Node** *(optional)* — for `node --check` on JavaScript
- **PHPCS + PHPStan** *(optional)* — point `WP_QUALITY_TOOLS` at your `vendor/bin`, or
  leave it unset and the scripts look in `PATH`. Deliberately kept outside your site repo:
  a 40 MB `vendor/` folder has no business anywhere near production.

## Scripts

Every script is standalone — run them without Claude if you like.

**`wp-code-cleaner/scripts/`**

| Script | What it does |
|---|---|
| `quet_chet.py` | Reachability graph over a theme: orphan files, uncalled functions, suspect CSS classes. Read-only. |
| `go_ham.py` | Removes PHP functions by brace balance, not string markers. Self-calibrates with `php -l`. |
| `go_css.py` | Removes dead rules *and* dead comma-separated selector parts. Three structural checks. |
| `doi_chung_live.py` | Checks removed classes against **real production HTML**, and probes whether deleted files are actually gone. |
| `dung_so_computed.py` | Builds a per-element computed-style diff harness from real production pages. |

**`wp-delivery/scripts/`**

| Script | What it does |
|---|---|
| `wp_freshness.py` | Hash-compares public assets against the live host; normalizes CRLF/LF first. |
| `wp_safe_write.py` | Atomic writes: backup → temp → check → rename. Refuses empty or syntactically broken output. |
| `wp_patch.py` | String patching that throws unless the anchor is unique. |
| `wp_quality.py` | PHPCS/PHPStan wrapper that reports each check separately and fails closed on missing tools. |
| `wp_module_size.py` | File-size gate with a baseline, so legacy files can't quietly grow. |
| `wp_urlwatch.py` | Watches critical URLs for marker strings — HTTP 200 alone proves nothing. |

## What these skills refuse to do

- **Claim a check passed when it didn't run.** A missing tool is `UNAVAILABLE` and blocks —
  never silently "no errors found".
- **Promise speed gains that weren't measured.** Wrapping admin files in `is_admin()` is a
  scope improvement, not a performance one; OPcache makes the load cost ~zero.
- **Decide product questions.** An admin screen that controls a section nobody renders is a
  question for the site owner, not a cleanup target.

## License

MIT — see [LICENSE](LICENSE). Not affiliated with WordPress, Automattic, LiteSpeed, or Anthropic.

---
---

# WP Code Optimizer — bản tiếng Việt

**Ba skill cho Claude Code, dùng khi làm việc trên site WordPress đang chạy thật: đưa thay
đổi lên host mà không làm sập, dọn code chết mà chứng minh được, và tối ưu Core Web Vitals.**

## Đây là cái gì

Ba skill này rút ra từ việc làm thật trên các site WordPress đang bán hàng — nơi một lần
deploy hỏng là mất tiền ngay chiều hôm đó. Gần như mọi luật trong đây tồn tại vì **đã có
chuyện xảy ra trước**. Chỗ nào luật sinh ra từ một ca hỏng cụ thể thì ca đó được ghi ngay
bên cạnh, vì một luật không kèm lý do là một luật người ta sẽ lách.

| Skill | Dùng khi | Ý chính |
|---|---|---|
| **`wp-delivery`** | sửa theme/plugin rồi đưa lên host thật | Chứng minh local khớp host **trước khi** sửa. Deploy theo đợt có thứ tự. Không bao giờ mở file sống ở chế độ ghi. |
| **`wp-code-cleaner`** | soát hoặc xoá code chết | Xoá thì dễ; **chứng minh xoá không hỏng gì** mới là việc. Bốn tầng xác minh, tầng nào cũng phải hiệu chuẩn bằng ca hỏng đã biết. |
| **`wp-corewebvital`** | tối ưu CWV trên LiteSpeed | An toàn trước: chỉ dùng setting không thể làm hỏng site, không phụ thuộc dịch vụ bên thứ ba. |

Ba cái ghép được với nhau: soát bằng `wp-code-cleaner`, giao hàng bằng `wp-delivery`, rồi
tối ưu tốc độ bằng `wp-corewebvital`. Nhưng dùng riêng từng cái cũng được.

## Điều đáng lấy nhất, kể cả khi anh không cài skill

**Phép kiểm chưa hiệu chuẩn thì không phải phép kiểm.** Trước khi tin bất kỳ phép kiểm nào,
cho nó chạy qua đúng ca hỏng mà nó phải bắt. Nếu ca hỏng cũng PASS thì phép kiểm đang mù, và
mọi kết quả xanh nó đưa ra còn tệ hơn không kiểm — nó chế ra cảm giác an toàn.

Nghe hiển nhiên, và bị vi phạm liên tục, vì ca hiệu chuẩn dễ dựng thường quá yếu. Hai ca thật
từ chính những phiên làm việc sinh ra bộ skill này:

- Một script cắt hàm PHP được "kiểm" bằng cách dựng bản cắt hụt một dòng rồi chờ `php -l`
  báo lỗi. Nó **PASS** — dòng cuối vùng cắt là dòng trống, bỏ hụt nó chẳng sai gì. Ca hiệu
  chuẩn đúng phải là **bỏ lại một dấu `}` mồ côi**.
- Một bộ so CSS nạp cùng một trang hai lần với hai stylesheet rồi so computed style. Nó báo
  *"0 phần tử lệch"* — vì thẻ `<base href>` biến đường dẫn CSS tương đối thành 404 và **cả
  hai bản đều không nạp được stylesheet nào**. Chỉ lộ ra nhờ ca đối chứng cố ý hỏng cũng báo 0.

Mọi script trong repo này đều **từ chối ghi** cho tới khi ca hiệu chuẩn của chính nó FAIL đúng.

## Cài

```bash
git clone https://github.com/mediagyancy/wp-code-optimizer.git
cp -r wp-code-optimizer/skills/* ~/.claude/skills/
```

Rồi gọi `/wp-delivery`, `/wp-code-cleaner`, `/wp-corewebvital`. Claude cũng tự nhận ra khi
anh mô tả một việc khớp — phần `description` trong mỗi `SKILL.md` lo chuyện đó.

## Cần gì

- **Python 3.8+** — chỉ dùng thư viện chuẩn, không phải cài thêm gì
- **PHP CLI** — để chạy `php -l`
- **Node** *(tuỳ)* — để `node --check` cho JavaScript
- **PHPCS + PHPStan** *(tuỳ)* — trỏ biến `WP_QUALITY_TOOLS` vào `vendor/bin` của anh, hoặc
  để trống thì script tự tìm trong `PATH`. Cố ý để **ngoài** repo của site: thư mục `vendor/`
  40 MB không có việc gì ở gần production.

## Ba điều những skill này từ chối làm

- **Báo đạt khi phép kiểm chưa chạy.** Thiếu công cụ là `UNAVAILABLE` và **chặn**, không bao
  giờ đọc thành "không thấy lỗi".
- **Hứa tốc độ chưa đo.** Bọc file admin trong `is_admin()` là giảm phạm vi, không phải tăng
  tốc — OPcache làm chi phí đó gần bằng không.
- **Tự quyết chuyện sản phẩm.** Một màn hình cài đặt điều khiển section không ai hiển thị là
  câu hỏi cho chủ site, không phải mục tiêu để xoá.

## Giấy phép

MIT — xem [LICENSE](LICENSE). Không liên kết với WordPress, Automattic, LiteSpeed hay Anthropic.
