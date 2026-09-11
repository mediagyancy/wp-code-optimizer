<?php
/**
 * Ca "ĐẢO CHIỀU điều kiện" — lỗi refactor số 6.
 *
 * Điều kiện này canh một phép ĐĂNG KÝ HOOK, không canh một phép in. Đảo chiều nó thì
 * trên trang chủ filter không còn được đăng ký — nhưng filter ấy tác động lên một thứ
 * `index.php` không in ra, nên HTML không đổi.
 *
 * Mặt bắt được: `hook_theme` (callback biến mất khỏi danh sách đăng ký). Đây là ca
 * chứng minh mặt hook bắt được cả việc MẤT cạnh, không chỉ việc ĐỔI THỨ TỰ cạnh.
 */

defined( 'ABSPATH' ) || exit;

add_action( 'wp', 'fxb_dang_ky_co_dieu_kien' );

function fxb_dang_ky_co_dieu_kien() {
	if ( ! is_admin() ) {
		add_filter( 'fxb_he_so', 'fxb_he_so_mac_dinh' );
	}
}

function fxb_he_so_mac_dinh( $x ) {
	return $x * 2;
}
