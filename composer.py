import os
from moviepy.editor import (VideoFileClip, ImageClip, CompositeVideoClip, vfx, 
                            TextClip)
from project_manager import ProjectManager

# --- STYLING AND ANIMATION ---

# Define our eye-catching style
FONT_COLOR = '#FFFF00'  # Bright Yellow
STROKE_COLOR = '#000000' # Black
FONT_SIZE = 90
STROKE_WIDTH = 5
FONT_PATH = 'assets/KOMIKAX_.ttf' # Make sure this font is in the assets folder

def animate_word(clip):
    """
    Animates a TextClip with a "pop" effect.
    - Fades in
    - Starts slightly larger and shrinks to normal size
    """
    # Duration of the pop animation in seconds (e.g., 0.1 seconds)
    pop_duration = min(0.1, clip.duration / 2)

    # Size effect: start at 120% and shrink to 100%
    clip = clip.fx(vfx.resize, lambda t: 1 + 0.2 * (1 - t / pop_duration) if t < pop_duration else 1)
    
    # Fade-in effect:
    clip = clip.crossfadein(pop_duration)
    
    return clip

# --- Main Functions ---

def create_subtitle_clips(project_id, start_time, end_time, final_size, subtitle_y_percent=75):
    transcription_data = ProjectManager.load_transcription(project_id)
    if not transcription_data:
        print("No transcription data found, skipping subtitles.")
        return []

    if not os.path.exists(FONT_PATH):
        print(f"Warning: Font file not found at {FONT_PATH}. Subtitles may not render correctly.")
        font_path = 'Arial-Bold' # Fallback font
    else:
        font_path = FONT_PATH

    all_words = []
    for segment in transcription_data:
        all_words.extend(segment['words'])

    words_in_range = [word for word in all_words if 'start' in word and 'end' in word and word['start'] < end_time and word['end'] > start_time]

    subtitle_clips = []
    print(f"Found {len(words_in_range)} words for subtitles in the given time range.")
    for word_info in words_in_range:
        word_text = word_info['word'].upper()
        word_start = word_info['start']
        word_end = word_info['end']
        
        clip_start = max(0, word_start - start_time)
        clip_duration = (word_end - start_time) - clip_start

        if clip_duration <= 0: continue
        
        position_y = (final_size[1] * (subtitle_y_percent / 100)) - (FONT_SIZE / 2) 
        
        txt_clip = TextClip(word_text, fontsize=FONT_SIZE, color=FONT_COLOR, font=font_path,
                            stroke_color=STROKE_COLOR, stroke_width=STROKE_WIDTH)
        
        txt_clip = txt_clip.set_duration(clip_duration)
        
        # Apply the animation
        animated_clip = animate_word(txt_clip)

        animated_clip = animated_clip.set_position(('center', position_y))
        animated_clip = animated_clip.set_start(clip_start)
        animated_clip = animated_clip.set_duration(clip_duration)
        
        subtitle_clips.append(animated_clip)
        
    return subtitle_clips


def compose_video_clip(project_id, start_time, end_time, layout, output_filename, 
                       primary_video_path, secondary_asset_path, subtitle_y_percent=75):
    """
    Cuts clips from source files, composes them into a final 9:16 video,
    and adds animated subtitles based on the selected layout.
    """
    final_size = (1080, 1920)
    clip_duration = end_time - start_time

    primary_clip = VideoFileClip(primary_video_path).subclip(start_time, end_time)

    secondary_clip = None
    if secondary_asset_path:
        file_ext = os.path.splitext(secondary_asset_path)[1].lower()
        if file_ext in ['.jpg', '.jpeg', '.png']:
            secondary_clip = ImageClip(secondary_asset_path).set_duration(clip_duration)
        else:
            secondary_clip_full = VideoFileClip(secondary_asset_path)
            if secondary_clip_full.duration < clip_duration:
                secondary_clip = secondary_clip_full.fx(vfx.loop, duration=clip_duration)
            else:
                secondary_clip = secondary_clip_full.subclip(0, clip_duration)

    composition_layers = []

    if layout in ['primary-top', 'primary-bottom']:
        if not secondary_clip: raise ValueError("Secondary asset is required for this layout.")
        pane_height = final_size[1] // 2
        
        primary_cropped = primary_clip.fx(vfx.crop, x_center=primary_clip.w/2, width=primary_clip.h * (final_size[0]/pane_height))
        primary_resized = primary_cropped.resize(height=pane_height)
        
        secondary_cropped = secondary_clip.fx(vfx.crop, x_center=secondary_clip.w/2, width=secondary_clip.h * (final_size[0]/pane_height))
        secondary_resized = secondary_cropped.resize(height=pane_height)

        if layout == 'primary-top':
            composition_layers.extend([
                primary_resized.set_position(('center', 0)), 
                secondary_resized.set_position(('center', pane_height))
            ])
        else:
            composition_layers.extend([
                secondary_resized.set_position(('center', 0)), 
                primary_resized.set_position(('center', pane_height))
            ])

    elif layout == 'primary-small-top':
        if not secondary_clip: raise ValueError("Secondary asset is required for this layout.")
        background_clip_cropped = secondary_clip.fx(vfx.crop, x_center=secondary_clip.w/2, width=secondary_clip.h * (9/16))
        background_clip = background_clip_cropped.resize(final_size)
        
        margin = 70
        small_pane_width = final_size[0] - (margin * 2)
        foreground_clip = primary_clip.resize(width=small_pane_width).set_position(('center', margin))
        composition_layers.extend([background_clip, foreground_clip])
        
    elif layout == 'primary-portrait-fill':
        if not secondary_clip: raise ValueError("Secondary asset is required for this layout.")
        background_clip = primary_clip.resize(final_size)
        
        margin = 50
        floating_frame_width = final_size[0] - (margin * 2)
        foreground_clip = secondary_clip.resize(width=floating_frame_width).set_position(('center', margin))
        composition_layers.extend([background_clip, foreground_clip])

    elif layout == 'full-primary':
        cropped_clip = primary_clip.fx(vfx.crop, x_center=primary_clip.w/2, width=primary_clip.h * (9/16))
        composition_layers.append(cropped_clip.resize(final_size))

    elif layout == 'full-secondary':
        if not secondary_clip: raise ValueError("Secondary asset is required for this layout.")
        cropped_clip = secondary_clip.fx(vfx.crop, x_center=secondary_clip.w/2, width=secondary_clip.h * (9/16))
        composition_layers.append(cropped_clip.resize(final_size))

    subtitle_clips = create_subtitle_clips(project_id, start_time, end_time, final_size, subtitle_y_percent)
    composition_layers.extend(subtitle_clips)

    if composition_layers:
        final_clip = CompositeVideoClip(composition_layers, size=final_size).set_duration(clip_duration)
        final_clip.audio = primary_clip.audio

        project_clips_dir = os.path.join(os.path.dirname(primary_video_path), 'clips')
        os.makedirs(project_clips_dir, exist_ok=True)
        output_path = os.path.join(project_clips_dir, output_filename)
        
        print(f"Writing final clip to {output_path}...")
        final_clip.write_videofile(output_path, codec='libx264', audio_codec='aac', preset='medium', threads=4)
        
        primary_clip.close()
        if secondary_clip and hasattr(secondary_clip, 'close'):
            secondary_clip.close()
        final_clip.close()

        return os.path.join(project_id, 'clips', output_filename)

    return None