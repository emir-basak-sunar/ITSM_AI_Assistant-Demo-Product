# Product Requirements Document (PRD) — ITSM AI Asistanı

## 1. Ürün Özeti
**ITSM AI Asistanı**, kurum içi servis yönetiminde kullanıcıların doğal dilde ilettiği talepleri karşılayan, 4 kademeli taksonomi ile sınıflandıran, geçmiş çözüm kayıtlarından (KB) self-service çözümler öneren, eksik alanları tamamlayarak bilet açan ve zamanlanmış analitik raporlama JOB süreçlerini yürüten ilk kademe yapay zeka destekli bir asistandır.

## 2. Toplantı Gereksinimleri & Kapsam

| # | Modül / Gereksinim | Açıklama |
|---|---|---|
| 1 | **Talebi Anlama & Netleştirme** | Kullanıcının doğal dil talebini anlama; muğlak ifadelerde bağlama uygun akıllı takip sorularıyla netleştirme. |
| 2 | **AI ile Çözüm Üretme & Yorumlama** | Geçmiş ITSM çözüm kayıtlarından (Knowledge Base) faydalanarak adım adım self-service çözümler sunma. |
| 3 | **Veri Tamamlama (Dynamic Slots)** | Bilet açılışı öncesinde kategoriye özel zorunlu alanları (Varlık, Lokasyon, Etki, Hata Kodu, Fatura No vb.) kullanıcıdan toplama. |
| 4 | **4 Kademeli Talep Sınıflandırma** | *Talep Türü → Birim → Modül → Süreç/Talep Tipi* ve Öncelik/SLA belirleme (BT, İdari İşler, İK, Finans). |
| 5 | **Raporlama & Günlük JOB Süreçleri** | Chatbot üzerinden verilen rapor komutlarını kuyruğa alma, günlük JOB ile çalıştırma ve özetleri iletme. |

## 3. Başarı Kriterleri
- 27 sınıf genelinde `%94+` NLU sınıflandırma doğruluğu.
- Uçtan uca tüm diyalog senaryolarının (`eval_dialogues.py`) hatasız geçmesi.
- Anlaşılır, estetik ve işlevsel Streamlit arayüzü & yönetici kokpiti.
