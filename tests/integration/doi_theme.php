<?php
/**
 * Đổi theme đang kích hoạt của site test, rồi thoát. Không chụp gì.
 *
 * Vì sao cần file này: `adn-nen.php --theme-slug=X` gọi `switch_theme( X )` và để
 * nguyên — đúng thiết kế, vì nó cần theme đó ở request kế tiếp. Nhưng hệ quả là bộ test
 * nào chạy SAU nó mà không tự đặt theme sẽ chụp nhầm theme của bộ trước. Ca thật: chạy
 * `test_cong_graph.py` rồi `test_integration.py` → `fxt-bac--1` không còn trong HTML vì
 * site đang ở `fixture-bien-doi`, và khẳng định "class ghép chuỗi được giữ" đỏ.
 *
 * CI đã xanh chỉ vì thứ tự job — đúng loại "xanh nhờ may" mà CHANGELOG v0.5.0 ghi cho
 * `kiem_rieng_tu.py`. Từ nay mỗi bộ test tự bảo đảm tiền đề của mình bằng file này.
 *
 *     php doi_theme.php --theme-slug=fixture-theme
 *
 * In một dòng JSON: {"truoc": ..., "sau": ..., "doi": true|false}. Exit 0 nếu sau khi
 * chạy theme kích hoạt đúng là theme yêu cầu; 2 nếu không.
 */

$slug = '';
foreach ( array_slice( $argv, 1 ) as $tham_so ) {
	if ( preg_match( '/^--theme-slug=(.+)$/', $tham_so, $m ) ) {
		$slug = $m[1];
	}
}
if ( $slug === '' ) {
	fwrite( STDERR, "USAGE: php doi_theme.php --theme-slug=<slug>\n" );
	exit( 1 );
}

$_SERVER['HTTP_HOST']      = 'localhost:8899';
$_SERVER['SERVER_NAME']    = 'localhost';
$_SERVER['REQUEST_METHOD'] = 'GET';
$_SERVER['REQUEST_URI']    = '/';
$_SERVER['SCRIPT_NAME']    = '/index.php';

ob_start();
require __DIR__ . '/site/wp-load.php';
ob_end_clean();

$truoc = get_stylesheet();
$doi   = false;
if ( $truoc !== $slug ) {
	if ( ! wp_get_theme( $slug )->exists() ) {
		echo wp_json_encode( array( 'truoc' => $truoc, 'loi' => 'theme khong ton tai: ' . $slug ) ), "\n";
		exit( 2 );
	}
	switch_theme( $slug );
	$doi = true;
}

// Đọc lại từ option, không tin biến trong bộ nhớ: switch_theme ghi DB, và đây là
// cái mà request KẾ TIẾP sẽ thấy.
wp_cache_flush();
$sau = get_option( 'stylesheet' );
echo wp_json_encode( array( 'truoc' => $truoc, 'sau' => $sau, 'doi' => $doi ) ), "\n";
exit( $sau === $slug ? 0 : 2 );
