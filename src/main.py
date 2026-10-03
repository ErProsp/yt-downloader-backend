import os
import shutil
import subprocess
import sys

# Forza l'aggiornamento di yt-dlp all'ultima versione disponibile ad ogni esecuzione
try:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"])
except Exception as e:
    print(f"Aggiornamento yt-dlp non riuscito: {e}")

import yt_dlp
from appwrite.client import Client
from appwrite.services.storage import Storage
from appwrite.input_file import InputFile

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

    # Configurazione con client iOS e User-Agent mobile per eludere i blocchi datacenter
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{download_dir}/%(id)s.%(ext)s',
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android']
            }
        },
        'geo_bypass': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/605.1.15'
        }
    }

    if os.path.exists(local_cookies):
        ydl_opts['cookiefile'] = local_cookies
        context.log(f"Cookie caricati correttamente da: {local_cookies}")
    else:
        context.log(f"ATTENZIONE: File cookie non trovato in {local_cookies}")

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
