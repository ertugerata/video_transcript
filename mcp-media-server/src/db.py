from supabase import create_client, Client

# Supabase bağlantısı
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

def save_chunk_to_db(file_path: str, video_id: str, url: str) -> str:
    """Parçayı veritabanına kaydeder (transkriptsiz)."""
    try:
        # FileUpload için dosyayı açıyoruz. create çağrısı bitene kadar açık kalmalı.
        # TODO: Handle file upload if needed for chunks
        
        data = {
            "video_id": video_id,
            "url": url,
            "full_transcript": "",
            "simple_transcript": "",
            "language": "auto",
            "summary": "",
            "created": datetime.now().isoformat(),
            # "audio_file": ... # Handle file upload to Supabase Storage if needed
        }
        response = supabase.table('transcripts').insert(data).execute()
        if response.data:
            return response.data[0]['id']
        return None
    except Exception as e:
        print(f"DB Kayıt hatası ({file_path}): {e}")
        return None

def update_transcript(record_id: str, full_text: str, summary: str = ""):
    """Kaydı transkript ve özet ile günceller."""
    try:
        supabase.table('transcripts').update({
            "full_transcript": full_text,
            "simple_transcript": full_text,
            "summary": summary
        }).eq('id', record_id).execute()
        return True
    except Exception as e:
        print(f"Transkript güncelleme hatası: {e}")
        return False
