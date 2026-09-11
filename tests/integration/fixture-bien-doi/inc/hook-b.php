<?php
/** Nửa sau của ca "đổi THỨ TỰ ĐĂNG KÝ ở cùng priority". Xem `hook-a.php`. */

defined( 'ABSPATH' ) || exit;

add_action( 'init', 'fxb_init_b', 20 );

function fxb_init_b() {
	$GLOBALS['fxb_vet'] = ( $GLOBALS['fxb_vet'] ?? '' ) . 'b';
}
