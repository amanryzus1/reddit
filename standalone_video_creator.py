"""
mobile_youtube_shorts_processor.py

MOBILE YOUTUBE SHORTS VERSION - Preserves original scale and quality
Creates videos for mobile YouTube Shorts without audio
CROPS to mobile format instead of resizing to maintain original quality
*** NO OVERWRITE VERSION *** - Creates unique filenames to prevent overwriting

Dependencies:
pip install moviepy==1.0.3 opencv-python pillow pyyaml

"""

# ===============================================
# CONFIGURATION - EASY TO MODIFY
# ===============================================
INPUT_DIR = r"E:\nVidiaShadowPlay\for_reddit\others"
OUTPUT_DIR = "processed_backgrounds"
NUMBER_OF_VIDEOS = 8  # Set to 0 or None for NO LIMIT (creates as many as possible)
VIDEO_DURATION_MINUTES = 3  # Duration per video in minutes
# ===============================================

import os
import glob
import random
import gc
from pathlib import Path
from datetime import datetime


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

    # If file doesn't exist, use the original name
    if not output_path.exists():
        return str(output_path)

    # File exists, so create a unique version
    counter = 1
    while True:
        unique_name = f"{base_name}_{counter:03d}{extension}"
        unique_path = Path(output_dir) / unique_name

        if not unique_path.exists():
            print(f"  🔄 File exists, using: {unique_name}")
            return str(unique_path)

        counter += 1

        # Safety limit to prevent infinite loop
        if counter > 999:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            fallback_name = f"{base_name}_{timestamp}{extension}"
            fallback_path = Path(output_dir) / fallback_name
            print(f"  🔄 Using timestamp fallback: {fallback_name}")
            return str(fallback_path)


# ===============================================
# MOBILE YOUTUBE SHORTS PROCESSOR
# ===============================================

class MobileYoutubeShortsProcessor:
    def __init__(self, input_dir, output_dir, target_count=8, target_duration=180):
        """Initialize for mobile YouTube Shorts with configurable settings"""

        if not setup_moviepy_dependencies():
            raise RuntimeError("MoviePy dependencies not properly configured")

        from moviepy.editor import VideoFileClip, concatenate_videoclips
        self.VideoFileClip = VideoFileClip
        self.concatenate_videoclips = concatenate_videoclips

        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Mobile YouTube Shorts specifications
        self.target_duration = target_duration  # Duration in seconds
        self.mobile_aspect_ratio = 9 / 16  # Mobile vertical ratio
        self.target_count = target_count  # Number of videos (0 or None for no limit)

        print(f"📹 Input directory: {self.input_dir}")
        print(f"📁 Output directory: {self.output_dir}")

        if self.target_count == 0 or self.target_count is None:
            print(f"🎯 Target: NO LIMIT - create as many videos as possible")
            print(f"⏱️ Duration: {self.target_duration / 60:.1f} minutes each")
        else:
            print(f"🎯 Target: {self.target_count} videos of {self.target_duration / 60:.1f} minutes each")

        print(f"📱 Format: Mobile YouTube Shorts (9:16 aspect ratio)")
        print(f"⭐ Quality: ORIGINAL SCALE PRESERVED (crop only, no resize)")
        print(f"🔇 Audio: DISABLED")
        print(f"🛡️ Overwrite Protection: ENABLED (creates unique filenames)")

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
            print(f"  {i + 1}. {filename} ({file_size:.1f} MB)")

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
            print("  🔧 Preprocessing (preserving original quality)...")

            # Remove audio only
            if hasattr(clip, 'audio') and clip.audio:
                clip = clip.without_audio()

            # PRESERVE ORIGINAL FPS - don't change it
            print(f"  📊 Keeping original FPS: {clip.fps}")

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
            target_ratio = self.mobile_aspect_ratio  # 9:16 = 0.5625

            print(f"  📊 Original: {original_w}x{original_h} (ratio: {original_ratio:.3f})")
            print(f"  🎯 Target ratio: {target_ratio:.3f} (9:16 mobile)")

            # Remove audio if present
            if hasattr(clip, 'audio') and clip.audio:
                working_clip = clip.without_audio()
            else:
                working_clip = clip.copy()

            if not self.validate_clip(working_clip, "Working clip"):
                return None

            if original_ratio > target_ratio:
                # Video is wider than target - crop width (keep full height)
                new_width = int(original_h * target_ratio)
                x_center = original_w / 2

                print(f"  ✂️ Cropping width: {original_w} → {new_width} (preserving height {original_h})")

                cropped_clip = working_clip.crop(
                    x_center=x_center,
                    width=new_width,
                    height=original_h
                )
            else:
                # Video is taller than target - crop height (keep full width)
                new_height = int(original_w / target_ratio)
                y_center = original_h / 2

                print(f"  ✂️ Cropping height: {original_h} → {new_height} (preserving width {original_w})")

                cropped_clip = working_clip.crop(
                    y_center=y_center,
                    width=original_w,
                    height=new_height
                )

            working_clip.close()

            if not self.validate_clip(cropped_clip, "Final cropped clip"):
                cropped_clip.close()
                return None

            final_w = cropped_clip.w
            final_h = cropped_clip.h
            final_ratio = final_w / final_h

            print(f"  ✅ Final: {final_w}x{final_h} (ratio: {final_ratio:.3f}) - ORIGINAL SCALE PRESERVED")

            return cropped_clip

        except Exception as e:
            print(f"  ❌ Error in mobile crop: {e}")
            return None

    def create_mobile_shorts(self):
        """Create mobile YouTube Shorts preserving original quality with NO OVERWRITE"""
        video_files = self.get_video_files()

        if not video_files:
            print("❌ No video files found in the directory")
            return []

        print(f"\n🎬 Analyzing video durations...")

        video_pool = []
        total_duration = 0

        for video_file in video_files:
            duration = self.analyze_video_duration(video_file)
            if duration > 10:
                video_pool.append({
                    'path': video_file,
                    'duration': duration,
                    'filename': os.path.basename(video_file)
                })
                total_duration += duration
                print(f"  📹 {os.path.basename(video_file)}: {duration:.1f}s ({duration / 60:.1f}m)")

        print(f"\n📊 Total available content: {total_duration:.1f}s ({total_duration / 60:.1f}m)")

        created_videos = []

        # Determine how many videos to create
        if self.target_count == 0 or self.target_count is None:
            # NO LIMIT - create as many as possible
            max_possible = len(video_pool)
            print(f"🚀 NO LIMIT mode: Creating up to {max_possible} videos")
            video_limit = max_possible
        else:
            # Limited number
            video_limit = min(self.target_count, len(video_pool))
            print(f"🎯 Creating {video_limit} videos")

        for video_num in range(1, video_limit + 1):
            print(f"\n🎯 Creating mobile short {video_num}/{video_limit} ({self.target_duration / 60:.1f} minutes)...")

            # Randomly select a source video
            source_video = random.choice(video_pool)
            video_path = source_video['path']
            video_duration = source_video['duration']

            print(f"  📹 Selected: {source_video['filename']} ({video_duration:.1f}s)")

            try:
                # Load the source video
                clip = self.VideoFileClip(video_path)

                if not self.validate_clip(clip, f"Source video {video_num}"):
                    clip.close()
                    continue

                # Preprocess (remove audio, preserve quality)
                clip = self.preprocess_video(clip)

                # Extract segment based on target duration
                if video_duration > self.target_duration:
                    max_start_time = video_duration - self.target_duration
                    start_time = random.uniform(0, max_start_time)
                    end_time = start_time + self.target_duration

                    print(f"  ✂️ Extracting: {start_time:.1f}s - {end_time:.1f}s")
                    segment = clip.subclip(start_time, end_time)
                else:
                    print(f"  📏 Using full video duration ({video_duration:.1f}s)")
                    segment = clip

                if not self.validate_clip(segment, f"Segment {video_num}"):
                    segment.close()
                    clip.close()
                    continue

                # Crop to mobile format (preserving original scale)
                print(f"  📱 Cropping to mobile format (preserving original scale)...")
                gc.collect()

                mobile_clip = self.crop_to_mobile_format(segment)

                if mobile_clip is None:
                    print(f"  ❌ Failed to crop segment {video_num}")
                    segment.close()
                    clip.close()
                    continue

                # Generate UNIQUE filename (NO OVERWRITE)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_filename = f"mobile_short_{video_num:02d}_{timestamp}"
                output_path = generate_unique_filename(self.output_dir, base_filename, ".mp4")
                output_filename = os.path.basename(output_path)

                print(f"  💾 Exporting: {output_filename} (MAXIMUM QUALITY, NO AUDIO, NO OVERWRITE)")

                # Use original FPS and high quality settings
                mobile_clip.write_videofile(
                    str(output_path),
                    fps=mobile_clip.fps,  # PRESERVE ORIGINAL FPS
                    codec='libx264',
                    bitrate='15000k',  # HIGH BITRATE for quality
                    verbose=False,
                    logger=None,
                    audio=False,
                    preset='slow',  # Slower encoding for better quality
                    ffmpeg_params=['-crf', '18']  # High quality CRF setting
                )

                created_videos.append(str(output_path))
                file_size = os.path.getsize(output_path) / (1024 * 1024)
                print(f"  ✅ Created: {output_filename} ({file_size:.1f} MB)")

                # Cleanup
                mobile_clip.close()
                segment.close()
                clip.close()

            except Exception as e:
                print(f"  ❌ Error creating video {video_num}: {e}")
                continue

        return created_videos


def main():
    """Main function for mobile YouTube Shorts creation"""
    print("📱 Mobile YouTube Shorts Processor - NO OVERWRITE VERSION")
    print("=" * 70)

    try:
        if not os.path.exists(INPUT_DIR):
            print(f"❌ Input directory not found: {INPUT_DIR}")
            print(f"💡 Please update INPUT_DIR at the top of the script")
            return

        # Check existing files in output directory
        existing_files = list(Path(OUTPUT_DIR).glob("*.mp4")) if Path(OUTPUT_DIR).exists() else []
        if existing_files:
            print(f"📋 Found {len(existing_files)} existing files in output directory:")
            for existing_file in existing_files[:5]:  # Show first 5
                print(f"  - {existing_file.name}")
            if len(existing_files) > 5:
                print(f"  ... and {len(existing_files) - 5} more")
            print(f"🛡️ Don't worry - new files will have unique names (no overwrite)")

        # Initialize processor with configurations from top
        print("\n🚀 Initializing Mobile YouTube Shorts Processor...")

        target_duration_seconds = VIDEO_DURATION_MINUTES * 60
        processor = MobileYoutubeShortsProcessor(
            INPUT_DIR,
            OUTPUT_DIR,
            target_count=NUMBER_OF_VIDEOS,  # 0 or None for no limit
            target_duration=target_duration_seconds
        )

        # Create mobile shorts
        if NUMBER_OF_VIDEOS == 0 or NUMBER_OF_VIDEOS is None:
            print(f"\n🚀 Creating mobile YouTube Shorts (NO LIMIT)...")
        else:
            print(f"\n🎯 Creating {NUMBER_OF_VIDEOS} mobile YouTube Shorts...")

        created_videos = processor.create_mobile_shorts()

        # Results
        print(f"\n🎉 Processing complete!")
        print(f"📁 Created {len(created_videos)} mobile shorts in '{OUTPUT_DIR}/'")

        if created_videos:
            print("\n📋 Created mobile YouTube Shorts (NO OVERWRITE):")
            total_size = 0

            for i, video_path in enumerate(created_videos, 1):
                filename = os.path.basename(video_path)
                file_size = os.path.getsize(video_path) / (1024 * 1024)
                total_size += file_size
                duration_min = VIDEO_DURATION_MINUTES
                print(f"  {i}. {filename} ({file_size:.1f} MB, {duration_min} min)")

            print(f"\n📊 Total output: {total_size:.1f} MB")
            print(f"\n✅ Ready for mobile YouTube Shorts!")
            print(f"\n📱 Mobile YouTube Shorts features:")
            print("  • ORIGINAL SCALE PRESERVED - no quality loss from resizing")
            print("  • Perfect 9:16 aspect ratio for mobile viewing")
            print(f"  • Each video is exactly {VIDEO_DURATION_MINUTES} minutes")
            print("  • NO AUDIO - ready for custom background music")
            print("  • Maximum quality encoding (CRF 18, 15Mbps bitrate)")
            print("  • Cropped (not resized) to maintain sharpness")
            print("  • 🛡️ NO OVERWRITE - existing files are safe!")

            if NUMBER_OF_VIDEOS == 0 or NUMBER_OF_VIDEOS is None:
                print("  • NO LIMIT mode - created as many videos as possible")

    except Exception as e:
        print(f"\n❌ Critical error: {e}")


if __name__ == "__main__":
    main()
