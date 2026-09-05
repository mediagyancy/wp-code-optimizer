<?php
/* Template gốc theme = điểm vào. Gọi một hàm và một template-part. */
get_header();
fx_ham_php_that();
get_template_part( 'template-parts/duoc-goi' );
get_template_part( 'template-parts/co-hau', 'ban' );
get_footer();
