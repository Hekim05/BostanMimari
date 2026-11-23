# Testler

`python tests/calistir.py` sayfayı yerel sunucuda açar ve uçtan uca kontrol eder:

| Test | Ne doğrular |
|---|---|
| surum_eslesmesi | `sw.js` ile `index.html` sürümü aynı, manifest geçerli |
| acilis_ve_calismalar | Çalışmalar sayfası, kart açma, adım rehberi |
| hesap_tutarliligi | I/L/U × malzeme kasası × 4 malzeme: sonsuz/boş değer yok |
| kasa_dayanimi | Bilinen durumlar: ahşap 45 cm uygun, briket 60 cm yetersiz, gömülmemiş ince tahta yetersiz |
| damla_hidroligi | 4 bar'da basınç düşürücü eklenir, 0,2 bar'da kritik uyarı, PC damlatıcı sabit debi |
| malzeme_eslesmesi | Malzeme adı → görsel eşleşmesi (ör. “sulama” ≠ “lama”) |
| metin_pdf | Rapor PDF'i metin tabanlı, DejaVu gömülü |
| hazirlik_klasoru | ZIP üretimi, ajanın 2. kontrolünde hata yok, önizleme sekmeleri |
| esitleme | Sahte GitHub API ile iki cihaz arası birleştirme |

Her `main` gönderiminde GitHub Actions'ta otomatik çalışır (Actions › Testler). Başarısız testin ekran görüntüsü `tests/cikti/` altına yazılır.
