#!/usr/bin/env python3
"""把本地預覽版 index.html / product.html 轉成可貼進 Shopline「客製化語法元件」的程式碼。
用法：python3 build.py  → 產生 home.code.html、shop.code.html（以及本地可開的 *.preview.html）"""
import re, os, sys
D = os.path.dirname(os.path.abspath(__file__)); SRC = os.path.dirname(D)
IMG = 'https://shoplineimg.com/6a0c197329b5de004d6571e5/{}/1200x.webp?source_format=png'
ASSET = 'https://cdn.jsdelivr.net/gh/Jaycheng1103/moocella-assets@6c755bc52c2964e757a8cfbaaf72f73a0259bab8/'  # 釘在固定版本：repo 超過 jsDelivr 50MB 上限，新版本有時會被拒
SHOP_PAGE = '/pages/moocella-shop'          # 新商品頁網址
BUY = {'1': 'https://www.moocella.com/cart?affiliate_ref_id=0fc66d42-76b9-49ed-a9ed-a2c0831eadf4&affiliate_source=express_link&sl-ref=',
       '2': '/products/moocella-beauty-drink-2',
       '10': '/products/moocella-beauty-drink-10'}
KF = ['megaIn', 'mq', 'shine', 'sway', 'vmIn', 'vmUp']

def strip_comments(css): return re.sub(r'/\*.*?\*/', '', css, flags=re.S)

def split_top(s, ch=','):
    out, depth, cur = [], 0, ''
    for c in s:
        if c in '([': depth += 1
        if c in ')]': depth -= 1
        if c == ch and depth == 0: out.append(cur); cur = ''
        else: cur += c
    out.append(cur); return out

def pre_sel(sel):
    s = sel.strip()
    if not s: return s
    if re.match(r'^html\b', s):
        rest = s[4:]
        return 'html:has(#mcx)' + rest if not rest.strip() or rest.startswith(':') else '#mcx' + re.sub(r'^\s*body\b', '', rest)
    if s.startswith(':root'): return '#mcx' + s[5:]
    if re.match(r'^body\b', s): return '#mcx' + s[4:]
    return '#mcx ' + s

def block_end(css, i):  # css[i] == '{'
    depth = 0
    for j in range(i, len(css)):
        if css[j] == '{': depth += 1
        elif css[j] == '}':
            depth -= 1
            if depth == 0: return j
    raise ValueError('unbalanced')

def rename_anim(decl):
    def fix(m):
        v = m.group(2)
        for k in KF: v = re.sub(r'\b%s\b' % k, 'mcx-' + k, v)
        return m.group(1) + v
    return re.sub(r'(animation(?:-name)?\s*:)([^;}]*)', fix, decl)

def prefix_css(css):
    out, i = [], 0
    while i < len(css):
        j = css.find('{', i)
        if j < 0:
            rest = css[i:].strip()
            if rest: out.append(rest)
            break
        pre = css[i:j].strip()
        # @import / @charset 等以分號結束的規則
        while pre.startswith('@') and ';' in pre and not pre.startswith(('@media', '@supports', '@keyframes')):
            k = pre.index(';'); out.append(pre[:k+1]); pre = pre[k+1:].strip()
        e = block_end(css, j); body = css[j+1:e]
        if pre.startswith(('@media', '@supports')):
            out.append(pre + '{' + prefix_css(body) + '}')
        elif pre.startswith('@keyframes'):
            name = pre.split()[1]; out.append('@keyframes mcx-' + name + '{' + body + '}')
        elif pre.startswith('@font-face'):
            out.append(pre + '{' + body + '}')
        else:
            sels = ','.join(pre_sel(s) for s in split_top(pre))
            out.append(sels + '{' + rename_anim(body) + '}')
        i = e + 1
    return '\n'.join(out)

THEME_CSS = '''
body:has(#mcx) #shopline-section-announcement,body:has(#mcx) #shopline-section-header,body:has(#mcx) #shopline-section-footer,body:has(#mcx) .sl-goto-top,body:has(#mcx) .CustomPage-title{display:none!important}
body:has(#mcx){padding-top:0!important;overflow-x:clip}
body:has(#mcx) #Content,body:has(#mcx) .CustomPage,body:has(#mcx) .block-inner,body:has(#mcx) .container{padding:0!important;margin:0!important;max-width:none!important;width:auto!important;overflow:visible!important}
#mcx{overflow-x:clip;font-size:16px;line-height:normal;text-align:start;text-transform:none;letter-spacing:normal;font-weight:400}
#mcx :where(:not(svg,svg *)){all:revert}
'''

def live_html(h, page):
    # 1. 拿掉草稿用的待補內容
    h = re.sub(r'\s*<div class="ann-msg"><span class="tag-todo">[^<]*</span></div>', '', h)
    h = re.sub(r'<small class="tag-todo">\[ 檔期優惠 \]</small>', '', h)
    h = re.sub(r'<span class="tag-todo">\[ 評價數 \] 則評價</span>', '', h)
    h = re.sub(r'<li class="tag-todo">[^<]*</li>', '', h)
    h = re.sub(r'<div class="badge-ph">[^<]*</div>', '', h)
    h = re.sub(r'<time class="tag-todo">[^<]*</time>', '', h)
    h = re.sub(r'\s*<div class="draft">.*?</div>', '', h, flags=re.S)
    h = h.replace('<h2 class="h2"><span class="tag-todo">[ 年末送禮 ]</span></h2>', '<h2 class="h2">年末送禮，<br>送一份好好照顧自己</h2>')
    h = h.replace('<p class="tag-todo">[ 一兩句說明：限定包裝，送給忙碌的她，也送給自己 ]</p>', '<p>一盒 10 包、每天一包，撕開就能喝。送給忙碌的她，也記得為自己留一份。</p>')
    h = h.replace('<a class="btn" href="#products">[ 選購禮盒 ]</a>', '<a class="btn" href="%s?plan=2">選購 2 盒免運</a>' % SHOP_PAGE)
    # 文章摘要
    ex = {'第一次認識美妍水光飲': '盒數、包數與食用方式，第一次喝之前先看這篇。',
          '一盒 10 包，怎麼訂購？': '單盒價格、購買數量與預購出貨時間，一次說清楚。',
          '一包的食用與保存筆記': '從開封到日常收納，怎麼喝、怎麼放最方便。',
          '也記得，為自己留一份。': '選一份適合自己的安排，從認識沐菈美妍水光飲開始。'}
    for t, x in ex.items():
        h = re.sub(r'(<h3>%s</h3>)<p class="tag-todo">[^<]*</p>' % re.escape(t), r'\1<p>%s</p>' % x, h)
    h = h.replace('href="https://www.moocella.com/pages/journal"><', 'href="/pages/journal"><')
    # 文章連到各自頁面
    h = re.sub(r'(<h3>第一次認識美妍水光飲</h3><p>[^<]*</p><a class="more" href=")[^"]*', r'\1/pages/first-drink', h)
    h = re.sub(r'(<h3>一包的食用與保存筆記</h3><p>[^<]*</p><a class="more" href=")[^"]*', r'\1/pages/storage', h)
    h = re.sub(r'(<h3>(?:照顧自己，不該是有空才做的事|也記得，為自己留一份。)</h3><p>[^<]*</p><a class="more" href=")[^"]*', r'\1/about', h)
    # 2. 連結
    h = h.replace('href="index.html#', 'href="/#').replace('href="index.html"', 'href="/"')
    h = h.replace('product.html', SHOP_PAGE)
    h = h.replace('<a class="logo" href="#">', '<a class="logo" href="/">')
    h = h.replace('href="#" title="搜尋"', 'href="/products" title="搜尋"')
    h = h.replace('class="acct" href="#"', 'class="acct" href="/users/sign_in"')
    h = h.replace('class="cart" href="#"', 'class="cart" href="/cart"')
    h = h.replace('<b>0</b></a>', '</a>')
    h = h.replace('<a href="#" aria-label="Facebook">', '<a href="https://www.facebook.com/profile.php?id=61594309412572" target="_blank" rel="noopener" aria-label="Facebook">')
    h = h.replace('<a href="#" aria-label="Instagram">', '<a href="https://www.instagram.com/moocellatw/" target="_blank" rel="noopener" aria-label="Instagram">')
    h = h.replace('<a href="#" aria-label="Threads">', '<a href="https://www.threads.com/@moocellatw" target="_blank" rel="noopener" aria-label="Threads">')
    foot = {'美妍水光飲': SHOP_PAGE, '常見問題': '/pages/faq', '付款與配送': '/about/delivery-policy', '退換貨政策': '/about/policy',
            '條款與細則': '/about/terms', '隱私政策': '/about/privacy-policy', '品牌故事': '/about', '沐菈日常': '/pages/journal',
            '防詐騙宣導': '/about/anti-fraud', '聯絡我們': 'https://lin.ee/p22IPUQ'}
    for k, v in foot.items():
        h = h.replace('<li>%s</li>' % k, '<li><a href="%s">%s</a></li>' % (v, k))
    # 3. 圖片、logo、影片
    h = re.sub(r'(["\'(])img/([0-9a-f]{24})\.webp', lambda m: m.group(1) + IMG.format(m.group(2)), h)
    h = re.sub(r'(["\'(])logos/', r'\1' + ASSET + 'logos/', h)
    h = re.sub(r"f:'videos/", "f:'" + ASSET + "videos/", h)
    # 4. 商品頁：評價區先拿掉（範例評價不能上線），按鈕改成直接購買
    if page == 'shop':
        h = re.sub(r'\s*<a class="stars" href="#reviews">.*?</a>', '', h, flags=re.S)
        h = re.sub(r'<section class="rvw wrap" id="reviews">.*?</section>', '', h, flags=re.S)
        h = re.sub(r'\n// 評價：看更多\n\(\(\)=>\{.*?\}\)\(\);', '', h)
        # 快速結帳連結一次只能帶固定盒數，所以拿掉數量增減，按鈕改成「立即購買」
        h = h.replace('加入購物車・<span id="tot">', '立即購買・<span id="tot">')
        h = h.replace(">加入購物車</button></div>", ">立即購買</button></div>")
        h = h.replace('</style>', '.qty{display:none!important}</style>', 1)
    return h

LIVE_JS_HEAD = "var MCX_BUY=%s;var MCX_SHOP='%s';\n" % (repr(BUY).replace("'", '"'), SHOP_PAGE)
# 直接用 Shopline 購物車 API 放進購物車再到 /cart（不經過主題的商品頁）；失敗才退回原本連結
LIVE_JS_HEAD += r"""var MCX_M='/api/merchants/6a0c197329b5de004d6571e5',MCX_SINGLE='6aa7aa368532ea1079c417c2',MCX_SETS={'2':'6aa7ab0439923b9e40ffc48e','10':'6b083e860b20e22661883607'};
function mcxBuy(plan,btn){var it=plan==='1'?{product_id:MCX_SINGLE,quantity:1,type:'product',variation_id:null,blacklisted_delivery_option_ids:[],triggering_item_id:null}:{product_id:MCX_SETS[plan],quantity:1,type:'product_set',variation_id:null,blacklisted_delivery_option_ids:[],triggering_item_id:null,item_data:{selected_child_products:[{child_product_id:MCX_SINGLE,child_variation_id:null,quantity:+plan}]}};
var fb=function(){location.href=MCX_BUY[plan]};if(btn){if(btn.dataset.busy)return;btn.dataset.busy=1;btn.style.opacity=.7}
var m=document.querySelector('meta[name=csrf-token]');try{fetch(MCX_M+'/cart/items',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-Requested-With':'XMLHttpRequest','X-CSRF-Token':m?m.content:''},body:JSON.stringify({item:it,cart_options:{skip_calculate_order:true,is_cart_page:false}})}).then(function(r){return r.ok?r.json():null}).then(function(j){if(j&&j.result)location.href='/cart';else fb()}).catch(fb)}catch(e){fb()}}
"""
# 預覽模式（草稿）時：兩頁互連改指到草稿預覽網址；Shopline 預覽 SDK 會擋掉所有連結點擊，所以自己導頁。正式發佈後這段不會作用
LIVE_JS_HEAD += r"""if(/[?&]draft=true/.test(location.search)){var MCX_PV={'/pages/moocella-shop':'/pages/6b084129f2c7d816102ebab7','/':'/pages/6b084037b3102f1c273be02e'};var MCX_Q='draft=true&is_preview=2&locale=zh-hant';var mcxPv=function(h){var m=h.match(/^(\/pages\/moocella-shop|\/)(\?[^#]*)?(#.*)?$/);return m?MCX_PV[m[1]]+(m[2]?m[2]+'&':'?')+MCX_Q+(m[3]||''):h};document.querySelectorAll('#mcx a[href]').forEach(function(a){a.setAttribute('href',mcxPv(a.getAttribute('href')))});MCX_SHOP=mcxPv(MCX_SHOP);window.addEventListener('click',function(e){var a=e.target.closest&&e.target.closest('#mcx a[href]');if(!a)return;var h=a.getAttribute('href');if(!h||h.charAt(0)==='#'||e.metaKey||e.ctrlKey)return;e.preventDefault();e.stopPropagation();if(a.target==='_blank')window.open(a.href,'_blank','noopener');else location.href=a.href;},true);}
"""
# Shopline 頁面有 <base href="https://www.moocella.com/">，#錨點會被當成跳回網站根目錄，所以自己處理頁內捲動
LIVE_JS_HEAD += r"""document.addEventListener('click',function(e){var a=e.target.closest&&e.target.closest('#mcx a[href^="#"]');if(!a)return;var id=a.getAttribute('href').slice(1);e.preventDefault();if(!id)return;var t=document.getElementById(id);if(!t)return;var n=document.querySelector('#mcx .nav.open');if(n)n.classList.remove('open');t.scrollIntoView({behavior:'smooth',block:'start'});try{history.replaceState(null,'',location.href.split('#')[0]+'#'+id)}catch(_){}},true);
"""

def build(src, page):
    raw = open(os.path.join(SRC, src), encoding='utf-8').read()
    raw = live_html(raw, page)
    open(os.path.join(D, page + '.standalone.html'), 'w', encoding='utf-8').write(raw.replace('</head>', '<base href="../"></head>', 1))
    links = ''.join(re.findall(r'<link[^>]*fonts[^>]*>', raw))
    css = ''.join(re.findall(r'<style>(.*?)</style>', raw, flags=re.S))
    body = re.search(r'<body[^>]*>(.*)</body>', raw, flags=re.S).group(1)
    scripts = re.findall(r'<script>(.*?)</script>', body, flags=re.S)
    body = re.sub(r'<script>.*?</script>', '', body, flags=re.S).strip()
    js = '\n'.join(scripts)
    # 首頁：加入購物車 → 前往商品頁
    js = js.replace("const toast=()=>{", "const toast=()=>{location.href=MCX_SHOP;return;")
    if page == 'shop':
        js = js.replace("atc.onclick=()=>{", "atc.onclick=()=>{mcxBuy(cur().dataset.plan,atc);return;")
    pcss = prefix_css(strip_comments(css))
    code = (links + '<style>' + THEME_CSS + pcss + '</style>\n<div id="mcx" data-page="%s">\n' % page + body +
            '\n</div>\n<script>(function(){\n' + LIVE_JS_HEAD + js + '\n})();</script>')
    code = re.sub(r'\n\s*\n+', '\n', code)
    open(os.path.join(D, page + '.code.html'), 'w', encoding='utf-8').write(code)
    # 本地測試用：模擬 Shopline 外框
    prev = ('<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<style>body{margin:0;font-family:serif;color:red;line-height:2}h2{font-size:40px;color:green}a{color:blue;text-decoration:underline}.btn{background:red}</style></head>'
            '<body><div id="shopline-section-header">THEME HEADER</div><div id="Content"><div class="CustomPage"><h1 class="CustomPage-title">title</h1><div class="block-inner">'
            + code + '</div></div></div><div id="shopline-section-footer">THEME FOOTER</div></body></html>')
    open(os.path.join(D, page + '.preview.html'), 'w', encoding='utf-8').write(prev)
    print(page, len(code.encode()), 'bytes')

build('index.html', 'home'); build('product.html', 'shop')

# ---- 主題頁外框（購物車、會員、商品頁等 Shopline 系統頁）：放在版面頁尾的「客製化語法元件」，用新網站的公告列、選單、頁尾換掉主題的 ----
SKIN_KW = re.compile(r'ann|hdr|header|\.site|\.nav|mega|logo|burger|tools|\.cur\b|\.acct|\.cart\b|chev|footer|\.foot|\.about|\.soc|\.legal|\.wrap\b|\.h4|^\s*#mcx\s*$|#mcx\s*:where|#mcx\s*\*|#mcx\s*(a|img|svg|button|ul|li|h4|h6|b|small|em|p)\b')
def filter_css(css):
    out, i = [], 0
    while i < len(css):
        j = css.find('{', i)
        if j < 0: break
        pre = css[i:j].strip(); e = block_end(css, j); body = css[j+1:e]
        if pre.startswith(('@media', '@supports')):
            inner = filter_css(body)
            if inner: out.append(pre + '{' + inner + '}')
        elif pre.startswith(('@keyframes', '@font-face')):
            out.append(pre + '{' + body + '}')
        elif pre.startswith('@'):
            pass
        else:
            sels = [s for s in split_top(pre) if SKIN_KW.search(s)]
            if sels: out.append(','.join(sels) + '{' + body + '}')
        i = e + 1
    return '\n'.join(out)

def build_skin():
    raw = live_html(open(os.path.join(SRC, 'product.html'), encoding='utf-8').read(), 'shop')
    links = ''.join(re.findall(r'<link[^>]*fonts[^>]*>', raw))
    css = ''.join(re.findall(r'<style>(.*?)</style>', raw, flags=re.S))
    pcss = prefix_css(strip_comments(css))
    pcss = pcss.replace('html:has(#mcx)', 'html.mcxs-on')
    pcss = filter_css(pcss)
    pcss = re.sub(r'#mcx\b', '.mcxs', pcss)
    top = re.search(r'<div class="ann" id="ann">.*?</header>', raw, flags=re.S).group(0)
    top = top.replace(' id="ann"', '').replace("document.querySelector('.nav')", "this.parentNode.querySelector('.nav')")
    # 頁內錨點（#ingredients）在主題頁不存在，改成回商品頁
    top = top.replace('href="#ingredients"', 'href="%s#ingredients"' % SHOP_PAGE)
    foot = re.search(r'<footer>.*?</footer>', raw, flags=re.S).group(0)
    theme = '''
html.mcxs-on #shopline-section-announcement,html.mcxs-on #shopline-section-header,html.mcxs-on #shopline-section-footer,html.mcxs-on .sl-goto-top{display:none!important}
.mcxs-skin{display:none}
html.mcxs-on .mcxs-skin{display:block}
.mcxs{font-size:16px;line-height:normal;text-align:start;text-transform:none;letter-spacing:normal;font-weight:400}
.mcxs :where(:not(svg,svg *)){all:revert}
html.mcxs-on .mcxs-top{display:contents}
'''
    js = r"""(function(){
var T=document.getElementById('mcxs-top'),F=document.getElementById('mcxs-foot');if(!T||!F)return;
if(document.getElementById('mcx')){T.remove();F.remove();return}
var H=document.getElementById('shopline-section-header')||document.getElementById('shopline-section-announcement'),C=document.getElementById('Content');
if(H)H.parentNode.insertBefore(T,H);else document.body.insertBefore(T,document.body.firstChild);
if(C&&C.parentNode)C.parentNode.insertBefore(F,C.nextSibling);else document.body.appendChild(F);
document.documentElement.classList.add('mcxs-on');
var m=[].slice.call(T.querySelectorAll('.ann-msg')),i=0;if(m.length>1){var sh=function(n){m[i].classList.remove('on');i=(n+m.length)%m.length;m[i].classList.add('on')};T.querySelector('.ann .prev').onclick=function(){sh(i-1)};T.querySelector('.ann .next').onclick=function(){sh(i+1)};setInterval(function(){sh(i+1)},5000)}
})();"""
    code = (links + '<style>' + theme + pcss + '</style>\n<div class="mcxs mcxs-skin mcxs-top" id="mcxs-top">' + top +
            '</div>\n<div class="mcxs mcxs-skin" id="mcxs-foot">' + foot + '</div>\n<script>' + js + '</script>')
    code = re.sub(r'\n\s*\n+', '\n', code)
    open(os.path.join(D, 'skin.code.html'), 'w', encoding='utf-8').write(code)
    print('skin', len(code.encode()), 'bytes')

build_skin()
