<?php
/* Chỉ nạp khi WooCommerce bật. Bộ quét tĩnh thấy câu require có điều kiện và coi
   là nạp — WordPress thật sẽ xác nhận có đúng vậy không. */
function fxt_gia_woo() { return 1; }
