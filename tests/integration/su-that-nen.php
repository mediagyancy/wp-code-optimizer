<?php
/**
 * Lấy SỰ THẬT NỀN từ một WordPress đang chạy thật, có WooCommerce.
 *
 * Phân tích tĩnh chỉ ĐOÁN file nào được nạp và class nào xuất hiện. Ở đây hỏi
 * thẳng WordPress:
 *   · get_included_files()  -> file theme nào THỰC SỰ được nạp
 *   · HTML render ra        -> class nào THỰC SỰ xuất hiện
 *
 * Xuất JSON để bên Python so với kết luận của bộ quét.
 */
$_SERVER['HTTP_HOST']      = 'localhost:8899';
$_SERVER['SERVER_NAME']    = 'localhost';
$_SERVER['REQUEST_METHOD'] = 'GET';
$_SERVER['REQUEST_URI']    = '/';
$_SERVER['SCRIPT_NAME']    = '/index.php';

ob_start();
require __DIR__ . '/site/wp-load.php';
ob_end_clean();

$theme = wp_normalize_path( get_template_directory() );

/* 1. File của theme mà WordPress đã nạp tính tới lúc này (bootstrap + functions.php
      + mọi require nó kéo theo). */
$nap = array();
foreach ( get_included_files() as $f ) {
	$f = wp_normalize_path( $f );
	if ( strpos( $f, $theme ) === 0 ) {
		$nap[] = ltrim( substr( $f, strlen( $theme ) ), '/' );
	}
}

/* 2. Render trang chủ để lấy HTML thật và bắt thêm những file nạp lúc render
      (template, template-part). */
$html = '';
ob_start();
$q = new WP_Query( array( 'post_type' => 'post', 'posts_per_page' => 1 ) );
wp_reset_postdata();
require $theme . '/index.php';
$html = ob_get_clean();

$nap_sau = array();
foreach ( get_included_files() as $f ) {
	$f = wp_normalize_path( $f );
	if ( strpos( $f, $theme ) === 0 ) {
		$nap_sau[] = ltrim( substr( $f, strlen( $theme ) ), '/' );
	}
}

/* 3. Class thật sự có trong HTML render ra. */
$class = array();
if ( preg_match_all( '/class="([^"]*)"/', $html, $m ) ) {
	foreach ( $m[1] as $c ) {
		foreach ( preg_split( '/\s+/', trim( $c ) ) as $x ) {
			if ( $x !== '' ) {
				$class[ $x ] = true;
			}
		}
	}
}

/* 4. Hook thật sự đã đăng ký — bằng chứng cứng cho "file có hook mà không được nạp". */
global $wp_filter;
$co_hook_init = isset( $wp_filter['init'] ) &&
	in_array( 'fxt_khong_bao_gio_chay', array_keys( $wp_filter['init']->callbacks[10] ?? array() ), true );

echo wp_json_encode( array(
	'theme_dir'        => $theme,
	'file_da_nap'      => array_values( array_unique( $nap_sau ) ),
	'class_trong_html' => array_keys( $class ),
	'ham_ton_tai'      => array(
		'fxt_gia_woo'            => function_exists( 'fxt_gia_woo' ),
		'fxt_khong_bao_gio_chay' => function_exists( 'fxt_khong_bao_gio_chay' ),
	),
	'hook_init_dang_ky'  => $co_hook_init,
	'woocommerce_active' => class_exists( 'WooCommerce' ),
	'do_dai_html'        => strlen( $html ),
), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE );
