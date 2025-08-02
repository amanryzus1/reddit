"""
mobile_youtube_shorts_processor_FULL_PATHS.py

FULL PATH VERSION - Uses complete paths for FFmpeg installation
Works with FFmpeg installed in C:\ffmpeg\bin
"""

import subprocess
import os
import glob
import random
from pathlib import Path
from datetime import datetime
from multiprocessing import Pool
import time
import json

# Your configuration
INPUT_DIR = r"E:\nVidiaShadowPlay\for_reddit\others"
OUTPUT_DIR = "processed_backgrounds"
VIDEO_DURATION_MINUTES = 3
MIN_VIDEOS_TO_CREATE = 10

# FULL FFMPEG PATHS - Using your installation
FFMPEG_FULL_PATH = r"C:\ffmpeg\bin\ffmpeg.exe"
FFPROBE_FULL_PATH = r"C:\ffmpeg\bin\ffprobe.exe"

def check_ffmpeg_full_paths():
    """Check FFmpeg installation using full paths"""
    try:
        # Check if ffprobe exists at full path
        if not os.path.exists(FFPROBE_FULL_PATH):
            print(f"❌ FFprobe not found at: {FFPROBE_FULL_PATH}")
            return False

        if not os.path.exists(FFMPEG_FULL_PATH):
            print(f"❌ FFmpeg not found at: {FFMPEG_FULL_PATH}")
            return False

        # Test ffprobe with full path
        result = subprocess.run([FFPROBE_FULL_PATH, '-version'],
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ FFprobe working from: {FFPROBE_FULL_PATH}")
            print(f"✅ FFmpeg found at: {FFMPEG_FULL_PATH}")
            return True
        else:
            print(f"❌ FFprobe test failed")
            return False

    except Exception as e:
        print(f"❌ Error checking FFmpeg at full paths: {e}")
        return False

def analyze_video_duration_full_path(video_path):
    """Analyze video duration using full FFprobe path"""
    try:
        # Using full ffprobe path
        cmd = [
            FFPROBE_FULL_PATH,  # Full path to ffprobe
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            str(video_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                duration = float(data['format']['duration'])
                print(f"  📊 {Path(video_path).name}: {duration:.1f}s ({duration/60:.1f}m)")
                return duration
            except (KeyError, ValueError, json.JSONDecodeError) as e:
                print(f"  ❌ {Path(video_path).name}: JSON parse error - {e}")

                # Fallback method using full path
                cmd_fallback = [
                    FFPROBE_FULL_PATH,  # Full path to ffprobe
                    '-i', str(video_path),
                    '-show_entries', 'format=duration',
                    '-v', 'quiet',
                    '-of', 'csv=p=0'
                ]

                result = subprocess.run(cmd_fallback, capture_output=True, text=True, timeout=30)
                if result.returncode == 0 and result.stdout.strip():
                    try:
                        duration = float(result.stdout.strip())
                        print(f"  📊 {Path(video_path).name}: {duration:.1f}s ({duration/60:.1f}m) [fallback]")
                        return duration
                    except ValueError:
                        pass

                return 0
        else:
            print(f"  ❌ {Path(video_path).name}: FFprobe error - {result.stderr}")
            return 0

    except subprocess.TimeoutExpired:
        print(f"  ⏰ {Path(video_path).name}: Analysis timeout")
        return 0
    except Exception as e:
        print(f"  ❌ {Path(video_path).name}: Error - {e}")
        return 0

def process_video_full_path_ffmpeg(task_data):
    """Process video using full FFmpeg path"""
    try:
        worker_id, video_info, output_dir, target_duration = task_data

        video_path = video_info['path']
        video_filename = video_info['filename']
        video_duration = video_info['duration']

        print(f"⚡ Worker {worker_id}: Processing {video_filename}")

        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_name = "".join(c for c in video_filename.split('.')[0][:15] if c.isalnum() or c in ('_',))
        output_filename = f"mobile_{worker_id:02d}_{clean_name}_{timestamp}.mp4"
        output_path = Path(output_dir) / output_filename

        # Calculate random start time for variety
        if video_duration > target_duration:
            max_start = video_duration - target_duration
            start_time = random.uniform(0, max_start)
        else:
            start_time = 0
            target_duration = video_duration  # Use full video if shorter

        # FFmpeg command using FULL PATH
        cmd = [
            FFMPEG_FULL_PATH,                         # FULL PATH to ffmpeg
            '-ss', str(start_time),                   # Start time
            '-i', str(video_path),                    # Input video (full path)
            '-t', str(target_duration),               # Duration
            '-vf', 'crop=ih*9/16:ih',                # Crop to 9:16 aspect ratio
            '-c:v', 'libx264',                       # Video codec
            '-preset', 'fast',                       # Fast encoding
            '-crf', '18',                            # High quality
            '-movflags', '+faststart',               # Web optimization
            '-an',                                   # No audio
            '-y',                                    # Overwrite
            str(output_path)                         # Output path (full path)
        ]

        start_time_process = time.time()

        # Execute FFmpeg command with full path and timeout
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)  # 5 minute timeout

        encoding_time = time.time() - start_time_process

        if result.returncode == 0 and output_path.exists():
            file_size = os.path.getsize(output_path) / (1024 * 1024)
            print(f"  ✅ Worker {worker_id}: SUCCESS - {output_filename} ({file_size:.1f}MB, {encoding_time:.1f}s)")

            return {
                'path': str(output_path),
                'worker': worker_id,
                'size': file_size,
                'filename': output_filename,
                'source_video': video_filename,
                'encoding_time': encoding_time
            }
        else:
            print(f"  ❌ Worker {worker_id}: FFmpeg error")
            if result.stderr:
                print(f"      Error details: {result.stderr[:200]}...")
            return None

    except subprocess.TimeoutExpired:
        print(f"  ⏰ Worker {worker_id}: Processing timeout")
        return None
    except Exception as e:
        print(f"  ❌ Worker {worker_id}: Error - {e}")
        return None

def main():
    """Main function using full paths"""
    print("⚡ Mobile YouTube Shorts Processor - FULL PATHS VERSION")
    print("=" * 70)
    print(f"🔧 Using FFmpeg at: {FFMPEG_FULL_PATH}")
    print(f"🔧 Using FFprobe at: {FFPROBE_FULL_PATH}")

    # Check FFmpeg installation with full paths
    if not check_ffmpeg_full_paths():
        print(f"\n🚨 FFmpeg not found at expected locations!")
        print(f"\n💡 SOLUTION:")
        print(f"1. Verify FFmpeg is installed at: C:\\ffmpeg\\bin\\")
        print(f"2. Download from: https://ffmpeg.org/download.html")
        print(f"3. Extract to C:\\ffmpeg\\")
        print(f"4. Make sure files exist:")
        print(f"   - {FFMPEG_FULL_PATH}")
        print(f"   - {FFPROBE_FULL_PATH}")
        return

    start_time = time.time()

    # Setup output directory with full path
    output_dir = Path(OUTPUT_DIR).resolve()  # Get full path
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dynamic_output_dir = output_dir / f"batch_{timestamp}"
    dynamic_output_dir.mkdir(parents=True, exist_ok=True)

    print(f"📁 Full output path: {dynamic_output_dir}")

    # Get video files with full paths
    input_path = Path(INPUT_DIR).resolve()  # Get full path
    print(f"📹 Full input path: {input_path}")

    video_extensions = ['*.mp4', '*.avi', '*.mov', '*.mkv', '*.wmv', '*.flv', '*.webm', '*.m4v', '*.3gp']
    video_files = []
    for ext in video_extensions:
        found_files = glob.glob(str(input_path / ext))
        video_files.extend(found_files)

    print(f"📁 Found {len(video_files)} video files:")
    for i, vf in enumerate(video_files, 1):
        filename = Path(vf).name
        file_size = os.path.getsize(vf) / (1024 * 1024)
        print(f"  {i:2d}. {filename} ({file_size:.1f} MB)")
        print(f"       Full path: {Path(vf).resolve()}")

    if not video_files:
        print(f"\n❌ No video files found in: {input_path}")
        print("💡 Make sure your video files are in the correct directory")
        return

    # Analyze videos with full path FFprobe
    print(f"\n🔍 Analyzing video durations using full paths...")
    video_pool = []

    for video_file in video_files:
        filename = os.path.basename(video_file)
        full_video_path = Path(video_file).resolve()  # Get full path

        # Check file accessibility with full path
        if not full_video_path.exists():
            print(f"  ❌ {filename}: File not found at {full_video_path}")
            continue

        if not os.access(str(full_video_path), os.R_OK):
            print(f"  ❌ {filename}: No read permission for {full_video_path}")
            continue

        duration = analyze_video_duration_full_path(str(full_video_path))

        if duration >= 30:  # At least 30 seconds
            video_pool.append({
                'path': str(full_video_path),  # Store full path
                'duration': duration,
                'filename': filename
            })
        else:
            if duration > 0:
                print(f"  ⚠️ {filename}: Too short ({duration:.1f}s)")

    print(f"\n📊 Analysis Results:")
    print(f"  Total files scanned: {len(video_files)}")
    print(f"  Suitable videos found: {len(video_pool)}")

    if not video_pool:
        print(f"\n❌ No suitable videos found!")
        print(f"\n🔧 Troubleshooting with full paths:")
        print(f"  1. Check if videos exist at full paths")
        print(f"  2. Verify FFprobe can read the video formats")
        print(f"  3. Test manually: {FFPROBE_FULL_PATH} -i \"[video_path]\"")
        return

    # Determine how many videos to create
    target_videos = min(len(video_pool), MIN_VIDEOS_TO_CREATE)
    print(f"🎯 Creating {target_videos} videos using full paths")

    # Prepare parallel tasks with full paths
    selected_videos = random.sample(video_pool, target_videos) if len(video_pool) > target_videos else video_pool
    parallel_tasks = []

    for worker_id, video_info in enumerate(selected_videos, 1):
        task_data = (
            worker_id,
            video_info,  # Contains full paths
            str(dynamic_output_dir),  # Full output path
            VIDEO_DURATION_MINUTES * 60
        )
        parallel_tasks.append(task_data)

    # Process with full path FFmpeg
    print(f"⚡ Processing {len(parallel_tasks)} videos using full path FFmpeg...")

    with Pool(processes=min(6, len(parallel_tasks))) as pool:
        results = pool.map(process_video_full_path_ffmpeg, parallel_tasks)

    # Results
    successful_results = [r for r in results if r]
    total_time = time.time() - start_time

    print(f"\n🎉 FULL PATH processing complete!")
    print(f"⚡ Total time: {total_time:.1f} seconds")
    print(f"✅ Created {len(successful_results)} videos")

    if successful_results:
        total_size = sum(r['size'] for r in successful_results)
        print(f"📊 Total output: {total_size:.1f} MB")
        print(f"📁 All files in: {dynamic_output_dir}")

        print(f"\n📋 Created videos using full paths:")
        for result in successful_results:
            full_output_path = Path(result['path']).resolve()
            print(f"  📹 {result['filename']} ({result['size']:.1f}MB)")
            print(f"      Full path: {full_output_path}")
            print(f"      Source: {result['source_video']}")

        print(f"\n✅ SUCCESS! All videos created using full paths!")
        print(f"🔧 FFmpeg full path: {FFMPEG_FULL_PATH}")
        print(f"🔧 Output full path: {dynamic_output_dir.resolve()}")

    else:
        print(f"\n❌ No videos were successfully created.")
        print(f"💡 Check the error messages above for troubleshooting")
        print(f"🔧 Verify FFmpeg works manually:")
        print(f"   {FFMPEG_FULL_PATH} -version")

if __name__ == "__main__":
    main()
