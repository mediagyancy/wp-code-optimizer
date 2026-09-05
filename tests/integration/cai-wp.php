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

echo 'WooCommerce class_exists: ', class_exists( 'WooCommerce' ) ? 'co' : 'KHONG', "\n";
