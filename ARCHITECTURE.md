# Architecture — ITSM Asistanı

Python + Streamlit + 27-Class Multi-Level ITSM NLU & Knowledge Engine.

## 1. Runtime Flow

```text
User message
    → taxonomy.classify_request          (Keywords first, 27-Class TF-IDF + LogReg fallback)
    → sentiment / intents / report command detection
    → solutions.find_solutions           (RAG past ITSM solution records & KB)
    → slots (Dynamic field extraction by category)
    → orchestrator.handle_turn
         ├─ clarify (Intelligent contextual clarification question)
         ├─ suggest_solution (ITIL step-by-step resolution recommendation)
         ├─ collect_fields (Dynamic category-specific slot filling)
         ├─ ticket_open (Structured ticket creation)
         └─ report_queued (Scheduled analytics reporting command)
    → app.py: requester chat interface & admin management queue
```

Daily JOB: `python src/daily_jobs.py` runs queued report commands and stores comprehensive multi-unit executive summaries.

## 2. Core Modules

| File | Role |
|---|---|
| `src/taxonomy.py` | 4-level ITSM classification across 4 Units, 12 Modules, and 27 Processes |
| `src/itsm_nlu.py` | TF-IDF + Logistic Regression 27-class model inference (`models/itsm_*.joblib`) |
| `src/train_itsm_nlu.py` | Retrain the 27-class ITSM classifier on 1000 dataset rows (94.7%+ accuracy) |
| `src/solutions.py` | Retrieve past ITIL solution records and self-service troubleshooting guides |
| `src/slots.py` | Dynamic category-driven ticket field extraction and slot filling |
| `src/reports.py` / `src/daily_jobs.py` | Natural language report commands + Background JOB execution |
| `src/sentiment.py` / `src/intents.py` / `src/rules.py` | Tone analysis, user intents, high-risk detection |
| `src/summaries.py` | Executive supervisor brief generation |
| `src/llm_analyze.py` | Optional LLM integration for supervisor notes & customer reply refinement |
| `src/tickets.py` | `data/tickets.jsonl` runtime tickets store |
| `src/orchestrator.py` | Multi-turn dialog state machine & decision orchestration |
| `src/app.py` | Modern Streamlit web application & management dashboard |

## 3. 4-Level Taxonomy Structure

```text
1. BİLGİ TEKNOLOJİLERİ (IT Destek)
   ├── Donanım: Bilgisayar Arıza/Onarım, Monitör/Çevre Birimi Arızası, Yeni Ekipman Kurulumu
   ├── Ağ/Network: İnternet Bağlantı Sorunu, VPN Erişim Sorunu, Wi-Fi Bağlantı Sorunu
   ├── Yazılım: Uygulama Hatası, Yazılım Lisans/Kurulum Talebi
   ├── Güvenlik ve Erişim: Şifre Sıfırlama, Sistem/Klasör Yetki Talebi, Yeni Kullanıcı Hesabı
   └── Sunucu/Sistem: Sunucu/Servis Kesintisi, Veritabanı Erişim Hatası

2. İDARİ İŞLER & TESİS
   ├── Ofis Ekipmanı: Yazıcı/Fotokopi Arıza Bildirimi, Toner/Kartuş Talebi
   ├── Bina/Tesis Bakım: Elektrik/Aydınlatma Arızası, Klima/Isıtma Arızası
   ├── Güvenlik & Ulaşım: Kayıp Giriş Kartı, Ziyaretçi Giriş Talebi, Servis Güzergah Talebi
   └── Satınalma/Malzeme: Kırtasiye Malzeme Talebi, Ofis Mobilya Değişimi

3. İNSAN KAYNAKLARI (İK)
   ├── Bordro & Özlük: Bordro/Maaş Bilgisi Talebi, Özlük/Çalışma Belgesi Talebi
   └── İzin Yönetimi: Yıllık İzin Talebi/Bakiye Sorgulama, İzin İptal/Değişiklik

4. FİNANS & MUHASEBE
   └── Masraf & Ödeme: Masraf/Harcama Formu Onayı, Avans Talebi, Fatura Ödeme Takibi
```

## 4. Data Assets

- `data/itsm_dataset.json` — 1000 rich Turkish records with 4-level taxonomy, ITIL solution steps, dynamic slots, and clarification questions
- `data/solutions.jsonl` — 27 process knowledge base items & self-service guides
- `data/schemas.json` — Dynamic slot requirements per process
- `data/itsm_siniflandirma.csv` — Labeled classification dataset
- `data/tickets.jsonl` — Runtime ticket records
- `data/report_jobs.jsonl` — Queued and executed analytics report jobs
