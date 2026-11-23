#!/usr/bin/env python3
"""Bostan Mimarı uçtan uca testleri.

Çalıştırma (depo kökünde):
    pip install playwright && python -m playwright install chromium
    python tests/calistir.py

Sunucu otomatik açılır (python -m http.server). CDN kütüphaneleri internetten
alınır; internetsiz ortamda NODE_MODULES=/yol/node_modules verilirse oradan okunur
(npm i html2canvas@1.4.1 jspdf@2.5.1 jszip@3.10.1 jspdf-autotable@3.8.2 svg2pdf.js@2.2.3 dejavu-fonts-ttf@2.37.3).
Çıkış kodu: 0 = hepsi geçti, 1 = en az bir test başarısız.
"""
import asyncio, io, json, os, re, socket, subprocess, sys, time, zipfile, traceback
from pathlib import Path
from playwright.async_api import async_playwright

KOK = Path(__file__).resolve().parent.parent
CIKTI = Path(os.environ.get('CIKTI', KOK / 'tests' / 'cikti')); CIKTI.mkdir(parents=True, exist_ok=True)
NM = os.environ.get('NODE_MODULES')
LIB = {'html2canvas@': 'html2canvas/dist/html2canvas.min.js', 'jspdf@': 'jspdf/dist/jspdf.umd.min.js', 'jszip@': 'jszip/dist/jszip.min.js',
       'jspdf-autotable@': 'jspdf-autotable/dist/jspdf.plugin.autotable.min.js', 'svg2pdf.js@': 'svg2pdf.js/dist/svg2pdf.umd.min.js',
       'DejaVuSans.ttf': 'dejavu-fonts-ttf/ttf/DejaVuSans.ttf', 'DejaVuSans-Bold.ttf': 'dejavu-fonts-ttf/ttf/DejaVuSans-Bold.ttf'}
SONUC = []

def bos_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p

async def cdn(route):
    u = route.request.url
    for k in sorted(LIB, key=len, reverse=True):
        if ('/' + k) in u:
            return await route.fulfill(path=str(Path(NM) / LIB[k]), headers={'access-control-allow-origin': '*'},
                                       content_type='font/ttf' if k.endswith('.ttf') else 'application/javascript')
    if 'three' in u: return await route.continue_()
    await route.abort()

ORNEK = """()=>{const p=bosProje();p.meta.ad='Test bostanı';p.meta.bostan='Test';p.meta.hazirlayan='Test';p.alan={en:30,boy:20,kuzey:0,enlem:39.9};p.sulama.basinc=3;p.gruplar=[
 yeniGrup(0,{L:600,W:200,H:60,sekil:'U',kolEn:150,kolBoy:500,mk:'ic',mkD:45,mkYer:'kolBas',x:1,y:1,sutun:1}),
 yeniGrup(1,{L:300,W:120,H:45,malzeme:'galvaniz',t:0.08,tahtaH:0,dikme:4,x:10,y:1,sutun:2,mk:'dis',mkD:45,mkYer:'bas'})];projeEkle(p)}"""

def test(f):
    async def sar(ctx, url):
        ad = f.__name__; t0 = time.time()
        pg = await ctx.new_page(); hatalar = []
        pg.on('pageerror', lambda e: hatalar.append(str(e)))
        if NM: await pg.route('https://cdn.jsdelivr.net/**', cdn)
        try:
            await pg.goto(url); await pg.wait_for_timeout(300)
            await f(pg)
            assert not hatalar, 'sayfa hatası: ' + '; '.join(hatalar)
            SONUC.append((ad, True, f'{time.time()-t0:.1f} sn'))
        except Exception as e:
            await pg.screenshot(path=str(CIKTI / f'HATA_{ad}.png'))
            SONUC.append((ad, False, f'{e}\n{traceback.format_exc(limit=2)}'))
        finally:
            await pg.close()
    sar.__name__ = f.__name__; return sar

@test
async def surum_eslesmesi(pg):
    sw = (KOK / 'sw.js').read_text(encoding='utf-8'); ix = (KOK / 'index.html').read_text(encoding='utf-8')
    a = re.search(r"VERSION = '([^']+)'", sw).group(1); b = re.search(r"APP_VERSION = '([^']+)'", ix).group(1)
    assert a == b, f'sw.js {a} ≠ index.html {b}'
    json.loads((KOK / 'manifest.webmanifest').read_text(encoding='utf-8'))

@test
async def acilis_ve_calismalar(pg):
    assert await pg.is_visible('#t-ev'), 'Çalışmalar sayfası açılmadı'
    await pg.click('#evOrnek'); await pg.wait_for_timeout(200)
    assert await pg.is_visible('#adimlar'), 'adım rehberi yok'
    await pg.click('#btnProje'); await pg.wait_for_timeout(200)
    assert await pg.locator('.evKart').count() >= 2

@test
async def hesap_tutarliligi(pg):
    r = await pg.evaluate("""()=>{const out=[];for(const sekil of['I','L','U'])for(const mk of['yok','ic','dis'])for(const m of['ahsap','galvaniz','beton','kompozit']){
      const p=bosProje();const z=MALZ[m];p.gruplar=[yeniGrup(0,{L:500,W:120,H:45,sekil,kolEn:100,kolBoy:300,mk,mkD:45,malzeme:m,t:z.t,tahtaH:z.tahtaH,dikme:z.dikme,gomme:m==='beton'?0:20})];
      const H=hesapla(p),o=H.top;const bad=Object.entries(o).filter(([k,v])=>typeof v==='number'&&!Number.isFinite(v)).map(([k])=>k);
      if(bad.length||!(o.ekim>0)||!(o.mixL>0))out.push(`${sekil}/${mk}/${m}: ${bad.join(',')} ekim=${o.ekim}`)}return out}""")
    assert not r, '; '.join(r)

@test
async def dis_kose_l_profil(pg):
    r = await pg.evaluate("""()=>{const p=bosProje();p.gruplar=[yeniGrup(0,{L:600,W:200,H:60,sekil:'U',kolEn:150,kolBoy:500}),yeniGrup(1,{L:300,W:120,H:45,disL:'hayir',x:9}),yeniGrup(2,{L:300,W:120,H:45,malzeme:'galvaniz',t:0.08,tahtaH:0,dikme:4,x:14})];
      const H=hesapla(p),n=G=>G.parca.filter(x=>/L profili/.test(x.kalem)).reduce((s,x)=>s+x.adet,0);return[n(H.gr[0]),n(H.gr[1]),n(H.gr[2]),H.gr[0].k.nV,malzAnahtar('Galvaniz dış köşe L profili (geniş) 100×100×3 mm')]}""")
    assert r[0] == r[3] == 8 and r[1] == 0 and r[2] == 0 and r[4] == 'lprofil', r

@test
async def kasa_dayanimi(pg):
    r = await pg.evaluate("""()=>{const d=o=>{const p=bosProje();p.gruplar=[yeniGrup(0,o)];const H=hesapla(p);return H.gr[0].day};
      return{ahsap:d({L:300,W:120,H:45}).durum,beton60:d({L:300,W:120,H:60,malzeme:'beton',t:19,tahtaH:20,dikme:0,gomme:0}).durum,
       beton40:d({L:300,W:120,H:40,malzeme:'beton',t:19,tahtaH:20,dikme:0,gomme:0}).durum,ince:d({L:400,W:120,H:35,t:2,tahtaH:12,dikme:5,gomme:0}).eta}}""")
    assert r['ahsap'] == 'ok', r; assert r['beton60'] == 'kritik', r; assert r['beton40'] == 'ok', r; assert r['ince'] > 1, r

@test
async def damla_hidroligi(pg):
    r = await pg.evaluate("""()=>{const h=S=>{const p=bosProje();Object.assign(p.sulama,S);p.gruplar=[yeniGrup(0,{L:300,W:120,H:45,sutun:3})];const H=hesapla(p);return{reg:H.hid.reg,Pmin:H.hid.tas.Pmin,qmin:H.hid.tas.qmin,b:H.sorun.map(x=>x.sev+':'+x.baslik)}};
      return{yuksek:h({basinc:4}),dusuk:h({basinc:0.2}),pc:h({basinc:4,damlaTip:'pc'})}}""")
    assert r['yuksek']['reg'] == 1.5, r['yuksek']
    assert any(x.startswith('kritik:Hat sonunda') for x in r['dusuk']['b']), r['dusuk']['b']
    assert abs(r['pc']['qmin'] - 2) < 0.01, r['pc']

@test
async def malzeme_eslesmesi(pg):
    r = await pg.evaluate("""()=>({sul:malzAnahtar('Damla sulama sisteminin kurulumu, basınç ve debi (kova) testi'),lama:malzAnahtar('Galvaniz delikli lama 40×3 mm'),
      vida:malzAnahtar('Galvaniz köşebent vidası 5×40'),toprak:malzAnahtar('Bahçe toprağı (elenmiş)'),gergi:malzAnahtar('Gergi çıtası')})""")
    assert r == {'sul': 'genel', 'lama': 'lama', 'vida': 'vida', 'toprak': 'toprak', 'gergi': 'gergi'}, r

@test
async def metin_pdf(pg):
    await pg.evaluate(ORNEK)
    r = await pg.evaluate("""async()=>{const x=await raporPDF();const b=new Uint8Array(await x.blob.arrayBuffer());let s='';for(let i=0;i<b.length;i+=65536)s+=String.fromCharCode.apply(null,b.subarray(i,i+65536));return{metin:x.metin,sayfa:x.sayfa,font:/FontFile2/.test(s),boy:b.length}}""")
    assert r['metin'] and r['font'], r; assert r['sayfa'] >= 6, r

@test
async def hazirlik_klasoru(pg):
    await pg.evaluate(ORNEK)
    await pg.click('#altNav button[data-t="ihale"]'); await pg.wait_for_timeout(200)
    await pg.click('#btnIhale')
    await pg.wait_for_selector('#ihaleCikti:not([hidden]), #btnIhaleTaslak:not([hidden])', timeout=120000)
    if await pg.is_visible('#btnIhaleTaslak'):
        await pg.click('#btnIhaleTaslak'); await pg.wait_for_selector('#ihaleCikti:not([hidden])', timeout=120000)
    kontrol = await pg.inner_text('#ihaleKontrol')
    son = kontrol.split('2. kontrol')[-1]
    assert '⛔' not in son, son
    await pg.click('#btnIhaleOn'); await pg.wait_for_timeout(200)
    for k in ['sartname', 'm1', 'cizim', 'ic']:
        await pg.click(f'[data-on="{k}"]'); await pg.wait_for_timeout(150)

@test
async def ara_dikme_lamasi(pg):
    await pg.evaluate(ORNEK); await pg.wait_for_timeout(300)
    r = await pg.evaluate("""()=>{const G=H.gr.find(g=>g.k.m==='ahsap'&&g.k.araTop>0);const say=g=>parcalar(g).filter(x=>/lama 40×3/.test(x.kalem)).reduce((a,x)=>a+x.adet,0);
      const a=say(G),ar=G.k.araTop,d=JSON.stringify(dayanim(G,st)).includes('dikey lama dahil');G.g.araLama='hayir';const b=say(G);G.g.araLama='evet';
      const gal=H.gr.find(g=>g.k.m==='galvaniz');return{a,ar,b,d,gal:gal?say(gal):0}}""")
    assert r['a'] == r['ar'] > 0 and r['b'] == 0 and r['d'] and r['gal'] == 0, r

@test
async def sulama_detayi(pg):
    await pg.evaluate(ORNEK); await pg.wait_for_timeout(300)
    r = await pg.evaluate("""()=>{const G=H.gr.find(x=>x.d);const s=svgSulamaDetay(G,st);const d=new DOMParser().parseFromString(s,'image/svg+xml');
      const L=sulamaListe(st,H).map(x=>x[0]||x.ad||'').join('|');return{hata:!!d.querySelector('parsererror'),n:(s.match(/Duvar geçişi|Bölme geçişi|mini vana|Başlangıç conta/g)||[]).length,
      klasor:ihaleCizimleri().some(x=>/sulama_detayi/.test(x[0])),liste:/Duvar geçiş contası/.test(JSON.stringify(sulamaListe(st,H)))}}""")
    assert not r['hata'] and r['n'] >= 4 and r['klasor'] and r['liste'], r
    await pg.evaluate("()=>{cizimMod='suldetay';cizimCiz(true)}")
    assert await pg.locator('#cizimKutu svg, .cizim svg').count() > 0

@test
async def esitleme(pg):
    # İki cihaz: sahte GitHub API
    GIST = {}
    def gj(i): return {'id': i, 'description': GIST[i]['d'], 'files': {k: {'content': v['content'], 'truncated': False} for k, v in GIST[i]['f'].items()}}
    async def api(route):
        r = route.request; u = r.url.replace('https://api.github.com', ''); m = r.method
        if r.headers.get('authorization') != 'Bearer ghp_TEST': return await route.fulfill(status=401, body='{}')
        if m == 'GET' and u.startswith('/gists?'): return await route.fulfill(json=[gj(i) for i in GIST])
        if m == 'POST': b = json.loads(r.post_data); i = f'g{len(GIST)+1}'; GIST[i] = {'d': b['description'], 'f': b['files']}; return await route.fulfill(status=201, json=gj(i))
        i = u.split('/')[2]
        if m == 'PATCH': GIST[i]['f'].update(json.loads(r.post_data)['files'])
        return await route.fulfill(json=gj(i))
    ctx = pg.context; url = pg.url
    B = await ctx.browser.new_context(service_workers='block'); pb = await B.new_page()
    for x in (pg, pb): await x.route('https://api.github.com/**', api)
    await pb.goto(url); await pb.wait_for_timeout(300)
    await pg.evaluate("()=>{const p=bosProje();p.meta.ad='Cihaz A';projeEkle(p)}")
    await pb.evaluate("()=>{const p=bosProje();p.meta.ad='Cihaz B';projeEkle(p)}")
    for x in (pg, pb):
        await x.evaluate("async()=>{ESY={token:'ghp_TEST'};await esitle(true)}")
    await pg.evaluate("async()=>esitle(true)")
    a = await pg.evaluate("()=>Object.values(DB.projeler).map(p=>p.meta.ad)"); b = await pb.evaluate("()=>Object.values(DB.projeler).map(p=>p.meta.ad)")
    assert 'Cihaz A' in b and 'Cihaz B' in a, (a, b)
    assert len(GIST) == 1, GIST.keys()
    await B.close()

async def main():
    port = bos_port(); srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(port)], cwd=KOK, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(0.8); url = f'http://127.0.0.1:{port}/'
        async with async_playwright() as p:
            b = await p.chromium.launch()
            for t in [surum_eslesmesi, acilis_ve_calismalar, hesap_tutarliligi, dis_kose_l_profil, kasa_dayanimi, damla_hidroligi, malzeme_eslesmesi, metin_pdf, hazirlik_klasoru, ara_dikme_lamasi, sulama_detayi, esitleme]:
                ctx = await b.new_context(service_workers='block', viewport={'width': 390, 'height': 844}, accept_downloads=True)
                await t(ctx, url); await ctx.close()
            await b.close()
    finally:
        srv.terminate()
    gec = sum(1 for _, ok, _ in SONUC if ok)
    for ad, ok, m in SONUC: print(('✓ ' if ok else '✗ ') + ad + (f'  ({m})' if ok else '\n   ' + m))
    print(f'\n{gec}/{len(SONUC)} test geçti'); sys.exit(0 if gec == len(SONUC) else 1)

if __name__ == '__main__':
    asyncio.run(main())
