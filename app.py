# app.py
from flask import Flask, render_template, request, jsonify, send_file
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
from google import genai
from google.genai import types
from supabase import create_client, Client
import re
from datetime import datetime
import os
import time
import tempfile
import io
import base64
from dotenv import load_dotenv

load_dotenv()

# MCP Client import
try:
    from mcp_client_utils import call_process_youtube_workflow, call_transcribe_audio, call_convert_media
except ImportError as e:
    print(f"MCP Client Utils import failed: {e}")
    def call_process_youtube_workflow(url): return f"MCP Client modülü yüklenemedi: {e}"
    def call_transcribe_audio(file_path, model_size="base"): return f"MCP Client modülü yüklenemedi: {e}"
    def call_convert_media(file_path, target_format="mp3"): return f"MCP Client modülü yüklenemedi: {e}"

app = Flask(__name__)

# Gemini API yapılandırması
api_key = os.getenv('GEMINI_API_KEY')
print(f"DEBUG: GEMINI_API_KEY loaded: {bool(api_key)}")
client = genai.Client(api_key=api_key)

# Supabase bağlantısı
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

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

            if "404" in error_str or "NOT_FOUND" in error_str or "not found" in error_str:
                last_error = e
                continue

            last_error = e

    if last_error:
        print(f"All models failed. Last error: {last_error}")
        raise last_error
    else:
        raise Exception("No models available or unknown error")

# YouTube URL patterns
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
        
        cookies_file = 'youtube_cookies.txt'
        cookies = cookies_file if os.path.exists(cookies_file) else None
        
        ytt = YouTubeTranscriptApi()
        
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
        
        full_transcript = []
        for item in transcript_data:
            timestamp = format_timestamp(item.start)
            text = item.text
            full_transcript.append(f"[{timestamp}] {text}")
        
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
        prompt = f"""Aşağıdaki metni özetle. Önemli noktaları maddeler halinde belirt:

        {text[:100000]}
        """
        response = generate_content_with_retry(contents=prompt)
        return response.text, None
    except Exception as e:
        return None, f"Özet oluşturma hatası: {str(e)}"

def save_to_supabase(data, file_obj=None):
    """Transkripti Supabase'e kaydeder"""
    try:
        # TODO: Handle file upload to Supabase Storage if needed
        # if file_obj:
        #     data['audio_file'] = ... 

        response = supabase.table('transcripts').insert(data).execute()
        # Supabase returns the inserted data
        if response.data:
            return response.data[0]['id'], None
        return None, "Kayıt başarısız, veri dönmedi."
    except Exception as e:
        return None, f"Veritabanı hatası: {str(e)}"

def get_from_supabase(video_id):
    """Supabase'den transkript getirir"""
    try:
        response = supabase.table('transcripts').select("*").eq('video_id', video_id).execute()
        if response.data:
            return response.data[0], None
        return None, "Kayıt bulunamadı"
    except Exception as e:
        return None, f"Veritabanı hatası: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/transcript', methods=['POST'])
def get_transcript_api():
    try:
        if 'audio_file' in request.files:
            return handle_file_upload()
        
        if request.is_json:
            data = request.json
            return handle_youtube_url(data)

        if request.form.get('url'):
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

@app.route('/api/process_youtube_local', methods=['POST'])
def process_youtube_local():
    """
    YouTube videosunu indirir, parçalar ve yerel Whisper ile işler.
    (local_media_server.process_youtube_workflow kullanır)

    GÜNCELLEME: Artık uzaktaki MCP sunucusunu (ertugrulerata-mcp-media-server.hf.space) kullanıyor.
    """
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({'error': 'URL gerekli'}), 400

        url = data['url']
        print(f"\n=== YEREL YOUTUBE İŞLEME İSTEĞİ (MCP REMOTE) ===")
        print(f"URL: {url}")

        # Uzaktaki MCP sunucusuna istek gönder
        report = call_process_youtube_workflow(url)

        return jsonify({
            'success': True,
            'report': report
        })

    except Exception as e:
        print(f"HATA: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/convert', methods=['POST'])
def convert_media():
    temp_path = None
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Dosya bulunamadı'}), 400

        file = request.files['file']
        target_format = request.form.get('format', 'mp3')

        if file.filename == '':
            return jsonify({'error': 'Dosya seçilmedi'}), 400

        # Create temp file
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
            file.save(temp.name)
            temp_path = temp.name

        print(f"Media conversion requested (MCP Remote): {file.filename} -> {target_format}")

        # Convert via MCP
        result_base64 = call_convert_media(temp_path, target_format)

        # Check for errors
        if result_base64.startswith("Hata:") or result_base64.startswith("MCP Client Error:"):
            return jsonify({'error': result_base64}), 400

        # Decode result
        data = base64.b64decode(result_base64)

        return send_file(
            io.BytesIO(data),
            as_attachment=True,
            download_name=f"{os.path.splitext(file.filename)[0]}.{target_format}",
            mimetype=f"audio/{target_format}"
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # Cleanup input temp file
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)

def handle_file_upload():
    """Dosya yükleme işlemlerini yönetir"""
    temp_path = None
    try:
        file = request.files['audio_file']
        generate_summary_flag = request.form.get('generate_summary') == 'true'
        model_size = request.form.get('model_size', 'base')
        
        if file.filename == '':
            return jsonify({'error': 'Dosya seçilmedi'}), 400

        print(f"\n=== YENİ DOSYA YÜKLEME ===")
        print(f"Dosya: {file.filename}")
        print(f"Model: {model_size}")
        
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
            file.save(temp.name)
            temp_path = temp.name

        print("Whisper (MCP Remote) ile transkript alınıyor...")
        transcript_result = call_transcribe_audio(temp_path, model_size=model_size)
        
        if transcript_result.startswith("Hata:") or transcript_result.startswith("Transkripsiyon hatası:") or transcript_result.startswith("MCP Client Error:"):
            return jsonify({'error': transcript_result}), 400

        transcript_text = transcript_result

        summary = None
        if generate_summary_flag:
            print("Özet oluşturuluyor...")
            summary, sum_error = generate_summary(transcript_text)
            if sum_error:
                summary = f"Özet oluşturulamadı: {sum_error}"

        print("Veritabanına kaydediliyor...")

        with open(temp_path, 'rb') as f:
            data = {
                "video_id": "",
                "url": "",
                "full_transcript": transcript_text,
                "simple_transcript": transcript_text,
                "language": "auto",
                "summary": summary or "",
                "created": datetime.now().isoformat()
            }
            record_id, save_error = save_to_supabase(data, file_obj=(file.filename, f))

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

    if use_cache:
        cached_record, error = get_from_supabase(video_id)
        if cached_record:
            # Supabase returns dict, not object
            transcript_text = cached_record['full_transcript'] if include_timestamps else cached_record['simple_transcript']
            return jsonify({
                'success': True,
                'video_id': video_id,
                'transcript': transcript_text,
                'summary': cached_record.get('summary', ''),
                'language': cached_record.get('language', ''),
                'from_cache': True,
                'record_id': cached_record['id']
            })

    transcript_data, error = get_transcript(video_id)
    if error:
        return jsonify({'error': error}), 400

    summary = None
    if generate_summary_flag:
        summary, sum_error = generate_summary(transcript_data['simple_text'])
        if sum_error:
            summary = f"Özet oluşturulamadı: {sum_error}"

    data = {
        "video_id": video_id,
        "url": url,
        "full_transcript": transcript_data['full_text'],
        "simple_transcript": transcript_data['simple_text'],
        "language": transcript_data['language'],
        "summary": summary or "",
        "created": datetime.now().isoformat()
    }
    record_id, save_error = save_to_supabase(data)

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
        response = supabase.table('transcripts').select("*").order('created', desc=True).limit(50).execute()
        
        items = [{
            'id': record['id'],
            'video_id': record.get('video_id', ''),
            'url': record.get('url', ''),
            'created': record['created'], # Supabase returns ISO format usually
            'language': record.get('language', ''),
            'has_summary': bool(record.get('summary'))
        } for record in response.data]
        
        return jsonify({'success': True, 'items': items})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/<record_id>', methods=['GET'])
def export_transcript(record_id):
    """Transkripti text dosyası olarak indirir"""
    try:
        response = supabase.table('transcripts').select("*").eq('id', record_id).execute()
        if not response.data:
             return jsonify({'error': 'Kayıt bulunamadı'}), 404
             
        record = response.data[0]
        format_type = request.args.get('format', 'txt')
        
        safe_name = record.get('video_id', '') or f"upload_{record['id']}"

        if format_type == 'md':
            filename = f"transcript_{safe_name}.md"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"# Transkript\n\n")
                if record.get('url'):
                    f.write(f"**URL:** {record['url']}\n\n")
                f.write(f"**Tarih:** {record['created']}\n\n")
                f.write("---\n\n")
                f.write("## Metin\n\n")
                f.write(record['full_transcript'].replace('\n', '\n\n'))
                if record.get('summary'):
                    f.write("\n\n---\n\n")
                    f.write("## AI Özeti\n\n")
                    f.write(record['summary'])
        else:
            filename = f"transcript_{safe_name}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                if record.get('url'):
                    f.write(f"URL: {record['url']}\n")
                f.write(f"Tarih: {record['created']}\n")
                f.write("\n" + "="*50 + "\n\n")
                f.write(record['full_transcript'])
                if record.get('summary'):
                    f.write("\n\n" + "="*50 + "\n")
                    f.write("ÖZET:\n\n")
                    f.write(record['summary'])
        
        return send_file(filename, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
