import os
import re
import sys
import uuid
import base64
import threading
import time
import json
import tempfile
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
import yt_dlp
import imageio_ffmpeg

app = Flask(__name__, template_folder='templates')

# Server Cache Directory
CACHE_DIR = Path(__file__).parent / 'temp_cache'
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Stats File for Persistence
STATS_FILE = Path(__file__).parent / 'stats.json'

# Get ffmpeg binary path from imageio_ffmpeg
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()

# In-memory storage for active download statuses & DDoS protection
DOWNLOAD_TASKS = {}
IP_REQUEST_LOGS = {}
MAX_CONCURRENT_DOWNLOADS = 5
CURRENT_ACTIVE_DOWNLOADS = 0
DOWNLOAD_LOCK = threading.Lock()

# Load or initialize stats
def load_stats():
    if STATS_FILE.exists():
        try:
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {'total_downloads': 1248, 'total_visitors': 3820}

def save_stats(stats):
    try:
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats, f)
    except Exception:
        pass

SERVER_STATS = load_stats()

# Anti-DDoS Rate Limiter Middleware
@app.before_request
def anti_ddos_protection():
    client_ip = request.remote_addr or '127.0.0.1'
    now = time.time()
    
    # Initialize IP log
    if client_ip not in IP_REQUEST_LOGS:
        IP_REQUEST_LOGS[client_ip] = []
    
    # Filter requests older than 60 seconds
    IP_REQUEST_LOGS[client_ip] = [t for t in IP_REQUEST_LOGS[client_ip] if now - t < 60]
    
    # Check limit: Max 60 requests per minute per IP
    if len(IP_REQUEST_LOGS[client_ip]) > 60:
        return jsonify({
            'error': '🛡️ DDoS Koruması Devrede: Çok fazla istek gönderildi. Lütfen 1 dakika bekleyin.'
        }), 429
    
    IP_REQUEST_LOGS[client_ip].append(now)

# YouTube cookie dosyasını env'den oku ve temp'e yaz
COOKIE_FILE_PATH = None

def setup_cookies():
    global COOKIE_FILE_PATH
    yt_cookies_b64 = os.environ.get('YT_COOKIES', '')
    if yt_cookies_b64:
        try:
            cookie_data = base64.b64decode(yt_cookies_b64).decode('utf-8')
            tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
            tmp.write(cookie_data)
            tmp.close()
            COOKIE_FILE_PATH = tmp.name
            print(f"✅ YouTube cookies yüklendi: {COOKIE_FILE_PATH}")
        except Exception as e:
            print(f"⚠️ Cookie yükleme hatası: {e}")
    else:
        print("⚠️ YT_COOKIES env değişkeni bulunamadı — bot koruması devreye girebilir")

setup_cookies()

# YouTube bot detection bypass options
YT_BYPASS_OPTS = {}

def get_yt_opts_with_cookies():
    """Cookie dosyası varsa ekle."""
    opts = dict(YT_BYPASS_OPTS)
    if COOKIE_FILE_PATH:
        opts['cookiefile'] = COOKIE_FILE_PATH
    return opts

def get_format_opts(quality_key):
    opts = {
        'ffmpeg_location': FFMPEG_PATH,
        'outtmpl': str(CACHE_DIR / '%(title).100s_%(id)s.%(ext)s'),
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        **get_yt_opts_with_cookies(),
    }

    if quality_key == 'mp3_std':
        opts.update({
            'format': 'bestaudio/bestvideo+bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',
            }],
        })
    elif quality_key == 'mp3_hd':
        opts.update({
            'format': 'bestaudio/bestvideo+bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
        })
    elif quality_key == 'mp4_sd':
        opts.update({
            'format': 'bestvideo[height<=480]+bestaudio/best[height<=480]/bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
        })
    elif quality_key == 'mp4_hd':
        opts.update({
            'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
        })
    elif quality_key == 'mp4_2k':
        opts.update({
            'format': 'bestvideo[height<=1440]+bestaudio/best[height<=1440]/bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
        })
    elif quality_key == 'mp4_4k':
        opts.update({
            'format': 'bestvideo[height<=2160]+bestaudio/best[height<=2160]/bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
        })
    else:  # best
        opts.update({
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
        })

    return opts

@app.route('/')
def index():
    global SERVER_STATS
    SERVER_STATS['total_visitors'] += 1
    save_stats(SERVER_STATS)
    return render_template('index.html', download_dir=str(CACHE_DIR))

@app.route('/api/stats', methods=['GET'])
def get_stats():
    # Calculate live dynamic active users simulation (e.g. 12-25 online)
    active_now = 12 + (int(time.time()) % 11)
    return jsonify({
        'total_downloads': SERVER_STATS['total_downloads'],
        'total_visitors': SERVER_STATS['total_visitors'],
        'active_users': active_now,
        'ddos_status': 'Protected 🟢 (Rate-Limited)'
    })

@app.route('/api/info', methods=['POST'])
def get_info():
    data = request.json or {}
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'Lütfen geçerli bir video/ses linki girin.'}), 400

    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'ffmpeg_location': FFMPEG_PATH,
            **get_yt_opts_with_cookies(),
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            title = info.get('title', 'Bilinmeyen Başlık')
            duration = info.get('duration', 0)
            thumbnail = info.get('thumbnail', '')
            uploader = info.get('uploader', info.get('extractor_key', 'Platform'))
            
            return jsonify({
                'success': True,
                'title': title,
                'duration': duration,
                'thumbnail': thumbnail,
                'uploader': uploader,
                'extractor': info.get('extractor_key', 'Media'),
                'url': url
            })
    except Exception as e:
        return jsonify({'error': f'Link çözümlenemedi veya desteklenmiyor: {str(e)}'}), 500

def run_download_thread(task_id, url, quality):
    global CURRENT_ACTIVE_DOWNLOADS, SERVER_STATS
    task = DOWNLOAD_TASKS[task_id]
    task['status'] = 'downloading'
    task['progress'] = 0

    with DOWNLOAD_LOCK:
        CURRENT_ACTIVE_DOWNLOADS += 1

    def progress_hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            if total > 0:
                percent = round((downloaded / total) * 100, 1)
                task['progress'] = percent
                task['speed'] = d.get('_speed_str', '')
                task['eta'] = d.get('_eta_str', '')
            task['status_msg'] = f"İndiriliyor: %{task['progress']} ({task.get('speed', '')})"
        elif d['status'] == 'finished':
            task['progress'] = 99
            task['status_msg'] = 'Dönüştürülüyor ve hazırlanıyor...'

    try:
        opts = get_format_opts(quality)
        opts['progress_hooks'] = [progress_hook]

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            if 'mp3' in quality:
                base, _ = os.path.splitext(filename)
                filename = base + '.mp3'
                
            task['status'] = 'completed'
            task['progress'] = 100
            task['filename'] = os.path.basename(filename)
            task['filepath'] = filename
            task['status_msg'] = 'Tamamlandı! İndirmek için aşağıdaki butona tıkla.'
            
            # Increment total download count
            SERVER_STATS['total_downloads'] += 1
            save_stats(SERVER_STATS)
    except Exception as e:
        task['status'] = 'failed'
        task['error'] = str(e)
        task['status_msg'] = f'Hata: {str(e)}'
    finally:
        with DOWNLOAD_LOCK:
            CURRENT_ACTIVE_DOWNLOADS = max(0, CURRENT_ACTIVE_DOWNLOADS - 1)

@app.route('/api/download', methods=['POST'])
def start_download():
    global CURRENT_ACTIVE_DOWNLOADS
    
    # Anti-DDoS check for concurrent downloads
    if CURRENT_ACTIVE_DOWNLOADS >= MAX_CONCURRENT_DOWNLOADS:
        return jsonify({
            'error': '🛡️ Sunucu yoğun: Çok fazla eşzamanlı dönüştürme yapılıyor. Lütfen birkaç saniye bekleyip tekrar deneyin.'
        }), 429

    data = request.json or {}
    url = data.get('url', '').strip()
    quality = data.get('quality', 'mp4_hd')

    if not url:
        return jsonify({'error': 'Geçerli bir URL gerekli.'}), 400

    task_id = str(uuid.uuid4())
    DOWNLOAD_TASKS[task_id] = {
        'id': task_id,
        'url': url,
        'quality': quality,
        'status': 'starting',
        'progress': 0,
        'created_at': time.time()
    }

    t = threading.Thread(target=run_download_thread, args=(task_id, url, quality))
    t.daemon = True
    t.start()

    return jsonify({'success': True, 'task_id': task_id})

@app.route('/api/status/<task_id>', methods=['GET'])
def get_status(task_id):
    task = DOWNLOAD_TASKS.get(task_id)
    if not task:
        return jsonify({'error': 'Görev bulunamadı.'}), 404
    return jsonify(task)

@app.route('/api/files', methods=['GET'])
def list_files():
    try:
        files = []
        for file_path in CACHE_DIR.glob('*'):
            if file_path.is_file():
                files.append({
                    'name': file_path.name,
                    'size_mb': round(file_path.stat().st_size / (1024 * 1024), 2),
                    'created': time.ctime(file_path.stat().st_ctime)
                })
        files.sort(key=lambda x: x['created'], reverse=True)
        return jsonify({'files': files, 'folder': str(CACHE_DIR)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.after_request
def add_security_and_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-DDoS-Protection"] = "Active-RateLimiter-v2"
    return response

@app.route('/download_file/<filename>')
def download_file(filename):
    return send_from_directory(CACHE_DIR, filename, as_attachment=True)

if __name__ == '__main__':
    import socket
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        local_ip = '127.0.0.1'
    port = int(os.environ.get('PORT', 5001))
    print("=" * 60)
    print(f"🚀 MP3 MP4 Loader Every Link Server Başlatıldı!")
    print(f"🛡️ Anti-DDoS ve Rate Limiting Koruması: AKTİF")
    print(f"📁 Geçici Önbellek Klasörü: {CACHE_DIR}")
    print(f"⚙️ FFmpeg Konumu: {FFMPEG_PATH}")
    print(f"🌐 Kendi bilgisayarın: http://127.0.0.1:{port}")
    print(f"🌐 Arkadaşların için link: http://{local_ip}:{port}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port, debug=False)

