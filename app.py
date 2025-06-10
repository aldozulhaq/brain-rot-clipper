from flask import Flask, render_template, request, jsonify, send_from_directory, Response
from project_manager import ProjectManager
from downloader import download_video
from transcriber import transcribe_video
import yt_dlp
import os
import humanize
import requests
from dotenv import load_dotenv
from datetime import datetime
import json
import re
from composer import compose_video_clip
from clipper import cut_video_clip
from werkzeug.utils import secure_filename
import platform
import subprocess

load_dotenv()  # Load environment variables

app = Flask(__name__)

@app.route('/projects', methods=['GET'])
def get_projects():
    """List all available projects."""
    projects = ProjectManager.list_projects()
    return jsonify({"success": True, "projects": projects})

@app.route('/project/<project_id>', methods=['GET'])
def get_project_details(project_id):
    """Get all details for a specific project to load its state."""
    metadata = ProjectManager.get_project_metadata(project_id)
    if not metadata:
        return jsonify({"success": False, "message": "Project not found."})

    metadata['downloaded'] = ProjectManager.file_exists(project_id, "original_video.mp4")
    metadata['transcribed'] = ProjectManager.file_exists(project_id, "transcription.json")
    metadata['viral_detected'] = ProjectManager.file_exists(project_id, "viral_moments.json")
    
    metadata['secondary_asset_file'] = metadata.get('files', {}).get('secondary_asset')
    if metadata['secondary_asset_file'] and not ProjectManager.file_exists(project_id, metadata['secondary_asset_file']):
         metadata['secondary_asset_file'] = None

    clips_dir = os.path.join(ProjectManager.get_project_path(project_id), 'clips')
    existing_clips = []
    if os.path.exists(clips_dir):
        for filename in sorted(os.listdir(clips_dir), reverse=True):
            if filename.endswith('.mp4'):
                title = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ')
                existing_clips.append({
                    "filename": filename,
                    "path": os.path.join(project_id, 'clips', filename).replace(os.path.sep, '/'),
                    "title": title
                })
    metadata['existing_clips'] = existing_clips

    return jsonify({"success": True, "project_data": metadata})

@app.route('/show-in-folder', methods=['POST'])
def show_in_folder():
    data = request.json
    project_id = data.get('project_id')
    if not project_id: return jsonify({"success": False, "message": "Project ID missing."})

    try:
        path = os.path.join(ProjectManager.get_project_path(project_id), 'clips')
        os.makedirs(path, exist_ok=True)
        if platform.system() == "Windows": os.startfile(os.path.realpath(path))
        elif platform.system() == "Darwin": subprocess.run(["open", os.path.realpath(path)])
        else: subprocess.run(["xdg-open", os.path.realpath(path)])
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/delete-clip', methods=['POST'])
def delete_clip():
    data = request.json
    project_id = data.get('project_id')
    filename = data.get('filename')

    if not project_id or not filename:
        return jsonify({"success": False, "message": "Missing parameters."})

    try:
        
        # Security check 1: Ensure the filename doesn't change after sanitizing.
        # This guards against tricky inputs, though we are not using the sanitized version to build the path.
        if secure_filename(filename) != filename:
            # This is a very strict check. A more lenient one might be needed if filenames
            # are expected to have some special characters that secure_filename removes.
            # For now, we assume filenames created by the app are safe.
            print(f"Warning: Filename '{filename}' and secure_filename '{secure_filename(filename)}' differ.")

        project_path = ProjectManager.get_project_path(project_id)
        clip_path = os.path.join(project_path, 'clips', filename)

        # Security check 2: Prevent path traversal (e.g., filename like ../../some_other_file)
        # This is the most important security check.
        if not os.path.realpath(clip_path).startswith(os.path.realpath(project_path)):
             return jsonify({"success": False, "message": "Path traversal attempt detected."})

        if os.path.exists(clip_path):
            os.remove(clip_path)
            return jsonify({"success": True, "message": "Clip deleted."})
        else:
            print(f"Delete failed. Clip not found at path: {clip_path}")
            return jsonify({"success": False, "message": "Clip not found."})
            
    except Exception as e:
        print(f"Error in delete_clip: {e}")
        return jsonify({"success": False, "message": str(e)})

# --- Main Endpoints ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/extract-info', methods=['POST'])
def extract_info():
    data = request.json
    url = data.get('url')
    if not url: return jsonify({"success": False, "message": "No URL provided"})
    
    try:
        ydl_opts = {'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            project = ProjectManager.create_project(info.get('id'), info.get('title'))
            project_id = project['project_id']

            # --- Save extended metadata for persistence ---
            duration = info.get('duration', 0)
            upload_date_str = info.get('upload_date')
            
            extended_meta = {
                "duration_formatted": f"{duration // 60}:{duration % 60:02d}",
                "views_formatted": humanize.intcomma(info.get('view_count', 0)),
                "channel": info.get('uploader', 'Unknown'),
                "upload_date_formatted": datetime.strptime(upload_date_str, '%Y%m%d').strftime('%b %d, %Y') if upload_date_str else "Unknown",
                "resolution": "Unknown",
                "youtube_url": url,
            }

            if 'formats' in info:
                best_format = max([f for f in info['formats'] if f.get('height')], key=lambda x: x.get('height', 0), default=None)
                if best_format:
                    extended_meta['resolution'] = f"{best_format.get('width', '?')}x{best_format.get('height', '?')}"
            
            # Save thumbnail locally
            thumbnail_url = info.get('thumbnail')
            if thumbnail_url:
                thumb_path = os.path.join(ProjectManager.get_project_path(project_id), 'thumbnail.jpg')
                if not os.path.exists(thumb_path):
                    thumb_res = requests.get(thumbnail_url)
                    if thumb_res.status_code == 200:
                        with open(thumb_path, 'wb') as f:
                            f.write(thumb_res.content)
            
            ProjectManager.update_project_metadata(project_id, extended_meta)
            
            return get_project_details(project_id)
            
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/download', methods=['POST'])
def download():
    data = request.json
    url = data.get('url')
    project_id = data.get('project_id')
    
    if not url or not project_id:
        return jsonify({"success": False, "message": "Missing parameters"})
    
    try:
        download_video(url, project_id)
        return jsonify({
            "success": True, 
            "message": "Video downloaded successfully!",
            "downloaded": True
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Download error: {str(e)}"})

@app.route('/transcribe', methods=['POST'])
def transcribe():
    data = request.json
    project_id = data.get('project_id')
    is_redo = data.get('redo', False)  # Check for the redo flag

    if not project_id:
        return jsonify({"success": False, "message": "Project ID missing"})

    if not ProjectManager.file_exists(project_id, "original_video.mp4"):
        return jsonify({"success": False, "message": "Video not downloaded yet"})

    transcription_json_path = os.path.join(ProjectManager.get_project_path(project_id), "transcription.json")
    transcription_txt_path = os.path.join(ProjectManager.get_project_path(project_id), "transcription.txt")

    # If it's a redo request, delete existing files first
    if is_redo:
        if os.path.exists(transcription_json_path): os.remove(transcription_json_path)
        if os.path.exists(transcription_txt_path): os.remove(transcription_txt_path)
    # If it's not a redo and the file already exists, return early
    elif os.path.exists(transcription_json_path):
        return jsonify({"success": True, "message": "Transcription already exists", "transcribed": True})

    from threading import Thread
    Thread(target=transcribe_video, args=(project_id,)).start()
    return jsonify({"success": True, "message": "Transcription started"})

@app.route('/transcription-status/<project_id>')
def transcription_status(project_id):
    if ProjectManager.file_exists(project_id, "transcription.json"):
        return jsonify({"success": True, "transcribed": True})
    return jsonify({"success": True, "transcribed": False})

@app.route('/detect-viral-moments', methods=['POST'])
def detect_viral_moments():
    data = request.json
    project_id = data.get('project_id')
    
    if not project_id:
        return jsonify({"success": False, "message": "Project ID missing"})
    
    transcription_path = os.path.join(ProjectManager.get_project_path(project_id), "transcription.json")
    if not os.path.exists(transcription_path):
        return Response("Transcription not available", status=400)
    
    with open(transcription_path, 'r') as f:
        transcription = f.read()

    prompt = (
        f"""
        Analyze this transcript and identify the most viral-worthy moments for TikTok/short-form content.
        
        TRANSCRIPT:
        {transcription}
        """
        "Identify 5 viral moments with the duration between 15-60 seconds from this transcript suitable for TikTok clips. "
        """
        CRITERIA for viral moments:
        - Funny, shocking, or controversial statements
        - Hot takes or unpopular opinions  
        - Storytelling with dramatic reveals
        - Relatable life experiences
        - Moments that would make people comment/share
        """
        "For each moment:\n"
        "1. Provide exact start time (seconds)\n"
        "2. Provide exact end time (seconds)\n"
        "3. Title (catchy, <8 words)\n"
        "4. Description (why it's viral)\n"
        "5. Confidence score (1-5)\n\n"
        "CRITICAL! Each clip has to be at least 15 seconds long and not cutting context/mid segment!\n"
        "Format response as JSON:\n"
        "{\"clips\": [{\"start\": float, \"end\": float, \"title\": str, \"description\": str, \"confidence\": int}]}\n\n"
    )
    
    headers = {
        "Authorization": f"Bearer {os.getenv('CHUTES_API_TOKEN')}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-ai/DeepSeek-R1-0528",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "stream": True
    }

    try:
        response = requests.post(
            "https://llm.chutes.ai/v1/chat/completions",
            headers=headers,
            json=payload,
            stream=True
        )
        response.raise_for_status()

        def generate_stream():
            full_content = ""
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith('data: '):
                        json_str = decoded_line[6:]
                        if json_str.strip() == '[DONE]': break
                        try:
                            data = json.loads(json_str)
                            delta = data['choices'][0]['delta'].get('content', '')
                            if delta:
                                full_content += delta
                                yield delta
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
            
            try:
                json_match = re.search(r'\{[\s\S]*\}', full_content)
                if json_match:
                    json_content = json.loads(json_match.group(0))
                    ProjectManager.save_viral_moments(project_id, json_content)
                    print(f"Viral moments for {project_id} saved successfully.")
                else:
                    print(f"Could not find valid JSON in AI response for {project_id}.")
            except Exception as e:
                print(f"Error saving viral moments for {project_id}: {e}")

        return Response(generate_stream(), mimetype='text/plain')

    except requests.exceptions.RequestException as e:
        return Response(f"AI API request error: {e}", status=500)
    except Exception as e:
        return Response(f"An unexpected error occurred: {e}", status=500)

@app.route('/cut-clip', methods=['POST'])
def cut_clip_route():
    data = request.json
    project_id, start, end, title = data.get('project_id'), data.get('start'), data.get('end'), data.get('title')

    if not all([project_id, title]) or start is None or end is None:
        return jsonify({"success": False, "message": "Missing required parameters."})

    try:
        safe_title = ProjectManager.sanitize_filename(title)
        output_filename = f"preview_{safe_title}_{int(float(start))}-{int(float(end))}.mp4"
        
        clip_path = cut_video_clip(project_id, float(start), float(end), output_filename)

        return jsonify({"success": True, "message": "Preview clip created!", "clip_path": clip_path.replace(os.path.sep, '/')})
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to cut clip: {str(e)}"})

@app.route('/generate-clip', methods=['POST'])
def generate_clip():
    data = request.json
    project_id, start, end, title, layout = data.get('project_id'), data.get('start'), data.get('end'), data.get('title'), data.get('layout')

    if not all([project_id, title, layout]) or start is None or end is None:
        return jsonify({"success": False, "message": "Missing required parameters."})

    try:
        metadata = ProjectManager.get_project_metadata(project_id)
        if not metadata: return jsonify({"success": False, "message": "Project not found."})

        primary_video_file = metadata.get('files', {}).get('original_video')
        secondary_asset_file = metadata.get('files', {}).get('secondary_asset')

        if layout not in ['full-primary'] and not secondary_asset_file:
            return jsonify({"success": False, "message": "A secondary asset is required for this layout."})
        
        if not primary_video_file:
             return jsonify({"success": False, "message": "Primary video is missing."})
        
        project_path = ProjectManager.get_project_path(project_id)
        primary_video_path = os.path.join(project_path, primary_video_file)
        
        secondary_asset_path = None
        if secondary_asset_file:
            secondary_asset_path = os.path.join(project_path, secondary_asset_file)

        safe_title = ProjectManager.sanitize_filename(title)
        output_filename = f"{safe_title}_{layout}_{int(float(start))}-{int(float(end))}.mp4"

        clip_path = compose_video_clip(project_id, float(start), float(end), layout, output_filename, primary_video_path, secondary_asset_path)
        
        if clip_path:
            return jsonify({"success": True, "clip_path": clip_path.replace(os.path.sep, '/')})
        else:
            raise Exception("Composition failed. Check layout and asset paths.")

    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to generate clip: {str(e)}"})

@app.route('/add-secondary-asset', methods=['POST'])
def add_secondary_asset():
    if 'file' not in request.files: return jsonify({"success": False, "message": "No file part."})
    file = request.files['file']
    project_id = request.form.get('project_id')
    if not project_id: return jsonify({"success": False, "message": "No project ID."})
    if file.filename == '': return jsonify({"success": False, "message": "No file selected."})

    if file:
        filename = secure_filename(file.filename)
        project_path = ProjectManager.get_project_path(project_id)
        file.save(os.path.join(project_path, filename))
        
        metadata = ProjectManager.get_project_metadata(project_id)
        if metadata:
            metadata['files']['secondary_asset'] = filename
            ProjectManager.update_project_metadata(project_id, metadata)
        return jsonify({"success": True, "filename": filename})
        
    return jsonify({"success": False, "message": "File upload failed."})

@app.route('/project-files/<path:filename>')
def project_files(filename):
    return send_from_directory('projects', filename)

if __name__ == '__main__':
    from waitress import serve
    if not os.path.exists("projects"):
        os.makedirs("projects")
    print("Starting production server on http://127.0.0.1:5000")
    serve(app, host='127.0.0.1', port=5000)