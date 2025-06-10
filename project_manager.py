import os
import json
import re
from datetime import datetime

PROJECTS_DIR = "projects"

class ProjectManager:
    @staticmethod
    def list_projects():
        """Scans the projects directory and returns a list of project info."""
        projects = []
        if not os.path.exists(PROJECTS_DIR):
            return []
            
        for project_id in os.listdir(PROJECTS_DIR):
            project_path = os.path.join(PROJECTS_DIR, project_id)
            metadata_path = os.path.join(project_path, "metadata.json")
            if os.path.isdir(project_path) and os.path.exists(metadata_path):
                try:
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                        projects.append({
                            "project_id": metadata.get("project_id"),
                            "title": metadata.get("title", "Untitled Project"),
                            "created_at": metadata.get("created_at")
                        })
                except (json.JSONDecodeError, KeyError):
                    print(f"Warning: Could not read metadata for {project_id}")
        
        # Sort projects by creation date, newest first
        projects.sort(key=lambda p: p.get('created_at', ''), reverse=True)
        return projects

    @staticmethod
    def sanitize_filename(name):
        """Remove invalid characters from filenames"""
        return re.sub(r'[\\/*?:"<>|]', "", name).strip()

    @staticmethod
    def create_project(video_id, title):
        """Create a new project folder for a video"""
        safe_title = ProjectManager.sanitize_filename(title)[:50]
        project_id = f"{safe_title}_{video_id}"
        project_path = os.path.join(PROJECTS_DIR, project_id)
        
        os.makedirs(project_path, exist_ok=True)
        
        metadata_path = os.path.join(project_path, "metadata.json")
        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                return json.load(f)
        
        metadata = {
            "project_id": project_id,
            "video_id": video_id,
            "title": title,
            "created_at": datetime.now().isoformat(),
            "files": {
                "original_video": "original_video.mp4",
                "transcription_json": "transcription.json",
                "transcription_txt": "transcription.txt",
                "viral_moments": "viral_moments.json"
            }
        }
        
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
            
        return metadata
    
    @staticmethod
    def save_viral_moments(project_id, moments):
        """Save viral moments to a project"""
        project_path = os.path.join(PROJECTS_DIR, project_id)
        with open(os.path.join(project_path, "viral_moments.json"), "w") as f:
            json.dump(moments, f, indent=2)

    @staticmethod
    def get_project_path(project_id):
        """Get the absolute path to a project folder"""
        return os.path.join(PROJECTS_DIR, project_id)

    @staticmethod
    def get_project_metadata(project_id):
        """Get metadata for a project"""
        metadata_path = os.path.join(PROJECTS_DIR, project_id, "metadata.json")
        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                return json.load(f)
        return None

    @staticmethod
    def file_exists(project_id, filename):
        """Check if a file exists in a project"""
        if not filename: return False
        file_path = os.path.join(PROJECTS_DIR, project_id, filename)
        return os.path.exists(file_path)

    @staticmethod
    def save_transcription(project_id, segments, full_text):
        """Save transcription to a project"""
        project_path = os.path.join(PROJECTS_DIR, project_id)
        
        with open(os.path.join(project_path, "transcription.json"), "w") as f:
            json.dump(segments, f, indent=2)
        
        with open(os.path.join(project_path, "transcription.txt"), "w") as f:
            f.write(full_text)
            
        return True
    
    @staticmethod
    def update_project_metadata(project_id, new_data):
        """Update metadata for a project."""
        metadata_path = os.path.join(PROJECTS_DIR, project_id, "metadata.json")
        if not os.path.exists(metadata_path):
            return None 

        with open(metadata_path, "r+") as f:
            metadata = json.load(f)
            metadata.update(new_data)
            f.seek(0)
            json.dump(metadata, f, indent=2)
            f.truncate()
        return metadata