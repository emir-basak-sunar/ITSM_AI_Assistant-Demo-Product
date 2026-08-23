# Architecture — Kurumsal ITSM AI Asistanı

Python + Streamlit + 27 Sınıflı Multi-Level ITSM NLU + Google Gemini 3.5 Flash Çözüm Motoru.

## 1. Runtime Flow (Çalışma Akışı)

```text
Kullanıcı Talebi (Doğal Dil)
    │
    ├── 1. NLU & Taksonomi Sınıflandırma (taxonomy.classify_request)
    │      ├── Güçlü Anahtar Kelime & Regex Eşleşmesi
    │      └── 27 Sınıflı TF-IDF + Logistic Regression ML Modeli (Fallback)
    │
    ├── 2. Duygu & Niyet Analizi (sentiment.py, intents.py)
    │      └── Aciliyet, yüksek risk & raporlama niyeti tespiti
    │
    ├── 3. Çözüm Öneri Motoru (solutions.py + llm_engine.py)
    │      ├── ITIL Süreç Çözüm Kütüphanesi (RAG KB)
    │      └── Google Gemini 3.5 Flash Dinamik 3 Adımlı Çözüm Sentezi
    │
    ├── 4. Dinamik Slot & Veri Tamamlama (slots.py)
    │      └── Sürece özel zorunlu alanların (Varlık, Lokasyon, Etki, vb.) toplanması
    │
    └── 5. Diyalog Yönetimi & Karar Motoru (orchestrator.py)
           ├── clarify (Akıllı netleştirme sorusu)
           ├── suggest_solution (Adım adım çözüm önerisi & self-service)
           ├── collect_fields (Eksik parametre tamamlama)
           ├── ticket_open (Yapılandırılmış bilet kaydı oluşturma)
           └── report_queued (Günlük özet analitik JOB kuyruğu)
```

## 2. Temel Modüller & Görevleri

| Dosya | Görev |
|---|---|
| `src/taxonomy.py` | 4 Birim, 11 Modül ve 27 Süreç içeren 4 kademeli taksonomi ve alias haritaları |
| `src/itsm_nlu.py` | 27 sınıflı makine öğrenmesi modeli çıkarımı (`models/itsm_*.joblib`) |
| `src/train_itsm_nlu.py` | 1.500 verilik veri setiyle TF-IDF + Lojistik Regresyon eğitimi (%97.62 Accuracy) |
| `src/llm_engine.py` | Google Gemini 3.5 Flash / Lite entegrasyonu ve yedekli model çağrı zinciri |
| `src/solutions.py` | ITIL kurumsal çözüm kütüphanesi ve dinamik çözüm oluşturucu |
| `src/slots.py` | Sürece özel dinamik alan (slot) çıkarma ve doğrulama |
| `src/reports.py` / `src/daily_jobs.py` | Doğal dil raporlama kuyruğu ve günlük arka plan analitik JOB motoru |
| `src/tickets.py` | `data/tickets.jsonl` bilet yaşam döngüsü ve CRUD işlemleri |
| `src/orchestrator.py` | Çok turlu diyalog durum makinesi (State Machine) |
| `src/app.py` | Streamlit glassmorphism tabanlı kullanıcı sohbet ve yönetici kokpiti arayüzü |
| `src/eval_dialogues.py` | 13 uçtan uca kurumsal diyalog test senaryosu |

## 3. 4 Kademeli Kurumsal Taksonomi Yapısı

```text
1. BİLGİ TEKNOLOJİLERİ
   ├── Donanım: Bilgisayar Arıza/Onarım, Monitör/Çevre Birimi Arızası, Yeni Ekipman Kurulumu
   ├── Ağ & Altyapı: İnternet Bağlantı Sorunu, VPN Erişim Sorunu, Wi-Fi Bağlantı Sorunu
   ├── Yazılım: Uygulama Hatası (Outlook, Teams, Excel vb.), Yazılım Lisans/Kurulum Talebi
   ├── Güvenlik & Yetki: Şifre Sıfırlama, Sistem/Klasör Yetki Talebi, Yeni Kullanıcı Hesabı
   └── Sunucu & Sistem: Sunucu/Servis Kesintisi, Veritabanı Erişim Hatası

2. İDARİ İŞLER
   ├── Ofis Ekipmanı: Yazıcı/Fotokopi Arıza Bildirimi, Toner/Kartuş Talebi
   ├── Tesis & Bakım: Elektrik/Aydınlatma Arızası, Klima/Isıtma Arızası
   ├── Güvenlik & Ulaşım: Kayıp Giriş Kartı, Servis Güzergah Talebi
   └── Malzeme & Mobilya: Kırtasiye Malzeme Talebi, Ofis Mobilya Değişimi

3. İNSAN KAYNAKLARI (İK)
   ├── Bordro & Özlük: Özlük/Çalışma Belgesi Talebi (Evlilik, ÖSS, BES, Sigorta vb.)
   └── İzin Yönetimi: Yıllık İzin Talebi/Bakiye Sorgulama, İzin İptal/Değişiklik (Doğum, Babalık, Mazeret vb.)

4. FİNANS & MUHASEBE
   ├── Masraf & Harcama: Masraf/Harcama Formu Onayı, Avans Talebi
   └── Fatura & Ödeme: Fatura Ödeme Takibi
```

## 4. Veri Varlıkları

- `data/itsm_dataset.json` — 1.500 dengeli Türkçe kurumsal kayıt
- `data/itsm_siniflandirma.csv` — CSV formatında etiketlenmiş eğitim veri seti
- `data/solutions.jsonl` — 27 süreç için ITIL çözüm bankası
- `data/schemas.json` — Süreç bazlı dinamik slot gereksinim şemaları
- `data/tickets.jsonl` — Gerçek zamanlı bilet kayıtları
- `data/report_jobs.jsonl` — Raporlama JOB kayıtları
