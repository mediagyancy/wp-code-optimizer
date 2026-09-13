<?php
/**
 * File nạp chính. Theo đúng luật của repo, nó chỉ chứa guard, hằng số nền, require,
 * và một lời gọi khởi động — không chứa logic tính năng.
 *
 * THỨ TỰ REQUIRE Ở ĐÂY LÀ DỮ LIỆU, KHÔNG PHẢI HÌNH THỨC. `hook-a.php` và `hook-b.php`
 * cùng đăng ký lên `init` ở cùng priority 20; WordPress chạy callback cùng priority
 * theo ĐÚNG THỨ TỰ ĐĂNG KÝ, mà thứ tự đăng ký ở đây do thứ tự require quyết định.
 * Đảo hai dòng require là đổi hành vi — mà `php -l` sạch, markup không đổi một byte,
 * và cả bốn tầng xác minh cũ đều không hỏi tới. Đó là lỗi refactor số 1.
 */

defined( 'ABSPATH' ) || exit;

define( 'FXB_PHIEN_BAN', '1.0.0' );
define( 'FXB_DUONG_DAN', get_template_directory() );

require_once FXB_DUONG_DAN . '/inc/hook-a.php';
require_once FXB_DUONG_DAN . '/inc/hook-b.php';
require_once FXB_DUONG_DAN . '/inc/hook-dong.php';
require_once FXB_DUONG_DAN . '/inc/uu-tien.php';
require_once FXB_DUONG_DAN . '/inc/tham-so.php';
require_once FXB_DUONG_DAN . '/inc/loc-dau-vao.php';
require_once FXB_DUONG_DAN . '/inc/dieu-kien.php';

add_action( 'wp_enqueue_scripts', 'fxb_enqueue' );

function fxb_enqueue() {
	wp_enqueue_style(
		'fxb-main',
		get_template_directory_uri() . '/assets/css/main.css',
		array(),
		FXB_PHIEN_BAN
	);
}
