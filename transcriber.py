import os
import subprocess
import json
from faster_whisper import WhisperModel
from project_manager import ProjectManager
import time

def extract_audio(video_path, audio_path="audio.wav"):
    """Extract audio from video using ffmpeg"""
    try:
        command = [
            'ffmpeg',
            '-i', video_path,
            '-vn',
            '-acodec', 'pcm_s16le',
            '-ar', '16000',
            '-ac', '1',
            audio_path,
            '-y'
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"FFmpeg error: {result.stderr}")
            return None
        return audio_path
    except Exception as e:
        print(f"Audio extraction error: {e}")
        return None

def transcribe_video(project_id):
    """Transcribe video using faster-whisper"""
    try:
        project_path = ProjectManager.get_project_path(project_id)
        video_path = os.path.join(project_path, "original_video.mp4")
        audio_path = os.path.join(project_path, "temp_audio.wav")
        
        # Extract audio
        print(f"Extracting audio from {video_path}...")
        if not extract_audio(video_path, audio_path):
            return None, "Audio extraction failed"
        
        # Load whisper model
        print("Loading Whisper model...")
        model = WhisperModel("small", device="cpu", compute_type="int8")
        
        print("Starting transcription...")
        start_time = time.time()
        
        # Transcribe audio
        segments, info = model.transcribe(
            audio_path,
            beam_size=5,
            word_timestamps=True
        )
        
        # Process segments
        transcription_segments = []
        full_text = ""
        segment_count = 0
        
        for segment in segments:
            segment_data = {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
                "words": [{"word": w.word, "start": w.start, "end": w.end} for w in segment.words]
            }
            transcription_segments.append(segment_data)
            full_text += segment.text.strip() + " "
            segment_count += 1
            
            # Print progress every 5 segments
            if segment_count % 5 == 0:
                print(f"Transcribed segment {segment_count} ({segment.start:.1f}s - {segment.end:.1f}s)")
        
        # Save transcription
        print("Saving transcription...")
        ProjectManager.save_transcription(project_id, transcription_segments, full_text.strip())
        
        # Clean up temporary audio
        if os.path.exists(audio_path):
            os.remove(audio_path)
        
        duration = time.time() - start_time
        print(f"Transcription completed in {duration:.2f} seconds")
        
        return full_text.strip(), transcription_segments
    except Exception as e:
        print(f"Transcription error: {e}")
        return None, str(e)