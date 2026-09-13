<?php
/**
 * Ca "dời `get_template_part` sang ĐIỂM KHÁC trong lifecycle" — lỗi refactor số 5.
 *
 * `bo-phan.php` gọi `wp_enqueue_style()`. Gọi nó SAU `wp_head()` là quá muộn: hàng đợi
 * style đã được in xong, nên style ấy không bao giờ ra `<head>`. Site không lỗi, `php -l`
 * sạch, không một dòng cảnh báo nào — chỉ là một phần giao diện mất style.
 *
 * Ở bản đúng, template part được gọi TRƯỚC `wp_head()`. Dời nó xuống sau là ca hỏng.
 * Đây là đúng họ lỗi "mất style im lặng" mà `cam-bay.md` mục 6 đã trả giá.
 */

defined( 'ABSPATH' ) || exit;
?>
<!DOCTYPE html>
<html <?php language_attributes(); ?>>
<head>
	<meta charset="<?php bloginfo( 'charset' ); ?>">
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<?php get_template_part( 'template-parts/bo-phan' ); ?>
	<?php wp_head(); ?>
</head>
<body <?php body_class(); ?>>
<header class="fxb-dau">
	<p class="fxb-dau__ten"><?php bloginfo( 'name' ); ?></p>
</header>
