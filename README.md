# Eğitim Koçu Asistanı - Analiz Motoru

Bu proje, LGS ve YKS sınav sorularını otomatik olarak analiz eden bir sistemdir.

## Kurulum

1. Gerekli kütüphaneleri yükleyin:
```bash
pip install -r requirements.txt
```

2. `.env` dosyası oluşturun ve Gemini API anahtarınızı ekleyin:
```bash
cp .env.example .env
# .env dosyasını düzenleyip GEMINI_API_KEY değerini girin
```

Gemini API anahtarı almak için: https://aistudio.google.com/app/apikey

3. PDF dosyalarını `PDFler` klasörüne yerleştirin:
   - `Lgs.pdf`
   - `Yks.pdf`

4. PDF'leri analiz edip müfredat veritabanını güncelleyin (isteğe bağlı):
```bash
python pdf_analiz.py
```

## Kullanım

1. Analiz motorunu başlatın:
```bash
python analiz_motoru.py
```

2. Analiz edilecek soru görsellerini `soru_resimleri` klasörüne sürükleyin.

3. Raporlar otomatik olarak `raporlar` klasörüne kaydedilecektir.

## Klasör Yapısı

```
Otomasyon/
├── PDFler/              # Lgs.pdf ve Yks.pdf dosyaları
├── soru_resimleri/      # Analiz edilecek görseller (JPG/PNG)
├── raporlar/            # Oluşturulan analiz raporları
├── mufredat_db.json     # Müfredat veritabanı
├── analiz_motoru.py     # Ana analiz motoru
├── pdf_analiz.py        # PDF analiz scripti
├── requirements.txt     # Python bağımlılıkları
└── .env                 # API anahtarları (oluşturulmalı)
```

## Özellikler

- ✅ Otomatik görsel izleme (watchdog)
- ✅ Gemini 1.5 Pro ile görsel analiz
- ✅ Müfredat veritabanı ile konu eşleştirme
- ✅ Geçmiş yıl soru dağılımı analizi
- ✅ Pedagojik koç tavsiyeleri
- ✅ 10 saniye içinde rapor üretimi

## Notlar

- Sistem sadece JPG ve PNG formatındaki görselleri işler
- Her görsel için benzersiz bir rapor oluşturulur
- Kritik konular otomatik olarak işaretlenir
- Raporlar hem konu analizi hem de öğrenci tavsiyeleri içerir

