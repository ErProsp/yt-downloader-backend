import os
import re
import shutil
import subprocess
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
import yt_dlp

# Scarica e configura FFmpeg automaticamente all'avvio su Render
try:
    from ffdl import ffmpeg_download
    if not os.path.exists("/tmp/ffmpeg"):
        print("Download di FFmpeg in corso...")
        ffmpeg_download(bin_dir="/tmp")
        os.environ["PATH"] += os.pathsep + "/tmp"
        print("FFmpeg configurato correttamente!")
except Exception as e:
    print(f"Errore nella configurazione di FFmpeg: {e}")

app = FastAPI()
DOWNLOAD_DIR = "/tmp/downloads"

@app.get("/download")
def download_audio(url: str = Query(..., description="URL di YouTube")):
    # Pulisce la cartella dai download precedenti
    if os.path.exists(DOWNLOAD_DIR):
        shutil.rmtree(DOWNLOAD_DIR)
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{DOWNLOAD_DIR}/%(id)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        # AGGIRAMENTO BOT: Usa OAuth2 (Simula Smart TV)
        'username': 'oauth2',
        'password': '', 
        'extractor_args': {'youtube': {'player_client': 'tv'}},
        # Dice a yt-dlp dove trovare il nostro FFmpeg temporaneo
        'ffmpeg_location': '/tmp',
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info['id']
            video_title = info['title']
            
            expected_file = os.path.join(DOWNLOAD_DIR, f"{video_id}.mp3")
            
            if os.path.exists(expected_file):
                safe_title = re.sub(r'[^\w\s-]', '', video_title).strip() + ".mp3"
                return FileResponse(
                    expected_file, 
                    media_type='audio/mpeg', 
                    filename=safe_title
                )
            else:
                raise HTTPException(status_code=500, detail="Errore di conversione FFmpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/update-ytdlp")
def update_ytdlp():
    try:
        result = subprocess.run(["pip", "install", "--upgrade", "yt-dlp"], capture_output=True, text=True)
        return {"status": "success", "output": result.stdout}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})
