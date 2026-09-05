<?php
/* File này KHÔNG được functions.php require. Có add_action nhưng hook không bao
   giờ đăng ký vì file không bao giờ được nạp. Bộ quét phải xếp nó vào mục 2. */
add_action( 'init', 'fx_khong_bao_gio_chay' );
function fx_khong_bao_gio_chay() {}
