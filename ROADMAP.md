# 🗺️ ITSM AI Asistanı — Kurumsal Gelecek Geliştirme Yol Haritası (Roadmap)

Bu doküman, 1 haftalık MVP prototip sprinti sonrasında sistemin 10.000+ kullanıcılı canlı kurumsal ortamlara entegrasyonu ve ölçeklenmesi için planlanan **Faz 2 ve Faz 3** mimari geliştirme maddelerini içermektedir.

---

## 📌 Tamamlanan Geliştirmeler (MVP Fazı):
- [x] **1. Talebi Anlama & Netleştirme:** 27 Süreç, 4 birimli Türkçe NLU ve akıllı netleştirme mekanizması.
- [x] **2. AI Destekli Çözüm Önerisi (RAG):** Dinamik yapay zeka yorumlamalı, ITIL standartlarında rehberlik.
- [x] **3. Dinamik Veri Tamamlama (Slot Filling):** Eksik zorunlu alanları diyalogla tamamlama.
- [x] **4. 4 Kademeli Kurumsal Taksonomi:** `Talep Türü → Birim → Modül → Süreç` yönlendirmesi.
- [x] **5. Otomatik Günlük Raporlama JOB:** Doğal dil komutlarıyla zamanlanmış analitik motoru.
- [x] **6. Çözüm Başarı Puanlama & Öğrenme (Feedback Loop):** Canlı başarı oranı takibi ve kullanıcı geri bildirimi.
- [x] **7. Ethereal Botanical Glassmorphism Arayüz:** Modern, nefes alan yönetici ve sohbet portali.

---

## 🚀 Planlanan Gelecek Geliştirmeler (Faz 2 & Faz 3)

---

### 1. 🔑 Active Directory & SSO Entegrasyonu (Otomatik Çalışan Profili)
* **Amaç:** Kullanıcı sisteme Windows / Google Workspace SSO ile girdiğinde, kimlik ve cihaz bilgilerinin otomatik çekilmesi.
* **Sağlayacağı Fayda:**
  - Kullanıcıya *"Adınız nedir?", "Hangi kattasınız?", "Cihaz seri numaranız nedir?"* gibi sorular sorma ihtiyacı ortadan kalkar.
  - Bilet açma süresi 30 saniyeden **3 saniyeye** iner.
* **Teknik Entegrasyon:**
  - Microsoft Entra ID (Azure AD) / LDAP / Okta REST API bağlantısı.
  - `user_profile = {"name": "Ahmet Y.", "unit": "Pazarlama", "location": "Levent Plaza Kat 4", "asset": "ThinkPad X1 Carbon (SN: TP-8842)"}`

---

### 2. 📑 Yönetici Raporlarının Otomatik PDF/Excel Dağıtımı & E-Posta Servisi
* **Amaç:** Günlük JOB sürecinin ürettiği özetlerin ilgili birim yöneticilerine otomatik postalanması.
* **Sağlayacağı Fayda:**
  - Yöneticilerin portala girmesine gerek kalmadan her sabah saat 08:30'da departman karnesi masalarında olur.
* **Teknik Entegrasyon:**
  - Python `ReportLab` / `WeasyPrint` ile PDF rapor bülteni üretimi.
  - Kurumsal SMTP / SendGrid / Exchange Web Services entegrasyonu.

---

### 3. 💬 Çoklu Kanal (Omnichannel) Desteği: MS Teams & Slack Bot
* **Amaç:** Asistanın sadece web arayüzünden değil, çalışanların günlük iletişim araçları içinden kullanılması.
* **Sağlayacağı Fayda:**
  - Çalışanlar ayrı bir link açmadan Teams sohbetinden *"VPN'e bağlanamıyorum"* yazarak destek alabilir.
* **Teknik Entegrasyon:**
  - Microsoft Bot Framework (`botbuilder-core`) & Azure Bot Service.
  - Slack Bolt API entegrasyonu.

---

### 4. 🔄 Canlı Kurumsal ITSM Entegrasyonları (ServiceNow & Jira API)
* **Amaç:** Dosya tabanlı bilet deposunun gerçek kurumsal ITSM sistemlerine bağlanması.
* **Sağlayacağı Fayda:**
  - Asistan bilet açtığında gerçek ServiceNow `INC0012345` veya Jira `IT-4492` kaydı oluşur ve teknisyenin ekranına düşer.
* **Teknik Entegrasyon:**
  - ServiceNow REST Table API (`/api/now/table/incident`).
  - Jira Service Management REST API (`/rest/servicedeskapi/request`).

---

### 5. 🧠 Vektör Veritabanı ile Semantik Arama (Semantic RAG)
* **Amaç:** Çözüm bankası 10.000+ dokümana ulaştığında anlamsal benzerlik yakalama gücünü artırmak.
* **Sağlayacağı Fayda:**
  - Kullanıcı teknik olmayan argolar veya dolaylı ifadeler kullansa bile en doğru çözüme ulaşır.
* **Teknik Entegrasyon:**
  - ChromaDB / Qdrant / Pinecone vektör veritabanı.
  - Türkçe Embedding modelleri (`bge-m3` veya `text-embedding-3-small`).

---

### 6. 📈 Sürekli Öğrenme ve Teknisyen Notu Geri Bildirimi (Active Learning)
* **Amaç:** Biletler uzman teknisyenler tarafından çözüldüğünde girilen "Kapanış Notu"nun otomatik olarak yapay zeka bilgi bankasına aktarılması.
* **Sağlayacağı Fayda:**
  - Sistem zamanla insan müdahalesine ihtiyaç duymadan şirket içi yeni çıkan arızaları da öğrenir.
