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
*   PocketBase
*   Google Gemini API Anahtarı

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
    *   PocketBase'i indirin ve çalıştırın (`./pocketbase serve` veya `pocketbase.exe serve`). Varsayılan olarak `http://127.0.0.1:8090` adresinde çalışacaktır.
    *   Admin paneline gidin (`http://127.0.0.1:8090/_/`).
    *   `transcripts` adında bir koleksiyon ("Base" type) oluşturun ve aşağıdaki alanları ekleyin (veya `pocketbase_schema.json` dosyasını referans alın):
        *   `video_id` (Text)
        *   `url` (URL)
        *   `full_transcript` (Text)
        *   `simple_transcript` (Text)
        *   `language` (Text)
        *   `summary` (Text)
    *   API Kurallarını (API Rules) uygulamanın erişebileceği şekilde ayarladığınızdan emin olun (Geliştirme için kuralları boş bırakarak herkese açık yapabilirsiniz).

## Kullanım

1.  **Uygulamayı başlatın:**
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
*   `pocketbase_schema.json`: Veritabanı şema örneği.
