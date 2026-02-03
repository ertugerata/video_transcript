# MCP Medya Sunucusu (Media Processing Server)

Bu modül, ana uygulamanın (`app.py`) ağır medya işlemlerini gerçekleştirdiği arka uç servisidir. **Model Context Protocol (MCP)** standardını kullanarak, istemcilere medya işleme yetenekleri sunar.

## 🚀 Özellikler

Sunucu aşağıdaki araçları (Tools) sağlar:

1.  **`transcribe_audio_base64`**: Base64 formatında gelen ses dosyasını alır, yerel **Whisper** modelini kullanarak metne dönüştürür.
2.  **`process_youtube_workflow`**: Bir YouTube URL'si alır, videoyu indirir (`yt-dlp`), sesini ayıklar ve metne dönüştürür.
3.  **`convert_media_base64`**: Medya dosyalarını formatlar arası (mp3, wav vb.) dönüştürür.

## 🛠️ Teknoloji Yığını

*   **FastMCP:** MCP protokolü uygulaması.
*   **OpenAI Whisper:** Yerel yapay zeka tabanlı ses tanıma.
*   **FFmpeg:** Güçlü ses ve video işleme aracı.
*   **Ollama:** (Opsiyonel/Docker) Yerel LLM desteği için.

## 🐳 Kurulum ve Çalıştırma (Docker ile Önerilen)

En temiz kurulum yöntemi Docker kullanmaktır. Bu yöntem FFmpeg, Whisper modelleri ve Ollama servisini otomatik olarak ayağa kaldırır.

1.  **Docker Konteynerlerini Başlatın:**
    Bu klasörün içindeyken (`mcp-media-server/`):

    ```bash
    docker-compose up --build
    ```

    Bu komut iki servis başlatır:
    *   `app`: Medya sunucusu (Python/FastMCP).
    *   `llm`: Ollama servisi (Yerel LLM işlemleri için).

2.  **Kullanım:**
    Sunucu çalışmaya başladığında, istemci uygulamalar (örneğin ana dizindeki `app.py`) bu sunucuya bağlanarak işlem yaptırabilir.

## 🐍 Yerel Kurulum (Python ile)

Docker kullanmadan çalıştırmak isterseniz sisteminizde **FFmpeg** kurulu olmalıdır.

1.  **Gereksinimleri Yükleyin:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **FFmpeg Kurulumu:**
    *   **Ubuntu/Debian:** `sudo apt install ffmpeg`
    *   **macOS:** `brew install ffmpeg`
    *   **Windows:** FFmpeg resmi sitesinden indirip PATH'e ekleyin.

3.  **Sunucuyu Başlatın:**
    ```bash
    # src klasörünü PYTHONPATH'e ekleyerek başlatın
    export PYTHONPATH=$PYTHONPATH:$(pwd)/src
    python src/server.py
    ```

## 📂 Dosya Yapısı

*   `src/server.py`: MCP sunucusunun ana giriş noktası. Araçları tanımlar.
*   `src/transcribe.py`: Whisper model yönetimi ve transkripsiyon mantığı.
*   `src/audio.py`: FFmpeg ile ses işleme fonksiyonları.
*   `docker-compose.yml`: Docker servis tanımları.
