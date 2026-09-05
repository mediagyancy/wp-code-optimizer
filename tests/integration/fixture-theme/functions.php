<?php
/* Theme fixture cho integration test: mỗi file dưới đây đại diện một ca mà bộ
   phân tích tĩnh phải phân biệt được, và WordPress thật sẽ nói ai đúng ai sai. */
defined( 'ABSPATH' ) || exit;

define( 'FXT_DIR', get_template_directory() );

require_once __DIR__ . '/inc/qua-dir.php';
require_once FXT_DIR . '/inc/qua-hang-so.php';
require_once get_template_directory() . '/inc/qua-ham.php';
require_once 'inc/duong-dan-tran.php';
include_once FXT_DIR . '/inc/qua-include-once.php';

if ( class_exists( 'WooCommerce' ) ) {
	require_once FXT_DIR . '/inc/chi-khi-co-woo.php';
}

/* KHÔNG require inc/hook-khong-ai-nap.php — đó là ca thử. */

function fxt_enqueue() {
	wp_enqueue_style( 'fxt-main', get_template_directory_uri() . '/assets/css/main.css', array(), '1.0' );
}
add_action( 'wp_enqueue_scripts', 'fxt_enqueue' );

add_theme_support( 'woocommerce' );
