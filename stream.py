import os
import time
import ffmpeg
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from flask import Flask
import discord
from discord.ext import commands

# 🔒 Replace with your actual bot token
BOT_TOKEN = "MTM0MjE3MDI0ODAyMjk4Njg2Ng.GojGpW.Ffu_Q4jx1JuZy_jLZj5k5ubnAhwzPNG-8ZlJ5Y"

# ✅ Configuration
MUSIC_FOLDER = "music"
GIF_FILE = "assets/bg.gif"
WATERMARK = "assets/wc.png"
OUTPUT_FILE = "output.flv"  # 🔥 Using FLV instead of MP4
RTMP_URL = "rtmp://a.rtmp.youtube.com/live2/5833-33rp-07u7-m5bh-7wvf"

# ✅ Ensure required folders exist
os.makedirs(MUSIC_FOLDER, exist_ok=True)
os.makedirs(os.path.dirname(GIF_FILE), exist_ok=True)

# ✅ Function to get MP3 list (NO SHUFFLE)
def get_playlist():
    return [os.path.join(MUSIC_FOLDER, f) for f in sorted(os.listdir(MUSIC_FOLDER)) if f.endswith(".mp3")]

# ✅ Function to merge MP3s into one audio file
def merge_audio():
    playlist = get_playlist()
    if not playlist:
        print("❌ No MP3 files found!")
        return None  # ✅ FIXED: Return None to avoid issues later

    audio_output = "merged_audio.mp3"
    concat_file = "playlist.txt"

    with open(concat_file, "w") as f:
        for mp3 in playlist:
            f.write(f"file '{mp3}'\n")

    ffmpeg.input(concat_file, format="concat", safe=0) \
        .output(audio_output, format="mp3", acodec="libmp3lame") \
        .overwrite_output() \
        .run()

    return audio_output if os.path.exists(audio_output) else None  # ✅ FIXED: Ensure file exists

# ✅ Function to generate FLV video with audio
def generate_video():
    audio_file = merge_audio()
    if not audio_file:
        print("❌ Error: No valid audio file generated.")
        return  # ✅ FIXED: Prevent `None` being passed to ffmpeg

    if not os.path.exists(GIF_FILE):
        print("❌ GIF file not found!")
        return

    print("🎥 Generating output.flv with songs in order...")

    video_stream = ffmpeg.input(GIF_FILE, stream_loop=-1).filter("scale", 1280, 720, flags="lanczos")
    audio_stream = ffmpeg.input(audio_file)

    ffmpeg.output(video_stream, audio_stream, OUTPUT_FILE, format="flv", vcodec="libx264", acodec="aac", audio_bitrate="192k", shortest=True) \
        .overwrite_output() \
        .run()

    print("✅ Video generated successfully!")

# ✅ Start Streaming to YouTube RTMP
def start_stream():
    print("🚀 Starting Stream to RTMP...")
    while True:
        if not os.path.exists(OUTPUT_FILE):
            print("❌ output.flv not found, regenerating video...")
            generate_video()
            time.sleep(5)
            continue
        
        try:
            ffmpeg.input(OUTPUT_FILE) \
                .output(RTMP_URL, format="flv", vcodec="libx264", acodec="aac", audio_bitrate="192k") \
                .run(overwrite_output=True)
        except Exception as e:
            print(f"❌ Stream error: {e}")
            time.sleep(5)

# ✅ Watch for File Changes (MP3 & GIF)
class FileChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith(".mp3") or event.src_path.endswith(".gif"):
            print(f"🔄 Detected change in {event.src_path}, regenerating video...")
            generate_video()

# ✅ Start File Watcher
observer = Observer()
observer.schedule(FileChangeHandler(), path=MUSIC_FOLDER, recursive=True)
observer.schedule(FileChangeHandler(), path=os.path.dirname(GIF_FILE), recursive=True)
observer.start()

# ✅ Start RTMP Stream in a Thread
stream_thread = threading.Thread(target=start_stream, daemon=True)
stream_thread.start()

# ✅ Discord Bot for MP3 Upload/Delete
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"🤖 Logged in as {bot.user}")

@bot.command()
async def upload(ctx):
    if not ctx.message.attachments:
        await ctx.send("❌ No file attached!")
        return

    for attachment in ctx.message.attachments:
        if attachment.filename.endswith(".mp3"):
            file_path = os.path.join(MUSIC_FOLDER, attachment.filename)
            await attachment.save(file_path)
            await ctx.send(f"✅ Uploaded: {attachment.filename}")
            generate_video()

@bot.command()
async def delete(ctx, filename):
    file_path = os.path.join(MUSIC_FOLDER, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        await ctx.send(f"✅ Deleted: {filename}")
        generate_video()
    else:
        await ctx.send("❌ File not found!")

@bot.command()
async def list(ctx):
    files = os.listdir(MUSIC_FOLDER)
    if not files:
        await ctx.send("📂 No MP3 files found!")
    else:
        await ctx.send("🎵 Available MP3s:\n" + "\n".join(files))

# ✅ Start Bot & Flask API
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "🎥 24/7 Stream Running"

def run_flask():
    flask_app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    bot.run(BOT_TOKEN)
