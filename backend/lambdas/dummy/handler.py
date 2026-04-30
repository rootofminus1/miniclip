import os
import subprocess

def lambda_handler(event, context):
    ffmpeg_path = "/opt/bin/ffmpeg"

    return {
        "opt": os.listdir("/opt") if os.path.exists("/opt") else None,
        "opt_bin": os.listdir("/opt/bin") if os.path.exists("/opt/bin") else None,
        "ffmpeg_exists": os.path.exists(ffmpeg_path),
        "ffmpeg_version": subprocess.getoutput(f"{ffmpeg_path} -version") if os.path.exists(ffmpeg_path) else None
    }