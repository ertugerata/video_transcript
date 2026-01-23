# app.py
from flask import Flask, render_template, request, jsonify, send_file
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import google.generativeai as genai
from pocketbase import PocketBase
from pocketbase.client import ClientResponseError
import re
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# PocketBase bağlantısı
pb = PocketBase('http://127.0.0.1:8090')

# Gemini API yapılandırması
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-pro')

def extract_video_id(url):
    """YouTube URL'sinden video ID çıkarır"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)',
        r'youtube\.com\/embed\/([^&\n?#]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_video_info(video_id):
    """Video başlığını almaya çalışır (basit yöntem)"""
    try:
        # YouTube Transcript API'den dil bilgilerini alırken video başlığı da gelebilir
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        return f"YouTube Video - {video_id}"
    except:
        return f"YouTube Video - {video_id}"

def get_transcript(video_id, language='tr'):
    """YouTube video transkriptini alır - TAM METİN"""
    try:
        print(f"Video ID için transkript alınıyor: {video_id}")
        
        # Cookies dosyası varsa kullan
        cookies_file = 'youtube_cookies.txt'
        cookies = cookies_file if os.path.exists(cookies_file) else None
        
        if cookies:
            print(f"Cookies dosyası kullanılıyor: {cookies_file}")
        
        # Basit yöntem - direkt transkript al
        try:
            print(f"Türkçe transkript deneniyor...")
            transcript_data = YouTubeTranscriptApi.get_transcript(
                video_id, 
                languages=['tr'],
                cookies=cookies
            )
            detected_language = 'tr'
            print(f"Türkçe transkript bulundu!")
        except:
            try:
                print(f"İngilizce transkript deneniyor...")
                transcript_data = YouTubeTranscriptApi.get_transcript(
                    video_id, 
                    languages=['en'],
                    cookies=cookies
                )
                detected_language = 'en'
                print(f"İngilizce transkript bulundu!")
            except:
                print(f"Otomatik transkript deneniyor...")
                transcript_data = YouTubeTranscriptApi.get_transcript(
                    video_id,
                    cookies=cookies
                )
                detected_language = 'auto'
                print(f"Otomatik transkript bulundu!")
        
        print(f"Transkript verisi alındı: {len(transcript_data)} satır")
        
        # Tam metin - zaman damgaları ile birlikte
        full_transcript = []
        for item in transcript_data:
            timestamp = format_timestamp(item['start'])
            text = item['text']
            full_transcript.append(f"[{timestamp}] {text}")
        
        # Basit metin (zaman damgası olmadan)
        simple_text = ' '.join([item['text'] for item in transcript_data])
        
        return {
            'full_text': '\n'.join(full_transcript),
            'simple_text': simple_text,
            'language': detected_language
        }, None
    
    except TranscriptsDisabled:
        print(f"HATA: Transkript kapalı")
        return None, "Bu video için transkript kapalı."
    except NoTranscriptFound:
        print(f"HATA: Transkript bulunamadı")
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
    """Gemini Pro ile özet oluşturur"""
    try:
        prompt = f"""Aşağıdaki YouTube video transkriptini özetle. 
        Önemli noktaları maddeler halinde belirt:

        {text[:30000]}  # Token limiti için kısıtlama
        """
        
        response = model.generate_content(prompt)
        return response.text, None
    except Exception as e:
        return None, f"Özet oluşturma hatası: {str(e)}"

def save_to_pocketbase(video_id, url, transcript_data, summary=None):
    """Transkripti PocketBase'e kaydeder"""
    try:
        data = {
            "video_id": video_id,
            "url": url,
            "full_transcript": transcript_data['full_text'],
            "simple_transcript": transcript_data['simple_text'],
            "language": transcript_data['language'],
            "summary": summary or "",
            "created": datetime.now().isoformat()
        }
        
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
        data = request.json
        url = data.get('url')
        use_cache = data.get('use_cache', True)
        generate_summary_flag = data.get('generate_summary', False)
        include_timestamps = data.get('include_timestamps', True)
        
        print(f"\n=== YENİ İSTEK ===")
        print(f"URL: {url}")
        print(f"Cache: {use_cache}, Summary: {generate_summary_flag}, Timestamps: {include_timestamps}")
        
        if not url:
            return jsonify({'error': 'URL gerekli'}), 400
        
        video_id = extract_video_id(url)
        print(f"Video ID: {video_id}")
        
        if not video_id:
            return jsonify({'error': 'Geçersiz YouTube URL\'si'}), 400
        
        # Önce cache'e bak
        if use_cache:
            print(f"Cache kontrol ediliyor...")
            cached_record, error = get_from_pocketbase(video_id)
            if cached_record:
                print(f"Cache'den bulundu!")
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
            else:
                print(f"Cache'de bulunamadı: {error}")
        
        # Transkripti al
        print(f"Transkript alınıyor...")
        transcript_data, error = get_transcript(video_id)
        if error:
            print(f"Transkript hatası: {error}")
            return jsonify({'error': error}), 400
        
        print(f"Transkript başarıyla alındı!")
        
        summary = None
        if generate_summary_flag and transcript_data:
            print(f"Özet oluşturuluyor...")
            summary, sum_error = generate_summary(transcript_data['simple_text'])
            if sum_error:
                print(f"Özet hatası: {sum_error}")
                summary = f"Özet oluşturulamadı: {sum_error}"
            else:
                print(f"Özet başarıyla oluşturuldu!")
        
        # PocketBase'e kaydet
        print(f"Veritabanına kaydediliyor...")
        record_id, save_error = save_to_pocketbase(video_id, url, transcript_data, summary)
        if save_error:
            print(f"Kayıt hatası: {save_error}")
        else:
            print(f"Başarıyla kaydedildi! Record ID: {record_id}")
        
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
    
    except Exception as e:
        print(f"\n!!! BEKLENMEYEN HATA !!!")
        print(f"Hata tipi: {type(e).__name__}")
        print(f"Hata mesajı: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Sunucu hatası: {str(e)}'}), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    """Geçmiş kayıtları getirir"""
    try:
        records = pb.collection('transcripts').get_list(
            1, 50,
            {'sort': '-created'}
        )
        
        items = []
        for record in records.items:
            items.append({
                'id': record.id,
                'video_id': record.video_id,
                'url': record.url,
                'created': record.created,
                'language': record.language,
                'has_summary': bool(record.summary)
            })
        
        return jsonify({'success': True, 'items': items})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/<record_id>', methods=['GET'])
def export_transcript(record_id):
    """Transkripti text dosyası olarak indirir"""
    try:
        record = pb.collection('transcripts').get_one(record_id)
        format_type = request.args.get('format', 'txt')
        
        if format_type == 'md':
            # Markdown formatı
            filename = f"transcript_{record.video_id}.md"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"# YouTube Video Transkript\n\n")
                f.write(f"**Video ID:** {record.video_id}\n\n")
                f.write(f"**URL:** {record.url}\n\n")
                f.write(f"**Dil:** {record.language}\n\n")
                f.write(f"**Tarih:** {record.created}\n\n")
                f.write("---\n\n")
                f.write("## Transkript\n\n")
                f.write(record.full_transcript.replace('\n', '\n\n'))
                if record.summary:
                    f.write("\n\n---\n\n")
                    f.write("## AI Özeti\n\n")
                    f.write(record.summary)
        else:
            # Text formatı
            filename = f"transcript_{record.video_id}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"Video ID: {record.video_id}\n")
                f.write(f"URL: {record.url}\n")
                f.write(f"Dil: {record.language}\n")
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