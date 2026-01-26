# app.py
from flask import Flask, render_template, request, jsonify, send_file
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
from google import genai
from google.genai import types
from pocketbase import PocketBase
from pocketbase.client import ClientResponseError
from pocketbase.models import FileUpload
import re
from datetime import datetime
import os
import time
import tempfile
from dotenv import load_dotenv
from local_media_server import transcribe_local

load_dotenv()

app = Flask(__name__)

# PocketBase bağlantısı
pb = PocketBase('http://127.0.0.1:8090')

# Gemini API yapılandırması
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

# Fallback models to try in order
GEMINI_MODELS = [
    'gemini-1.5-flash',
    'gemini-1.5-flash-001',
    'gemini-1.5-flash-002',
    'gemini-2.0-flash-exp',
    'gemini-1.5-pro',
    'gemini-1.5-pro-001'
]

def generate_content_with_retry(contents, config=None):
    """
    Tries to generate content using a list of fallback models.
    """
    last_error = None

    # Try models in order
    for model_name in GEMINI_MODELS:
        try:
            print(f"Trying Gemini model: {model_name}")
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config
            )
            print(f"Success with model: {model_name}")
            return response
        except Exception as e:
            error_str = str(e)
            print(f"Failed with model {model_name}: {error_str}")

            # If it's a 404 (Not Found), we try the next one.
            # If it's a 429 (Resource Exhausted) or other errors, we might still want to try others or stop.
            # For now, we catch all and retry, but we could be more specific.
            if "404" in error_str or "NOT_FOUND" in error_str or "not found" in error_str:
                last_error = e
                continue

            # For other errors, we might want to fail fast, but
            # sometimes different models have different quotas/availabilities.
            # Let's keep trying.
            last_error = e

    # If we get here, all models failed
    if last_error:
        print(f"All models failed. Last error: {last_error}")
        raise last_error
    else:
        raise Exception("No models available or unknown error")

# YouTube URL patterns - Module level compilation for performance
VIDEO_ID_PATTERNS = [
    re.compile(r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)'),
    re.compile(r'youtube\.com\/embed\/([^&\n?#]+)'),
]

def extract_video_id(url):
    """YouTube URL'sinden video ID çıkarır"""
    for pattern in VIDEO_ID_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)
    return None

def get_transcript(video_id, language='tr'):
    """YouTube video transkriptini alır - TAM METİN"""
    try:
        print(f"Video ID için transkript alınıyor: {video_id}")
        
        # Cookies dosyası varsa kullan
        cookies_file = 'youtube_cookies.txt'
        cookies = cookies_file if os.path.exists(cookies_file) else None
        
        ytt = YouTubeTranscriptApi()
        
        # Basit yöntem - direkt transkript al
        try:
            print(f"Türkçe transkript deneniyor...")
            transcript_data = ytt.fetch(video_id, languages=['tr'])
            detected_language = 'tr'
            print(f"Türkçe transkript bulundu!")
        except:
            try:
                print(f"İngilizce transkript deneniyor...")
                transcript_data = ytt.fetch(video_id, languages=['en'])
                detected_language = 'en'
                print(f"İngilizce transkript bulundu!")
            except:
                print(f"Otomatik transkript deneniyor...")
                transcript_data = ytt.fetch(video_id)
                detected_language = 'auto'
                print(f"Otomatik transkript bulundu!")
        
        print(f"Transkript verisi alındı: {len(transcript_data)} satır")
        
        # Tam metin - zaman damgaları ile birlikte
        full_transcript = []
        for item in transcript_data:
            timestamp = format_timestamp(item.start)
            text = item.text
            full_transcript.append(f"[{timestamp}] {text}")
        
        # Basit metin (zaman damgası olmadan)
        simple_text = ' '.join([item.text for item in transcript_data])
        
        return {
            'full_text': '\n'.join(full_transcript),
            'simple_text': simple_text,
            'language': detected_language
        }, None
    
    except TranscriptsDisabled:
        return None, "Bu video için transkript kapalı."
    except NoTranscriptFound:
        return None, "Bu video için transkript bulunamadı."
    except Exception as e:
        print(f"HATA: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, f"Hata: {str(e)}"

def format_timestamp(seconds):
    """Saniyeyi [HH:MM:SS] formatına çevirir"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"

def generate_summary(text):
    """Gemini ile özet oluşturur"""
    try:
        # Metin çok uzunsa kırp (Gemini 1.5 Pro 1M token alabilir ama biz yine de dikkatli olalım)
        # Gemini Pro (1.0) limiti 30k karakter civarıydı, 1.5 çok daha yüksek.
        # Yine de güvenli sınırda tutalım.
        prompt = f"""Aşağıdaki metni özetle. Önemli noktaları maddeler halinde belirt:

        {text[:100000]}
        """
        
        # Helper fonksiyonu kullan (fallback mekanizması ile)
        response = generate_content_with_retry(contents=prompt)
        return response.text, None
    except Exception as e:
        return None, f"Özet oluşturma hatası: {str(e)}"

def transcribe_audio_file(file_path, mime_type):
    """Gemini ile ses dosyasını transkript eder"""
    try:
        print(f"Dosya Gemini'ye yükleniyor: {file_path} ({mime_type})")

        # Dosyayı Gemini File API'ye yükle
        # mime_type otomatik de algılanabilir ama varsa verelim
        myfile = client.files.upload(
            file=file_path,
            config={'mime_type': mime_type}
        )
        print(f"Yüklendi: {myfile.name}")

        # İşlenmesini bekle
        while myfile.state == "PROCESSING":
            print("Dosya işleniyor...", end='\r')
            time.sleep(1)
            myfile = client.files.get(name=myfile.name)

        if myfile.state == "FAILED":
            raise ValueError("Gemini dosya işleme hatası")

        print("\nTranskript oluşturuluyor...")
        prompt = "Bu ses/video dosyasının tam, kelimesi kelimesine dökümünü (transkriptini) çıkar. Konuşmaları olduğu gibi yaz. Zaman damgası ekleme."

        # Helper fonksiyonu kullan (fallback mekanizması ile)
        response = generate_content_with_retry(contents=[prompt, myfile])
        
        # İşimiz bitince dosyayı silebiliriz (opsiyonel, Gemini kotası için iyi olur)
        # client.files.delete(name=myfile.name)

        return response.text, None

    except Exception as e:
        print(f"AI Ses Hatası: {str(e)}")
        return None, f"AI Transkript hatası: {str(e)}"

def save_to_pocketbase(data, file_obj=None):
    """Transkripti PocketBase'e kaydeder"""
    try:
        # Dosya varsa data'ya FileUpload olarak ekle
        if file_obj:
            # file_obj: ('filename', open_file_stream)
            data['audio_file'] = FileUpload(file_obj)

        record = pb.collection('transcripts').create(data)
        return record.id, None
    except ClientResponseError as e:
        return None, f"Veritabanı hatası: {str(e)}"
    except Exception as e:
        return None, f"Kayıt hatası: {str(e)}"

def get_from_pocketbase(video_id):
    """PocketBase'den transkript getirir"""
    try:
        records = pb.collection('transcripts').get_list(
            1, 1,
            {'filter': f'video_id="{video_id}"'}
        )
        if records.items:
            return records.items[0], None
        return None, "Kayıt bulunamadı"
    except Exception as e:
        return None, f"Veritabanı hatası: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/transcript', methods=['POST'])
def get_transcript_api():
    try:
        # Dosya Yükleme Kontrolü
        if 'audio_file' in request.files:
            return handle_file_upload()
        
        # JSON (YouTube URL) Kontrolü
        if request.is_json:
            data = request.json
            return handle_youtube_url(data)

        # Eğer form data içinde JSON verisi varsa (multipart ama dosya yoksa)
        if request.form.get('url'):
             # Form data'yı dict'e çevirip işle
             data = {
                 'url': request.form.get('url'),
                 'use_cache': request.form.get('use_cache') == 'true',
                 'generate_summary': request.form.get('generate_summary') == 'true',
                 'include_timestamps': request.form.get('include_timestamps') == 'true'
             }
             return handle_youtube_url(data)

        return jsonify({'error': 'Geçersiz istek formatı'}), 400

    except Exception as e:
        print(f"\n!!! BEKLENMEYEN HATA !!!")
        print(f"Hata tipi: {type(e).__name__}")
        print(f"Hata mesajı: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Sunucu hatası: {str(e)}'}), 500

def handle_file_upload():
    """Dosya yükleme işlemlerini yönetir"""
    temp_path = None
    try:
        file = request.files['audio_file']
        generate_summary_flag = request.form.get('generate_summary') == 'true'
        
        if file.filename == '':
            return jsonify({'error': 'Dosya seçilmedi'}), 400

        print(f"\n=== YENİ DOSYA YÜKLEME ===")
        print(f"Dosya: {file.filename}")
        
        # Geçici dosyaya kaydet
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
            file.save(temp.name)
            temp_path = temp.name

        # Whisper ile transkript al (Local Media Server)
        print("Whisper (Local) ile transkript alınıyor...")
        transcript_result = transcribe_local(temp_path, model_size="base")
        
        # Hata kontrolü
        if transcript_result.startswith("Hata:") or transcript_result.startswith("Transkripsiyon hatası:"):
            return jsonify({'error': transcript_result}), 400

        transcript_text = transcript_result

        summary = None
        if generate_summary_flag:
            print("Özet oluşturuluyor...")
            summary, sum_error = generate_summary(transcript_text)
            if sum_error:
                summary = f"Özet oluşturulamadı: {sum_error}"

        # PocketBase'e kaydet
        print("Veritabanına kaydediliyor...")

        # Dosyayı tekrar açıp PocketBase'e gönder
        with open(temp_path, 'rb') as f:
            data = {
                "video_id": "", # Dosya yüklemelerinde boş
                "url": "",
                "full_transcript": transcript_text,
                "simple_transcript": transcript_text, # Ses dosyasında şimdilik ikisi aynı
                "language": "auto", # Gemini auto detect ediyor
                "summary": summary or "",
                "created": datetime.now().isoformat()
            }
            record_id, save_error = save_to_pocketbase(data, file_obj=(file.filename, f))

        if save_error:
            print(f"Kayıt hatası: {save_error}")
        
        return jsonify({
            'success': True,
            'video_id': None,
            'transcript': transcript_text,
            'summary': summary,
            'language': 'auto',
            'from_cache': False,
            'saved': record_id is not None,
            'record_id': record_id
        })

    finally:
        # Geçici dosyayı temizle
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)

def handle_youtube_url(data):
    """Mevcut YouTube URL işleme mantığı"""
    url = data.get('url')
    use_cache = data.get('use_cache', True)
    generate_summary_flag = data.get('generate_summary', False)
    include_timestamps = data.get('include_timestamps', True)
    
    print(f"\n=== YENİ URL İSTEĞİ ===")
    print(f"URL: {url}")

    if not url:
        return jsonify({'error': 'URL gerekli'}), 400

    video_id = extract_video_id(url)
    if not video_id:
        return jsonify({'error': 'Geçersiz YouTube URL\'si'}), 400

    # Cache kontrol
    if use_cache:
        cached_record, error = get_from_pocketbase(video_id)
        if cached_record:
            transcript_text = cached_record.full_transcript if include_timestamps else cached_record.simple_transcript
            return jsonify({
                'success': True,
                'video_id': video_id,
                'transcript': transcript_text,
                'summary': cached_record.summary,
                'language': cached_record.language,
                'from_cache': True,
                'record_id': cached_record.id
            })

    # Transkript al
    transcript_data, error = get_transcript(video_id)
    if error:
        return jsonify({'error': error}), 400

    summary = None
    if generate_summary_flag:
        summary, sum_error = generate_summary(transcript_data['simple_text'])
        if sum_error:
            summary = f"Özet oluşturulamadı: {sum_error}"

    # Kaydet
    data_pb = {
        "video_id": video_id,
        "url": url,
        "full_transcript": transcript_data['full_text'],
        "simple_transcript": transcript_data['simple_text'],
        "language": transcript_data['language'],
        "summary": summary or "",
        "created": datetime.now().isoformat()
    }
    record_id, save_error = save_to_pocketbase(data_pb)

    transcript_text = transcript_data['full_text'] if include_timestamps else transcript_data['simple_text']

    return jsonify({
        'success': True,
        'video_id': video_id,
        'transcript': transcript_text,
        'summary': summary,
        'language': transcript_data['language'],
        'from_cache': False,
        'saved': record_id is not None,
        'record_id': record_id
    })

@app.route('/api/debug/models', methods=['GET'])
def list_models():
    """Mevcut Gemini modellerini listeler"""
    try:
        models_info = []
        for model in client.models.list():
            models_info.append({
                'name': model.name,
                'supported_generation_methods': model.supported_generation_methods,
                'display_name': getattr(model, 'display_name', '')
            })
        return jsonify({'success': True, 'models': models_info})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    """Geçmiş kayıtları getirir"""
    try:
        records = pb.collection('transcripts').get_list(
            1, 50,
            {'sort': '-created'}
        )
        
        items = [{
            'id': record.id,
            'video_id': getattr(record, 'video_id', ''),
            'url': getattr(record, 'url', ''),
            'created': record.created,
            'language': record.language,
            'has_summary': bool(record.summary)
        } for record in records.items]
        
        return jsonify({'success': True, 'items': items})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/<record_id>', methods=['GET'])
def export_transcript(record_id):
    """Transkripti text dosyası olarak indirir"""
    try:
        record = pb.collection('transcripts').get_one(record_id)
        format_type = request.args.get('format', 'txt')
        
        # Video ID yoksa (ses dosyası ise) generic bir isim kullan
        safe_name = getattr(record, 'video_id', '') or f"upload_{record.id}"

        if format_type == 'md':
            filename = f"transcript_{safe_name}.md"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"# Transkript\n\n")
                if getattr(record, 'url', ''):
                    f.write(f"**URL:** {record.url}\n\n")
                f.write(f"**Tarih:** {record.created}\n\n")
                f.write("---\n\n")
                f.write("## Metin\n\n")
                f.write(record.full_transcript.replace('\n', '\n\n'))
                if record.summary:
                    f.write("\n\n---\n\n")
                    f.write("## AI Özeti\n\n")
                    f.write(record.summary)
        else:
            filename = f"transcript_{safe_name}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                if getattr(record, 'url', ''):
                    f.write(f"URL: {record.url}\n")
                f.write(f"Tarih: {record.created}\n")
                f.write("\n" + "="*50 + "\n\n")
                f.write(record.full_transcript)
                if record.summary:
                    f.write("\n\n" + "="*50 + "\n")
                    f.write("ÖZET:\n\n")
                    f.write(record.summary)
        
        return send_file(filename, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
