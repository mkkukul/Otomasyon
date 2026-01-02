"""
Analiz Motoru - Eğitim Koçu Asistanı
Watchdog ile görsel izleme ve Gemini API ile soru analizi
"""
import os
import json
import time
from datetime import datetime
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image

# .env dosyasını yükle
load_dotenv()

# Klasör yolları
SORU_RESIMLERI_DIR = Path(r"D:\Git HubX\Otomasyon\soru_resimleri")
RAPORLAR_DIR = Path(r"D:\Git HubX\Otomasyon\raporlar")
MUFREDAT_DB_PATH = Path(r"D:\Git HubX\Otomasyon\mufredat_db.json")

# Gemini API yapılandırması
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY .env dosyasında tanımlanmamış!")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro')

# Müfredat veritabanını yükle
with open(MUFREDAT_DB_PATH, 'r', encoding='utf-8') as f:
    MUFREDAT_DB = json.load(f)


class SoruAnalizHandler(FileSystemEventHandler):
    """Yeni görsel dosyaları için event handler"""
    
    def __init__(self):
        self.processed_files = set()
    
    def on_created(self, event):
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # Sadece görsel dosyalarını işle
        if file_path.suffix.lower() not in ['.jpg', '.jpeg', '.png']:
            return
        
        # Dosya tamamen yazılana kadar bekle
        time.sleep(1)
        
        # Zaten işlenmiş dosyaları atla
        if str(file_path) in self.processed_files:
            return
        
        self.processed_files.add(str(file_path))
        print(f"Yeni görsel tespit edildi: {file_path.name}")
        
        try:
            self.analiz_et(file_path)
        except Exception as e:
            print(f"Hata: {e}")
    
    def analiz_et(self, image_path):
        """Görseli analiz et ve rapor oluştur"""
        start_time = time.time()
        
        # Görseli PIL Image olarak yükle
        try:
            image = Image.open(image_path)
        except Exception as e:
            print(f"Görsel açılamadı: {e}")
            return
        
        # Gemini API'ye gönder
        prompt = self.olustur_prompt()
        
        try:
            response = model.generate_content([prompt, image])
            analiz_sonucu = response.text
            
            # Müfredat veritabanından konu bilgilerini çıkar
            konu_bilgisi = self.konu_bilgisi_cikar(analiz_sonucu)
            
            # Rapor oluştur
            rapor = self.rapor_olustur(analiz_sonucu, konu_bilgisi, image_path)
            
            # Raporu kaydet
            rapor_dosyasi = self.rapor_kaydet(rapor, konu_bilgisi)
            
            elapsed_time = time.time() - start_time
            print(f"✓ Analiz tamamlandı! ({elapsed_time:.2f} saniye)")
            print(f"✓ Rapor kaydedildi: {rapor_dosyasi}")
            
        except Exception as e:
            print(f"Gemini API hatası: {e}")
            raise
    
    def olustur_prompt(self):
        """Gemini API için prompt oluştur"""
        return """Bu görselde bir LGS veya YKS sınav sorusu var. Lütfen şu bilgileri tespit et:

1. Sınav Tipi: LGS mi YKS mi? (Eğer YKS ise TYT mi AYT mi?)
2. Ders/Branş: Hangi ders? (Türkçe, Matematik, Fen Bilimleri, Fizik, Kimya, Biyoloji, vb.)
3. Konu: Sorunun hangi konuya ait olduğunu belirle. Mümkün olduğunca spesifik ol.

Cevabını şu formatta ver:
SINAV_TİPİ: [LGS/YKS-TYT/YKS-AYT]
DERS: [Ders adı]
KONU: [Konu adı]
AÇIKLAMA: [Sorunun kısa açıklaması]"""
    
    def konu_bilgisi_cikar(self, analiz_sonucu):
        """Analiz sonucundan konu bilgisini çıkar ve müfredat DB'den eşleştir"""
        sinav_tipi = None
        ders = None
        konu = None
        
        # Analiz sonucunu parse et
        for line in analiz_sonucu.split('\n'):
            if 'SINAV_TİPİ' in line or 'Sınav Tipi' in line:
                if 'LGS' in line:
                    sinav_tipi = 'LGS'
                elif 'TYT' in line:
                    sinav_tipi = 'YKS-TYT'
                elif 'AYT' in line:
                    sinav_tipi = 'YKS-AYT'
            elif 'DERS' in line or 'Ders' in line:
                ders = line.split(':')[-1].strip()
            elif 'KONU' in line or 'Konu' in line:
                konu = line.split(':')[-1].strip()
        
        # Müfredat DB'den eşleşen konuyu bul
        konu_bilgisi = None
        
        if sinav_tipi == 'LGS' and ders:
            if ders in MUFREDAT_DB['LGS']:
                for konu_adi, konu_data in MUFREDAT_DB['LGS'][ders].items():
                    if konu and (konu.lower() in konu_adi.lower() or konu_adi.lower() in konu.lower()):
                        konu_bilgisi = {
                            'sinav_tipi': sinav_tipi,
                            'ders': ders,
                            'konu': konu_adi,
                            'data': konu_data
                        }
                        break
        
        elif sinav_tipi and sinav_tipi.startswith('YKS-'):
            yks_tipi = 'TYT' if 'TYT' in sinav_tipi else 'AYT'
            if yks_tipi in MUFREDAT_DB['YKS'] and ders:
                if ders in MUFREDAT_DB['YKS'][yks_tipi]:
                    for konu_adi, konu_data in MUFREDAT_DB['YKS'][yks_tipi][ders].items():
                        if konu and (konu.lower() in konu_adi.lower() or konu_adi.lower() in konu.lower()):
                            konu_bilgisi = {
                                'sinav_tipi': sinav_tipi,
                                'ders': ders,
                                'konu': konu_adi,
                                'data': konu_data
                            }
                            break
        
        return konu_bilgisi or {
            'sinav_tipi': sinav_tipi or 'Bilinmiyor',
            'ders': ders or 'Bilinmiyor',
            'konu': konu or 'Bilinmiyor',
            'data': None
        }
    
    def rapor_olustur(self, analiz_sonucu, konu_bilgisi, image_path):
        """Detaylı rapor oluştur"""
        rapor = []
        rapor.append("=" * 60)
        rapor.append("SORU ANALİZ RAPORU")
        rapor.append("=" * 60)
        rapor.append(f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        rapor.append(f"Görsel: {image_path.name}")
        rapor.append("")
        
        # 1. Tespit Edilen Konu
        rapor.append("1. TESPİT EDİLEN KONU")
        rapor.append("-" * 60)
        if konu_bilgisi['data']:
            rapor.append(f"Sınav: {konu_bilgisi['sinav_tipi']}")
            rapor.append(f"Ders: {konu_bilgisi['ders']}")
            rapor.append(f"Konu: {konu_bilgisi['konu']}")
            if 'alt_konular' in konu_bilgisi['data']:
                rapor.append(f"Alt Konular: {', '.join(konu_bilgisi['data']['alt_konular'])}")
        else:
            rapor.append(f"Sınav: {konu_bilgisi['sinav_tipi']}")
            rapor.append(f"Ders: {konu_bilgisi['ders']}")
            rapor.append(f"Konu: {konu_bilgisi['konu']}")
            rapor.append("(Müfredat veritabanında eşleşme bulunamadı)")
        rapor.append("")
        
        # 2. Sınav Ağırlığı
        rapor.append("2. SINAV AĞIRLIĞI")
        rapor.append("-" * 60)
        if konu_bilgisi['data'] and 'history' in konu_bilgisi['data']:
            history = konu_bilgisi['data']['history']
            ortalama = sum(history) / len(history) if history else 0
            toplam_soru = sum(history)
            yuzde_etkisi = (ortalama / 50) * 100 if konu_bilgisi['sinav_tipi'] == 'LGS' else (ortalama / 80) * 100
            
            rapor.append(f"Bu konudan 2018-2024 yılları arasında:")
            rapor.append(f"  • Yıllık ortalama soru sayısı: {ortalama:.1f}")
            rapor.append(f"  • Toplam soru sayısı: {toplam_soru}")
            rapor.append(f"  • Soru dağılımı: {history}")
            rapor.append(f"  • Başarı şansına etkisi: %{yuzde_etkisi:.1f}")
            
            if konu_bilgisi['data'].get('importance') == 'Kritik':
                rapor.append(f"  ⚠️  ÖNEM DERECESİ: KRİTİK - Bu konu her yıl düzenli soru çıkıyor!")
        else:
            rapor.append("Geçmiş yıl verisi bulunamadı.")
        rapor.append("")
        
        # 3. Koç Tavsiyesi
        rapor.append("3. KOÇ TAVSİYESİ")
        rapor.append("-" * 60)
        
        if konu_bilgisi['data']:
            ders = konu_bilgisi['ders']
            konu = konu_bilgisi['konu']
            importance = konu_bilgisi['data'].get('importance', 'Normal')
            
            # Ders ve konuya özel tavsiyeler
            tavsiyeler = self.tavsiye_olustur(ders, konu, importance, konu_bilgisi['data'])
            rapor.append(tavsiyeler)
        else:
            rapor.append("Bu konuyla ilgili özel tavsiye için müfredat veritabanında eşleşme gereklidir.")
            rapor.append("Genel tavsiye: Soruyu dikkatlice okuyun, tüm seçenekleri değerlendirin.")
        
        rapor.append("")
        rapor.append("=" * 60)
        rapor.append("Gemini AI Analiz Sonucu:")
        rapor.append("-" * 60)
        rapor.append(analiz_sonucu)
        rapor.append("=" * 60)
        
        return "\n".join(rapor)
    
    def tavsiye_olustur(self, ders, konu, importance, konu_data):
        """Ders ve konuya özel pedagojik tavsiye oluştur"""
        tavsiyeler = []
        
        # Genel tavsiyeler
        if importance == 'Kritik':
            tavsiyeler.append(f"⚠️  {konu} konusu KRİTİK öneme sahip. Bu konudan her yıl düzenli soru çıkmaktadır.")
            tavsiyeler.append("   Bu konuyu mutlaka iyi öğrenmelisiniz!")
        
        # Ders bazlı tavsiyeler
        if ders == "Matematik":
            if "Üslü" in konu or "Köklü" in konu:
                tavsiyeler.append("💡 Üslü ve köklü sayılarda kuralları ezberlemek yerine mantığını anlamaya çalışın.")
                tavsiyeler.append("   Özellikle üslü sayıların çarpımı ve bölümü kurallarına dikkat edin.")
            elif "Geometri" in konu:
                tavsiyeler.append("📐 Geometri sorularında şekil çizmek ve görselleştirmek çok önemlidir.")
                tavsiyeler.append("   Teoremleri ezberlemek yerine ispat mantığını anlamaya çalışın.")
            elif "Problem" in konu:
                tavsiyeler.append("🔢 Problem sorularında önce verilenleri ve istenenleri netleştirin.")
                tavsiyeler.append("   Denklem kurarken dikkatli olun, işlem hatalarına dikkat edin.")
        
        elif ders == "Fen Bilimleri" or ders == "Fizik":
            if "Basınç" in konu:
                tavsiyeler.append("🌊 Basınç konusunda derinlik, yoğunluk ve yüzey alanı ilişkisine dikkat edin.")
                tavsiyeler.append("   Sıvı basıncında derinlik kavramı kritiktir - P = h.d.g formülünü iyi öğrenin.")
            elif "Kuvvet" in konu or "Hareket" in konu:
                tavsiyeler.append("⚙️  Kuvvet ve hareket sorularında serbest cisim diyagramı çizmek faydalıdır.")
                tavsiyeler.append("   Newton yasalarını uygularken kuvvetleri doğru yönde işaretleyin.")
            elif "Elektrik" in konu:
                tavsiyeler.append("⚡ Elektrik konusunda devre analizi yaparken Ohm yasasını doğru uygulayın.")
                tavsiyeler.append("   Seri ve paralel bağlantı farklarını iyi bilin.")
        
        elif ders == "Türkçe":
            if "Paragraf" in konu:
                tavsiyeler.append("📖 Paragraf sorularında önce soruyu okuyun, sonra paragrafı okuyun.")
                tavsiyeler.append("   Ana düşünce, yardımcı düşünce ve paragrafın yapısına dikkat edin.")
            elif "Dil Bilgisi" in konu:
                tavsiyeler.append("📝 Dil bilgisi sorularında kuralları bilmek kadar uygulama yapmak da önemlidir.")
                tavsiyeler.append("   Özellikle fiilimsi ve cümlenin öğeleri konularında bol pratik yapın.")
        
        elif ders == "Kimya":
            if "Tepkime" in konu:
                tavsiyeler.append("🧪 Kimyasal tepkimelerde denkleştirme ve mol hesaplamalarına dikkat edin.")
                tavsiyeler.append("   Stokiyometri problemlerinde birim dönüşümlerine özen gösterin.")
        
        elif ders == "Biyoloji":
            if "Genetik" in konu:
                tavsiyeler.append("🧬 Genetik sorularında çaprazlama tablolarını doğru çizmek çok önemlidir.")
                tavsiyeler.append("   Mendel yasalarını ve kalıtım tiplerini iyi öğrenin.")
        
        # Alt konular varsa onlara da değin
        if 'alt_konular' in konu_data and konu_data['alt_konular']:
            tavsiyeler.append("")
            tavsiyeler.append("📚 Bu konunun alt başlıkları:")
            for alt_konu in konu_data['alt_konular']:
                tavsiyeler.append(f"   • {alt_konu}")
        
        return "\n".join(tavsiyeler)
    
    def rapor_kaydet(self, rapor, konu_bilgisi):
        """Raporu dosyaya kaydet"""
        # Dosya adı oluştur
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ders = konu_bilgisi.get('ders', 'Bilinmeyen').replace(' ', '_')
        konu = konu_bilgisi.get('konu', 'Bilinmeyen').replace(' ', '_')[:20]
        
        dosya_adi = f"rapor_{timestamp}_{ders}_{konu}.txt"
        dosya_yolu = RAPORLAR_DIR / dosya_adi
        
        with open(dosya_yolu, 'w', encoding='utf-8') as f:
            f.write(rapor)
        
        return dosya_yolu


def main():
    """Ana fonksiyon"""
    print("=" * 60)
    print("EĞİTİM KOÇU ASİSTANI - ANALİZ MOTORU")
    print("=" * 60)
    print(f"İzlenen klasör: {SORU_RESIMLERI_DIR}")
    print(f"Rapor klasörü: {RAPORLAR_DIR}")
    print("")
    
    # Klasörleri oluştur
    SORU_RESIMLERI_DIR.mkdir(exist_ok=True)
    RAPORLAR_DIR.mkdir(exist_ok=True)
    
    # Watchdog observer başlat
    event_handler = SoruAnalizHandler()
    observer = Observer()
    observer.schedule(event_handler, str(SORU_RESIMLERI_DIR), recursive=False)
    observer.start()
    
    print("✓ Sistem aktif! Yeni görselleri bekliyorum...")
    print("  (Çıkmak için Ctrl+C)")
    print("")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n✓ Sistem durduruldu.")
    
    observer.join()


if __name__ == "__main__":
    main()

