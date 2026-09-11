<?php
/**
 * CA HIỆU CHUẨN CHO CỔNG GRAPH — hai cạnh mà phân tích tĩnh KHÔNG THỂ giải được.
 *
 * File này không tồn tại để làm tính năng. Nó tồn tại để chứng minh cổng
 * `cong_graph.py` thật sự bắt được vùng mù của đồ thị tĩnh. Không có nó thì cổng chỉ
 * từng chạy trên những theme mà đồ thị tĩnh vừa đúng — và một phép kiểm chưa bao giờ
 * gặp ca hỏng thì mọi PASS của nó là `NOT_TESTED`, không phải "đã kiểm".
 *
 * Hai dạng dưới đây là hai dạng phổ biến nhất trong WordPress thật, không phải hai ca
 * nhân tạo:
 *
 *   1. TÊN HOOK LÀ BIẾN. WordPress core dùng đầy họ hook ghép chuỗi —
 *      `save_post_{$post_type}`, `wp_ajax_{$action}`, `woocommerce_*`. Đọc mã nguồn
 *      thì chỉ thấy một biến, không thấy tên.
 *   2. TÊN CALLBACK GHÉP CHUỖI. Phân tích tĩnh thấy hai literal rời, không thấy hàm.
 *
 * Đồ thị tĩnh phải ĐẾM cả hai vào `dynamic_unresolved` chứ không được đoán — đoán ở
 * đây là bịa ra một cạnh, mà cạnh bịa tệ hơn cạnh thiếu: cạnh thiếu làm ta thận trọng,
 * cạnh bịa làm ta tự tin. Còn ADN runtime thì thấy cả hai, vì lúc chạy chúng là hai
 * callback thật trong `$wp_filter`.
 *
 * Khoảng lệch đúng 2 cạnh ấy là thứ cổng phải in ra. In ra được thì cổng sống; không
 * in ra được thì cổng mù và phải sửa cổng, không phải sửa file này.
 */

defined( 'ABSPATH' ) || exit;

$fxb_ten_hook = 'init';
add_action( $fxb_ten_hook, 'fxb_dong_a' );

add_action( 'init', 'fxb_' . 'dong_b' );

function fxb_dong_a() {
	$GLOBALS['fxb_dong'] = ( $GLOBALS['fxb_dong'] ?? '' ) . 'A';
}

function fxb_dong_b() {
	$GLOBALS['fxb_dong'] = ( $GLOBALS['fxb_dong'] ?? '' ) . 'B';
}
