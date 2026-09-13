<?php
/**
 * Template chính.
 *
 * Chú ý lời gọi `fxb_gia( 100, 1.1 )`: nó truyền ĐỦ hai tham số. Đó là lý do việc đổi
 * giá trị mặc định của `$ty_le` trong `inc/tham-so.php` không làm đổi một ký tự HTML
 * nào — và là lý do ca đó cần một mặt đo riêng.
 */

defined( 'ABSPATH' ) || exit;

get_header();
?>
<main class="fxb-than">
	<p class="fxb-gia"><?php echo esc_html( (string) fxb_gia( 100, 1.1 ) ); ?></p>
	<p class="fxb-tim"><?php echo fxb_tu_khoa(); ?></p>
	<?php if ( have_posts() ) : ?>
		<?php while ( have_posts() ) : the_post(); ?>
			<article class="fxb-bai">
				<h2 class="fxb-bai__ten"><?php the_title(); ?></h2>
			</article>
		<?php endwhile; ?>
	<?php endif; ?>
</main>
<?php
get_footer();
