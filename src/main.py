import os
import shutil
import re
from appwrite.client import Client
from appwrite.services.storage import Storage
from appwrite.input_file import InputFile
import yt_dlp

# Download automatico di FFmpeg all'interno del container temporaneo di Appwrite
try:
    from ffdl import ffmpeg_download
    if not os.path.exists("/tmp/ffmpeg"):
        ffmpeg_download(bin_dir="/tmp")
        os.environ["PATH"] += os.pathsep + "/tmp"
except Exception as e:
    print(f"Errore inizializzazione FFmpeg: {e}")

def main(context):
    # Recupera i dati inviati dall'app Flutter (sia via POST JSON che via GET)
    req_data = context.req.body_json or context.req.query
    youtube_url = req_data.get('url')
    
    # IMPORTANTE: Cambia questo ID con quello del tuo Bucket reale creato su appwrite.io
    bucket_id = "music_bucket" 

    if not youtube_url:
        return context.res.json({"status": "error", "message": "URL mancante"}, 400)

    # Cartella di lavoro temporanea consentita all'interno dei container Appwrite
    download_dir = "/tmp/downloads"
    if os.path.exists(download_dir):
        shutil.rmtree(download_dir)
    os.makedirs(download_dir, exist_ok=True)

    # Configurazione della cache OAuth2 per evitare il blocco anti-bot di YouTube
    local_oauth_cache = os.path.join(os.getcwd(), "youtube_oauth2_cache.json")
    container_oauth_dir = "/tmp/.cache/yt-dlp"
    
    if os.path.exists(local_oauth_cache):
        os.makedirs(container_oauth_dir, exist_ok=True)
        shutil.copy(local_oauth_cache, os.path.join(container_oauth_dir, "youtube_oauth2_cache.json"))
        os.environ["XDG_CACHE_HOME"] = "/tmp/.cache"

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{download_dir}/%(id)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'username': 'oauth2',
        'password': '',
        'extractor_args': {'youtube': {'player_client': 'tv'}},
        'ffmpeg_location': '/tmp',
    }

    try:
        context.log(f"Inizio il download di: {youtube_url}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            video_id = info['id']
            video_title = info['title']
            
            mp3_path = os.path.join(download_dir, f"{video_id}.mp3")
            
            if not os.path.exists(mp3_path):
                return context.res.json({"status": "error", "message": "Estrazione audio fallita"}, 500)

            # Inizializza l'SDK Server sfruttando le variabili d'ambiente native di Appwrite
            client = Client()
            client.set_endpoint(os.environ["APPWRITE_FUNCTION_API_ENDPOINT"])
            client.set_project(os.environ["APPWRITE_FUNCTION_PROJECT_ID"])
            # Usa la chiave API temporanea generata dalla funzione stessa
            client.set_key(os.environ["APPWRITE_FUNCTION_JWT"]) 
            
            storage = Storage(client)
            
            # Carica il file MP3 convertito nello Storage di Appwrite Cloud
            context.log("Caricamento del file nello Storage...")
            result = storage.create_file(
                bucket_id=bucket_id,
                file_id='unique()',
                file=InputFile.from_path(mp3_path),
            )
            
            context.log(f"Download e caricamento completati! File ID: {result['$id']}")
            return context.res.json({
                "status": "success",
                "fileId": result['$id'],
                "bucketId": bucket_id,
                "title": video_title
            })

    except Exception as e:
        context.error(f"Errore durante l'esecuzione: {str(e)}")
        return context.res.json({"status": "error", "message": str(e)}, 500)
