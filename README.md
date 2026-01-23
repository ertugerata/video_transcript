# Video Transcript & Summarizer

Bu proje, YouTube videolarının transkriptlerini çeken, Google Gemini API kullanarak özetleyen ve PocketBase veritabanında saklayan bir Flask web uygulamasıdır.

## Özellikler

*   YouTube videolarından transkript çekme (zaman damgalı veya düz metin).
*   Google Gemini Pro ile otomatik özet oluşturma.
*   Geçmiş aramaları PocketBase veritabanında saklama.
*   Transkriptleri `.txt` veya `.md` formatında indirme.
*   Önbellekleme sistemi (aynı video tekrar sorgulandığında veritabanından getirilir).

## Gereksinimler

*   Python 3.8+
*   PocketBase (Otomatik kurulum scripti mevcuttur)
*   Google Gemini API Anahtarı
*   `wget` ve `unzip` (Linux/macOS otomatik kurulum scripti için)

## Kurulum

1.  **Depoyu klonlayın:**
    ```bash
    git clone <repo-url>
    cd <repo-folder>
    ```

2.  **Gerekli Python paketlerini yükleyin:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Çevresel değişkenleri ayarlayın:**
    Proje ana dizininde `.env` dosyası oluşturun ve Gemini API anahtarınızı ekleyin:
    ```
    GEMINI_API_KEY=sizin_api_anahtariniz
    ```

4.  **PocketBase Kurulumu:**

    Proje içerisinde gelen kurulum scriptini kullanarak PocketBase'i hızlıca kurabilir ve yapılandırabilirsiniz. Bu script PocketBase'i indirir, veritabanı şemasını oluşturur ve bir yönetici hesabı tanımlar.

    ```bash
    chmod +x setup_pocketbase.sh
    ./setup_pocketbase.sh
    ```

    **Not:** Script varsayılan olarak şu yönetici hesabını oluşturur:
    *   **Email:** `admin@local.host`
    *   **Şifre:** `password123456`

    Eğer kurulumu manuel yapmak isterseniz, PocketBase'i indirip `pb_migrations` klasöründeki migration dosyasını uygulayabilirsiniz.

5.  **PocketBase'i Başlatın:**
    ```bash
    ./pocketbase serve
    ```
    PocketBase `http://127.0.0.1:8090` adresinde çalışacaktır. Admin paneline `http://127.0.0.1:8090/_/` adresinden erişebilirsiniz.

## Kullanım

1.  **Uygulamayı başlatın (Farklı bir terminalde):**
    ```bash
    python app.py
    ```

2.  **Tarayıcıda açın:**
    `http://localhost:5000` adresine gidin.

3.  **Video İşleme:**
    *   Bir YouTube video URL'si yapıştırın.
    *   "Transkript Getir" butonuna tıklayın.
    *   "Özet Oluştur" kutucuğunu işaretleyerek yapay zeka özeti de alabilirsiniz.
    *   Geçmiş aramalarınızı "Geçmiş" bölümünden görüntüleyebilirsiniz.

## Proje Yapısı

*   `app.py`: Ana Flask uygulaması ve backend mantığı.
*   `templates/`: HTML arayüz dosyaları.
*   `requirements.txt`: Gerekli Python kütüphaneleri.
*   `setup_pocketbase.sh`: PocketBase otomatik kurulum ve yapılandırma scripti.
*   `pb_migrations/`: Veritabanı şema değişiklikleri (Migrations).
*   `pocketbase_schema.json`: Veritabanı şema örneği (Referans için).
