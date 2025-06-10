import os
import subprocess
from project_manager import ProjectManager

def cut_video_clip(project_id, start_seconds, end_seconds, output_filename):
    """
    Cuts a video clip from the original video using ffmpeg.
    Uses stream copy for speed, so it's very fast and doesn't re-encode.
    """
    try:
        project_path = ProjectManager.get_project_path(project_id)
        input_video = os.path.join(project_path, "original_video.mp4")

        # Create a 'clips' subdirectory within the project folder
        clips_dir = os.path.join(project_path, 'clips')
        os.makedirs(clips_dir, exist_ok=True)

        output_path = os.path.join(clips_dir, output_filename)

        # Check if the source video exists
        if not os.path.exists(input_video):
            raise FileNotFoundError(f"Source video not found: {input_video}")

        # Construct the ffmpeg command
        # -ss: seek to start time
        # -to: go to end time
        # -c copy: use stream copy to avoid re-encoding (very fast)
        # -y: overwrite output file if it exists
        command = [
            'ffmpeg',
            '-i', input_video,         # Specify the input file
            '-ss', str(start_seconds), # Seek to the start time
            '-to', str(end_seconds),   # Cut until this timestamp FROM THE ORIGINAL aVIDEO
            #'-c', 'copy',              # Use stream copy to avoid re-encoding
            '-y',
            output_path
        ]

        print(f"Running ffmpeg command: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        
        # Return the relative path for the frontend to use
        relative_clip_path = os.path.join(project_id, 'clips', output_filename)
        return relative_clip_path

    except FileNotFoundError as e:
        print(f"Error: {e}")
        raise
    except subprocess.CalledProcessError as e:
        print(f"ffmpeg error cutting video for project {project_id}:")
        print(f"Stderr: {e.stderr}")
        print(f"Stdout: {e.stdout}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred in cut_video_clip: {e}")
        raise

