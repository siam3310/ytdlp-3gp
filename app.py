from flask import Flask, request, jsonify
import yt_dlp, boto3, subprocess, os
from botocore.client import Config
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allow all origins (frontend access)

# Cloudflare R2 config
R2_ENDPOINT_URL = "https://d541eba02ae37eba4719d0d4aa61287c.r2.cloudflarestorage.com/siam"
R2_ACCESS_KEY = "e392355ef4c84c70a3b6cb7751efb6c7"
R2_SECRET_KEY = "f6bbd8f4506f7aefb64a26bf467d17227dd16021af3beae91570f48b1a65d99b"
R2_BUCKET_NAME = "siam"
R2_PUBLIC_URL = "https://pub-d8f5af7f053343ed8295b16a145f6c1c.r2.dev/siam"

r2_client = boto3.client(
    's3',
    endpoint_url=R2_ENDPOINT_URL,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    config=Config(signature_version='s3v4')
)

def download_video(url, output_path="video.mp4"):
    ydl_opts = {
        'format': 'bv*[ext=mp4][height<=480]+ba[ext=m4a]/b[ext=mp4][height<=480]/best',
        'outtmpl': output_path
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def convert_to_3gp(input_file, output_file="video.3gp"):
    vf = "scale=480:-2:force_original_aspect_ratio=decrease,pad=480:360:(ow-iw)/2:(oh-ih)/2"
    subprocess.run([
        "ffmpeg", "-i", input_file,
        "-vf", vf,
        "-c:v", "mpeg4", "-b:v", "300k",
        "-c:a", "aac", "-b:a", "64k",
        "-y", output_file
    ])

def upload_to_r2(file_path, file_name):
    r2_client.upload_file(Filename=file_path, Bucket=R2_BUCKET_NAME, Key=file_name)
    return f"{R2_PUBLIC_URL}/{file_name}"

@app.route("/convert", methods=["POST"])
def convert():
    try:
        data = request.json
        url = data.get("url")
        if not url:
            return jsonify({"status": "error", "message": "URL missing"}), 400

        download_video(url, "video.mp4")
        convert_to_3gp("video.mp4", "video.3gp")
        file_url = upload_to_r2("video.3gp", "video.3gp")

        return jsonify({"status": "success", "url": file_url})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/", methods=["GET"])
def home():
    return "YouTube to 3GP backend is live ✅"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
