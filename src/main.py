import os
import shutil
import re
from appwrite.client import Client
from appwrite.services.storage import Storage
from appwrite.input_file import InputFile
import yt_dlp

# Download automatico di FFmpeg nel container Appwrite
try:
    from ffdl import ffmpeg_download
    if not os.path.exists("/tmp/ffmpeg"):
        ffmpeg_download(bin_dir="/tmp")
        os.environ["PATH"] += os.pathsep + "/tmp"
except Exception as e:
    print(f"Errore FFmpeg: {e}")

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

    # Cerca il file dei cookie caricato insieme alla funzione
    local_cookies = os.path.join(os.getcwd(), "cookies.txt")

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{download_dir}/%(id)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'ffmpeg_location': '/tmp',
        # Configurazione User-Agent per simulare un browser reale insieme ai cookie
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    }

    # Se il file cookies.txt è presente, lo passa a yt-dlp
    if os.path.exists(local_cookies):
        ydl_opts['cookiefile'] = local_cookies
        context.log("Uso dei cookie rilevato ed abilitato.")
    else:
        context.log("ATTENZIONE: cookies.txt non trovato. Il download potrebbe fallire sui server cloud.")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            video_id = info['id']
            video_title = info['title']
            
            mp3_path = os.path.join(download_dir, f"{video_id}.mp3")
            
            if not os.path.exists(mp3_path):
                return context.res.json({"status": "error", "message": "Estrazione fallita"}, 500)

            # Caricamento nello storage di Appwrite
            client = Client()
            client.set_endpoint(os.environ["APPWRITE_FUNCTION_API_ENDPOINT"])
            client.set_project(os.environ["APPWRITE_FUNCTION_PROJECT_ID"])
            client.set_key(os.environ["APPWRITE_FUNCTION_JWT"]) 
            
            storage = Storage(client)
            result = storage.create_file(
                bucket_id=bucket_id,
                file_id='unique()',
                file=InputFile.from_path(mp3_path),
            )
            
            return context.res.json({
                "status": "success",
                "fileId": result['$id'],
                "bucketId": bucket_id,
                "title": video_title
            })

    except Exception as e:
        return context.res.json({"status": "error", "message": str(e)}, 500)
