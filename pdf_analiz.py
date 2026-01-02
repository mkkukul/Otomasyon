"""
PDF Analiz Scripti
Lgs.pdf ve Yks.pdf dosyalarını okuyup müfredat verilerini çıkarır
"""
import PyPDF2
import pdfplumber
import json
import re
from pathlib import Path

def extract_text_from_pdf(pdf_path):
    """PDF'den metin çıkarır"""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        print(f"pdfplumber ile okuma hatası: {e}, PyPDF2 deneniyor...")
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e2:
            print(f"PyPDF2 ile okuma hatası: {e2}")
    return text

def parse_lgs_content(text):
    """LGS PDF içeriğini parse eder"""
    lgs_data = {
        "Türkçe": {},
        "Matematik": {},
        "Fen Bilimleri": {},
        "İnkılap Tarihi": {},
        "Din Kültürü": {},
        "İngilizce": {}
    }
    
    # Basit pattern matching ile konuları bul
    # Bu kısım PDF formatına göre özelleştirilmeli
    lines = text.split('\n')
    current_subject = None
    current_unit = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Ders isimlerini bul
        for subject in lgs_data.keys():
            if subject.lower() in line.lower() and len(line) < 50:
                current_subject = subject
                break
        
        # Ünite ve konu yapısını parse et
        # Bu kısım gerçek PDF formatına göre ayarlanmalı
    
    return lgs_data

def parse_yks_content(text):
    """YKS PDF içeriğini parse eder"""
    yks_data = {
        "TYT": {},
        "AYT": {}
    }
    
    # TYT ve AYT ayrımı yap
    lines = text.split('\n')
    current_exam = None
    
    for line in lines:
        line = line.strip()
        if 'TYT' in line.upper() or 'TEMEL YETERLİLİK' in line.upper():
            current_exam = "TYT"
        elif 'AYT' in line.upper() or 'ALAN YETERLİLİK' in line.upper():
            current_exam = "AYT"
    
    return yks_data

def extract_statistics(text):
    """2018-2024 arası soru dağılım tablolarını çıkarır"""
    # Tablo formatını parse et
    # Örnek: "2024: 2, 2023: 2, 2022: 1..." gibi
    stats = {}
    years = [2018, 2019, 2020, 2021, 2022, 2023, 2024]
    
    # Pattern matching ile yıllık soru sayılarını bul
    for year in years:
        pattern = rf'{year}.*?(\d+)'
        matches = re.findall(pattern, text)
        if matches:
            stats[year] = int(matches[0])
    
    return stats

def analyze_pdfs():
    """Ana analiz fonksiyonu"""
    pdf_dir = Path("PDFler")
    lgs_path = pdf_dir / "Lgs.pdf"
    yks_path = pdf_dir / "Yks.pdf"
    
    if not lgs_path.exists():
        print(f"UYARI: {lgs_path} bulunamadı!")
        return None
    
    if not yks_path.exists():
        print(f"UYARI: {yks_path} bulunamadı!")
        return None
    
    print("PDF'ler okunuyor...")
    lgs_text = extract_text_from_pdf(lgs_path)
    yks_text = extract_text_from_pdf(yks_path)
    
    print("İçerik analiz ediliyor...")
    lgs_data = parse_lgs_content(lgs_text)
    yks_data = parse_yks_content(yks_text)
    
    # İstatistikleri çıkar
    lgs_stats = extract_statistics(lgs_text)
    yks_stats = extract_statistics(yks_text)
    
    return {
        "LGS": lgs_data,
        "YKS": yks_data,
        "statistics": {
            "LGS": lgs_stats,
            "YKS": yks_stats
        }
    }

if __name__ == "__main__":
    result = analyze_pdfs()
    if result:
        with open("mufredat_db.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print("mufredat_db.json oluşturuldu!")
    else:
        print("PDF analizi tamamlanamadı. PDF dosyalarını kontrol edin.")

