# Product Requirements Document (PRD) — Kurumsal ITSM AI Asistanı

## 1. Ürün Özeti
**Kurumsal ITSM AI Asistanı**, kurum içi servis yönetiminde çalışanların doğal dilde ilettiği talepleri karşılayan, 4 kademeli taksonomi ile sınıflandıran, Google Gemini 3.5 Flash ve geçmiş ITIL çözüm kayıtlarıyla anında self-service çözümler öneren, eksik alanları tamamlayarak bilet açan ve zamanlanmış analitik raporlama JOB süreçlerini yürüten ilk kademe (L1) yapay zeka asistanıdır.

## 2. Toplantı Gereksinimleri & Tamamlanma Durumu

| # | Modül / Gereksinim | Açıklama | Durum |
|---|---|---|:---:|
| 1 | **Talebi Anlama & Netleştirme** | Kullanıcının doğal dil talebini anlama; muğlak ifadelerde bağlama uygun akıllı takip sorularıyla netleştirme. | ✅ TAMAMLANDI |
| 2 | **AI ile Çözüm Üretme & Yorumlama** | Gemini 3.5 Flash ve geçmiş ITSM çözüm kayıtlarıyla 3 adımlı uygulanabilir çözümler sunma. | ✅ TAMAMLANDI |
| 3 | **Veri Tamamlama (Dynamic Slots)** | Bilet açılışı öncesinde kategoriye özel zorunlu alanları (Varlık, Lokasyon, Etki, Hata Kodu, vb.) diyalog içinde tamamlama. | ✅ TAMAMLANDI |
| 4 | **4 Kademeli Talep Sınıflandırma** | *Talep Türü → Birim → Modül → Süreç/Talep Tipi* ve Öncelik belirleme (1.500 dengeli örnek, BT, İdari İşler, İK, Finans). | ✅ TAMAMLANDI |
| 5 | **Raporlama & Günlük JOB Süreçleri** | Chatbot üzerinden verilen rapor komutlarını kuyruğa alma, günlük JOB ile çalıştırma ve analitik özetleri iletme. | ✅ TAMAMLANDI |

## 3. Başarı Kriterleri ve Sonuçlar
- **NLU Doğruluğu:** 27 sınıf genelinde **%97.62** Test Doğruluğu (Hedef %94+ idi).
- **Diyalog Testleri:** `eval_dialogues.py` 13 kurumsal test senaryosunun tamamı **%100 (PASSED)**.
- **Tasarım:** Streamlit üzerinde lüks botanik cam (Glassmorphism) teması, anında mesajlaşma ve animasyonlu düşünme göstergesi.
