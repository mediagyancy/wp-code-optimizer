<?php
/**
 * Ca "MẤT lời gọi sanitise khi dời code" — lỗi refactor số 4.
 *
 * `esc_html()` ở đây là thứ duy nhất ngăn một tham số URL đi thẳng vào HTML. Gỡ nó ra
 * thì trên request không có `?fxb_tim=` — tức đúng request mà bộ đo đang chụp — HTML
 * ra GIỐNG HỆT. Không mặt runtime nào thấy gì.
 *
 * Đây là lý do Tầng 5 không thể chỉ gồm các mặt runtime: phải có một mặt TĨNH đọc mã
 * nguồn và hỏi "mỗi điểm đọc superglobal có còn hàm sanitise bọc ngoài không". Mặt đó
 * nằm ở phía Python, vì nó không cần chạy WordPress mới trả lời được.
 */

defined( 'ABSPATH' ) || exit;

function fxb_tu_khoa() {
	return esc_html( wp_unslash( $_GET['fxb_tim'] ?? '' ) );
}
