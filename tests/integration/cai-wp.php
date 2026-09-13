<?php
/**
 * Cài WordPress cho integration test, rồi kích hoạt WooCommerce và theme fixture.
 * Chạy một lần; chạy lại thì bỏ qua phần đã xong.
 */
define( 'WP_INSTALLING', true );
$_SERVER['HTTP_HOST']   = 'localhost:8899';
$_SERVER['REQUEST_URI'] = '/';
$_SERVER['SERVER_NAME'] = 'localhost';
$_SERVER['REQUEST_METHOD'] = 'GET';

require __DIR__ . '/site/wp-load.php';
require_once ABSPATH . 'wp-admin/includes/upgrade.php';
require_once ABSPATH . 'wp-admin/includes/plugin.php';

if ( ! is_blog_installed() ) {
	$r = wp_install( 'Fixture Site', 'admin', 'it@example.test', true, '', 'matkhau-it' );
	echo "WordPress: da cai, user_id={$r['user_id']}\n";
} else {
	echo "WordPress: da cai tu truoc\n";
}

$kq = activate_plugin( 'woocommerce/woocommerce.php' );
echo 'WooCommerce: ', is_wp_error( $kq ) ? 'LOI ' . $kq->get_error_message() : 'da kich hoat', "\n";

switch_theme( 'fixture-theme' );
echo 'Theme: ', get_stylesheet(), "\n";

// Lần chạy ĐẦU: activate_plugin() include file plugin nên class có ngay. Lần chạy LẠI:
// plugin đã active nên activate_plugin() không include gì, và WP_INSTALLING=true làm
// wp_get_active_and_valid_plugins() trả rỗng → class_exists() = false dù site hoàn toàn
// tốt. Ca thật 13/09/2026: dung_wp.py báo "KHÔNG dựng được" trên site đang chạy 14/14
// test. Nên khi plugin đã active mà class chưa có thì nạp tường minh rồi mới hỏi.
if ( ! class_exists( 'WooCommerce' ) && is_plugin_active( 'woocommerce/woocommerce.php' ) ) {
	include_once WP_PLUGIN_DIR . '/woocommerce/woocommerce.php';
}
echo 'WooCommerce class_exists: ', class_exists( 'WooCommerce' ) ? 'co' : 'KHONG', "\n";
