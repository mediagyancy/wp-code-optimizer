<?php
/**
 * Nửa đầu của ca "đổi THỨ TỰ ĐĂNG KÝ ở cùng priority".
 *
 * Cố ý KHÔNG in gì ra HTML. Nếu nó in thì phép so HTML cũng bắt được ca này, và khi đó
 * ta không biết mặt `hook_theme` có thực sự cần thiết hay chỉ đang trùng lặp. Để chứng
 * minh mặt hook là LOAD-BEARING, phải có ít nhất một ca mà CHỈ nó bắt được.
 *
 * Nên hai callback chỉ nối vào một biến toàn cục, không render. Kết quả "ab" hay "ba"
 * không xuất hiện ở bất kỳ đâu trong markup.
 */

defined( 'ABSPATH' ) || exit;

add_action( 'init', 'fxb_init_a', 20 );

function fxb_init_a() {
	$GLOBALS['fxb_vet'] = ( $GLOBALS['fxb_vet'] ?? '' ) . 'a';
}
