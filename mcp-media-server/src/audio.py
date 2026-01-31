import os
import subprocess
import glob

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
