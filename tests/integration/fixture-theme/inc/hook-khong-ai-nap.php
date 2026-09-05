<?php
/* KHÔNG được functions.php require. Có add_action nhưng hook không bao giờ đăng ký. */
add_action( 'init', 'fxt_khong_bao_gio_chay' );
function fxt_khong_bao_gio_chay() {}
