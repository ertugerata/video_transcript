import os
import shutil
import traceback
import base64
import tempfile
import glob
from fastmcp import FastMCP
try:
    from .download import download_youtube_audio
    from .audio import split_media
    from .transcribe import transcribe_local
    from .db import save_chunk_to_db, update_transcript
    from .llm import generate_summary
except ImportError:
    from download import download_youtube_audio
    from audio import split_media
    from transcribe import transcribe_local
    from db import save_chunk_to_db, update_transcript
    from llm import generate_summary

# Sunucuyu başlatıyoruz
mcp = FastMCP("LocalMediaServer")

# Temporary directory for uploaded chunks
UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "mcp_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@mcp.tool()
def upload_chunk(upload_id: str, chunk_index: int, chunk_data: str) -> str:
    """
    Receives a chunk of a file and saves it to a temporary directory associated with the upload_id.
    chunk_data should be base64 encoded.
    """
    try:
        # Sanitize upload_id to prevent path traversal (simple alphanumeric check would be best, but basename is minimal)
        safe_upload_id = os.path.basename(upload_id)
        if not safe_upload_id:
             return "Error: Invalid upload_id"

        # Create a specific directory for this upload session
        file_dir = os.path.join(UPLOAD_DIR, safe_upload_id)
        os.makedirs(file_dir, exist_ok=True)

        chunk_path = os.path.join(file_dir, f"{chunk_index:05d}.part")

        with open(chunk_path, "wb") as f:
            f.write(base64.b64decode(chunk_data))

        return f"Chunk {chunk_index} received for {safe_upload_id}"
    except Exception as e:
        return f"Error receiving chunk: {str(e)}"

def assemble_file(upload_id: str, filename: str) -> str:
    """
    Assembles chunks for the given upload_id and returns the path to the assembled file.
    Uses filename only to determine the extension.
    """
    safe_upload_id = os.path.basename(upload_id)
    file_dir = os.path.join(UPLOAD_DIR, safe_upload_id)

    if not os.path.exists(file_dir):
        raise FileNotFoundError(f"No chunks found for {safe_upload_id}")

    # Get all parts and sort them
    parts = sorted(glob.glob(os.path.join(file_dir, "*.part")))

    if not parts:
        raise FileNotFoundError(f"No parts found in {file_dir}")

    # Reconstruct file extension from filename or default to .tmp
    # Sanitize filename just in case
    safe_filename = os.path.basename(filename)
    _, ext = os.path.splitext(safe_filename)
    if not ext:
        ext = ".tmp"

    # Create a temporary file for the assembled content
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp:
        assembled_path = temp.name

    with open(assembled_path, "wb") as outfile:
        for part in parts:
            with open(part, "rb") as infile:
                shutil.copyfileobj(infile, outfile)

    # Cleanup chunks directory
    shutil.rmtree(file_dir)

    return assembled_path

@mcp.tool()
def transcribe_uploaded_file(upload_id: str, filename: str, model_size: str = "base") -> str:
    """
    Assembles previously uploaded chunks for 'upload_id' and transcribes the result.
    filename is provided to preserve the file extension.
    """
    assembled_path = None
    try:
        assembled_path = assemble_file(upload_id, filename)
        return transcribe_local(assembled_path, model_size)
    except Exception as e:
        return f"Error in transcribe_uploaded_file: {str(e)}"
    finally:
        if assembled_path and os.path.exists(assembled_path):
            os.unlink(assembled_path)

@mcp.tool()
def convert_uploaded_file(upload_id: str, filename: str, output_format: str = "mp3") -> str:
    """
    Assembles previously uploaded chunks for 'upload_id', converts it, and returns the result as base64.
    """
    assembled_path = None
    output_path = None
    try:
        from .audio import convert_media_core
        assembled_path = assemble_file(upload_id, filename)

        # Convert
        output_path = convert_media_core(assembled_path, output_format)

        # Read result
        with open(output_path, "rb") as f:
            result_data = f.read()

        return base64.b64encode(result_data).decode("utf-8")

    except Exception as e:
        return f"Error in convert_uploaded_file: {str(e)}"
    finally:
        if assembled_path and os.path.exists(assembled_path):
            os.unlink(assembled_path)
        if output_path and os.path.exists(output_path):
            os.unlink(output_path)


@mcp.tool()
def transcribe_local_file(file_path: str, model_size: str = "base") -> str:
    """
    Yerel bir ses dosyasını (mp3, wav, m4a) Whisper kullanarak metne çevirir.
    Tool wrapper for the transcribe module.
    """
    return transcribe_local(file_path, model_size)

@mcp.tool()
def transcribe_audio_base64(audio_data: str, filename: str, model_size: str = "base") -> str:
    """
    Base64 encoded ses verisini alır, geçici dosyaya kaydeder ve transcribe eder.
    """
    try:
        # Create temp file
        suffix = os.path.splitext(filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
            temp.write(base64.b64decode(audio_data))
            temp_path = temp.name

        try:
            return transcribe_local(temp_path, model_size)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    except Exception as e:
        return f"Hata: {str(e)}"

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
def convert_media_base64(audio_data: str, filename: str, output_format: str = "mp3") -> str:
    """
    Base64 encoded ses verisini alır, dönüştürür ve base64 olarak geri döndürür.
    """
    try:
        from .audio import convert_media_core
        # Create temp file
        suffix = os.path.splitext(filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
            temp.write(base64.b64decode(audio_data))
            temp_path = temp.name

        output_path = None
        try:
            # Convert
            output_path = convert_media_core(temp_path, output_format)

            # Read result
            with open(output_path, "rb") as f:
                result_data = f.read()

            return base64.b64encode(result_data).decode("utf-8")

        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            if output_path and os.path.exists(output_path):
                os.unlink(output_path)

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
