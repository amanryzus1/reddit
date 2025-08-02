"""
mobile_youtube_shorts_processor_NO_REPETITION.py

NO REPETITION VERSION - Prevents selecting the same video multiple times
Creates videos for mobile YouTube Shorts without audio using unique source videos

Dependencies:
pip install moviepy==1.0.3 opencv-python pillow pyyaml

"""

# ===============================================
# CONFIGURATION - EASY TO MODIFY
# ===============================================
INPUT_DIR = r"E:\nVidiaShadowPlay\for_reddit\others"
OUTPUT_DIR = "processed_backgrounds"  # Base directory
# Dynamic folder options (choose one):
DYNAMIC_FOLDER_TYPE = "datetime"  # Options: "datetime", "source", "batch", "custom"
CUSTOM_FOLDER_NAME = "genshin_batch_01"  # Only used if DYNAMIC_FOLDER_TYPE = "custom"

NUMBER_OF_VIDEOS = 0  # Set to 0 or None for NO LIMIT
VIDEO_DURATION_MINUTES = 3  # Duration per video in minutes
# ===============================================

import os
import glob
import random
import gc
from pathlib import Path
from datetime import datetime

# ===============================================
# DYNAMIC FOLDER GENERATOR
# ===============================================

def create_dynamic_folder(base_dir, input_dir, folder_type="datetime", custom_name=None):
    """Create a dynamic subfolder inside the base directory"""
    base_path = Path(base_dir)
    base_path.mkdir(exist_ok=True)

    if folder_type == "datetime":
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dynamic_folder = base_path / f"batch_{timestamp}"
    elif folder_type == "source":
        source_name = Path(input_dir).name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        dynamic_folder = base_path / f"{source_name}_{timestamp}"
    elif folder_type == "batch":
        counter = 1
        while True:
            dynamic_folder = base_path / f"batch_{counter:03d}"
            if not dynamic_folder.exists():
                break
            counter += 1
    elif folder_type == "custom":
        if custom_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            dynamic_folder = base_path / f"{custom_name}_{timestamp}"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dynamic_folder = base_path / f"custom_{timestamp}"
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dynamic_folder = base_path / f"output_{timestamp}"

    dynamic_folder.mkdir(exist_ok=True)
    print(f"📁 Created dynamic folder: {dynamic_folder}")
    return str(dynamic_folder)

# ===============================================
# PIL COMPATIBILITY FIX
# ===============================================

def fix_pil_antialias_compatibility():
    """Apply PIL.Image.ANTIALIAS compatibility fix for Pillow 10.0.0+"""
    try:
        import PIL.Image
        if not hasattr(PIL.Image, 'ANTIALIAS'):
            print("🔧 Applying PIL.Image.ANTIALIAS compatibility fix...")
            PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
            print("✅ PIL compatibility fix applied")
        else:
            print("✅ PIL.Image.ANTIALIAS is available")
    except ImportError:
        print("⚠️ PIL not available")

def check_opencv_availability():
    """Check if OpenCV is available (MoviePy prefers OpenCV over PIL)"""
    try:
        import cv2
        print(f"✅ OpenCV available: {cv2.__version__}")
        return True
    except ImportError:
        print("⚠️ OpenCV not available - MoviePy will use PIL")
        print("  Install with: pip install opencv-python")
        return False

def setup_moviepy_dependencies():
    """Setup and check all MoviePy dependencies"""
    print("🔍 Checking MoviePy dependencies...")
    opencv_available = check_opencv_availability()

    if not opencv_available:
        fix_pil_antialias_compatibility()

    try:
        from moviepy.editor import VideoFileClip
        print("✅ MoviePy imports successfully")
        return True
    except Exception as e:
        print(f"❌ MoviePy import failed: {e}")
        return False

# ===============================================
# UNIQUE FILENAME GENERATOR
# ===============================================

def generate_unique_filename(output_dir, base_name, extension=".mp4"):
    """Generate a unique filename that won't overwrite existing files"""
    output_path = Path(output_dir) / f"{base_name}{extension}"

    if not output_path.exists():
        return str(output_path)

    counter = 1
    while True:
        unique_name = f"{base_name}_{counter:03d}{extension}"
        unique_path = Path(output_dir) / unique_name

        if not unique_path.exists():
            print(f"  🔄 File exists, using: {unique_name}")
            return str(unique_path)

        counter += 1

        if counter > 999:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            fallback_name = f"{base_name}_{timestamp}{extension}"
            fallback_path = Path(output_dir) / fallback_name
            print(f"  🔄 Using timestamp fallback: {fallback_name}")
            return str(fallback_path)

# ===============================================
# MOBILE YOUTUBE SHORTS PROCESSOR - NO REPETITION
# ===============================================

class MobileYoutubeShortsProcessorNoRepetition:
    def __init__(self, input_dir, output_dir, target_count=8, target_duration=180):
        """Initialize for mobile YouTube Shorts with NO VIDEO REPETITION"""

        if not setup_moviepy_dependencies():
            raise RuntimeError("MoviePy dependencies not properly configured")

        from moviepy.editor import VideoFileClip, concatenate_videoclips
        self.VideoFileClip = VideoFileClip
        self.concatenate_videoclips = concatenate_videoclips

        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)

        self.target_duration = target_duration
        self.mobile_aspect_ratio = 9/16
        self.target_count = target_count

        print(f"📹 Input directory: {self.input_dir}")
        print(f"📁 Dynamic output directory: {self.output_dir}")

        if self.target_count == 0 or self.target_count is None:
            print(f"🎯 Target: NO LIMIT - create as many videos as possible")
            print(f"⏱️ Duration: {self.target_duration/60:.1f} minutes each")
        else:
            print(f"🎯 Target: {self.target_count} videos of {self.target_duration/60:.1f} minutes each")

        print(f"📱 Format: Mobile YouTube Shorts (9:16 aspect ratio)")
        print(f"⭐ Quality: ORIGINAL SCALE PRESERVED")
        print(f"🔇 Audio: DISABLED")
        print(f"🛡️ Overwrite Protection: ENABLED")
        print(f"🔗 Video Combining: ENABLED")
        print(f"🚫 Video Repetition: PREVENTED (each video used only once)")

    def validate_clip(self, clip, operation_name="operation"):
        """Validate clip before operations"""
        if clip is None:
            print(f"❌ {operation_name}: Clip is None")
            return False

        try:
            duration = clip.duration
            if duration <= 0:
                print(f"❌ {operation_name}: Invalid duration {duration}")
                return False

            test_frame = clip.get_frame(0)
            if test_frame is None:
                print(f"❌ {operation_name}: Cannot access frames")
                return False

            return True
        except Exception as e:
            print(f"❌ {operation_name}: Clip validation failed - {e}")
            return False

    def get_video_files(self):
        """Get all video files from the input directory"""
        video_extensions = ['*.mp4', '*.avi', '*.mov', '*.mkv', '*.wmv', '*.flv', '*.webm']
        video_files = []

        for extension in video_extensions:
            pattern = self.input_dir / extension
            video_files.extend(glob.glob(str(pattern)))

        video_files.sort(key=lambda x: os.path.getctime(x))

        print(f"📁 Found {len(video_files)} video files:")
        for i, file in enumerate(video_files):
            filename = os.path.basename(file)
            file_size = os.path.getsize(file) / (1024 * 1024)
            print(f"  {i+1}. {filename} ({file_size:.1f} MB)")

        return video_files

    def analyze_video_duration(self, video_path):
        """Analyze video duration and return in seconds"""
        try:
            clip = self.VideoFileClip(video_path)
            duration = clip.duration
            clip.close()
            return duration
        except Exception as e:
            print(f"❌ Error analyzing {video_path}: {e}")
            return 0

    def preprocess_video(self, clip):
        """Preprocess video - PRESERVE ORIGINAL QUALITY"""
        try:
            if hasattr(clip, 'audio') and clip.audio:
                clip = clip.without_audio()
            return clip
        except Exception as e:
            print(f"  ⚠️ Preprocessing failed: {e}")
            return clip

    def crop_to_mobile_format(self, clip):
        """Crop to mobile format preserving ORIGINAL SCALE and quality"""
        try:
            if not self.validate_clip(clip, "Mobile crop input"):
                return None

            original_w = clip.w
            original_h = clip.h
            original_ratio = original_w / original_h
            target_ratio = self.mobile_aspect_ratio

            if hasattr(clip, 'audio') and clip.audio:
                working_clip = clip.without_audio()
            else:
                working_clip = clip.copy()

            if not self.validate_clip(working_clip, "Working clip"):
                return None

            if original_ratio > target_ratio:
                new_width = int(original_h * target_ratio)
                x_center = original_w / 2
                cropped_clip = working_clip.crop(
                    x_center=x_center,
                    width=new_width,
                    height=original_h
                )
            else:
                new_height = int(original_w / target_ratio)
                y_center = original_h / 2
                cropped_clip = working_clip.crop(
                    y_center=y_center,
                    width=original_w,
                    height=new_height
                )

            working_clip.close()

            if not self.validate_clip(cropped_clip, "Final cropped clip"):
                cropped_clip.close()
                return None

            return cropped_clip

        except Exception as e:
            print(f"  ❌ Error in mobile crop: {e}")
            return None

    def combine_videos_to_target_duration_no_repeat(self, available_videos):
        """Combine multiple videos to reach target duration WITHOUT REPETITION"""
        combined_clips = []
        total_duration = 0
        used_videos = []

        print(f"  🔗 Combining videos to reach {self.target_duration/60:.1f} minutes (NO REPETITION)...")
        print(f"  📊 Available videos for selection: {len(available_videos)}")

        # Shuffle available videos for randomness
        random.shuffle(available_videos)

        while total_duration < self.target_duration and available_videos:
            video = available_videos.pop(0)  # REMOVE video from pool after selection
            video_path = video['path']
            video_duration = video['duration']

            try:
                print(f"    📹 Loading: {video['filename']} ({video_duration:.1f}s)")
                clip = self.VideoFileClip(video_path)

                if not self.validate_clip(clip, f"Video {video['filename']}"):
                    clip.close()
                    continue

                clip = self.preprocess_video(clip)
                remaining_duration = self.target_duration - total_duration

                if video_duration <= remaining_duration:
                    print(f"    ✅ Using entire video ({video_duration:.1f}s)")
                    combined_clips.append(clip)
                    total_duration += video_duration
                    used_videos.append(video['filename'])
                else:
                    needed_duration = remaining_duration
                    print(f"    ✂️ Using {needed_duration:.1f}s from {video_duration:.1f}s")

                    segment = clip.subclip(0, needed_duration)
                    if self.validate_clip(segment, "Video segment"):
                        combined_clips.append(segment)
                        total_duration += needed_duration
                        used_videos.append(f"{video['filename']} (partial)")
                    else:
                        segment.close()

                    clip.close()
                    break

            except Exception as e:
                print(f"    ❌ Error loading {video['filename']}: {e}")
                continue

        if not combined_clips:
            print(f"    ❌ No valid clips to combine")
            return None, available_videos

        if total_duration < 60:
            print(f"    ⚠️ Combined duration too short ({total_duration:.1f}s), skipping")
            for clip in combined_clips:
                clip.close()
            return None, available_videos

        print(f"    ✅ Combined {len(combined_clips)} clips, total: {total_duration:.1f}s")
        print(f"    🚫 Used videos (won't repeat): {', '.join(used_videos[:3])}{'...' if len(used_videos) > 3 else ''}")
        print(f"    📊 Remaining videos for future use: {len(available_videos)}")

        try:
            if len(combined_clips) == 1:
                final_clip = combined_clips[0]
            else:
                final_clip = self.concatenate_videoclips(combined_clips)

            return final_clip, available_videos

        except Exception as e:
            print(f"    ❌ Error combining clips: {e}")
            for clip in combined_clips:
                clip.close()
            return None, available_videos

    def create_mobile_shorts_no_repetition(self):
        """Create mobile YouTube Shorts with NO VIDEO REPETITION"""
        video_files = self.get_video_files()

        if not video_files:
            print("❌ No video files found in the directory")
            return []

        print(f"\n🎬 Analyzing video durations...")

        # Create initial video pool
        video_pool = []
        total_duration = 0

        for video_file in video_files:
            duration = self.analyze_video_duration(video_file)
            if duration > 5:
                video_pool.append({
                    'path': video_file,
                    'duration': duration,
                    'filename': os.path.basename(video_file)
                })
                total_duration += duration
                print(f"  📹 {os.path.basename(video_file)}: {duration:.1f}s ({duration/60:.1f}m)")

        print(f"\n📊 Total available content: {total_duration:.1f}s ({total_duration/60:.1f}m)")

        # Create a COPY of video pool for processing (preserves original)
        available_videos = video_pool.copy()
        created_videos = []

        if self.target_count == 0 or self.target_count is None:
            estimated_videos = int(total_duration // self.target_duration)
            print(f"🚀 NO LIMIT mode: Can create approximately {estimated_videos} videos")
            video_limit = estimated_videos
        else:
            video_limit = self.target_count
            print(f"🎯 Creating {video_limit} videos")

        for video_num in range(1, video_limit + 1):
            print(f"\n🎯 Creating mobile short {video_num}/{video_limit} ({self.target_duration/60:.1f} minutes)...")

            if not available_videos:
                print(f"  ❌ No more unique videos available for video {video_num}")
                print(f"  💡 All videos have been used. Created {video_num-1} unique videos.")
                break

            # Combine videos without repetition
            combined_clip, remaining_videos = self.combine_videos_to_target_duration_no_repeat(available_videos)
            available_videos = remaining_videos  # Update available videos

            if combined_clip is None:
                print(f"  ❌ Failed to combine videos for segment {video_num}")
                continue

            try:
                print(f"  📱 Cropping to mobile format (preserving original scale)...")
                gc.collect()

                mobile_clip = self.crop_to_mobile_format(combined_clip)

                if mobile_clip is None:
                    print(f"  ❌ Failed to crop combined video {video_num}")
                    combined_clip.close()
                    continue

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_filename = f"mobile_short_{video_num:02d}_{timestamp}"
                output_path = generate_unique_filename(self.output_dir, base_filename, ".mp4")
                output_filename = os.path.basename(output_path)

                print(f"  💾 Exporting: {output_filename} (MAXIMUM QUALITY, NO AUDIO, NO REPETITION)")

                mobile_clip.write_videofile(
                    str(output_path),
                    fps=mobile_clip.fps,
                    codec='libx264',
                    bitrate='15000k',
                    verbose=False,
                    logger=None,
                    audio=False,
                    preset='slow',
                    ffmpeg_params=['-crf', '18']
                )

                created_videos.append(str(output_path))
                file_size = os.path.getsize(output_path) / (1024 * 1024)
                print(f"  ✅ Created: {output_filename} ({file_size:.1f} MB)")

                mobile_clip.close()
                combined_clip.close()

            except Exception as e:
                print(f"  ❌ Error creating video {video_num}: {e}")
                if 'combined_clip' in locals():
                    combined_clip.close()
                if 'mobile_clip' in locals():
                    mobile_clip.close()
                continue

        return created_videos

def main():
    """Main function for mobile YouTube Shorts creation with NO REPETITION"""
    print("📱 Mobile YouTube Shorts Processor - NO REPETITION VERSION")
    print("=" * 75)

    try:
        if not os.path.exists(INPUT_DIR):
            print(f"❌ Input directory not found: {INPUT_DIR}")
            return

        print(f"\n📁 Creating dynamic folder structure...")
        print(f"Base directory: {OUTPUT_DIR}")
        print(f"Dynamic folder type: {DYNAMIC_FOLDER_TYPE}")

        dynamic_output_dir = create_dynamic_folder(
            OUTPUT_DIR,
            INPUT_DIR,
            DYNAMIC_FOLDER_TYPE,
            CUSTOM_FOLDER_NAME
        )

        print("🚀 Initializing Mobile YouTube Shorts Processor...")

        target_duration_seconds = VIDEO_DURATION_MINUTES * 60
        processor = MobileYoutubeShortsProcessorNoRepetition(
            INPUT_DIR,
            dynamic_output_dir,
            target_count=NUMBER_OF_VIDEOS,
            target_duration=target_duration_seconds
        )

        print(f"\n🎯 Creating mobile YouTube Shorts (NO VIDEO REPETITION)...")
        created_videos = processor.create_mobile_shorts_no_repetition()

        print(f"\n🎉 Processing complete!")
        print(f"📁 Created {len(created_videos)} mobile shorts in:")
        print(f"   {dynamic_output_dir}")

        if created_videos:
            print("\n📋 Created mobile YouTube Shorts (NO REPETITION):")
            total_size = 0

            for i, video_path in enumerate(created_videos, 1):
                filename = os.path.basename(video_path)
                file_size = os.path.getsize(video_path) / (1024 * 1024)
                total_size += file_size
                print(f"  {i}. {filename} ({file_size:.1f} MB, {VIDEO_DURATION_MINUTES} min)")

            print(f"\n📊 Total output: {total_size:.1f} MB")
            print(f"\n📁 All files saved in: {Path(dynamic_output_dir).name}")
            print(f"\n✅ Ready for mobile YouTube Shorts!")
            print(f"\n📱 Features:")
            print("  • ✅ COMBINES multiple short videos to reach exactly 3 minutes")
            print("  • ✅ ORIGINAL SCALE PRESERVED")
            print("  • ✅ Perfect 9:16 aspect ratio for mobile")
            print("  • ✅ NO AUDIO")
            print("  • ✅ OVERWRITE PROTECTION ENABLED")
            print("  • ✅ Maximum quality encoding")
            print("  • 🚫 NO VIDEO REPETITION - each source video used only once")

    except Exception as e:
        print(f"\n❌ Critical error: {e}")

if __name__ == "__main__":
    main()
