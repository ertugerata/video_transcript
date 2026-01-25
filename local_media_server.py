import os
import subprocess
import whisper
from fastmcp import FastMCP

# Sunucuyu başlatıyoruz
mcp = FastMCP("LocalMediaServer")

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
        result = model.transcribe(file_path)
        return result["text"]
    except Exception as e:
        return f"Transkripsiyon hatası: {str(e)}"

@mcp.tool()
def convert_media_format(input_path: str, output_format: str = "mp3") -> str:
    """
    FFmpeg kullanarak bir medya dosyasını başka bir formata dönüştürür.
    Örn: Videodan ses ayıklamak için input.mp4 -> mp3 yapabilirsiniz.

    Args:
        input_path: Kaynak dosyanın tam yolu.
        output_format: İstenen uzantı (örn: 'mp3', 'wav', 'mkv').
    """
    if not os.path.exists(input_path):
        return f"Hata: Dosya bulunamadı -> {input_path}"

    # Çıktı dosya adını oluştur
    base_name = os.path.splitext(input_path)[0]
    output_path = f"{base_name}.{output_format}"

    try:
        # FFmpeg komutunu çalıştır
        # -y: Dosya varsa üzerine yazar
        # -vn: Video verisini siler (sadece ses dönüşümü yapılıyorsa boyutu düşürür)
        command = [
            "ffmpeg", "-y",
            "-i", input_path,
            output_path
        ]

        # Eğer sadece ses formatına dönüştürüyorsak -vn ekleyelim
        if output_format in ["mp3", "wav", "m4a", "ogg"]:
             command.insert(2, "-vn")

        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return f"Başarılı! Dosya oluşturuldu: {output_path}"

    except subprocess.CalledProcessError as e:
        return f"FFmpeg Hatası: {e.stderr.decode() if e.stderr else str(e)}"

if __name__ == "__main__":
    # Sunucuyu çalıştır
    mcp.run()
