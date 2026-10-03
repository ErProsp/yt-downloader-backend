import os
import shutil
from appwrite.client import Client
from appwrite.services.storage import Storage
from appwrite.input_file import InputFile
import yt_dlp

def main(context):
    req_data = context.req.body_json or context.req.query
    youtube_url = req_data.get('url')
    bucket_id = "music_bucket" 

    if not youtube_url:
        return context.res.json({"status": "error", "message": "URL mancante"}, 400)

    download_dir = "/tmp/downloads"
    if os.path.exists(download_dir):
        shutil.rmtree(download_dir)
    os.makedirs(download_dir, exist_ok=True)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_cookies = os.path.join(script_dir, "youtube_cookies.txt")

    # ydl_opts va definito QUI dentro, dopo che download_dir è stata dichiarata
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{download_dir}/%(id)s.%(ext)s',
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        }
    }

    if os.path.exists(local_cookies):
        ydl_opts['cookiefile'] = local_cookies
        context.log(f"Cookie abilitati dal file: {local_cookies}")
    else:
        context.log(f"ATTENZIONE: File cookie non trovato al percorso {local_cookies}")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            video_id = info['id']
            video_title = info['title']
            video_ext = info.get('ext')
            
            audio_path = os.path.join(download_dir, f"{video_id}.{video_ext}")
            
            if not os.path.exists(audio_path):
                return context.res.json({"status": "error", "message": "Estrazione fallita o file non trovato"}, 500)

            # Caricamento nello storage di Appwrite
            client = Client()
            client.set_endpoint(os.environ["APPWRITE_FUNCTION_API_ENDPOINT"])
            client.set_project(os.environ["APPWRITE_FUNCTION_PROJECT_ID"])
            client.set_key(os.environ["APPWRITE_FUNCTION_JWT"]) 
            
            storage = Storage(client)
            result = storage.create_file(
                bucket_id=bucket_id,
                file_id='unique()',
                file=InputFile.from_path(audio_path),
            )
            
            return context.res.json({
                "status": "success",
                "fileId": result['$id'],
                "bucketId": bucket_id,
                "title": video_title,
                "format": video_ext
            })

    except Exception as e:
        return context.res.json({"status": "error", "message": str(e)}, 500)
