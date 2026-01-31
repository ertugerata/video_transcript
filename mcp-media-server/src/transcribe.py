import whisper
import os

model_cache = {}

def get_model(model_size="base"):
    """İstenen Whisper modelini yükler veya önbellekten getirir."""
    if model_size not in model_cache:
        print(f"Model yükleniyor: {model_size} (Bu işlem ilk seferde biraz sürebilir)...")
        model_cache[model_size] = whisper.load_model(model_size)
    return model_cache[model_size]

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
