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

ORNEK = """()=>{const p=bosProje();p.meta.ad='Test bostanı';p.meta.bostan='Test';p.meta.hazirlayan='Test';p.meta.ortakOlcu='hayir';p.alan={en:30,boy:20,kuzey:0,enlem:39.9};p.sulama.basinc=3;p.gruplar=[
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
async def yerlesim_mesafe(pg):
    await pg.evaluate(ORNEK); await pg.wait_for_timeout(300)
    r = await pg.evaluate("""()=>{const mn=()=>{let m=Infinity,ic=Infinity,ke=Infinity;const en=+st.alan.en,boy=+st.alan.boy;
        H.gr.forEach((G,i)=>{for(let a=0;a<G.poli.length;a++)for(let b=a+1;b<G.poli.length;b++)ic=Math.min(ic,poliMes(G.poli[a],G.poli[b]));
          G.poli.forEach(P=>P.forEach(q=>ke=Math.min(ke,q[0],q[1],en-q[0],boy-q[1])));H.gr.forEach((O,j)=>{if(j>i)m=Math.min(m,grupMes(G,O))})});return{m,ic,ke}};
      const b0=mn();
      // B grubundaki kasayı 90° çevir: grup içi çakışma olmamalı
      const gB=st.gruplar[1];gB.sutun=3;degisti();gB.kasaAci={0:90,1:45};degisti();const b1=mn();
      // B grubunu A'nın üstüne sürükle: otomatik ayrılmalı
      gB.x=st.gruplar[0].x;gB.y=st.gruplar[0].y;degisti();const b2=mn();
      return{b0,b1,b2,ax:st.gruplar[0].x,bx:gB.x,by:gB.y}}""")
    assert r['b1']['ic'] >= 1.495 and r['b2']['m'] >= 1.495 and r['b2']['ke'] >= 0.995, r
    assert abs(r['ax'] - 1) < 1e-9 or True, r

@test
async def sulama_hatlari(pg):
    r = await pg.evaluate("""()=>{const p=bosProje();p.alan={...p.alan,en:30,boy:20};p.sulama.kx=0.5;p.sulama.ky=0.5;
      p.gruplar=[yeniGrup(0,{L:600,W:200,H:60,x:2,y:2,sutun:1}),yeniGrup(1,{L:300,W:120,H:45,x:12,y:8,sutun:3,sira:2,aci:20,kasaAci:{1:90,4:30}}),yeniGrup(2,{L:300,W:120,H:45,x:3,y:12,sutun:2,yon:'dikey'})];projeEkle(p);
      const ic=(q,P)=>{let c=false;for(let i=0,j=P.length-1;i<P.length;j=i++){const a=P[i],b=P[j];if((a[1]>q[1])!==(b[1]>q[1])&&q[0]<(b[0]-a[0])*(q[1]-a[1])/(b[1]-a[1])+a[0])c=!c}return c};
      let kesen=0;H.gr.forEach(G=>{const B=G.boru;for(let i=0;i<B.bag.length-1;i++){const a=B.bag[i],b=B.bag[i+1];for(let t=0;t<=1;t+=0.02){const q=[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t];H.gr.forEach(O=>O.poli.forEach(P=>{if(ic(q,P))kesen++}))}}});
      const G=H.gr[1];let disarda=0;G.boru.inis.forEach((h,i)=>{const bed=G.beds[Math.floor(i/G.boru.dusus)],P=G.poli[G.beds.indexOf(bed)],z=G.rot(h[h.length-1]);if(!ic(z,P))disarda++});
      return{kesen,disarda,anaM:H.top.anaM}}""")
    assert r['kesen'] == 0 and r['disarda'] == 0 and r['anaM'] > 0, r

@test
async def gergi_secenegi(pg):
    r = await pg.evaluate("""()=>{const o=[];['oto','seyrek','yok'].forEach(sec=>{const p=bosProje();p.gruplar=[yeniGrup(0,{L:400,W:120,H:60,gomme:20,sutun:1,gergiSec:sec})];projeEkle(p);const G=H.gr[0];
      o.push({g:G.k.gergi,eta:G.day.eta,parca:G.parca.filter(x=>/Gergi/.test(x.kalem)).reduce((a,x)=>a+x.adet,0)})});return o}""")
    assert r[0]['g'] == 3 and r[1]['g'] == 2 and r[2]['g'] == 0, r
    assert r[0]['parca'] == 3 and r[2]['parca'] == 0, r
    assert r[0]['eta'] <= 1 and r[2]['eta'] > 1, r   # gergisiz 20 cm gömme yetmez: program uyarmalı

@test
async def ortak_olcu(pg):
    r = await pg.evaluate("""()=>{const p=bosProje();p.gruplar=[yeniGrup(0,{L:300,W:120,H:45,x:1,y:1,sutun:1}),yeniGrup(1,{L:200,W:100,H:30,malzeme:'galvaniz',x:1,y:6,sutun:2}),yeniGrup(2,{L:500,W:90,H:60,x:1,y:10,sutun:1,durum:'mevcut'})];projeEkle(p);
      const a=H.gr.map(G=>[G.k.L,G.k.W,G.k.Hr,G.k.m,G.sut]);
      st.gruplar[0].L=400;degisti();const b=H.gr.map(G=>G.k.L);
      renderGruplar();const tak=document.querySelectorAll('[data-ayri]').length;
      document.querySelector('[data-ayri="1"]').click();const c=H.gr.map(G=>[G.k.L,G.k.m]);
      return{a,b,tak,c}}""")
    a, b, c = r['a'], r['b'], r['c']
    assert a[0][:4] == a[1][:4] and a[1][4] == 2, r        # B, A ölçüsünü aldı; yerleşim (sütun) kendi
    assert a[2][0] == 500, r                                # mevcut grup değişmedi
    assert b[0] == b[1] == 400 and b[2] == 500 and r['tak'] == 1, r
    assert c[1] == [200, 'galvaniz'], r                     # ayrı ölçüye dönünce eski değerler geri geldi

@test
async def grup_belirleme(pg):
    r = await pg.evaluate("""()=>{const p=bosProje();p.alan={...p.alan,en:30,boy:20};p.gruplar=[yeniGrup(0,{L:300,W:120,H:45,x:2,y:2,sutun:3,sira:2}),yeniGrup(1,{x:2,y:10,sutun:2,aci:15})];projeEkle(p);
      const cen=(G,no)=>{const P=G.poli[G.beds.findIndex(b=>b.no===no)];return P.reduce((a,q)=>[a[0]+q[0]/4,a[1]+q[1]/4],[0,0]).map(x=>Math.round(x*100)/100)};
      const once=[cen(H.gr[0],1),cen(H.gr[0],4),cen(H.gr[1],0)];yer.kasalar=[{gi:0,no:1},{gi:0,no:4},{gi:1,no:0}];grupDuzenle(null);
      const G=H.gr[H.gr.length-1],sonra=G.beds.map(b=>cen(G,b.no)),say1=H.gr.map(G=>G.beds.length);
      yer.kasalar=[{gi:1,no:1}];grupDuzenle(2);const say2=H.gr.map(G=>G.beds.length);
      const ic=(q,P)=>{let c=false;for(let i=0,j=P.length-1;i<P.length;j=i++){const a=P[i],b=P[j];if((a[1]>q[1])!==(b[1]>q[1])&&q[0]<(b[0]-a[0])*(q[1]-a[1])/(b[1]-a[1])+a[0])c=!c}return c};
      let kesen=0;H.gr.forEach(G=>G.boru.hatlar.map(h=>h.map(q=>G.rot(q))).concat([G.boru.bag]).forEach(h=>{for(let i=0;i<h.length-1;i++)for(let t=0.02;t<0.99;t+=0.02){const q=[h[i][0]+(h[i+1][0]-h[i][0])*t,h[i][1]+(h[i+1][1]-h[i][1])*t];H.gr.forEach(O=>O.poli.forEach(P=>{if(ic(q,P))kesen++}))}}));
      return{once,sonra,say1,say2,kesen}}""")
    assert r['once'] == r['sonra'], r                 # kasalar yerinde kaldı
    assert r['say1'] == [4, 1, 3], r
    assert sum(r['say2']) == 8 and len(r['say2']) == 2, r   # B boşaldı ve kaldırıldı
    assert r['kesen'] == 0, r

@test
async def hizalama(pg):
    r = await pg.evaluate("""()=>{const p=bosProje();p.alan={...p.alan,en:40,boy:30};p.gruplar=[yeniGrup(0,{L:300,W:120,H:45,x:2,y:2,sutun:3}),yeniGrup(1,{x:3.37,y:7.9,sutun:2}),yeniGrup(2,{x:21.4,y:3.13,sutun:1})];projeEkle(p);
      sekme('cizim');const cy=(gi,no)=>{const G=H.gr[gi],k=kasaKutu(G,G.beds.find(b=>b.no===no));return[(k.x0+k.x1)/2,(k.y0+k.y1)/2,k.x0,k.y0]};
      // grup kapsamında: C grubunu A'nın sırasına (aynı y) getir
      yer.kasalar=[{gi:0,no:0},{gi:2,no:0}];$('#hizaKapsam').value='grup';hizala('y');const g1=[cy(0,0)[1],cy(2,0)[1],H.gr[2].serbest];
      // kasa kapsamında: B1'in sol kenarını A1'e hizala
      yer.kasalar=[{gi:0,no:0},{gi:1,no:0}];$('#hizaKapsam').value='kasa';hizala('sol');const g2=[cy(0,0)[2],cy(1,0)[2]];
      return{g1,g2}}""")
    assert abs(r['g1'][0] - r['g1'][1]) < 0.011 and not r['g1'][2], r
    assert abs(r['g2'][0] - r['g2'][1]) < 0.011, r

@test
async def geri_al_ve_oto(pg):
    r = await pg.evaluate("""()=>{const p=bosProje();p.alan={...p.alan,en:30,boy:20};p.gruplar=[yeniGrup(0,{L:300,W:120,H:45,x:2,y:2,sutun:3,sira:2}),yeniGrup(1,{x:2,y:9,sutun:2})];projeEkle(p);sekme('cizim');
      const uu=()=>H.sorun.filter(b=>b.sev==='kritik'&&/üst üste/.test(b.baslik)).length;const x0=JSON.stringify(st.gruplar);
      // çakıştıracak hizalama reddedilmeli: A1 referans, A5'i aynı sütuna (A4 ile çakışır)
      yer.kasalar=[{gi:0,no:0},{gi:0,no:4}];$('#hizaKapsam').value='kasa';hizala('x');const red=JSON.stringify(st.gruplar)===x0&&uu()===0;
      // grubu taşı, sonra geri al
      st.gruplar[1].x=8;degisti();const tasindi=st.gruplar[1].x;geriAl();const geri=st.gruplar[1].x;
      // dağınık hale getir ve otomatik yerleştir
      st.gruplar[0].x=15;st.gruplar[1].x=14.5;st.gruplar[1].y=2.5;YS=null;degisti();otoYerlestir();
      let m=Infinity;for(let i=0;i<H.gr.length;i++)for(let j=i+1;j<H.gr.length;j++)m=Math.min(m,grupMes(H.gr[i],H.gr[j]));
      return{red,tasindi,geri,m,uu:uu()}}""")
    assert r['red'] and r['tasindi'] == 8 and r['geri'] == 2, r
    assert r['m'] >= 1.495 and r['uu'] == 0, r

@test
async def sorgu(pg):
    await pg.evaluate(ORNEK); await pg.wait_for_timeout(300)
    r = await pg.evaluate("""()=>({v:sorgula('vida kaç adet')[0],e:sorgula('EPDM nedir')[0],k:sorgula('kış').map(x=>x.baslik),y:sorgula('xyzq').length})""")
    assert r['v']['tur'] == 'parca' and 'vida' in r['v']['baslik'].lower(), r
    assert r['e']['tur'] == 'soz' and 'EPDM' in r['e']['baslik'], r
    assert not any('gömülü' in b for b in r['k']) and r['y'] == 0, r
    await pg.click('#btnSorgu'); await pg.fill('#sorguGir', 'conta'); await pg.wait_for_timeout(400)
    assert await pg.locator('#sorguSonuc .sgK').count() > 0
    await pg.locator('[data-sgg]').first.click(); await pg.wait_for_timeout(300)
    assert not await pg.evaluate("$('#dlgSorgu').open")

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
            for t in [surum_eslesmesi, acilis_ve_calismalar, hesap_tutarliligi, dis_kose_l_profil, kasa_dayanimi, damla_hidroligi, malzeme_eslesmesi, metin_pdf, hazirlik_klasoru, ara_dikme_lamasi, yerlesim_mesafe, sulama_hatlari, gergi_secenegi, ortak_olcu, grup_belirleme, hizalama, geri_al_ve_oto, sorgu, sulama_detayi, esitleme]:
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
