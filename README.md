# 🏢 Kurumsal ITSM AI Asistanı & Yönetici Kokpiti

Yapay zeka destekli ilk kademe kurumsal destek (L1 Support) asistanı; **4 kademeli ITSM taksonomisi**, **Gemini 3.5 Flash çözüm sentezi**, **dinamik veri tamamlama (Slot Filling)**, **otomatik günlük analitik JOB motoru** ve **lüks cam arayüzü (Glassmorphism)** ile modernize edilmiştir.

---

## 🎯 Projenin 5 Temel Fonksiyonu

1. **Talebi Anlama & Netleştirme (NLU & Intent):**
   - Kullanıcının doğal dilde yazdığı talepleri anlar ve sınıflandırır.
   - Muğlak/belirsiz durumlarda (*"Bir sorunum var"*, *"Sistem çalışmıyor"*) akıllı takip sorularıyla talebi netleştirir.

2. **AI ile Çözüm Üretme & Yorumlama (Self-Service / RAG):**
   - 27 kurumsal süreç için geçmiş ITIL çözüm kayıtları ve **Google Gemini 3.5 Flash** modeliyle 3 adımlı, uygulanabilir kurumsal çözümler üretir.
   - Kullanıcı sorunun çözüldüğünü belirtirse çağrıyı bilet açmadan kapatır (*Self-Service Deflection*).

3. **Dinamik Veri Tamamlama (Dynamic Slot Filling):**
   - Bilet açılışı öncesinde ilgili sürece özel zorunlu parametreleri (*Varlık, Lokasyon, Etki, Hata Kodu, Fatura No, İzin Tarihleri vb.*) kullanıcıdan diyalog içinde toplayarak eksiksiz bilet oluşturur.

4. **4 Kademeli Hiyerarşik Sınıflandırma (1.500 Örnekli Dengeli Veri Seti):**
   - **1. Kademe - Talep Türü:** *Arıza (Incident) / Hizmet Talebi (Request) / Bilgi Talebi (Inquiry)*
   - **2. Kademe - Birim:** *Bilgi Teknolojileri / İdari İşler / İnsan Kaynakları / Finans*
   - **3. Kademe - Modül:** *Donanım, Ağ & Altyapı, Yazılım, Güvenlik, Ofis Ekipmanı, Tesis, Ulaşım, Bordro & Özlük, İzin, Masraf & Harcama, Fatura & Ödeme*
   - **4. Kademe - Süreç / Talep Tipi:** *27 Farklı Standart Süreç*
   - **Öncelik Seviyesi:** *Kritik / Yüksek / Orta / Düşük*

5. **Raporlama & Günlük JOB Süreçleri:**
   - Doğal dille verilen raporlama komutlarını kuyruğa alır.
   - Günlük arka plan JOB'ı (`python src/daily_jobs.py` veya Yönetici Kokpiti UI'ından tek tıkla) çalıştırılarak birim bazlı analitik özet raporlar üretilir ve arşivlenir.

---

## 📊 Veri Seti ve Model Başarısı

* **Eğitim Veri Seti:** 1.500 dengeli, gerçekçi Türkçe kurumsal talep kaydı.
  * 💻 **Bilgi Teknolojileri:** 450 örnek (%30.0)
  * 🏢 **İdari İşler:** 375 örnek (%25.0)
  * 👥 **İnsan Kaynakları:** 340 örnek (%22.7)
  * 💳 **Finans:** 335 örnek (%22.3)
* **NLU Sınıflandırıcı Başarısı:** TF-IDF + Lojistik Regresyon ile **%97.62 Test Doğruluğu (Accuracy)**.
* **Otomatik Test Süiti:** `src/eval_dialogues.py` içindeki 13 kurumsal diyalog testinin tamamı **%100 (PASSED)**.

---

## 🚀 Hızlı Başlangıç

### 1. Repoyu Klonlama ve Bağımlılıklar
```powershell
# Repoyu klonlayın
git clone https://github.com/asudekaqlan/ITSM_AI_Assistant.git
cd ITSM_AI_Assistant

# Sanal ortam oluşturup aktifleştirin
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Bağımlılıkları yükleyin
python -m pip install -r requirements.txt
```

### 2. Çevre Değişkenleri (Opsiyonel)
```powershell
# .env şablonunu kopyalayıp API anahtarınızı (Gemini / Groq) ekleyin
copy .env.example .env
```
> *Not: API anahtarı eklenmediğinde sistem otomatik olarak akıllı kural tabanlı hibrit RAG modunda çalışır.*

### 3. Modeli Eğitme ve Test Etme
```powershell
# 1.500 verili NLU modelini eğitir (%97.62 test doğruluğu)
python src\train_itsm_nlu.py

# 13 senaryolu uçtan uca diyalog testlerini çalıştırır
python src\eval_dialogues.py
```

### 4. Uygulamayı Başlatma
```powershell
streamlit run src\app.py
```

---

## 💻 Canlı Demo Senaryoları (Toplantı Maddeleri)

1. **💡 1. Çözüm Önerme (Donanım):** `"Laptopum açılmıyor, ekran siyah."` $\rightarrow$ Gemini AI çözüm adımları sunar.
2. **🎫 2. Dinamik Veri Tamamlama:** `"VPN bağlanamıyorum, talep aç"` $\rightarrow$ Eksik alanlar sorulur $\rightarrow$ Bilet oluşturulur.
3. **❓ 3. Muğlak Talep Netleştirme:** `"Bir sorunum var yardımcı olur musun"` $\rightarrow$ AI takip sorusu sorarak netleştirir.
4. **✅ 4. Self-Service Kapatma:** `"Çözüm işe yaradı, teşekkürler"` $\rightarrow$ Bilet açılmadan self-service çözüldü olarak kapatılır.
5. **📊 5. Günlük Raporlama:** `"Açık taleplerin raporunu hazırla, günlük özet istiyorum"` $\rightarrow$ Kuyruğa alınır $\rightarrow$ `python src/daily_jobs.py` ile çalıştırılır.
