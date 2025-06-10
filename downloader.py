import os
import yt_dlp
from project_manager import ProjectManager

def download_video(url, project_id):
    """Download a YouTube video to a project folder"""
    project_path = ProjectManager.get_project_path(project_id)
    video_path = os.path.join(project_path, "original_video.mp4")
    
    ydl_opts = {
        'outtmpl': video_path,
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'quiet': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        
    return video_path