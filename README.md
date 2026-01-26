# YouTube & Ses Dosyası Özetleyici (Video Transcript & Summarizer)

Bu proje, YouTube videolarından ve yüklenen ses dosyalarından transkript çıkaran, Google Gemini API kullanarak özetleyen ve tüm verileri yerel bir PocketBase veritabanında saklayan gelişmiş bir Flask web uygulamasıdır. Ayrıca medya formatı dönüştürme araçları da sunar.

## Özellikler

*   **YouTube Desteği:** Video linki (standart, short veya embed) üzerinden transkript çekme (Türkçe, İngilizce veya Otomatik).
*   **Yerel Ses Dosyası Desteği:** Bilgisayarınızdan ses dosyası yükleyerek **yerel Whisper modelleri** ile transkript oluşturma.
    *   Seçilebilir Whisper model boyutları (tiny, base, small, medium, large).
*   **Yapay Zeka Özeti:** Google Gemini (Pro/Flash) modelleri ile içeriklerin otomatik özetini çıkarma.
*   **Medya Dönüştürücü:** Ses ve video dosyalarını farklı formatlara (örn. mp3) dönüştürme aracı.
*   **Veritabanı Kaydı:** Tüm aramalar ve çeviriler PocketBase veritabanında saklanır. Aynı video tekrar sorgulandığında veriler veritabanından getirilir (Önbellekleme).
*   **Dışa Aktarma:** Transkriptleri ve özetleri `.txt` veya `.md` (Markdown) formatında indirme imkanı.

## Gereksinimler

*   **Python 3.8+**
*   **FFmpeg:** Ses işleme ve format dönüştürme işlemleri için sisteminizde kurulu olmalıdır.
    *   *Ubuntu/Debian:* `sudo apt install ffmpeg`
    *   *macOS:* `brew install ffmpeg`
    *   *Windows:* [FFmpeg indir](https://ffmpeg.org/download.html) ve PATH'e ekle.
*   **PocketBase:** Veritabanı olarak kullanılır (Otomatik kurulum scripti mevcuttur).
*   **Google Gemini API Anahtarı:** Özetleme özelliği için gereklidir.

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

    Proje içerisinde gelen kurulum scriptini kullanarak PocketBase'i hızlıca kurabilir ve yapılandırabilirsiniz. Bu script PocketBase'i indirir (v0.36.1+), gerekli şemaları oluşturur ve yönetici hesabını tanımlar.

    ```bash
    chmod +x setup_pocketbase.sh
    ./setup_pocketbase.sh
    ```

    **Varsayılan Yönetici Hesabı:**
    *   **Email:** `admin@local.host`
    *   **Şifre:** `password123456`

5.  **PocketBase'i Başlatın:**
    ```bash
    ./pocketbase serve
    ```
    PocketBase arka planda `http://127.0.0.1:8090` adresinde çalışacaktır.

## Kullanım

Uygulamayı çalıştırmak için PocketBase'in çalıştığından emin olduktan sonra yeni bir terminalde şu komutu girin:

```bash
python app.py
```

Tarayıcınızda **`http://localhost:5000`** adresine gidin.

### 1. YouTube Transkripti & Özeti
*   YouTube URL'sini ilgili kutuya yapıştırın.
*   "Transkript Getir" butonuna basın.
*   "Özet Oluştur" seçeneği işaretliyse, transkript çekildikten sonra Gemini ile özet oluşturulur.

### 2. Ses Dosyası Yükleme (Whisper)
*   "Dosya Yükle" sekmesine geçin veya dosya yükleme alanını kullanın.
*   Bir ses dosyası seçin.
*   Kullanılacak **Whisper Model Boyutunu** seçin (Model boyutu büyüdükçe doğruluk artar ancak işlem süresi uzar).
    *   *Not:* İlk kullanımda seçilen model internetten indirilir, sonraki kullanımlarda önbellekten çalışır.
*   İşlem tamamlandığında metin ve (varsa) özet ekranda görünür.

### 3. Medya Dönüştürücü
*   Dosyalarınızı farklı formatlara dönüştürmek için ilgili menüyü/alanı kullanın.
*   Dönüştürülen dosya otomatik olarak indirilecektir.

## Proje Yapısı

*   `app.py`: Flask web sunucusu ve uygulama mantığı.
*   `local_media_server.py`: Whisper ile yerel transkripsiyon ve FFmpeg ile dönüştürme işlemlerini yapan modül (Aynı zamanda FastMCP sunucusu).
*   `setup_pocketbase.sh`: PocketBase kurulum ve yapılandırma scripti.
*   `pb_migrations/`: Veritabanı şema tanımları (JavaScript).
*   `templates/`: HTML arayüz dosyaları.
