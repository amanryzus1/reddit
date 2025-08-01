"""
background_video_processor_final_fix.py
COMPREHENSIVE FIX for PIL.Image ANTIALIAS error + background video processing

Dependencies:
    pip install moviepy==1.0.3 opencv-python pillow pyyaml

OR if you prefer PIL solution:
    pip install moviepy==1.0.3 pillow==9.5.0 pyyaml
"""

import os
import random
from pathlib import Path
from datetime import datetime

# ===============================================
# PIL COMPATIBILITY FIX (Multiple Solutions)
# ===============================================

def fix_pil_antialias_compatibility():
    """Apply PIL.Image.ANTIALIAS compatibility fix for Pillow 10.0.0+"""
    try:
        import PIL.Image
        # Check if ANTIALIAS exists
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
        print("   Install with: pip install opencv-python")
        return False

def setup_moviepy_dependencies():
    """Setup and check all MoviePy dependencies"""
    print("🔍 Checking MoviePy dependencies...")

    # Check OpenCV first (preferred by MoviePy)
    opencv_available = check_opencv_availability()

    # Apply PIL fix if needed
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
# BACKGROUND VIDEO PROCESSOR - FIXED VERSION
# ===============================================

class BackgroundVideoProcessorFixed:
    def __init__(self, input_video_path, output_dir="processed_backgrounds"):
        """Initialize with comprehensive error handling and dependency checks"""

        # Setup dependencies first
        if not setup_moviepy_dependencies():
            raise RuntimeError("MoviePy dependencies not properly configured")

        # Import MoviePy after dependency check
        from moviepy.editor import VideoFileClip
        self.VideoFileClip = VideoFileClip

        self.input_path = Path(input_video_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        print(f"📹 Input video: {self.input_path}")
        print(f"📁 Output directory: {self.output_dir}")

    def check_video_integrity(self):
        """Comprehensive video file integrity check"""
        try:
            if not self.input_path.exists():
                print(f"❌ Video file not found: {self.input_path}")
                return False

            # Check file size
            file_size = self.input_path.stat().st_size
            size_mb = file_size / (1024 * 1024)

            print(f"📊 File size: {size_mb:.2f} MB")

            if file_size < 1024 * 1024:  # Less than 1MB
                print(f"⚠️ Video file seems too small: {size_mb:.2f} MB")
                print("This might indicate a corrupted or incomplete file.")
                return False

            return True

        except Exception as e:
            print(f"❌ Error checking video integrity: {e}")
            return False

    def analyze_video(self):
        """Analyze video with enhanced error handling"""
        if not self.check_video_integrity():
            return None

        try:
            print("🔍 Loading video for analysis...")
            clip = self.VideoFileClip(str(self.input_path))

            # Check duration
            if clip.duration < 1.0:
                print(f"⚠️ WARNING: Video duration is very short ({clip.duration:.2f} seconds)")
                print("This usually indicates a corrupted or incomplete video file.")
                clip.close()
                return None

            print(f"\n📊 Video Analysis:")
            print(f"   Duration: {clip.duration:.1f} seconds ({clip.duration/60:.1f} minutes)")
            print(f"   Resolution: {clip.w}x{clip.h}")
            print(f"   FPS: {clip.fps}")
            print(f"   Aspect ratio: {clip.w/clip.h:.2f}:1")

            # Calculate segments
            segments = int(clip.duration // 45)  # 45-second segments
            print(f"   Can create ~{segments} background segments (45s each)")

            video_info = {
                'duration': clip.duration,
                'width': clip.w,
                'height': clip.h,
                'fps': clip.fps,
                'segments': segments
            }

            clip.close()
            return video_info

        except Exception as e:
            print(f"❌ Error analyzing video: {e}")
            print("\n🔧 This might be due to:")
            print("1. Corrupted video file")
            print("2. Unsupported video format")
            print("3. MoviePy/PIL compatibility issues")
            print("4. Missing video codecs")
            return None

    def convert_to_vertical(self, clip, segment_number):
        """Convert clip to vertical format with enhanced error handling"""
        try:
            target_width = 1080
            target_height = 1920

            print(f"   🔄 Converting to vertical format ({target_width}x{target_height})...")

            # Resize to fit height first
            resized_clip = clip.resize(height=target_height)

            # Crop width if needed
            if resized_clip.w > target_width:
                x_center = resized_clip.w / 2
                cropped_clip = resized_clip.crop(
                    x_center=x_center,
                    width=target_width,
                    height=target_height
                )
            else:
                # If width is smaller, resize to fit width and crop height
                resized_clip = clip.resize(width=target_width)
                if resized_clip.h > target_height:
                    y_center = resized_clip.h / 2
                    cropped_clip = resized_clip.crop(
                        y_center=y_center,
                        width=target_width,
                        height=target_height
                    )
                else:
                    cropped_clip = resized_clip.resize((target_width, target_height))

            # Generate output filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"bg_vertical_{segment_number:02d}_{timestamp}.mp4"
            output_path = self.output_dir / output_filename

            print(f"   💾 Exporting: {output_filename}")

            # Export with optimized settings
            cropped_clip.write_videofile(
                str(output_path),
                fps=30,
                codec='libx264',
                bitrate='6000k',
                verbose=False,
                logger=None,
                audio=False  # Remove audio for background videos
            )

            # Cleanup
            resized_clip.close()
            cropped_clip.close()

            return str(output_path)

        except Exception as e:
            print(f"   ❌ Error converting segment: {e}")
            print(f"   This was likely the PIL.Image.ANTIALIAS error!")
            print(f"   💡 Solution: pip install opencv-python")
            return None

    def create_vertical_backgrounds(self, segment_duration=45, num_segments=3):
        """Create vertical background segments with comprehensive error handling"""
        try:
            print(f"\n🎬 Creating {num_segments} vertical background segments...")

            # Load source video
            print("📹 Loading source video...")
            source_clip = self.VideoFileClip(str(self.input_path))

            # Adjust parameters based on video length
            if source_clip.duration < segment_duration:
                print(f"⚠️ Video too short ({source_clip.duration:.1f}s) for {segment_duration}s segments")
                segment_duration = max(30, source_clip.duration * 0.8)
                print(f"📝 Adjusted segment duration to {segment_duration:.1f}s")

            if source_clip.duration < segment_duration * num_segments:
                max_segments = int(source_clip.duration // segment_duration)
                num_segments = max(1, max_segments)
                print(f"📝 Adjusted number of segments to {num_segments}")

            created_files = []

            for i in range(num_segments):
                print(f"\n📹 Processing segment {i+1}/{num_segments}...")

                # Calculate random start time
                max_start_time = max(0, source_clip.duration - segment_duration)
                start_time = random.uniform(0, max_start_time) if max_start_time > 0 else 0

                print(f"   ⏰ Using segment: {start_time:.1f}s - {start_time + segment_duration:.1f}s")

                # Extract segment
                try:
                    segment = source_clip.subclip(start_time, start_time + segment_duration)
                except Exception as e:
                    print(f"   ❌ Error extracting segment: {e}")
                    continue

                # Convert to vertical
                vertical_segment = self.convert_to_vertical(segment, i+1)

                if vertical_segment:
                    created_files.append(vertical_segment)
                    print(f"   ✅ Successfully created: {Path(vertical_segment).name}")
                else:
                    print(f"   ❌ Failed to create segment {i+1}")

                # Close segment to free memory
                segment.close()

            source_clip.close()
            return created_files

        except Exception as e:
            print(f"❌ Error creating backgrounds: {e}")
            return []

def main():
    """Main function with comprehensive error handling and solutions"""

    print("🎮 Background Video Processor - COMPREHENSIVE FIX VERSION")
    print("=" * 65)

    # Configuration
    INPUT_VIDEO = r"d:\witcher.mp4"  # Fixed path format
    OUTPUT_DIR = "processed_backgrounds"

    try:
        # Initialize processor
        print("🚀 Initializing processor...")
        processor = BackgroundVideoProcessorFixed(INPUT_VIDEO, OUTPUT_DIR)

        # Analyze video
        video_info = processor.analyze_video()
        if not video_info:
            print("\n❌ Cannot process video. Troubleshooting steps:")
            print("\n🔧 SOLUTION 1 (RECOMMENDED): Install OpenCV")
            print("   pip install opencv-python")
            print("   This bypasses the PIL.Image.ANTIALIAS issue entirely!")

            print("\n🔧 SOLUTION 2: Downgrade Pillow")
            print("   pip uninstall pillow")
            print("   pip install pillow==9.5.0")

            print("\n🔧 SOLUTION 3: Complete reinstall")
            print("   pip install moviepy==1.0.3 opencv-python pillow pyyaml")

            return

        # Create backgrounds
        print("\n🎯 Creating vertical background segments...")
        segments = processor.create_vertical_backgrounds(
            segment_duration=45,
            num_segments=3
        )

        # Results
        print(f"\n🎉 Processing complete!")
        print(f"📁 Created {len(segments)} background videos in '{OUTPUT_DIR}/'")

        if segments:
            print("\n📋 Created files:")
            for i, file_path in enumerate(segments, 1):
                filename = os.path.basename(file_path)
                file_size = os.path.getsize(file_path) / (1024 * 1024)
                print(f"   {i}. {filename} ({file_size:.1f} MB)")

            print(f"\n✅ Success! Ready for your Reddit video creator!")
            print(f"   Update your main script:")
            print(f"   BACKGROUND_VIDEO_PATH = \"{OUTPUT_DIR}/\"")

        else:
            print("\n❌ No videos were created.")
            print("\n🚨 MOST LIKELY CAUSE: PIL.Image.ANTIALIAS Error")
            print("\n💡 QUICK FIX:")
            print("   pip install opencv-python")
            print("   Then run this script again!")

    except Exception as e:
        print(f"\n❌ Critical error: {e}")
        print("\n🔧 Try these solutions:")
        print("1. pip install opencv-python")
        print("2. pip install pillow==9.5.0")
        print("3. Check if your video file is corrupted")

if __name__ == "__main__":
    main()
