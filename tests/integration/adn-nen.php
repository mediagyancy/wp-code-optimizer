<?php
/**
 * ADN NỀN — dấu vân tay CÓ THỨ TỰ của bề mặt quan sát được, lấy từ một WordPress
 * đang chạy thật.
 *
 * Khác `su-that-nen.php` ở đúng một điểm, và điểm đó là toàn bộ lý do file này tồn tại:
 * `su-that-nen.php` trả lời "tool báo chết có đúng không" — nó kiểm THÀNH VIÊN.
 * File này trả lời "hành vi có đổi không" — nên nó phải giữ THỨ TỰ.
 *
 * Vì sao thứ tự là bắt buộc: WordPress gọi callback cùng priority theo ĐÚNG THỨ TỰ
 * ĐĂNG KÝ. Một phép refactor dời hook sang file khác không đổi tập hook, không đổi
 * priority, không đổi một dòng markup nào — nhưng đổi thứ tự chạy. Phép kiểm theo
 * tập mù hoàn toàn trước ca đó. Đó là một trong sáu ca mà cả bốn tầng cũ đều bỏ lọt.
 *
 * Năm mặt được chụp:
 *   1. file theme được nạp       — THỨ TỰ NẠP THẬT (get_included_files)
 *   2. đăng ký hook              — (hook, priority, thứ tự trong bucket, callback, file:dòng)
 *   3. chuỗi hook fire           — THỨ TỰ THỰC THI THẬT (meta-hook 'all')
 *   4. registry script/style     — handle + mảng dependency + src + ver, giữ thứ tự
 *   5. chữ ký hàm của theme      — tên -> tham số có thứ tự kèm giá trị mặc định
 *   + HTML thô, KHÔNG mask ở đây
 *
 * HTML cố ý để thô: việc mask token động (nonce, timestamp, id) làm ở phía Python,
 * nơi mỗi mask phải mang lý do và nằm trong version control. Mask chôn trong PHP là
 * một vùng mù không ai soát được — và mỗi vùng mask là một chỗ regression vô hình
 * BẰNG CẤU TRÚC, nên nó phải để lại dấu.
 *
 * Dùng:  php adn-nen.php [--theme-slug=fixture-theme] [--giai-doan=render]
 */

$tuy_chon = array( 'theme-slug' => '', 'giai-doan' => 'render' );
foreach ( array_slice( $argv, 1 ) as $tham_so ) {
	if ( preg_match( '/^--([a-z-]+)=(.*)$/', $tham_so, $m ) ) {
		$tuy_chon[ $m[1] ] = $m[2];
	}
}

$_SERVER['HTTP_HOST']      = 'localhost:8899';
$_SERVER['SERVER_NAME']    = 'localhost';
$_SERVER['REQUEST_METHOD'] = 'GET';
$_SERVER['REQUEST_URI']    = '/';
$_SERVER['SCRIPT_NAME']    = '/index.php';

/* ───── bắt chuỗi hook fire. Phải đăng ký 'all' TRƯỚC khi render, nếu không thì
   chính phép đo bỏ mất giai đoạn mình cần đo nhất. */
$GLOBALS['adn_chuoi_fire'] = array();
$GLOBALS['adn_dang_ghi']   = false;

function adn_ghi_nhan_fire() {
	if ( ! empty( $GLOBALS['adn_dang_ghi'] ) ) {
		$GLOBALS['adn_chuoi_fire'][] = current_filter();
	}
}

ob_start();
require __DIR__ . '/site/wp-load.php';
ob_end_clean();

/**
 * Đổi theme đang kích hoạt nếu được yêu cầu.
 *
 * Phải FAIL-CLOSED: nếu slug truyền vào không khớp theme thật sự đang active sau khi
 * switch thì THOÁT, không chụp. Chụp nhầm theme rồi so với baseline của theme khác sẽ
 * cho ra một diff khổng lồ trông như regression — tức phép đo tự sinh ra báo động sai,
 * đúng loại làm người ta mất tin vào nó.
 */
if ( $tuy_chon['theme-slug'] !== '' ) {
	if ( get_template() !== $tuy_chon['theme-slug'] ) {
		switch_theme( $tuy_chon['theme-slug'] );
		// switch_theme không nạp lại functions.php của theme mới trong cùng request.
		// Phải chạy lại tiến trình; báo ra để bên gọi biết mà chạy lượt hai.
		echo wp_json_encode( array(
			'loi'        => 'CAN_CHAY_LAI',
			'theme_moi'  => $tuy_chon['theme-slug'],
			'giai_thich' => 'switch_theme da doi theme nhung functions.php cua theme moi khong duoc nap trong cung request. Chay lai lenh nay.',
		) );
		exit( 75 );
	}
}

$theme     = wp_normalize_path( get_template_directory() );
$theme_dir = rtrim( $theme, '/' ) . '/';

if ( $tuy_chon['theme-slug'] !== '' && basename( rtrim( $theme_dir, '/' ) ) !== $tuy_chon['theme-slug'] ) {
	echo wp_json_encode( array(
		'loi'      => 'THEME_KHONG_KHOP',
		'yeu_cau'  => $tuy_chon['theme-slug'],
		'thuc_te'  => basename( rtrim( $theme_dir, '/' ) ),
	) );
	exit( 76 );
}

/**
 * Biến một callable bất kỳ thành một định danh ỔN ĐỊNH + file:dòng.
 *
 * Ổn định nghĩa là: cùng một callback thì cùng một chuỗi giữa hai lần chạy. Closure
 * không có tên nên phải định danh bằng file:dòng khai báo — nếu dùng spl_object_hash
 * thì nó đổi mỗi lần chạy và diff sẽ báo lệch ở MỌI lượt, tức phép đo tự làm mình vô
 * dụng.
 */
function adn_mo_ta_callback( $cb, $theme_dir ) {
	$ten  = '?';
	$file = null;
	$dong = null;
	try {
		if ( is_string( $cb ) ) {
			$ten = $cb;
			if ( strpos( $cb, '::' ) !== false ) {
				list( $c, $m ) = explode( '::', $cb, 2 );
				$r    = new ReflectionMethod( $c, $m );
			} else {
				$r = new ReflectionFunction( $cb );
			}
		} elseif ( $cb instanceof Closure ) {
			$r   = new ReflectionFunction( $cb );
			$ten = 'Closure';
		} elseif ( is_array( $cb ) && count( $cb ) === 2 ) {
			$lop = is_object( $cb[0] ) ? get_class( $cb[0] ) : (string) $cb[0];
			$ten = $lop . ( is_object( $cb[0] ) ? '->' : '::' ) . $cb[1];
			$r   = new ReflectionMethod( $lop, $cb[1] );
		} elseif ( is_object( $cb ) && method_exists( $cb, '__invoke' ) ) {
			$ten = get_class( $cb ) . '->__invoke';
			$r   = new ReflectionMethod( $cb, '__invoke' );
		} else {
			return array( 'ten' => $ten, 'file' => null, 'dong' => null );
		}
		$f    = wp_normalize_path( (string) $r->getFileName() );
		$dong = $r->getStartLine();
		$file = ( $f && strpos( $f, $theme_dir ) === 0 )
			? substr( $f, strlen( $theme_dir ) )
			: adn_rut_gon_ngoai( $f );
	} catch ( Throwable $e ) {
		// Không phản chiếu được thì nói là không phản chiếu được. Không đoán.
		return array( 'ten' => $ten, 'file' => 'KHONG_PHAN_CHIEU_DUOC', 'dong' => null );
	}
	if ( $ten === 'Closure' && $file ) {
		$ten = 'Closure@' . $file . ':' . $dong;
	}
	return array( 'ten' => $ten, 'file' => $file, 'dong' => $dong );
}

/** File ngoài theme: chỉ giữ phần sau wp-content để đường dẫn máy không lọt vào artefact. */
function adn_rut_gon_ngoai( $f ) {
	if ( ! $f ) {
		return null;
	}
	$i = strpos( $f, '/wp-content/' );
	if ( $i !== false ) {
		return '…' . substr( $f, $i );
	}
	$i = strpos( $f, '/wp-includes/' );
	if ( $i !== false ) {
		return '…' . substr( $f, $i );
	}
	$i = strpos( $f, '/wp-admin/' );
	return $i !== false ? '…' . substr( $f, $i ) : '…/' . basename( $f );
}

/** File theme đã nạp, GIỮ THỨ TỰ NẠP (array_unique giữ lần xuất hiện đầu). */
function adn_file_theme_da_nap( $theme_dir ) {
	$ra = array();
	foreach ( get_included_files() as $f ) {
		$f = wp_normalize_path( $f );
		if ( strpos( $f, $theme_dir ) === 0 ) {
			$ra[] = substr( $f, strlen( $theme_dir ) );
		}
	}
	return array_values( array_unique( $ra ) );
}

/**
 * Đi hết $wp_filter, GIỮ cả priority và thứ tự trong bucket.
 *
 * Tên hook thì ksort để thứ tự khoá của mảng PHP không tự sinh ra noise; nhưng
 * BÊN TRONG một hook thì tuyệt đối không sort — priority đi từ thấp lên cao đúng
 * như `do_action` chạy, và thứ tự trong cùng một bucket chính là thứ tự đăng ký.
 * Sort chỗ đó là xoá đúng cái tín hiệu mình cần.
 */
function adn_dang_ky_hook( $theme_dir, $chi_theme ) {
	global $wp_filter;
	$ra = array();
	$ten_hook = array_keys( (array) $wp_filter );
	sort( $ten_hook, SORT_STRING );
	foreach ( $ten_hook as $hook ) {
		$doi_tuong = $wp_filter[ $hook ];
		if ( ! ( $doi_tuong instanceof WP_Hook ) ) {
			continue;
		}
		$priorities = array_keys( $doi_tuong->callbacks );
		sort( $priorities, SORT_NUMERIC );
		foreach ( $priorities as $uu_tien ) {
			$thu_tu = 0;
			foreach ( $doi_tuong->callbacks[ $uu_tien ] as $muc ) {
				$mo_ta = adn_mo_ta_callback( $muc['function'], $theme_dir );
				$thu_tu++;
				$la_theme = $mo_ta['file'] !== null
					&& strpos( (string) $mo_ta['file'], '…' ) !== 0
					&& $mo_ta['file'] !== 'KHONG_PHAN_CHIEU_DUOC';
				if ( $chi_theme && ! $la_theme ) {
					continue;
				}
				$ra[] = array(
					'hook'     => $hook,
					'uu_tien'  => (int) $uu_tien,
					'thu_tu'   => $thu_tu,
					'callback' => $mo_ta['ten'],
					'file'     => $mo_ta['file'],
					'dong'     => $mo_ta['dong'],
					'so_tham_so' => isset( $muc['accepted_args'] ) ? (int) $muc['accepted_args'] : null,
				);
			}
		}
	}
	return $ra;
}

/**
 * Registry script/style — CHỈ phần mang thông tin quyết định, giữ thứ tự.
 *
 * Dump cả `registered` là sai hướng: trên một WordPress + WooCommerce thật nó ra hơn
 * 300 handle của core và Woo, phình artefact mà không nói gì về theme. Tệ hơn, nó làm
 * người đọc diff phải lội qua 300 dòng không liên quan để tìm một dòng có liên quan —
 * và một phép đo mà người ta ngừng đọc là một phép đo đã chết.
 *
 * Hai mặt được giữ, vì hai mặt này là nơi ca hỏng xuất hiện:
 *   · `queue`  — handle THỰC SỰ được enqueue, THEO THỨ TỰ. Đây là mặt bắt được ca dời
 *                `get_template_part` sang điểm khác trong lifecycle, và ca một lệnh
 *                inline script phá chiến lược defer rồi lan theo cây dependency.
 *   · `theme`  — handle do chính theme đăng ký (src trỏ vào theme), kèm deps/ver.
 */
function adn_registry( $doi_tuong, $theme_dir ) {
	$ra = array( 'queue' => array(), 'theme' => array() );
	if ( ! $doi_tuong ) {
		return $ra;
	}
	$ra['queue'] = array_values( (array) ( $doi_tuong->queue ?? array() ) );
	$goc_theme   = str_replace( wp_normalize_path( ABSPATH ), '/', $theme_dir );
	foreach ( (array) ( $doi_tuong->registered ?? array() ) as $handle => $m ) {
		$src = $m->src ? preg_replace( '#^https?://[^/]+#', '', (string) $m->src ) : '';
		if ( $src === '' || strpos( $src, rtrim( $goc_theme, '/' ) ) === false ) {
			continue;
		}
		$ra['theme'][] = array(
			'handle' => (string) $handle,
			'deps'   => array_values( (array) ( $m->deps ?? array() ) ),
			'src'    => $src,
			'ver'    => $m->ver === null ? null : (string) $m->ver,
			'extra'  => array_keys( (array) ( $m->extra ?? array() ) ),
		);
	}
	return $ra;
}

/**
 * Chữ ký hàm do theme khai báo: tên -> tham số CÓ THỨ TỰ kèm giá trị mặc định.
 *
 * Đây là mặt bắt được ca "tách hàm ra với giá trị mặc định khác" — ca mà `php -l`
 * sạch, markup y nguyên, và cả bốn tầng cũ đều không hỏi tới.
 */
function adn_chu_ky_ham( $theme_dir ) {
	$ra = array();
	$ham = get_defined_functions();
	foreach ( $ham['user'] as $ten ) {
		try {
			$r = new ReflectionFunction( $ten );
			$f = wp_normalize_path( (string) $r->getFileName() );
			if ( ! $f || strpos( $f, $theme_dir ) !== 0 ) {
				continue;
			}
			$tham_so = array();
			foreach ( $r->getParameters() as $p ) {
				$mac_dinh = 'KHONG_CO';
				if ( $p->isDefaultValueAvailable() ) {
					try {
						$mac_dinh = var_export( $p->getDefaultValue(), true );
					} catch ( Throwable $e ) {
						$mac_dinh = 'KHONG_DOC_DUOC';
					}
				}
				$tham_so[] = array(
					'ten'       => $p->getName(),
					'mac_dinh'  => $mac_dinh,
					'bat_buoc'  => ! $p->isOptional(),
					'kieu'      => $p->hasType() ? (string) $p->getType() : null,
				);
			}
			$ra[] = array(
				'ten'     => $ten,
				'file'    => substr( $f, strlen( $theme_dir ) ),
				'dong'    => $r->getStartLine(),
				'tham_so' => $tham_so,
			);
		} catch ( Throwable $e ) {
			continue;
		}
	}
	usort( $ra, function ( $a, $b ) {
		return strcmp( $a['ten'], $b['ten'] );
	} );
	return $ra;
}

/* ───── 1. trước render: file đã nạp bởi bootstrap + functions.php */
$nap_truoc_render = adn_file_theme_da_nap( $theme_dir );

/* ───── 2. render, có ghi chuỗi hook fire.
 *
 * PHẢI gọi `wp()` trước khi render, và đây không phải chi tiết kỹ thuật nhỏ.
 *
 * Bản đầu của file này dựng một `WP_Query` bằng tay rồi require thẳng `index.php`. Nó
 * chạy sạch và ra HTML trông đúng — nhưng nó BỎ QUA toàn bộ giai đoạn `wp()`: main
 * query, `parse_request`, `send_headers`, và các hook `wp` / `template_redirect`.
 *
 * Hậu quả đo được: ca tiêm "đảo chiều điều kiện" KHÔNG mặt nào bắt được, vì callback
 * bị đảo chiều treo trên hook `wp` — hook chưa bao giờ fire, nên nó không chạy ở CẢ
 * bản đúng lẫn bản hỏng, và hiệu bằng rỗng một cách giả tạo. Phép đo khi ấy đang nhìn
 * vào chỗ mà hai nguyên nhân đều cho ra cùng một cảnh.
 *
 * Đây đúng là loại vùng mù mà `xac-minh.md` cảnh báo, và nó chỉ lộ ra nhờ ca hiệu
 * chuẩn. Nếu chỉ chạy bản đúng rồi thấy "0 lệch" thì đã kết luận ngược.
 */
add_action( 'all', 'adn_ghi_nhan_fire', 0 );
$GLOBALS['adn_dang_ghi'] = true;

ob_start();
wp();
require $theme_dir . 'index.php';
$html = ob_get_clean();

$GLOBALS['adn_dang_ghi'] = false;
remove_action( 'all', 'adn_ghi_nhan_fire', 0 );

/* ───── 3. sau render: mọi mặt còn lại.
   Đi $wp_filter ĐÚNG MỘT LẦN rồi lọc — gọi hai lần thì phản chiếu hơn 2.400 callback
   hai lượt, và tệ hơn là hai lượt có thể ra khác nhau nếu có gì đăng ký ở giữa. */
$nap_sau_render = adn_file_theme_da_nap( $theme_dir );
$hook_tat_ca    = adn_dang_ky_hook( $theme_dir, false );
$hook_theme     = array_values( array_filter( $hook_tat_ca, function ( $h ) {
	return $h['file'] !== null
		&& strpos( (string) $h['file'], '…' ) !== 0
		&& $h['file'] !== 'KHONG_PHAN_CHIEU_DUOC';
} ) );

echo wp_json_encode(
	array(
		'phien_ban' => 1,
		'moi_truong' => array(
			'php'         => PHP_VERSION,
			'wp'          => get_bloginfo( 'version' ),
			'woo'         => class_exists( 'WooCommerce' ) ? 'co' : 'khong',
			'theme_slug'  => basename( $theme_dir ),
		),
		/* 1 — THỨ TỰ NẠP, không phải tập */
		'file_nap_truoc_render' => $nap_truoc_render,
		'file_nap_sau_render'   => $nap_sau_render,
		/* 2 — priority + thứ tự trong bucket */
		'hook_theme'            => $hook_theme,
		'hook_tong_so'          => count( $hook_tat_ca ),
		/* 3 — THỨ TỰ FIRE THẬT */
		'chuoi_fire'            => $GLOBALS['adn_chuoi_fire'],
		/* 4 — registry, giữ thứ tự */
		'scripts'               => adn_registry( $GLOBALS['wp_scripts'] ?? null, $theme_dir ),
		'styles'                => adn_registry( $GLOBALS['wp_styles'] ?? null, $theme_dir ),
		/* 5 — chữ ký hàm kèm giá trị mặc định */
		'chu_ky_ham'            => adn_chu_ky_ham( $theme_dir ),
		/* HTML thô — mask làm ở phía Python, có lý do, trong version control */
		'html_tho'              => $html,
		'html_do_dai'           => strlen( $html ),
	),
	JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE
);
