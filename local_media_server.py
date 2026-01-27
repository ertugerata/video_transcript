import os
import subprocess
import whisper
from fastmcp import FastMCP
import math
import shutil
import glob
from datetime import datetime
import yt_dlp
from pocketbase import PocketBase
from pocketbase.models import FileUpload

# Sunucuyu başlatıyoruz
mcp = FastMCP("LocalMediaServer")

# PocketBase bağlantısı
pb = PocketBase('http://127.0.0.1:8090')

# Performans için modeli global değişkende tutalım (Lazy loading yapacağız)
model_cache = {}

def get_model(model_size="base"):
    """İstenen Whisper modelini yükler veya önbellekten getirir."""
    if model_size not in model_cache:
        print(f"Model yükleniyor: {model_size} (Bu işlem ilk seferde biraz sürebilir)...")
        model_cache[model_size] = whisper.load_model(model_size)
    return model_cache[model_size]

@mcp.tool()
def transcribe_local(file_path: str, model_size: str = "base") -> str:
    """
    Yerel bir ses dosyasını (mp3, wav, m4a) Whisper kullanarak metne çevirir.

    Args:
        file_path: Ses dosyasının tam dosya yolu.
        model_size: Model boyutu ('tiny', 'base', 'small', 'medium', 'large'). Varsayılan 'base'.
    """
    if not os.path.exists(file_path):
        return f"Hata: Dosya bulunamadı -> {file_path}"

    try:
        model = get_model(model_size)
        result = model.transcribe(file_path, fp16=False)
        return result["text"]
    except Exception as e:
        return f"Transkripsiyon hatası: {str(e)}"

def convert_media_core(input_path: str, output_format: str = "mp3") -> str:
    """
    FFmpeg kullanarak medya dönüşümü yapan çekirdek fonksiyon.
    Başarılı olursa çıktı dosya yolunu döndürür, hata olursa Exception fırlatır.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Dosya bulunamadı: {input_path}")

    # Çıktı dosya adını oluştur
    base_name = os.path.splitext(input_path)[0]
    output_path = f"{base_name}.{output_format}"

    # FFmpeg komutunu oluştur
    command = [
        "ffmpeg", "-y",
        "-i", input_path,
        output_path
    ]

    # Eğer sadece ses formatına dönüştürüyorsak -vn ekleyelim
    if output_format in ["mp3", "wav", "m4a", "ogg"]:
         command.insert(2, "-vn")

    process = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return output_path

@mcp.tool()
def convert_media_format(input_path: str, output_format: str = "mp3") -> str:
    """
    FFmpeg kullanarak bir medya dosyasını başka bir formata dönüştürür.
    Örn: Videodan ses ayıklamak için input.mp4 -> mp3 yapabilirsiniz.

    Args:
        input_path: Kaynak dosyanın tam yolu.
        output_format: İstenen uzantı (örn: 'mp3', 'wav', 'mkv').
    """
    try:
        output_path = convert_media_core(input_path, output_format)
        return f"Başarılı! Dosya oluşturuldu: {output_path}"
    except Exception as e:
        if isinstance(e, subprocess.CalledProcessError):
             return f"FFmpeg Hatası: {e.stderr.decode() if e.stderr else str(e)}"
        return f"Hata: {str(e)}"

def get_media_duration(file_path: str) -> float:
    """FFprobe kullanarak medya süresini (saniye) döndürür."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return float(result.stdout.strip())
    except Exception as e:
        print(f"Süre alma hatası: {e}")
        return 0.0

def download_youtube_audio(url: str, output_dir: str = ".") -> tuple[str, str, str]:
    """
    YouTube videosunu indirir (en iyi ses mp3) ve dosya yolunu, video id'sini ve başlığı döndürür.
    """
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{output_dir}/%(id)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # yt-dlp will save as ID.mp3 because of postprocessor
        video_id = info['id']
        title = info.get('title', 'Unknown')
        final_path = os.path.join(output_dir, f"{video_id}.mp3")
        return final_path, video_id, title

def split_media(file_path: str, chunk_length: int = 180) -> list[str]:
    """
    Dosyayı belirtilen saniye uzunluğunda parçalara ayırır (varsayılan 3 dk).
    Eğer süre 5 dakikadan (300sn) kısaysa bölmez.
    Parçaların dosya yollarını döndürür.
    """
    duration = get_media_duration(file_path)
    if duration <= 300: # 5 dk (300 sn) altındaysa bölme
        return [file_path]

    base_name, ext = os.path.splitext(file_path)
    output_pattern = f"{base_name}_part%03d{ext}"

    # FFmpeg segment komutu - c copy ile hızlı bölme
    # Reset timestamps önemli, yoksa playerlar kafayı yiyebilir
    cmd = [
        "ffmpeg", "-y", "-i", file_path,
        "-f", "segment",
        "-segment_time", str(chunk_length),
        "-c", "copy",
        "-reset_timestamps", "1",
        output_pattern
    ]

    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Oluşan dosyaları bul ve sırala
    chunk_files = sorted(glob.glob(f"{base_name}_part*{ext}"))
    return chunk_files

def save_chunk_to_db(file_path: str, video_id: str, url: str) -> str:
    """Parçayı veritabanına kaydeder (transkriptsiz)."""
    try:
        # FileUpload için dosyayı açıyoruz. create çağrısı bitene kadar açık kalmalı.
        with open(file_path, "rb") as f:
            data = {
                "video_id": video_id,
                "url": url,
                "full_transcript": "",
                "simple_transcript": "",
                "language": "auto",
                "summary": "",
                "created": datetime.now().isoformat(),
                "audio_file": FileUpload((os.path.basename(file_path), f))
            }
            record = pb.collection('transcripts').create(data)
            return record.id
    except Exception as e:
        print(f"DB Kayıt hatası ({file_path}): {e}")
        return None

@mcp.tool()
def process_youtube_workflow(url: str) -> str:
    """
    YouTube linkini alır, indirir, gerekirse böler, veritabanına kaydeder,
    transkript oluşturur ve transkripti de günceller.

    Adımlar:
    1. İndir
    2. Süre kontrolü (> 5dk ise 3'er dk böl)
    3. Her parça için:
       - DB'ye ses dosyasını kaydet
       - Transkript oluştur
       - DB kaydını transkript ile güncelle
    """
    temp_dir = "temp_downloads"
    os.makedirs(temp_dir, exist_ok=True)

    report = []
    file_path = None
    chunks = []

    try:
        # 1. İndir
        report.append(f"İndiriliyor: {url}")
        file_path, original_video_id, title = download_youtube_audio(url, temp_dir)
        report.append(f"İndirildi: {title} ({file_path})")

        # 2. Böl
        chunks = split_media(file_path)
        if len(chunks) > 1:
            report.append(f"Dosya {len(chunks)} parçaya bölündü.")
        else:
            report.append("Bölünmesine gerek kalmadı.")

        # 3. İşle
        for i, chunk_path in enumerate(chunks):
            chunk_name = os.path.basename(chunk_path)
            part_suffix = f"_part{i+1}" if len(chunks) > 1 else ""
            current_video_id = f"{original_video_id}{part_suffix}"

            report.append(f"İşleniyor: {chunk_name}...")

            # DB Kayıt (Önce dosyayı kaydet)
            record_id = save_chunk_to_db(chunk_path, current_video_id, url)

            if not record_id:
                report.append(f"  - DB Kayıt başarısız!")
                continue

            report.append(f"  - Kaydedildi (ID: {record_id})")

            # Transkript
            transcript_text = transcribe_local(chunk_path, model_size="base")

            if transcript_text.startswith("Hata") or transcript_text.startswith("Transkripsiyon hatası"):
                 report.append(f"  - Transkript hatası: {transcript_text}")
                 continue

            # DB Güncelleme
            try:
                pb.collection('transcripts').update(record_id, {
                    "full_transcript": transcript_text,
                    "simple_transcript": transcript_text
                })
                report.append(f"  - Transkript güncellendi.")
            except Exception as e:
                 report.append(f"  - Transkript güncelleme hatası: {e}")

    except Exception as e:
        import traceback
        traceback.print_exc()
        return "\n".join(report) + f"\nGenel Hata: {str(e)}"
    finally:
        # Temizlik
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except: pass

        if chunks and len(chunks) > 1:
            for c in chunks:
                if c and os.path.exists(c):
                    try:
                        os.remove(c)
                    except: pass

        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            try:
                os.rmdir(temp_dir)
            except: pass

    return "\n".join(report)

if __name__ == "__main__":
    # Sunucuyu çalıştır
    mcp.run()
