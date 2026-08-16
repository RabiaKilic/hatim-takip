import re
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from typing import List

from database import engine, Base, SessionLocal
import models


# =========================
# FASTAPI
# =========================

app = FastAPI(
    title="Hatim Takip API",
    version="2.0"
)


# =========================
# CORS
# =========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# VERİTABANI
# =========================

@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)

    # Eski Postgres veritabanlarında eksik sütun varsa ekle
    # (SQLite'ta buna gerek yok, create_all zaten tüm sütunları oluşturuyor)
    if engine.url.get_backend_name() != "sqlite":
        try:
            with engine.begin() as conn:
                conn.exec_driver_sql("""
                    ALTER TABLE cuzler
                    ADD COLUMN IF NOT EXISTS atanma_tarihi TIMESTAMP
                """)
        except Exception:
            pass


# =========================
# YARDIMCI FONKSİYONLAR
# =========================

TELEFON_DESENI = re.compile(r"^05[0-9]{9}$")


def telefon_gecerli_mi(telefon: str) -> bool:
    return bool(TELEFON_DESENI.match(telefon or ""))


def aktif_hatimi_getir(db):
    from models import Hatim

    return db.query(Hatim).filter(
        Hatim.durum == "aktif"
    ).first()


# =========================
# ANA SAYFA
# =========================

@app.get("/")
def ana_sayfa():
    return {
        "mesaj": "Hatim Takip API çalışıyor 🕋"
    }


# =========================
# KULLANICI OLUŞTUR
# =========================

class UserCreate(BaseModel):
    name: str
    phone: str


@app.post("/users")
def create_user(user: UserCreate):
    from models import User

    if not telefon_gecerli_mi(user.phone):
        return {
            "basarili": False,
            "mesaj": "Telefon numarası 05XXXXXXXXX formatında, 11 haneli olmalıdır."
        }

    db = SessionLocal()

    try:
        mevcut = db.query(User).filter(
            User.phone == user.phone
        ).first()

        if mevcut:
            return {
                "basarili": False,
                "mesaj": "Bu telefon numarası zaten kayıtlı.",
                "id": mevcut.id
            }

        new_user = User(
            name=user.name,
            phone=user.phone
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return {
            "basarili": True,
            "mesaj": "Kullanıcı başarıyla oluşturuldu",
            "id": new_user.id,
            "name": new_user.name,
            "phone": new_user.phone
        }

    finally:
        db.close()


# =========================
# TÜM KULLANICILARI GETİR
# =========================

@app.get("/users")
def get_users():
    from models import User

    db = SessionLocal()

    try:
        users = db.query(User).all()

        sonuc = []

        for user in users:
            sonuc.append({
                "id": user.id,
                "name": user.name,
                "phone": user.phone
            })

        return {
            "basarili": True,
            "kullanicilar": sonuc
        }

    finally:
        db.close()


# =========================
# TELEFON NUMARASI İLE GİRİŞ
# =========================

class GirisYap(BaseModel):
    phone: str


@app.post("/giris")
def giris_yap(veri: GirisYap):
    from models import User

    db = SessionLocal()

    try:
        user = db.query(User).filter(
            User.phone == veri.phone
        ).first()

        if user is None:
            return {
                "basarili": False,
                "mesaj": "Bu telefon numarasıyla kayıt bulunamadı."
            }

        return {
            "basarili": True,
            "mesaj": "Giriş başarılı.",
            "user_id": user.id,
            "name": user.name,
            "phone": user.phone
        }

    finally:
        db.close()


# =========================
# KULLANICININ CÜZLERİ
# =========================

@app.get("/users/{user_id}/cuzler")
def kullanici_cuzleri(user_id: int):
    from models import User, Cuz, Hatim

    db = SessionLocal()

    try:
        user = db.query(User).filter(
            User.id == user_id
        ).first()

        if user is None:
            return {
                "basarili": False,
                "mesaj": "Kullanıcı bulunamadı.",
                "kullanici": "",
                "cuzler": []
            }

        cuzler = db.query(Cuz).filter(
            Cuz.user_id == user_id
        ).order_by(Cuz.atanma_tarihi.desc()).all()

        sonuc = []

        for cuz in cuzler:
            hatim = db.query(Hatim).filter(
                Hatim.id == cuz.hatim_id
            ).first()

            sonuc.append({
                "cuz_id": cuz.id,
                "cuz_no": cuz.cuz_no,
                "okundu": cuz.okundu,
                "okunma_tarihi": cuz.okunma_tarihi,
                "hatim_id": cuz.hatim_id,
                "hatim_adi": hatim.name if hatim else None,
                "hatim_durumu": hatim.durum if hatim else None
            })

        return {
            "basarili": True,
            "kullanici": user.name,
            "cuzler": sonuc
        }

    finally:
        db.close()


# =========================
# AKTİF HATMİ GETİR
# =========================

@app.get("/hatims/aktif")
def aktif_hatim():
    db = SessionLocal()

    try:
        hatim = aktif_hatimi_getir(db)

        if hatim is None:
            return {
                "basarili": False,
                "mesaj": "Şu anda aktif bir hatim yok."
            }

        return {
            "basarili": True,
            "hatim_id": hatim.id,
            "adi": hatim.name,
            "baslama_tarihi": hatim.start_date,
            "bitis_tarihi": hatim.end_date,
            "durum": hatim.durum
        }

    finally:
        db.close()


# =========================
# HATİM BAŞLAT
# =========================

class HatimBaslat(BaseModel):
    name: str
    owner_id: int
    start_date: datetime
    end_date: datetime


@app.post("/hatims")
def hatim_baslat(veri: HatimBaslat):
    from models import Hatim, User

    db = SessionLocal()

    try:
        sahip = db.query(User).filter(
            User.id == veri.owner_id
        ).first()

        if sahip is None:
            return {
                "basarili": False,
                "mesaj": "Kullanıcı bulunamadı."
            }

        mevcut_aktif = aktif_hatimi_getir(db)

        if mevcut_aktif is not None:
            return {
                "basarili": False,
                "mesaj": "Zaten aktif bir hatim var. Yeni hatim başlatmadan önce mevcut hatmin tamamlanması gerekiyor.",
                "aktif_hatim_id": mevcut_aktif.id,
                "aktif_hatim_adi": mevcut_aktif.name
            }

        if not veri.name.strip():
            return {
                "basarili": False,
                "mesaj": "Hatmin kimin adına başlatıldığını yazmalısınız."
            }

        if veri.end_date <= veri.start_date:
            return {
                "basarili": False,
                "mesaj": "Bitiş zamanı, başlama zamanından sonra olmalıdır."
            }

        yeni_hatim = models.Hatim(
            name=veri.name.strip(),
            owner_id=veri.owner_id,
            start_date=veri.start_date,
            end_date=veri.end_date,
            durum="aktif"
        )

        db.add(yeni_hatim)
        db.commit()
        db.refresh(yeni_hatim)

        return {
            "basarili": True,
            "mesaj": "Hatim başarıyla başlatıldı.",
            "hatim_id": yeni_hatim.id,
            "adi": yeni_hatim.name,
            "baslama_tarihi": yeni_hatim.start_date,
            "bitis_tarihi": yeni_hatim.end_date
        }

    finally:
        db.close()


# =========================
# CÜZ SEÇ (kullanıcı kendi cüzünü seçer)
# =========================

class CuzSec(BaseModel):
    user_id: int
    cuz_no: int


@app.post("/hatims/{hatim_id}/cuz-sec")
def cuz_sec(hatim_id: int, veri: CuzSec):
    from models import User, Cuz, Hatim

    db = SessionLocal()

    try:
        hatim = db.query(Hatim).filter(
            Hatim.id == hatim_id
        ).first()

        if hatim is None:
            return {
                "basarili": False,
                "mesaj": "Hatim bulunamadı."
            }

        if hatim.durum != "aktif":
            return {
                "basarili": False,
                "mesaj": "Bu hatim artık aktif değil, cüz seçilemez."
            }

        user = db.query(User).filter(
            User.id == veri.user_id
        ).first()

        if user is None:
            return {
                "basarili": False,
                "mesaj": "Kullanıcı bulunamadı."
            }

        if veri.cuz_no < 1 or veri.cuz_no > 30:
            return {
                "basarili": False,
                "mesaj": "Cüz numarası 1 ile 30 arasında olmalıdır."
            }

        # Bu cüz bu hatimde başka birine atanmış mı?
        alinmis = db.query(Cuz).filter(
            Cuz.hatim_id == hatim_id,
            Cuz.cuz_no == veri.cuz_no
        ).first()

        if alinmis:
            return {
                "basarili": False,
                "mesaj": "Bu cüz başka biri tarafından alınmış. Lütfen başka bir cüz seçin."
            }

        yeni_cuz = Cuz(
            hatim_id=hatim_id,
            user_id=veri.user_id,
            cuz_no=veri.cuz_no,
            okundu=False,
            atanma_tarihi=datetime.utcnow()
        )

        db.add(yeni_cuz)
        db.commit()
        db.refresh(yeni_cuz)

        return {
            "basarili": True,
            "mesaj": "Cüz başarıyla alındı.",
            "cuz_id": yeni_cuz.id,
            "cuz_no": yeni_cuz.cuz_no
        }

    except IntegrityError:
        db.rollback()

        return {
            "basarili": False,
            "mesaj": "Bu cüz tam bu sırada başka biri tarafından alındı. Lütfen başka bir cüz seçin."
        }

    except Exception as e:
        db.rollback()

        return {
            "basarili": False,
            "mesaj": "Cüz seçilirken hata oluştu.",
            "hata": str(e)
        }

    finally:
        db.close()


# =========================
# ÇOKLU CÜZ SEÇ (aynı anda birden fazla cüz)
# =========================

class CuzSecCoklu(BaseModel):
    user_id: int
    cuz_no_listesi: List[int]


@app.post("/hatims/{hatim_id}/cuz-sec-coklu")
def cuz_sec_coklu(hatim_id: int, veri: CuzSecCoklu):
    from models import User, Cuz, Hatim

    db = SessionLocal()

    try:
        hatim = db.query(Hatim).filter(
            Hatim.id == hatim_id
        ).first()

        if hatim is None:
            return {
                "basarili": False,
                "mesaj": "Hatim bulunamadı."
            }

        if hatim.durum != "aktif":
            return {
                "basarili": False,
                "mesaj": "Bu hatim artık aktif değil, cüz seçilemez."
            }

        user = db.query(User).filter(
            User.id == veri.user_id
        ).first()

        if user is None:
            return {
                "basarili": False,
                "mesaj": "Kullanıcı bulunamadı."
            }

        cuz_no_listesi = sorted(set(veri.cuz_no_listesi))

        if not cuz_no_listesi:
            return {
                "basarili": False,
                "mesaj": "En az bir cüz seçmelisiniz."
            }

        for cuz_no in cuz_no_listesi:
            if cuz_no < 1 or cuz_no > 30:
                return {
                    "basarili": False,
                    "mesaj": "Cüz numaraları 1 ile 30 arasında olmalıdır."
                }

        alinan_cuzler = []
        alinamayan_cuzler = []

        # Her cüzü tek tek, ayrı bir commit ile deniyoruz. Böylece aynı anda
        # başka biri de cüz alıyorsa, veritabanındaki tekillik kısıtı devreye
        # girer ve sadece o cüz başarısız olur, diğerleri etkilenmez.
        for cuz_no in cuz_no_listesi:

            mevcut = db.query(Cuz).filter(
                Cuz.hatim_id == hatim_id,
                Cuz.cuz_no == cuz_no
            ).first()

            if mevcut:
                alinamayan_cuzler.append(cuz_no)
                continue

            try:
                yeni_cuz = Cuz(
                    hatim_id=hatim_id,
                    user_id=veri.user_id,
                    cuz_no=cuz_no,
                    okundu=False,
                    atanma_tarihi=datetime.utcnow()
                )

                db.add(yeni_cuz)
                db.commit()

                alinan_cuzler.append(cuz_no)

            except IntegrityError:
                db.rollback()
                alinamayan_cuzler.append(cuz_no)

        if alinan_cuzler and not alinamayan_cuzler:
            return {
                "basarili": True,
                "mesaj": "Seçtiğiniz cüzlerin hepsi başarıyla alındı.",
                "alinan_cuzler": alinan_cuzler,
                "alinamayan_cuzler": []
            }

        if alinan_cuzler and alinamayan_cuzler:
            return {
                "basarili": True,
                "mesaj": "Bazı cüzler alındı ama şu cüzler tam bu sırada başkası tarafından alınmış: " +
                          ", ".join(str(n) for n in alinamayan_cuzler),
                "alinan_cuzler": alinan_cuzler,
                "alinamayan_cuzler": alinamayan_cuzler
            }

        return {
            "basarili": False,
            "mesaj": "Seçtiğiniz cüzlerin hepsi başkası tarafından alınmış. Lütfen başka cüzler seçin.",
            "alinan_cuzler": [],
            "alinamayan_cuzler": alinamayan_cuzler
        }

    finally:
        db.close()


# =========================
# CÜZÜ OKUDUM
# =========================

@app.put("/cuzler/{cuz_id}/okundu")
def cuz_okundu(cuz_id: int):
    from models import Cuz, Hatim

    db = SessionLocal()

    try:
        cuz = db.query(Cuz).filter(
            Cuz.id == cuz_id
        ).first()

        if cuz is None:
            return {
                "basarili": False,
                "mesaj": "Cüz bulunamadı."
            }

        if cuz.okundu:
            return {
                "basarili": True,
                "mesaj": "Bu cüz zaten okunmuş.",
                "cuz_no": cuz.cuz_no,
                "okundu": True,
                "hatim_tamamlandi": False
            }

        cuz.okundu = True
        cuz.okunma_tarihi = datetime.utcnow()

        db.commit()
        db.refresh(cuz)

        # Bu cüzün ait olduğu hatimdeki tüm cüzler okundu mu?
        # Öyleyse hatim otomatik olarak tamamlanmış sayılır ve kapanır.
        hatim_tamamlandi = False

        hatim = db.query(Hatim).filter(
            Hatim.id == cuz.hatim_id
        ).first()

        if hatim and hatim.durum == "aktif":
            okunmayan_var_mi = db.query(Cuz).filter(
                Cuz.hatim_id == hatim.id,
                Cuz.okundu == False  # noqa: E712
            ).first()

            alinan_cuz_sayisi = db.query(Cuz).filter(
                Cuz.hatim_id == hatim.id
            ).count()

            if okunmayan_var_mi is None and alinan_cuz_sayisi == 30:
                hatim.durum = "tamamlandi"
                hatim.tamamlanma_tarihi = datetime.utcnow()
                db.commit()
                hatim_tamamlandi = True

        return {
            "basarili": True,
            "mesaj": "Cüz başarıyla okundu olarak işaretlendi.",
            "cuz_id": cuz.id,
            "cuz_no": cuz.cuz_no,
            "okundu": cuz.okundu,
            "okunma_tarihi": cuz.okunma_tarihi,
            "hatim_tamamlandi": hatim_tamamlandi
        }

    except Exception as e:
        db.rollback()

        return {
            "basarili": False,
            "mesaj": "Cüz okundu olarak işaretlenirken hata oluştu.",
            "hata": str(e)
        }

    finally:
        db.close()


# =========================
# HATİM DURUMU (İLERLEME)
# =========================

@app.get("/hatims/{hatim_id}/durum")
def hatim_durumu(hatim_id: int):
    from models import Hatim, Cuz

    db = SessionLocal()

    try:
        hatim = db.query(Hatim).filter(
            Hatim.id == hatim_id
        ).first()

        if hatim is None:
            return {
                "basarili": False,
                "mesaj": "Hatim bulunamadı."
            }

        # Bir hatim her zaman 30 cüzden oluşur
        toplam_cuz = 30

        okunan_cuz = db.query(Cuz).filter(
            Cuz.hatim_id == hatim_id,
            Cuz.okundu == True  # noqa: E712
        ).count()

        alinan_cuz = db.query(Cuz).filter(
            Cuz.hatim_id == hatim_id
        ).count()

        kalan_cuz = toplam_cuz - okunan_cuz

        ilerleme_yuzdesi = round(
            (okunan_cuz / toplam_cuz) * 100
        )

        return {
            "basarili": True,
            "hatim_id": hatim.id,
            "hatim_adi": hatim.name,
            "durum": hatim.durum,
            "toplam_cuz": toplam_cuz,
            "alinan_cuz": alinan_cuz,
            "okunan_cuz": okunan_cuz,
            "kalan_cuz": kalan_cuz,
            "ilerleme_yuzdesi": ilerleme_yuzdesi
        }

    finally:
        db.close()


# =========================
# HATİMDEKİ TÜM CÜZLERİN LİSTESİ (GENEL GÖRÜNÜM)
# =========================

@app.get("/hatims/{hatim_id}/cuzler-listesi")
def hatim_cuzler_listesi(hatim_id: int):
    from models import Hatim, Cuz, User

    db = SessionLocal()

    try:
        hatim = db.query(Hatim).filter(
            Hatim.id == hatim_id
        ).first()

        if hatim is None:
            return {
                "basarili": False,
                "mesaj": "Hatim bulunamadı."
            }

        cuzler = db.query(Cuz).filter(
            Cuz.hatim_id == hatim_id
        ).all()

        cuz_haritasi = {
            cuz.cuz_no: cuz
            for cuz in cuzler
        }

        sonuc = []

        for cuz_no in range(1, 31):
            cuz = cuz_haritasi.get(cuz_no)

            if cuz is None:
                sonuc.append({
                    "cuz_no": cuz_no,
                    "atanmis": False,
                    "kullanici": None,
                    "okundu": False
                })
                continue

            kullanici = db.query(User).filter(
                User.id == cuz.user_id
            ).first()

            sonuc.append({
                "cuz_no": cuz_no,
                "atanmis": True,
                "kullanici": kullanici.name if kullanici else None,
                "okundu": cuz.okundu
            })

        return {
            "basarili": True,
            "hatim_adi": hatim.name,
            "durum": hatim.durum,
            "cuzler": sonuc
        }

    finally:
        db.close()


# =========================
# TAMAMLANAN HATİMLER
# =========================

@app.get("/hatims/tamamlanan")
def tamamlanan_hatimler():
    from models import Hatim, User

    db = SessionLocal()

    try:
        hatimler = db.query(Hatim).filter(
            Hatim.durum == "tamamlandi"
        ).order_by(Hatim.tamamlanma_tarihi.desc()).all()

        sonuc = []

        for hatim in hatimler:
            baslatan = db.query(User).filter(
                User.id == hatim.owner_id
            ).first()

            sonuc.append({
                "hatim_id": hatim.id,
                "adi": hatim.name,
                "baslatan": baslatan.name if baslatan else None,
                "baslama_tarihi": hatim.start_date,
                "hedef_bitis_tarihi": hatim.end_date,
                "tamamlanma_tarihi": hatim.tamamlanma_tarihi
            })

        return {
            "basarili": True,
            "hatimler": sonuc
        }

    finally:
        db.close()


# =========================
# VERİTABANINI TEMİZLE (SADECE SEN KULLAN)
# =========================

# Bu şifreyi Render'da Environment Variables kısmından ADMIN_SIFRE olarak
# ayarlayabilirsin. Ayarlamazsan aşağıdaki varsayılan şifre kullanılır.
ADMIN_SIFRE = os.getenv("ADMIN_SIFRE", "4444")


class TemizlemeIstegi(BaseModel):
    sifre: str


@app.post("/admin/temizle")
def veritabanini_temizle(istek: TemizlemeIstegi):
    from models import User, Hatim, Cuz

    if istek.sifre != ADMIN_SIFRE:
        return {
            "basarili": False,
            "mesaj": "Şifre yanlış."
        }

    db = SessionLocal()

    try:
        db.query(Cuz).delete()
        db.query(Hatim).delete()
        db.query(User).delete()

        db.commit()

        return {
            "basarili": True,
            "mesaj": "Veritabanı tamamen temizlendi."
        }

    except Exception as e:
        db.rollback()

        return {
            "basarili": False,
            "mesaj": "Temizlerken hata oluştu.",
            "hata": str(e)
        }

    finally:
        db.close()
