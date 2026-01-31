import os
import shutil
import traceback
from fastmcp import FastMCP
from .download import download_youtube_audio
from .audio import split_media
from .transcribe import transcribe_local
from .db import save_chunk_to_db, update_transcript
from .llm import generate_summary

# Sunucuyu başlatıyoruz
mcp = FastMCP("LocalMediaServer")

@mcp.tool()
def transcribe_local_file(file_path: str, model_size: str = "base") -> str:
    """
    Yerel bir ses dosyasını (mp3, wav, m4a) Whisper kullanarak metne çevirir.
    Tool wrapper for the transcribe module.
    """
    return transcribe_local(file_path, model_size)

@mcp.tool()
def convert_media_format(input_path: str, output_format: str = "mp3") -> str:
    """
    FFmpeg kullanarak bir medya dosyasını başka bir formata dönüştürür.
    Bu serviste artık ana akış process_youtube_workflow üzerinden yapılıyor ama
    manuel araç olarak burada bırakıyoruz.
    """
    from .audio import convert_media_core
    try:
        output_path = convert_media_core(input_path, output_format)
        return f"Başarılı! Dosya oluşturuldu: {output_path}"
    except Exception as e:
        return f"Hata: {str(e)}"

@mcp.tool()
def process_youtube_workflow(url: str) -> str:
    """
    YouTube linkini alır, indirir, gerekirse böler, veritabanına kaydeder,
    transkript oluşturur, özetini çıkarır ve günceller.
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

            # Özetleme (Yeni Özellik)
            report.append(f"  - Özet çıkarılıyor (Llama 3.2)...")
            summary_text = generate_summary(transcript_text)
            
            # DB Güncelleme
            success = update_transcript(record_id, transcript_text, summary_text)
            if success:
                report.append(f"  - Transkript ve özet güncellendi.")
            else:
                report.append(f"  - DB güncelleme hatası.")

    except Exception as e:
        traceback.print_exc()
        return "\n".join(report) + f"\nGenel Hata: {str(e)}"
    finally:
        # Temizlik
        if file_path and os.path.exists(file_path):
            try: os.remove(file_path)
            except: pass

        if chunks and len(chunks) > 1:
            for c in chunks:
                if c and os.path.exists(c):
                    try: os.remove(c)
                    except: pass

        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            try: os.rmdir(temp_dir)
            except: pass

    return "\n".join(report)

if __name__ == "__main__":
    mcp.run()
