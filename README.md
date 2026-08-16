# Hatim Takip

WhatsApp grubunda dağıtılan hatim cüzlerinin takibini kolaylaştıran bir web uygulaması.
Kayıtlı bir kullanıcı hatim başlatır (kimin adına, başlama/bitiş tarihi ile), herkes
kendi istediği cüzü seçer, okuduğunda işaretler. Aynı cüz iki kişiye verilmez. Hatimdeki
30 cüzün tamamı okunduğunda hatim otomatik olarak "tamamlandı" sayılır ve kapanır;
tamamlanan hatimler ayrı bir sayfada açıklamalarıyla listelenir.

## Sayfalar ve akış

- `index.html` — giriş noktası; daha önce giriş yapılmışsa `panel.html`'e, yapılmamışsa
  `giris.html`'e yönlendirir.
- `kayit.html` — ad soyad ve telefon numarasıyla kayıt olunur, kayıt sonrası otomatik
  giriş yapılır.
- `giris.html` — telefon numarasıyla giriş yapılır.
- `panel.html` — ana sayfa: aktif hatim bilgisi, "cüzlerim", cüz okuma, hatim başlatma /
  cüz seçme yönlendirmeleri.
- `hatim-baslat.html` — yeni hatim başlatma formu (kimin adına, başlama/bitiş tarihi).
  Aktif bir hatim varken yeni hatim başlatılamaz.
- `cuz-sec.html` — aktif hatimden boşta olan cüzleri seçme ekranı. Bir kişi aynı anda
  birden fazla cüz seçip tek seferde alabilir (ör. 7, 13, 25). İki kişi tam aynı anda
  aynı cüzü almaya çalışırsa, veritabanı seviyesinde konulan kısıt sayesinde sadece biri
  başarılı olur; diğerine "bu cüz az önce başkası tarafından alındı" mesajı gösterilir.
- `genel-durum.html` — aktif hatimdeki 30 cüzün tamamının kimde olduğunu ve okunma
  durumunu gösterir.
- `biten-hatimler.html` — tamamlanmış hatimlerin listesi ve açıklaması (kimin adına,
  başlama/hedef bitiş/gerçek tamamlanma tarihleri).

Telefon numarası girişi 10 haneli olacak şekilde tasarlandı (başındaki "0" otomatik
ekleniyor, siz sadece "5" ile başlayan 10 haneyi yazıyorsunuz — örn. 505 058 84 34).

## Bu teslimde neler düzeltildi / eklendi

- `Cuz` modelinde `hatim_id` alanı hiç tanımlanmamıştı, bu yüzden cüz atama her denemede
  arka planda hataya düşüyordu. Alan eklendi.
- Kayıt/giriş/cüz okuma adresleri frontend ile backend arasında uyuşmuyordu, düzeltildi.
- Sayfalar arası geçiş ve yönlendirme akışı kuruldu (`index.html` artık bir yönlendirme
  noktası, kayıt/giriş sonrası otomatik panele geçiş var).
- Telefon numarası girişi 10 haneli hale getirildi, operatör kodunun başındaki "0" otomatik
  ekleniyor.
- Çoklu hatim desteği: artık tek sabit hatim yerine, kayıtlı kullanıcılar istedikleri zaman
  yeni bir hatim başlatabiliyor (kimin adına, başlama/bitiş tarihiyle). Aynı anda sadece
  bir hatim aktif olabiliyor.
- Kullanıcılar artık kendi istedikleri cüzü seçiyor (otomatik atama yerine); aynı cüz
  başka birine verilmiyor.
- Bir hatimdeki 30 cüzün tamamı okunduğunda hatim otomatik olarak "tamamlandı" durumuna
  geçiyor ve kapanıyor.
- Tamamlanan hatimlerin açıklamasını gösteren yeni bir sayfa eklendi.
- Veritabanı varsayılan olarak SQLite'a çevrildi, böylece Postgres kurup ayarlamaya
  gerek kalmadan tek komutla çalışıyor (istersen aşağıda anlatıldığı gibi Postgres'e
  geri dönebilirsin).

## Kurulum ve çalıştırma

```bash
# 1) Proje klasörüne gir
cd hatim_takip

# 2) Sanal ortam oluştur (isteğe bağlı ama önerilir)
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# 3) Gerekli paketleri kur
pip install -r requirements.txt

# 4) Sunucuyu başlat
uvicorn main:app --reload
```

Sunucu `http://127.0.0.1:8000` adresinde çalışmaya başlar. İlk açılışta otomatik olarak
`hatim.db` adında bir SQLite dosyası oluşturulur.

Ardından `frontend/index.html` dosyasını tarayıcıda aç — otomatik olarak kayıt/giriş
sayfasına yönlendirileceksin.

## Postgres kullanmak istersen

`database.py` içinde varsayılan olarak SQLite kullanılıyor. Postgres'e dönmek için
sunucuyu başlatmadan önce şu ortam değişkenini ayarlaman yeterli:

```bash
set DATABASE_URL=postgresql+psycopg2://postgres:sifre@localhost:5432/hatim_db   # Windows
# export DATABASE_URL=postgresql+psycopg2://postgres:sifre@localhost:5432/hatim_db  # Mac/Linux
```

Bu durumda `psycopg2-binary` paketini de kurman gerekir: `pip install psycopg2-binary`.

## Bilinmesi gereken sınırlamalar

- Aynı anda sadece bir hatim aktif olabilir; yeni hatim başlatmak için önceki hatmin
  tamamlanması (30 cüzün de okunması) gerekiyor.
- Şifre yok; giriş sadece telefon numarasıyla yapılıyor — bu haliyle sadece güvenilir,
  kapalı bir grup içinde (ör. aile/mahalle WhatsApp grubu) kullanılmaya uygun.
- Bir kullanıcı aynı aktif hatimde yalnızca bir cüz alabiliyor.
