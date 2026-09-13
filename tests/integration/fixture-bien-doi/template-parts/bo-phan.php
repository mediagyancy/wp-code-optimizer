<?php
/**
 * Template part CÓ TÁC DỤNG PHỤ: nó đăng ký và enqueue một style.
 *
 * Tác dụng phụ là chủ ý. Một template part chỉ in markup thì dời đi đâu cũng chỉ đổi
 * thứ tự markup, và phép so HTML toàn văn bắt được ngay. Part có tác dụng phụ lên hàng
 * đợi asset thì dời SAU `wp_head()` sẽ làm style biến mất khỏi `<head>` — một ca hỏng
 * nặng hơn nhiều mà nhìn bằng mắt trên đúng trang đang mở có thể không thấy.
 */

defined( 'ABSPATH' ) || exit;

wp_enqueue_style(
	'fxb-bo-phan',
	get_template_directory_uri() . '/assets/css/bo-phan.css',
	array( 'fxb-main' ),
	FXB_PHIEN_BAN
);
?>
<meta name="fxb-bo-phan" content="da-nap">
