<?php
/**
 * Ca "tách hàm ra với GIÁ TRỊ MẶC ĐỊNH khác" — lỗi refactor số 3.
 *
 * Đây là ca khó nhất trong sáu ca, vì nó vô hình với mọi phép đo dựa trên output:
 * `index.php` gọi `fxb_gia( 100, 1.1 )` — truyền ĐỦ tham số. Đổi giá trị mặc định của
 * `$ty_le` từ 1.1 sang 1.2 KHÔNG đổi một ký tự nào trong HTML, không đổi hook, không
 * đổi file nạp, không đổi asset. `php -l` sạch. PHPStan quét file rời cũng sạch.
 *
 * Nhưng nó là một quả mìn: lần sau có ai gọi `fxb_gia( 100 )` thì ra số khác. Trên một
 * site bán hàng, "ra số khác" nghĩa là giá sai.
 *
 * Mặt DUY NHẤT bắt được nó là bản đồ chữ ký hàm lấy qua Reflection lúc chạy.
 */

defined( 'ABSPATH' ) || exit;

function fxb_gia( $so, $ty_le = 1.1 ) {
	return (int) round( $so * $ty_le );
}
