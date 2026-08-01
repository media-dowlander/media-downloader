import os
import sys
from pathlib import Path
import yt_dlp
import imageio_ffmpeg

USER_DOWNLOADS = Path(os.path.expanduser('~/Downloads')) / 'V_Media_Downloads'
USER_DOWNLOADS.mkdir(parents=True, exist_ok=True)
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()

def print_banner():
    print("=" * 60)
    print(" 🔥 V OMNI MEDIA CONVERTER & DOWNLOADER - TERMINAL EDITION")
    print(" 🚀 YouTube | TikTok | Pornhub | Instagram | Twitter | 1800+ Siteden")
    print(" 📁 Kayıt Konumu:", USER_DOWNLOADS)
    print("=" * 60)

def download_link(url, choice):
    opts = {
        'ffmpeg_location': FFMPEG_PATH,
        'outtmpl': str(USER_DOWNLOADS / '%(title).100s_%(id)s.%(ext)s'),
        'noplaylist': True,
    }

    if choice == '1':  # MP3 Standard
        opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',
            }],
        })
    elif choice == '2':  # MP3 HD 320k
        opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
        })
    elif choice == '3':  # MP4 SD 480p
        opts.update({
            'format': 'bestvideo[height<=480]+bestaudio/best[height<=480]/best',
            'merge_output_format': 'mp4',
        })
    elif choice == '4':  # MP4 HD 1080p
        opts.update({
            'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',
            'merge_output_format': 'mp4',
        })
    elif choice == '5':  # MP4 2K 1440p
        opts.update({
            'format': 'bestvideo[height<=1440]+bestaudio/best[height<=1440]/best',
            'merge_output_format': 'mp4',
        })
    elif choice == '6':  # MP4 4K 2160p
        opts.update({
            'format': 'bestvideo[height<=2160]+bestaudio/best[height<=2160]/best',
            'merge_output_format': 'mp4',
        })

    print(f"\n[+] İndirme ve Dönüştürme Başlatılıyor: {url}")
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        print(f"\n[✔] İŞLEM BAŞARILI! Dosya şuraya kaydedildi: {USER_DOWNLOADS}\n")
    except Exception as e:
        print(f"\n[✘] Hata Oluştu: {e}\n")

def main():
    print_banner()
    while True:
        print("\nFORMAT SEÇİMİ:")
        print(" [1] MP3 (Standart - 128 kbps Ses)")
        print(" [2] HD MP3 (Stüdyo Kalitesi - 320 kbps Ses)")
        print(" [3] MP4 SD (480p Kalite)")
        print(" [4] MP4 HD (1080p Full HD Video)")
        print(" [5] MP4 2K (1440p QHD Video)")
        print(" [6] MP4 4K (2160p Ultra HD Video)")
        print(" [Q] Çıkış")
        
        choice = input("\nSeçiminiz (1-6 veya Q): ").strip().upper()
        if choice == 'Q':
            print("Görüşmek üzere, tatlım!")
            break
            
        if choice not in ['1', '2', '3', '4', '5', '6']:
            print("Geçersiz seçim! Lütfen 1-6 arasında bir rakam girin.")
            continue

        url = input("Dönüştürmek istediğin video/ses linkini yapıştır: ").strip()
        if url:
            download_link(url, choice)

if __name__ == '__main__':
    main()
