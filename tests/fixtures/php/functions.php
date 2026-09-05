<?php
/**
 * Fixture: các dạng require/include thật hay gặp trong theme WordPress.
 *
 * Mỗi dòng dưới đây là một dạng mà bộ quét PHẢI nhìn thấy. Thiếu một dạng là
 * một file bị báo chết oan, và người dùng tin theo thì xoá mất code đang chạy.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

define( 'FX_DIR', get_template_directory() );

require_once __DIR__ . '/inc/qua-dir.php';
require_once FX_DIR . '/inc/qua-hang-so.php';
require_once get_template_directory() . '/inc/qua-ham.php';
require_once 'inc/duong-dan-tran.php';
require( FX_DIR . '/inc/require-khong-once.php' );
include_once FX_DIR . '/inc/qua-include-once.php';

if ( class_exists( 'WooCommerce' ) ) {
	require_once FX_DIR . '/inc/co-dieu-kien.php';
	require_once FX_DIR . '/inc/co-ham-js.php';
}

/* Bẫy: chữ "required" trong chuỗi và trong HTML KHÔNG phải câu require.
   Bản đầu của bộ quét khớp nhầm chúng, ra 25 câu "không phân giải được" trong
   khi thật chỉ có 1. */
$fx_field = array( 'required' => false, 'type' => 'text' );
?>
<input type="text" required>
<p>This feature is required for checkout.</p>
<?php

/* require động: KHÔNG phân giải tĩnh được. Bộ quét phải ĐẾM và BÁO, không im lặng. */
$fx_tep = FX_DIR . '/inc/dong.php';
require_once $fx_tep;
