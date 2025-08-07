from flask import Flask, render_template, request, jsonify, send_from_directory
from pathlib import Path
import subprocess
import threading
import os
import re
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

DEFAULT_BASE_DIR = Path.home() / "Desktop" / "RenderTemp"
DEFAULT_BASE_DIR.mkdir(parents=True, exist_ok=True)
THUMB_DIR = DEFAULT_BASE_DIR / "temp_thumbs"
THUMB_DIR.mkdir(parents=True, exist_ok=True)
progress_data = {}

@app.route('/')
def index():
    base_dir = DEFAULT_BASE_DIR
    # Remove orphaned thumbnails
    existing_mov_files = {f.stem for f in base_dir.glob("*.mov")}
    for thumb_file in THUMB_DIR.glob("*.jpg"):
        if thumb_file.stem not in existing_mov_files:
            thumb_file.unlink()
    files = []
    for file in base_dir.glob("*.mov"):
        mp4_file = file.with_suffix('.mp4')
        thumb_file = THUMB_DIR / f"{file.stem}.jpg"
        if not thumb_file.exists():
            generate_temp_thumb(file)
        files.append({
            'name': file.name,
            'basename': file.stem,
            'encoded': mp4_file.exists(),
            'mp4': mp4_file.name if mp4_file.exists() else '',
            'thumb': thumb_file.name if thumb_file.exists() else ''
        })
    return render_template('index.html', files=files)

@app.route('/video/<path:filename>')
def serve_video(filename):
    safe_name = secure_filename(filename)

    full_path = DEFAULT_BASE_DIR / safe_name
    if full_path.exists():
        return send_from_directory(DEFAULT_BASE_DIR, safe_name)

    thumb_path = THUMB_DIR / safe_name
    if thumb_path.exists():
        return send_from_directory(THUMB_DIR, safe_name)

    return "File not found", 404

def run_ffmpeg_encode(input_path, output_path, job_id, filename):
    cmd = ['ffmpeg', '-i', str(input_path), '-y']

    # Add time limit if this is a countdown video
    if "countdown" in filename.lower():
        cmd.extend(['-t', '20'])

    cmd.extend([
        '-vf', 'scale=iw/2:ih/2',
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-b:v', '4500k',
        '-maxrate', '65400k',
        '-bufsize', '38000k',
        '-colorspace', '1',
        '-color_primaries', '1',
        '-color_trc', '1',
        str(output_path)
    ])

    print(f"Running FFmpeg command: {' '.join(cmd)}")  # Debugging log
    process = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)

    total_duration = None
    for line in process.stderr:
        print(line)  # Log each line from stderr
        if 'Duration' in line:
            match = re.search(r'Duration: (\d+):(\d+):(\d+).(\d+)', line)
            if match:
                h, m, s, ms = map(int, match.groups())
                total_duration = h * 3600 + m * 60 + s + ms / 100
        if 'time=' in line and total_duration:
            match = re.search(r'time=(\d+):(\d+):(\d+).(\d+)', line)
            if match:
                h, m, s, ms = map(int, match.groups())
                current = h * 3600 + m * 60 + s + ms / 100
                percent = min(100, int((current / total_duration) * 100))
                progress_data[job_id] = {'filename': filename, 'progress': percent}
    process.wait()

    # Add final 100% progress when encoding finishes
    progress_data[job_id] = {'filename': filename, 'progress': 100}

@app.route('/encode_one', methods=['POST'])
def encode_one():
    base_dir = DEFAULT_BASE_DIR
    data = request.get_json()
    filename = data.get('filename')
    if not filename:
        return jsonify({'error': 'Missing filename'}), 400

    input_path = base_dir / filename
    output_path = input_path.with_suffix('.mp4')
    job_id = f"job_{filename}"
    progress_data[job_id] = {'filename': filename, 'progress': 0}

    # Log to confirm the thread starts
    print(f"Starting encoding for {filename}")
    threading.Thread(target=run_ffmpeg_encode, args=(input_path, output_path, job_id, filename)).start()

    return jsonify({'status': 'started'})

@app.route('/progress', methods=['GET'])
def progress():
    return jsonify(progress_data)

@app.route('/export_still', methods=['POST'])
def export_still():
    base_dir = DEFAULT_BASE_DIR
    data = request.get_json()
    filename = data.get('filename')
    timecode = data.get('timecode', '00:00:01')
    if not filename:
        return jsonify({'error': 'Missing filename'}), 400

    basename = Path(filename).stem
    mp4_path = base_dir / f"{basename}.mp4"
    still_path = base_dir / f"{basename}.jpg"

    if not mp4_path.exists():
        return jsonify({'error': 'MP4 not found'}), 400

    cmd = [
        "ffmpeg", "-y", "-ss", timecode, "-i", str(mp4_path),
        "-vframes", "1", str(still_path)
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return jsonify({'status': 'success', 'output': still_path.name})

def generate_temp_thumb(file_path):
    thumb_path = THUMB_DIR / f"{file_path.stem}.jpg"
    if not thumb_path.exists():
        subprocess.run([
            'ffmpeg', '-y', '-ss', '00:00:02', '-i', str(file_path),
            '-vframes', '1', str(thumb_path)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# New delete route to handle file deletion
@app.route('/delete_file', methods=['POST'])
def delete_file():
    data = request.get_json()
    filename = data.get('filename')
    if not filename:
        return jsonify({'error': 'Missing filename'}), 400

    base_dir = DEFAULT_BASE_DIR
    mov_file = base_dir / filename
    mp4_file = base_dir / f"{filename.rsplit('.', 1)[0]}.mp4"

    try:
        if mov_file.exists():
            os.remove(mov_file)
        if mp4_file.exists():
            os.remove(mp4_file)
        return jsonify({'status': 'success', 'message': f'{filename} and its associated .mp4 were deleted successfully.'})
    except Exception as e:
        return jsonify({'error': f'Failed to delete files: {str(e)}'}), 500

# Generate thumbs at startup
if __name__ == '__main__':
    for mov_file in DEFAULT_BASE_DIR.glob("*.mov"):
        generate_temp_thumb(mov_file)

    app.run(host='0.0.0.0', port=5050, debug=True)