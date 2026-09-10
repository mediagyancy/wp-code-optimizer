<?php
/**
 * Ca "đổi PRIORITY" — lỗi refactor số 2.
 *
 * Priority 5 ở đây không phải số ngẫu nhiên: nó đặt callback này chạy TRƯỚC phần lớn
 * callback core của `wp_head` (core dùng mặc định 10). Đổi 5 thành 50 là đổi vị trí thẻ
 * meta trong `<head>`.
 *
 * Ca này cố ý CÓ in ra, vì nó kiểm một thứ khác: nó cho biết phép so HTML có bắt được
 * thay đổi THỨ TỰ trong cùng một tài liệu hay không — tức HTML phải được so TOÀN VĂN
 * theo byte, không phải so tập thẻ hay tập class. So tập thì ca này lọt.
 */

defined( 'ABSPATH' ) || exit;

add_action( 'wp_head', 'fxb_meta_som', 5 );

function fxb_meta_som() {
	echo '<meta name="fxb-moc" content="som">' . "\n";
}
