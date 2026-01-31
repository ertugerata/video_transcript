import yt_dlp
import os

def download_youtube_audio(url: str, output_dir: str = ".") -> tuple[str, str, str]:
    """
    YouTube videosunu indirir (en iyi ses mp3) ve dosya yolunu, video id'sini ve başlığı döndürür.
    """
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{output_dir}/%(id)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # yt-dlp will save as ID.mp3 because of postprocessor
        video_id = info['id']
        title = info.get('title', 'Unknown')
        final_path = os.path.join(output_dir, f"{video_id}.mp3")
        return final_path, video_id, title
