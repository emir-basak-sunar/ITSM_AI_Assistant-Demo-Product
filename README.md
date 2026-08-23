# ITSM AI Asistanı & Yönetici Portalı

Toplantı gereksinimlerine göre sıfırdan modernize edilmiş, 4 kademeli kurumsal ITSM sınıflandırması, ITIL çözüm önerisi (RAG), dinamik veri tamamlama (Slot Filling), ve otomatik günlük raporlama JOB motorunu içeren yapay zeka destekli ilk kademe destek asistanı.

---

## 🎯 Projenin 5 Temel Fonksiyonu

1. **Talebi Anlama & Netleştirme:**
   - Kullanıcının doğal dilde yazdığı talepleri anlar.
   - Belirsiz/muğlak durumlarda (*"Bir sorunum var"*, *"Sistem çalışmıyor"*) akıllı takip sorularıyla talebi netleştirir.

2. **AI ile Çözüm Üretme & Yorumlama (Self-Service / RAG):**
   - 27 kurumsal süreç için ITIL standartlarında hazırlanmış geçmiş çözüm kayıtlarından faydalanır.
   - Kullanıcıya adım adım uygulanabilir çözüm önerileri sunar. Çözüm işe yararsa bileti kapatır (Self-Service Deflection).

3. **Veri Tamamlama (Dynamic Slot Filling):**
   - Bilet açılışı öncesinde ilgili sürece özel zorunlu parametreleri (Varlık, Lokasyon, Etki, Hata Kodu, Fatura No, Sicil No vb.) kullanıcıdan toplayarak eksiksiz veriyle bilet oluşturur.

4. **4 Kademeli Hiyerarşik Sınıflandırma:**
   - **Talep Türü** (*Arıza / Hizmet Talebi / Bilgi Talebi*)
   - **Birim** (*Bilgi Teknolojileri / İdari İşler / İnsan Kaynakları / Finans*)
   - **Modül** (*Donanım, Ağ, Yazılım, Güvenlik, Sunucu, Ofis Ekipmanı, Tesis, Ulaşım, Bordro, İzin, Masraf*)
   - **Süreç / Talep Tipi** (*27 Farklı Süreç*)
   - Öncelik / Aciliyet Seviyesi (*Kritik / Yüksek / Orta / Düşük*)

5. **Raporlama & Günlük JOB Süreçleri:**
   - Doğal dille verilen rapor komutlarını kuyruğa alır.
   - Günlük arka plan JOB'ı (`python src/daily_jobs.py` veya UI üzerinden tek tıkla) ile birim bazlı analitik özet raporlar üretip ilgili birimlere iletir.

---

## 🚀 Hızlı Başlangıç

### 1. Ortam ve Bağımlılıklar
```powershell
python -m venv .asude
.\.asude\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 2. Modeli Eğitme ve Test Etme
```powershell
# 27 sınıflı NLU modelini eğitir (%94.7+ doğruluk)
python src\train_itsm_nlu.py

# 13 senaryolu uçtan uca diyalog testlerini çalıştırır
python src\eval_dialogues.py
```

### 3. Uygulamayı Başlatma
```powershell
streamlit run src\app.py
```

---

## 💻 Canlı Demo Senaryoları

1. **Çözüm Önerme (Donanım):** `"Laptopum açılmıyor, ekran siyah."` $\rightarrow$ AI çözüm adımları sunar $\rightarrow$ `"İşe yaradı teşekkürler"` ile self-service kapanır.
2. **Dinamik Veri Tamamlama:** `"VPN bağlanamıyorum, talep aç"` $\rightarrow$ Eksik alanlar sorulur $\rightarrow$ Bilet oluşturulur.
3. **Muğlak Talep Netleştirme:** `"Bir sorunum var yardımcı olur musun"` $\rightarrow$ AI takip sorusu sorarak netleştirir.
4. **Günlük Raporlama:** `"Açık taleplerin raporunu hazırla, günlük özet istiyorum"` $\rightarrow$ Kuyruğa alınır $\rightarrow$ `python src/daily_jobs.py` ile çalıştırılır.
