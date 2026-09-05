<?php
/* Markup của fixture CSS: quyết định class nào SỐNG.
   Class nào có ở đây là SỐNG; class nào không xuất hiện là chết.
   fx-bac--N cố ý ghép chuỗi để kiểm luật bảo vệ gốc tên. */
?>
<div class="fx-song fx-song__b fx-song__l fx-song--x">
	<span class="fx-song/2" data-list="a,b,c"></span>
	<i class="fx-bac--<?php echo (int) $bac; ?>"></i>
</div>
