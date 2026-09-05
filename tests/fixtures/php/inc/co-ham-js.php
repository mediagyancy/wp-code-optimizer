<?php
/* Bẫy: JavaScript nhúng trong PHP. `function fxJsOnly()` KHÔNG phải hàm PHP —
   đếm nó thành hàm PHP rồi báo "không ai gọi" là dụ người ta xoá code đang chạy. */
function fx_ham_php_that() { return 1; }
?>
<script>
function fxJsOnly(){ return 2; }
</script>
