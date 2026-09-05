#!/usr/bin/env python3
"""Dựng bộ so COMPUTED STYLE trước/sau, chạy trên HTML THẬT của production.

Đây là tầng kiểm mạnh nhất cho việc cắt CSS. Nó không hỏi "class còn trong HTML
không" mà hỏi thẳng: "từng phần tử trên trang có hiển thị y hệt trước không".
Bắt được cả những ca mà class vẫn còn nhưng rule định vị nó đã bị cắt.

Cách làm: lấy HTML thật của production, chèn <base href="https://site/"> để mọi
asset khác vẫn tải từ host, rồi thay ĐÚNG MỘT dòng link CSS bằng URL tuyệt đối về
server local — một bản trỏ CSS cũ, một bản trỏ CSS mới. Nạp hai bản vào hai iframe
cùng origin rồi duyệt mọi phần tử, so 25 thuộc tính computed.

HAI CÁI BẪY, CẢ HAI ĐỀU LÀM PHÉP SO BÁO "0 LỆCH" MÀ VÔ NGHĨA:

  1. URL CSS phải TUYỆT ĐỐI. Viết href="/main-moi.css" thì thẻ <base> kéo nó về
     https://site/main-moi.css -> 404 -> KHÔNG stylesheet nào của theme tải được,
     hai bản trông giống hệt nhau, và phép so vui vẻ báo 0 lệch. Trang so tự kiểm
     document.styleSheets trước khi đo, nhưng biết trước vẫn hơn.

  2. Thước phải chạy qua ca hỏng đã biết. Trang so tự dựng thêm một bản CSS cố ý
     xoá một rule ĐANG ĐƯỢC DÙNG và bắt phép so phải báo lệch ở đó. Nếu ca hỏng
     cũng ra 0 thì mọi số 0 khác là NOT_TESTED, không phải "đạt".

Sau khi chạy script này: mở thư mục ra bằng một static server rồi mở so.html.
Trong Claude Code: thêm một mục vào .claude/launch.json rồi preview_start.

Dùng:
  python dung_so_computed.py --site https://vd.com \
      --css-cu bản-cũ.css --css-moi bản-mới.css \
      --duong-dan-css wp-content/themes/ten-theme/assets/css/main.css \
      --url https://vd.com/ https://vd.com/lien-he/ \
      --ra /đường/dẫn/xem --port 5610
"""
import argparse
import gzip
import os
import re
import shutil
import sys
import urllib.request

TRANG_SO = """<meta charset="utf-8">
<title>So computed style truoc/sau</title>
<style>
 body{font:14px/1.5 ui-monospace,Consolas,monospace;margin:16px;background:#fff;color:#111}
 iframe{width:1280px;height:2200px;border:0;position:absolute;left:-9999px}
 table{border-collapse:collapse;margin-top:8px}td,th{border:1px solid #ccc;padding:4px 8px;text-align:left}
 .ok{color:#17632f;font-weight:700}.xau{color:#a8322a;font-weight:700}
 h2{font-size:15px;margin-top:22px}
</style>
<h1>So computed style tung phan tu — truoc/sau</h1>
<div id="ra">dang do... (5-30 giay tuy so trang)</div><div id="frames"></div>
<script>
const TRANG=__TRANG__;
const PROPS=['display','position','width','height','marginTop','marginBottom','marginLeft','marginRight',
 'paddingTop','paddingBottom','paddingLeft','paddingRight','color','backgroundColor','fontSize','fontWeight',
 'lineHeight','flexDirection','gridTemplateColumns','gap','borderRadius','boxShadow','textAlign','opacity','visibility'];
function nap(src){return new Promise(res=>{const f=document.createElement('iframe');f.src=src;
 f.onload=()=>setTimeout(()=>res(f),1500);document.getElementById('frames').appendChild(f);});}
function do_(doc){return [...doc.querySelectorAll('*')].map(el=>{const cs=doc.defaultView.getComputedStyle(el);
 return PROPS.map(p=>cs[p]).join('|');});}
function ten(doc,i){const el=doc.querySelectorAll('*')[i];if(!el)return '?';
 return el.tagName.toLowerCase()+(el.className&&typeof el.className==='string'
  ?'.'+el.className.trim().split(/\\s+/).slice(0,3).join('.'):'');}
function cssNap(doc,manh){
 const s=[...doc.styleSheets].find(x=>x.href&&x.href.includes(manh));
 if(!s) return {ok:false,vi:'khong thay stylesheet '+manh};
 let n=0; try{n=s.cssRules.length}catch(e){return {ok:false,vi:'CORS chan '+manh}}
 return n>0?{ok:true,n:n}:{ok:false,vi:manh+' co 0 rule'};
}
(async()=>{let html='';let tong=0;
 // 0. kiem thuoc co dang do that khong
 {const a=await nap(TRANG[0]+'-cu.html');
  const k=cssNap(a.contentDocument,'-cu.css');
  html+='<h2>Kiem so bo: CSS co that su nap khong</h2><p>'+
   (k.ok?'<span class="ok">nap duoc, '+k.n+' rule</span> -> phep so co y nghia'
        :'<span class="xau">KHONG NAP DUOC: '+k.vi+'</span> -> moi so 0 duoi day VO NGHIA, dung doc tiep')+'</p>';
  if(!k.ok){document.getElementById('ra').innerHTML=html;return;}}
 // 1. hieu chuan bang ban co y hong
 {const [a,b]=await Promise.all([nap(TRANG[0]+'-cu.html'),nap(TRANG[0]+'-hong.html')]);
  const da=do_(a.contentDocument),db=do_(b.contentDocument);let n=0;
  for(let i=0;i<da.length;i++) if(da[i]!==db[i]) n++;
  html+='<h2>Hieu chuan: ban co y xoa mot rule dang dung</h2><p>phan tu lech: <span class="'
   +(n?'ok':'xau')+'">'+n+'</span> '+(n?'-> thuoc BAT DUOC ca hong, so 0 duoi moi co nghia'
   :'-> THUOC MU, moi so 0 duoi day la NOT_TESTED')+'</p>';}
 // 2. do that
 for(const t of TRANG){const [a,b]=await Promise.all([nap(t+'-cu.html'),nap(t+'-moi.html')]);
  const da=do_(a.contentDocument),db=do_(b.contentDocument);let lech=[];
  if(da.length!==db.length){lech.push(['SO PHAN TU KHAC',da.length+' vs '+db.length]);}
  else{for(let i=0;i<da.length;i++){if(da[i]!==db[i]){const pa=da[i].split('|'),pb=db[i].split('|');
   const kh=PROPS.filter((p,k)=>pa[k]!==pb[k]).map(p=>p+': '+pa[PROPS.indexOf(p)]+' -> '+pb[PROPS.indexOf(p)]);
   lech.push([ten(a.contentDocument,i),kh.join('; ')]);}}}
  tong+=lech.length;
  html+='<h2>'+t+' — '+da.length+' phan tu, <span class="'+(lech.length?'xau':'ok')+'">'
   +lech.length+' phan tu lech</span></h2>';
  if(lech.length) html+='<table><tr><th>phan tu</th><th>khac o</th></tr>'
   +lech.slice(0,40).map(r=>'<tr><td>'+r[0]+'</td><td>'+r[1]+'</td></tr>').join('')+'</table>';}
 html='<p><b>TONG PHAN TU LECH: <span class="'+(tong?'xau':'ok')+'">'+tong+'</span></b> (phai la 0)</p>'+html;
 document.getElementById('ra').innerHTML=html;})();
</script>
"""


def tai(u):
    rq = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(rq, timeout=60) as r:
        d = r.read()
        return (gzip.decompress(d) if r.headers.get("Content-Encoding") == "gzip" else d).decode("utf-8", "replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--css-cu", required=True)
    ap.add_argument("--css-moi", required=True)
    ap.add_argument("--duong-dan-css", required=True,
                    help="đường dẫn CSS như nó xuất hiện trong HTML, vd wp-content/themes/x/assets/css/main.css")
    ap.add_argument("--url", nargs="+", required=True)
    ap.add_argument("--ra", required=True, help="thư mục xuất")
    ap.add_argument("--port", type=int, default=5610)
    ap.add_argument("--rule-hieu-chuan", default="",
                    help="regex một rule ĐANG DÙNG để dựng bản hỏng; để trống thì tự chọn rule đầu tiên")
    a = ap.parse_args()

    os.makedirs(a.ra, exist_ok=True)
    for f in os.listdir(a.ra):
        os.remove(os.path.join(a.ra, f))
    shutil.copy(a.css_cu, os.path.join(a.ra, "main-cu.css"))
    shutil.copy(a.css_moi, os.path.join(a.ra, "main-moi.css"))

    s = open(os.path.join(a.ra, "main-moi.css"), encoding="utf-8", errors="replace").read()
    mau = a.rule_hieu_chuan or r"\.[A-Za-z][A-Za-z0-9_-]*\s*\{[^}]*\}"
    m = re.search(mau, s)
    if not m:
        sys.exit("không tìm được rule để dựng ca hiệu chuẩn — truyền --rule-hieu-chuan")
    open(os.path.join(a.ra, "main-hong.css"), "w", encoding="utf-8").write(s[:m.start()] + s[m.end():])
    print(f"ca hiệu chuẩn: xoá rule {m.group(0)[:50]!r}")

    site = a.site.rstrip("/")
    mau_css = re.compile(r'href=(["\'])' + re.escape(site) + r"/" +
                         re.escape(a.duong_dan_css.strip("/")) + r'[^"\']*\1')
    ten_trang = []
    for i, u in enumerate(a.url):
        ten = re.sub(r"[^a-z0-9]+", "-", u.replace(site, "").strip("/").lower()) or "goc"
        ten_trang.append(ten)
        h = tai(u).replace("<head>", f'<head><base href="{site}/">', 1)
        for nhan, tep in (("cu", "main-cu.css"), ("moi", "main-moi.css"), ("hong", "main-hong.css")):
            if nhan == "hong" and i > 0:
                continue
            g = mau_css.sub(f'href="http://localhost:{a.port}/{tep}"', h)
            if g == h:
                sys.exit(f"KHÔNG thay được link CSS ở {u}.\n"
                         f"  Kiểm lại --duong-dan-css; nó phải khớp đúng href trong HTML.\n"
                         f"  Không thay được mà vẫn chạy thì phép so hoàn toàn vô nghĩa.")
            open(os.path.join(a.ra, f"{ten}-{nhan}.html"), "w", encoding="utf-8").write(g)
        print(f"  dựng {ten}")

    trang_js = "[" + ",".join(f"'{t}'" for t in ten_trang) + "]"
    open(os.path.join(a.ra, "so.html"), "w", encoding="utf-8").write(
        TRANG_SO.replace("__TRANG__", trang_js))

    print(f"\nxong. Thư mục: {a.ra}")
    print(f"Mở một static server ở cổng {a.port} trỏ vào thư mục đó, rồi mở so.html")
    print(f"  vd: python -m http.server {a.port} --directory \"{a.ra}\"")
    print("  (trong Claude Code: thêm mục vào .claude/launch.json rồi preview_start,")
    print("   đừng chạy server bằng Bash)")
    print("\nĐọc kết quả theo thứ tự: 'CSS co that su nap khong' -> 'Hieu chuan' -> rồi mới tới số lệch.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
