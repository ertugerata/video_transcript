# MCP Media Server

Bu modül, ana web uygulamasından (`app.py`) ayrılmış, ağır medya işlemlerini üstlenen sunucu tarafı bileşenidir. **Model Context Protocol (MCP)** kullanarak medya indirme, Whisper ile transkripsiyon ve format dönüştürme gibi işlemleri gerçekleştirir.

## Özellikler

*   **Whisper Entegrasyonu:** `openai-whisper` kullanarak yüksek doğrulukta yerel ses-metin dönüşümü.
*   **YouTube İndirici:** `yt-dlp` kullanarak YouTube videolarından ses ayıklama ve meta veri çekme.
*   **Medya İşleme:** FFmpeg kullanarak ses bölme, format dönüştürme ve süre analizi.
*   **MCP Sunucusu:** Diğer uygulamaların (Client) bağlanıp görev gönderebileceği bir MCP arayüzü sunar (`src/server.py`).

## Gereksinimler

Bu modül ağır işlem yapan kütüphanelere ihtiyaç duyar:

*   **Python 3.8+**
*   **FFmpeg:** (Sistemde kurulu olmalıdır)
*   **Python Kütüphaneleri:**
    *   `fastmcp[cli]`
    *   `openai-whisper`
    *   `torch` (Whisper için)
    *   `yt-dlp`
    *   `supabase`

## Kurulum

Ana uygulamanın (`app.py`) çalıştığı dizinde değil, bu klasör özelinde veya ana dizinden bu gereksinimleri yükleyerek kullanabilirsiniz:

```bash
pip install -r requirements.txt
```

*(Not: Eğer ana proje dizinindeyseniz `pip install -r mcp-media-server/requirements.txt` komutunu kullanın.)*

## Dosya Yapısı

*   `src/server.py`: MCP sunucusunun giriş noktası. `process_youtube_workflow` gibi araçları dışarıya açar.
*   `src/transcribe.py`: Whisper modellerini yükleyen ve transkripsiyon işlemini yapan çekirdek modül. Modeller ilk kullanımda önbelleğe alınır.
*   `src/audio.py`: Ses dosyası işlemlerini (süre bulma, parçalama, format değiştirme) yönetir.
*   `src/db.py`: İşlenen verilerin veritabanına kaydedilmesi için yardımcı fonksiyonlar.

## Kullanım

### Bağımsız MCP Sunucusu Olarak Çalıştırma

Bu sunucuyu Docker veya doğrudan Python ile çalıştırarak, `app.py` gibi istemcilerin uzaktan bağlanmasını sağlayabilirsiniz.

**Docker ile:**
```bash
docker-compose up --build
```

**Manuel:**
```bash
# src klasörü Python yoluna eklenmelidir
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
python src/server.py
```

### Monolitik Kullanım (Eski Yöntem)

Eğer `app.py` uygulamasının bu klasördeki modülleri doğrudan import etmesini istiyorsanız (Yerel İşleme), yukarıdaki kurulum adımını tamamlamanız yeterlidir. `app.py` otomatik olarak bu klasörü yoluna ekler ve modülleri kullanmaya başlar.
