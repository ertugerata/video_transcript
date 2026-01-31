import os
from pocketbase import PocketBase
from pocketbase.models import FileUpload
from datetime import datetime

pb_url = os.getenv("POCKETBASE_URL", "http://127.0.0.1:8090")
pb = PocketBase(pb_url)

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

def update_transcript(record_id: str, full_text: str, summary: str = ""):
    """Kaydı transkript ve özet ile günceller."""
    try:
        pb.collection('transcripts').update(record_id, {
            "full_transcript": full_text,
            "simple_transcript": full_text,
            "summary": summary
        })
        return True
    except Exception as e:
        print(f"Transkript güncelleme hatası: {e}")
        return False
