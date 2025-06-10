import os
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip, vfx, AudioFileClip

def compose_video_clip(project_id, start_time, end_time, layout, output_filename, primary_video_path, secondary_asset_path):
    """
    Cuts clips from source files and composes them into a final 9:16 video
    based on the selected layout.
    """
    # Define target resolution for 9:16
    final_size = (1080, 1920)
    clip_duration = end_time - start_time

    # --- 1. Load Primary Clip (always needed for audio) ---
    primary_clip = VideoFileClip(primary_video_path).subclip(start_time, end_time)

    # --- 2. Load Secondary Clip (if path is provided) ---
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

    # --- 3. Apply Layout Logic ---
    final_clip = None

    if layout in ['primary-top', 'primary-bottom']:
        if not secondary_clip: raise ValueError("Secondary asset is required for this layout.")
        pane_height = final_size[1] // 2
        
        primary_cropped = primary_clip.fx(vfx.crop, x_center=primary_clip.w/2, width=primary_clip.h * (final_size[0]/pane_height))
        primary_resized = primary_cropped.resize(height=pane_height)
        
        secondary_cropped = secondary_clip.fx(vfx.crop, x_center=secondary_clip.w/2, width=secondary_clip.h * (final_size[0]/pane_height))
        secondary_resized = secondary_cropped.resize(height=pane_height)

        if layout == 'primary-top':
            final_clip = CompositeVideoClip([primary_resized.set_position(('center', 0)), secondary_resized.set_position(('center', pane_height))], size=final_size)
        else:
            final_clip = CompositeVideoClip([secondary_resized.set_position(('center', 0)), primary_resized.set_position(('center', pane_height))], size=final_size)

    elif layout == 'primary-small-top':
        if not secondary_clip: raise ValueError("Secondary asset is required for this layout.")
        background_clip_cropped = secondary_clip.fx(vfx.crop, x_center=secondary_clip.w/2, width=secondary_clip.h * (9/16))
        background_clip = background_clip_cropped.resize(final_size)
        
        margin = 70
        small_pane_width = final_size[0] - (margin * 2)
        foreground_clip = primary_clip.resize(width=small_pane_width).set_position(('center', margin))

        final_clip = CompositeVideoClip([background_clip, foreground_clip], size=final_size)
        
    elif layout == 'primary-portrait-fill':
        if not secondary_clip: raise ValueError("Secondary asset is required for this layout.")
        background_clip = primary_clip.resize(final_size)
        
        margin = 50
        floating_frame_width = final_size[0] - (margin * 2)
        foreground_clip = secondary_clip.resize(width=floating_frame_width).set_position(('center', margin))

        final_clip = CompositeVideoClip([background_clip, foreground_clip], size=final_size)

    elif layout == 'full-primary':
        # Crop primary video to 9:16 and resize to fill the screen
        cropped_clip = primary_clip.fx(vfx.crop, x_center=primary_clip.w/2, width=primary_clip.h * (9/16))
        final_clip = cropped_clip.resize(final_size)

    elif layout == 'full-secondary':
        if not secondary_clip: raise ValueError("Secondary asset is required for this layout.")
        # Crop secondary video to 9:16 and resize to fill the screen
        cropped_clip = secondary_clip.fx(vfx.crop, x_center=secondary_clip.w/2, width=secondary_clip.h * (9/16))
        final_clip = cropped_clip.resize(final_size)

    # --- 4. Finalize and Write ---
    if final_clip:
        # Always use audio from the primary clip
        final_clip = final_clip.set_audio(primary_clip.audio)

        project_clips_dir = os.path.join(os.path.dirname(primary_video_path), 'clips')
        os.makedirs(project_clips_dir, exist_ok=True)
        output_path = os.path.join(project_clips_dir, output_filename)
        
        final_clip.write_videofile(output_path, codec='libx264', audio_codec='aac', preset='medium', threads=4)
        
        # Clean up moviepy objects
        primary_clip.close()
        if secondary_clip:
            secondary_clip.close()
        if hasattr(secondary_clip, 'close'): # handles video vs image
            secondary_clip.close()
        final_clip.close()

        return os.path.join(project_id, 'clips', output_filename)

    return None