ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{download_dir}/%(id)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'ffmpeg_location': '/tmp',
        'cookiefile': local_cookies,
        'extractor_args': {
            'youtube': {
                'player_client': ['android']  # Forza solo Android per evitare i blocchi di firma web
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        }
    }
