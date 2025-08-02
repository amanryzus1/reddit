import os
import random
import yaml
import textwrap
import json
import re
from datetime import datetime
from pathlib import Path
import nltk
from nltk.tokenize import sent_tokenize
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, concatenate_audioclips
from moviepy.config import change_settings
from pydub import AudioSegment
import shutil
import atexit
import glob


# ----------- 1. DYNAMIC IMAGEMAGICK PATH DETECTION ------------
def find_imagemagick_path():
    """Dynamically find ImageMagick installation"""
    search_patterns = [
        r"C:\Program Files\ImageMagick*\magick.exe",
        r"C:\Program Files (x86)\ImageMagick*\magick.exe",
        r"C:\ImageMagick*\magick.exe",
    ]

    print("🔍 Searching for ImageMagick...")

    # Search in common directories
    for pattern in search_patterns:
        matches = glob.glob(pattern)
        if matches:
            found_path = matches[0]
            print(f"📍 Found ImageMagick: {found_path}")
            return found_path

    # Try system PATH
    path_magick = shutil.which("magick")
    if path_magick:
        print(f"📍 Found ImageMagick in PATH: {path_magick}")
        return path_magick

    return None


IMAGEMAGICK_PATH = find_imagemagick_path()

if not IMAGEMAGICK_PATH:
    print("❌ ImageMagick not found!")
    raise SystemExit("Please install ImageMagick or add to PATH")

print(f"✅ Using ImageMagick at: {IMAGEMAGICK_PATH}")
change_settings({"IMAGEMAGICK_BINARY": IMAGEMAGICK_PATH})


# ----------- 2. NLTK Punkt Tab Fix -------------
def fix_nltk_dependencies():
    try:
        nltk.data.find('tokenizers/punkt_tab')
    except LookupError:
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')


fix_nltk_dependencies()


# ----------- 3. TEMP FILE CLEANUP MANAGER -------------
class TempFileManager:
    def __init__(self):
        self.temp_folders = set()
        self.temp_files = set()
        atexit.register(self.cleanup_all)

    def register_temp_folder(self, folder_path):
        self.temp_folders.add(Path(folder_path))

    def register_temp_file(self, file_path):
        self.temp_files.add(Path(file_path))

    def cleanup_all(self):
        print(f"\n🧹 Starting temp cleanup...")
        files_cleaned = 0
        folders_cleaned = 0

        for temp_file in list(self.temp_files):
            if temp_file.exists():
                try:
                    temp_file.unlink()
                    files_cleaned += 1
                except:
                    pass

        for temp_folder in list(self.temp_folders):
            if temp_folder.exists():
                try:
                    shutil.rmtree(temp_folder)
                    folders_cleaned += 1
                except:
                    pass

        print(f"✅ Cleanup complete: {files_cleaned} files, {folders_cleaned} folders")


# Global temp file manager
temp_manager = TempFileManager()


class FixedSequentialRedditVideoCreator:
    def __init__(self, stories_file="viral_stories_full.yaml",
                 background_videos_path="processed_backgrounds/batch_20250802_030654",
                 output_path="reddit_shorts/"):
        self.stories_file = Path(stories_file)
        self.background_path = Path(background_videos_path)

        # ========== DATE-WISE FOLDER CREATION ==========
        # Create readable date-wise output folder
        today = datetime.now().strftime("%Y-%m-%d_%H-%M")
        self.output_path = Path(output_path) / f"batch_{today}"
        self.temp_path = Path("temp_sequential")

        # Create directories
        self.output_path.mkdir(exist_ok=True, parents=True)
        self.temp_path.mkdir(exist_ok=True, parents=True)
        temp_manager.register_temp_folder(self.temp_path)

        print(f"📁 Date-wise output folder: {self.output_path}")

        # ========== TEXT & FONT CONFIGURATION ==========
        self.fontsize_sentence = 100  # Large and readable
        self.text_stroke_width = 2  # Clean, minimal outline for contrast without overpowering
        self.text_color = 'white'  # Best overall readability
        self.text_stroke_color = 'black'
        self.default_font = "Anton"  # Tall & bold
        self.textblock_width = 880
        self.wrap_chars_per_line = 20

        # ========== TIMING CONFIGURATION ==========
        self.text_start_delay = -0.15  # Delay before text appears
        self.text_duration_factor = 1.0  # Text display duration multiplier
        self.text_transition_gap = 0.15  # Gap between text chunks
        self.words_per_minute = 230  # TTS speech speed

        # ========== PART INDICATOR CONFIGURATION ==========
        self.part_indicator_color = 'cyan'  # Color for "Part X of Y" text
        self.part_indicator_duration = 2.0  # How long part indicator shows
        self.part_indicator_silence = 2.5  # Silence before main narration starts

        # ========== VIDEO LIMITS ==========
        self.max_stories_total = 1  # Total stories to process
        self.max_videos_per_story = 3  # Max parts per story
        self.max_video_duration = 120  # Max seconds per video (2 minutes)

        # Background video cycling
        self.video_counter = 0

        self.debug_mode = True

        print(f"🚀 FIXED Sequential Video Creator (NO THREADING)")
        print(f"📁 Output: {self.output_path}")
        print(f"🎵 Speech: {self.words_per_minute} WPM")
        print(f"📚 Max stories: {self.max_stories_total}")
        print(f"📺 Max videos per story: {self.max_videos_per_story}")
        print(f"⏰ Max video duration: {self.max_video_duration}s (2 min)")

    def load_stories(self):
        """Load stories and sort by popularity"""
        f = self.stories_file
        try:
            if f.suffix == ".yaml":
                with open(f, 'r', encoding='utf-8') as h:
                    stories = yaml.safe_load(h)
            elif f.suffix == ".json":
                with open(f, 'r', encoding='utf-8') as h:
                    stories = json.load(h)
            else:
                raise Exception(f"Story file suffix not recognized: {f}")

            # Sort by score (popularity)
            stories_with_scores = []
            for story in stories:
                score = story.get('score', 0)
                if isinstance(score, str):
                    try:
                        score = int(score.replace(',', '').replace('k', '000').replace('K', '000'))
                    except:
                        score = 0
                stories_with_scores.append((story, score))

            stories_with_scores.sort(key=lambda x: x[1], reverse=True)
            sorted_stories = [story for story, score in stories_with_scores]

            print(f"📚 Loaded {len(sorted_stories)} total stories")
            return sorted_stories

        except Exception as e:
            print(f"❌ Error loading stories: {e}")
            return []

    def get_background_videos(self):
        videos = []
        for ext in ('.mp4', '.avi', '.mov', '.mkv', '.wmv'):
            videos += list(Path(self.background_path).glob(f"*{ext}"))
        if not videos:
            raise SystemExit("Background video folder empty!")
        print(f"🎬 Found {len(videos)} background videos")
        return videos

    def cycle_background_video(self, background_videos):
        """Cycle through background videos for each new video"""
        bg_video = background_videos[self.video_counter % len(background_videos)]
        self.video_counter += 1
        print(f"🎮 Using background: {bg_video.name} (video #{self.video_counter})")
        return bg_video

    def generate_smart_filename(self, story_title, story_index, part_number=None, total_parts=1):
        """Generate smart filename from story title"""
        title = story_title.lower().strip()

        # Remove Reddit prefixes
        prefixes_to_remove = ['aita for', 'aita', 'tifu by', 'tifu', 'my', 'i', 'a', 'an', 'the']
        for prefix in prefixes_to_remove:
            if title.startswith(prefix):
                title = title[len(prefix):].strip()

        # Extract meaningful words
        words = re.findall(r'\b[a-zA-Z]+\b', title)
        stop_words = {'i', 'me', 'my', 'we', 'you', 'he', 'she', 'it', 'they', 'the', 'and', 'but', 'or', 'for', 'with',
                      'to'}
        meaningful_words = [word for word in words if word not in stop_words and len(word) > 2]

        if len(meaningful_words) < 3:
            meaningful_words = [word for word in words if len(word) > 2][:4]

        selected_words = meaningful_words[:4]
        filename_base = "_".join(selected_words[:4])
        filename_base = re.sub(r'[^\w\-_]', '', filename_base)

        if len(filename_base) > 40:
            filename_base = filename_base[:40]

        if total_parts > 1:
            return f"{filename_base}_{story_index:03d}_part_{part_number:02d}"
        else:
            return f"{filename_base}_{story_index:03d}"

    def split_story_for_2min_limit(self, story):
        """Split story into parts based on 2-minute limit"""
        title = story.get('title', '')
        content = story.get('full_story', '')
        full_script = f"{title}. {content}"

        total_words = len(full_script.split())
        estimated_duration = (total_words * 60) / self.words_per_minute

        print(f"📝 Story: {total_words} words (~{estimated_duration:.1f}s)")

        # If fits in 2 minutes, don't split
        if estimated_duration <= self.max_video_duration:
            print(f"✅ Single video ({estimated_duration:.1f}s ≤ {self.max_video_duration}s)")
            return [full_script]

        # Calculate parts needed (max 3 per story)
        ideal_parts = int(estimated_duration / self.max_video_duration) + 1
        actual_parts = min(ideal_parts, self.max_videos_per_story)

        if ideal_parts > self.max_videos_per_story:
            print(f"⚠️ Would need {ideal_parts} parts, limiting to {self.max_videos_per_story}")

        print(f"📊 Creating {actual_parts} parts for 2-minute limit")

        # Split content into sentences
        sentences = [s.strip() for s in sent_tokenize(content) if s.strip()]
        sentences_per_part = len(sentences) // actual_parts

        parts = []
        for part_num in range(actual_parts):
            if part_num == actual_parts - 1:
                # Last part gets remaining sentences
                part_sentences = sentences[part_num * sentences_per_part:]
            else:
                part_sentences = sentences[part_num * sentences_per_part:(part_num + 1) * sentences_per_part]

            part_content = f"{title}. " + " ".join(part_sentences)
            if part_content.strip():
                parts.append(part_content.strip())

        for i, part in enumerate(parts, 1):
            part_words = len(part.split())
            part_duration = (part_words * 60) / self.words_per_minute
            print(f"   Part {i}: {part_words} words (~{part_duration:.1f}s)")

        return parts

    def split_and_sync_chunks(self, story_text):
        """Split story part into chunks"""
        sentences = [s.strip() for s in sent_tokenize(story_text) if s.strip()]

        min_length = 8
        max_length = 25
        chunks = []
        buffer = ""

        for s in sentences:
            buffer_words = len(buffer.split())
            sentence_words = len(s.split())

            if buffer_words < min_length:
                buffer = (buffer + " " + s).strip()
            elif buffer_words + sentence_words <= max_length:
                buffer = (buffer + " " + s).strip()
            else:
                if buffer:
                    chunks.append(buffer)
                buffer = s

        if buffer:
            chunks.append(buffer)

        print(f"🔍 Split into {len(chunks)} chunks")
        return [c for c in chunks if c]

    def generate_tts_chunks_and_durations(self, chunks):
        """Generate TTS - NO THREADING"""
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', self.words_per_minute)
        engine.setProperty('volume', 0.93)

        # Select female voice
        for voice in engine.getProperty('voices'):
            if voice and hasattr(voice, 'name'):
                if 'zira' in voice.name.lower() or 'female' in voice.name.lower():
                    engine.setProperty('voice', voice.id)
                    break

        # Generate TTS files
        wavfiles = []
        print(f"🎵 Generating TTS for {len(chunks)} chunks at {self.words_per_minute} WPM...")

        for i, chunk in enumerate(chunks, 1):
            chunk_path = self.temp_path / f"tts_chunk_{i}_{datetime.now().strftime('%H%M%S_%f')}.wav"
            engine.save_to_file(chunk, str(chunk_path))
            wavfiles.append(str(chunk_path))
            temp_manager.register_temp_file(chunk_path)

            if i % 5 == 0 or i == len(chunks):
                print(f"🎵 Generated {i}/{len(chunks)} chunks...")

        engine.runAndWait()

        # Generate timing
        timings = []
        t = 0.0
        total_audio_duration = 0

        for chunk, wav in zip(chunks, wavfiles):
            audio_clip = AudioFileClip(str(wav))
            actual_audio_duration = audio_clip.duration
            text_duration = actual_audio_duration * self.text_duration_factor

            timings.append({
                'chunk': chunk,
                'audio_path': wav,
                'start': t,
                'text_duration': text_duration,
                'audio_duration': actual_audio_duration
            })

            t += actual_audio_duration + self.text_transition_gap
            total_audio_duration += actual_audio_duration
            audio_clip.close()

        print(f"✅ Total narration: {total_audio_duration:.1f}s")
        return timings

    def create_overlay_clip(self, text, duration, start, color=None):
        """Create text overlay clip using configurable settings"""
        # Use default color if none specified
        if color is None:
            color = self.text_color

        display_text = textwrap.fill(text, width=self.wrap_chars_per_line)
        adjusted_start = start + self.text_start_delay
        adjusted_duration = max(0.1, duration)

        tc = TextClip(
            txt=display_text,
            fontsize=self.fontsize_sentence,
            font=self.default_font,
            color=color,
            stroke_color=self.text_stroke_color,
            stroke_width=self.text_stroke_width,  # Now configurable
            method='caption',
            size=(self.textblock_width, None),
            align='center'
        ).set_position(('center', 'center')) \
            .set_start(adjusted_start).set_duration(adjusted_duration)
        return tc

    def create_single_video_part(self, story_part, part_number, total_parts, story_index, story_title,
                                 background_videos):
        """Create single video part with cycling background videos"""
        print(f"\n🎬 Creating Story {story_index} - Part {part_number}/{total_parts}")
        print(f"{'=' * 60}")

        # FIXED: Cycle through background videos for each video
        bg_video = self.cycle_background_video(background_videos)

        print(f"📖 Part {part_number}/{total_parts}: {len(story_part.split())} words")

        chunks = self.split_and_sync_chunks(story_part)
        overlays_info = self.generate_tts_chunks_and_durations(chunks)

        if not overlays_info:
            print("❌ No overlays for this part")
            return None

        # Load background video
        bg_clip = VideoFileClip(str(bg_video))
        bg_duration = bg_clip.duration

        # Calculate narration duration
        total_narration_duration = sum(t['audio_duration'] for t in overlays_info) + (
                len(overlays_info) * self.text_transition_gap)
        print(f"📊 Narration: {total_narration_duration:.1f}s")

        # Loop background if needed
        if bg_duration < total_narration_duration:
            print(f"🔄 Looping background to cover {total_narration_duration:.1f}s")
            bg_clip = bg_clip.loop(duration=total_narration_duration + 10)

        # Resize to vertical format
        bg_clip = bg_clip.resize(height=1920)
        if bg_clip.w > 1080:
            bg_clip = bg_clip.crop(x_center=bg_clip.w / 2, width=1080, height=1920)
        else:
            bg_clip = bg_clip.set_position('center').resize(width=1080)

        # Create overlays
        final_overlays = []
        audio_files_to_use = []

        # Add part indicator if multi-part
        if total_parts > 1:
            part_indicator = f"Part {part_number} of {total_parts}"
            part_overlay = self.create_overlay_clip(
                part_indicator,
                duration=self.part_indicator_duration,  # Now configurable
                start=0,
                color=self.part_indicator_color  # Now configurable
            )
            final_overlays.append(part_overlay)

        for i, t in enumerate(overlays_info):
            audio_files_to_use.append(t['audio_path'])

            # Adjust start time for part indicator
            start_time = t['start']
            if total_parts > 1:
                start_time += self.part_indicator_silence  # Now configurable

            print(f"🎯 Chunk {i + 1}: {start_time:.1f}s→{start_time + t['audio_duration']:.1f}s")

            final_overlays.append(self.create_overlay_clip(
                t['chunk'],
                duration=t['text_duration'],
                start=start_time,
                color=self.text_color  # Now configurable
            ))

        # Compose video
        overlay_audio_clips = [AudioFileClip(f) for f in audio_files_to_use]
        narration_clip = concatenate_audioclips(overlay_audio_clips)

        # Handle part indicator audio
        if total_parts > 1:
            silence_duration = self.part_indicator_silence  # Now configurable
            temp_silence_path = self.temp_path / f"silence_{story_index}_{part_number}_{datetime.now().strftime('%H%M%S_%f')}.wav"

            silence_audio = AudioSegment.silent(duration=int(silence_duration * 1000))
            silence_audio.export(str(temp_silence_path), format="wav")
            temp_manager.register_temp_file(temp_silence_path)

            silence_clip = AudioFileClip(str(temp_silence_path))
            full_audio = concatenate_audioclips([silence_clip, narration_clip])
            final_duration = full_audio.duration
        else:
            full_audio = narration_clip
            final_duration = narration_clip.duration

        print(f"🎬 FINAL DURATION: {final_duration:.1f}s ({final_duration / 60:.1f}m)")

        # Check if within 2-minute limit
        if final_duration > self.max_video_duration:
            print(f"⚠️ Warning: Video {final_duration:.1f}s exceeds {self.max_video_duration}s limit")
        else:
            print(f"✅ Video within 2-minute limit")

        all_clips = [bg_clip.set_duration(final_duration)] + final_overlays
        final = CompositeVideoClip(all_clips).set_audio(full_audio)

        # Generate smart filename
        smart_filename = self.generate_smart_filename(story_title, story_index, part_number, total_parts)
        out_fn = self.output_path / f"{smart_filename}.mp4"

        print(f"💾 Exporting: {smart_filename}.mp4")

        final.write_videofile(
            str(out_fn),
            fps=30,
            codec='libx264',
            audio_codec='aac',
            bitrate='8000k',
            verbose=False,
        )

        # Cleanup
        try:
            if total_parts > 1:
                full_audio.close()
                silence_clip.close()

            narration_clip.close()
            for clip in overlay_audio_clips:
                clip.close()
                if os.path.exists(clip.filename):
                    os.remove(clip.filename)
            bg_clip.close()
            final.close()
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")

        print(f"✅ COMPLETED: {smart_filename}.mp4 ({final_duration:.1f}s)")
        return str(out_fn)

    def create_story_videos(self, story, story_index, background_videos):
        """Create all video parts for a single story"""
        print(f"\n🎯 PROCESSING STORY {story_index}")
        print(f"{'=' * 80}")

        title = story.get('title', '')[:120]
        score = story.get('score', 0)

        print(f"📖 Story: {title[:50]}... (Score: {score:,})")

        # Split story based on 2-minute limit
        story_parts = self.split_story_for_2min_limit(story)
        total_parts = len(story_parts)

        if total_parts > 1:
            print(f"📺 Creating {total_parts}-part series (2-min limit)")
        else:
            print(f"📺 Creating single video")

        created_videos = []

        for part_num, story_part in enumerate(story_parts, 1):
            result = self.create_single_video_part(story_part, part_num, total_parts, story_index, title,
                                                   background_videos)
            if result:
                created_videos.append(result)
                print(f"✅ Part {part_num}/{total_parts} completed")
            else:
                print(f"❌ Part {part_num}/{total_parts} failed")

        print(f"🎉 Story {story_index} complete: {len(created_videos)}/{total_parts} parts")
        return created_videos

    def create_limited_videos(self):
        """Create videos with strict limits: 3 stories max, 2-min videos, cycling backgrounds"""
        print(f"\n🚀 CREATING LIMITED VIDEOS FOR TESTING")
        print(f"📚 Max stories: {self.max_stories_total}")
        print(f"📺 Max videos per story: {self.max_videos_per_story}")
        print(f"⏰ Max video duration: {self.max_video_duration}s (2 min)")
        print(f"🎮 Background cycling: ENABLED")
        print(f"{'=' * 80}")

        stories = self.load_stories()
        if not stories:
            print("❌ No stories loaded!")
            return

        background_videos = self.get_background_videos()

        # STRICT LIMIT: Only 3 stories total
        num_stories = min(len(stories), self.max_stories_total)
        selected_stories = stories[:num_stories]

        print(f"📝 Processing EXACTLY {num_stories} stories (max: {self.max_stories_total})")
        print(f"🎮 Will cycle through {len(background_videos)} background videos")

        # Show selected stories
        print(f"\n📋 Selected stories:")
        for i, story in enumerate(selected_stories, 1):
            title = story.get('title', 'Unknown')[:60]
            score = story.get('score', 0)
            print(f"   {i}. {title}... (Score: {score:,})")

        all_videos = []
        start_time = datetime.now()

        # Process each story sequentially
        for idx, story in enumerate(selected_stories, start=1):
            story_videos = self.create_story_videos(story, idx, background_videos)
            all_videos.extend(story_videos)

        end_time = datetime.now()
        creation_time = (end_time - start_time).total_seconds()

        # Cleanup
        temp_manager.cleanup_all()

        # Final summary
        print(f"\n🎉 LIMITED VIDEO CREATION COMPLETE!")
        print(f"{'=' * 80}")
        print(f"📁 Videos: {self.output_path}")
        print(f"⏱️  Time: {creation_time:.1f}s ({creation_time / 60:.1f}m)")
        print(f"📚 Stories processed: {len(selected_stories)}/{self.max_stories_total}")
        print(f"🎥 Total videos created: {len(all_videos)}")

        if all_videos:
            total_duration = 0
            for video_path in all_videos:
                try:
                    video_clip = VideoFileClip(video_path)
                    total_duration += video_clip.duration
                    video_clip.close()
                except:
                    pass

            avg_duration = total_duration / len(all_videos)
            print(f"📊 Avg video duration: {avg_duration:.1f}s ({avg_duration / 60:.1f}m)")

            print(f"\n📁 Created videos:")
            for video in all_videos:
                try:
                    size = Path(video).stat().st_size / (1024 * 1024)
                    duration_info = ""
                    try:
                        clip = VideoFileClip(video)
                        duration_info = f" - {clip.duration:.1f}s"
                        clip.close()
                    except:
                        pass
                    print(f"   • {Path(video).name} ({size:.1f} MB{duration_info})")
                except:
                    print(f"   • {Path(video).name}")

        print(f"\n💡 ALL CONFIGURED Features:")
        print(f"   • ✅ Font size: {self.fontsize_sentence}")
        print(f"   • ✅ Stroke width: {self.text_stroke_width} (thicker)")
        print(f"   • ✅ Text color: {self.text_color}")
        print(f"   • ✅ Speech speed: {self.words_per_minute} WPM")
        print(f"   • ✅ Dynamic ImageMagick detection")
        print(f"   • ✅ Date-wise folders: {self.output_path.name}")
        print(f"   • ✅ Max stories: {self.max_stories_total}")
        print(f"   • ✅ Max video duration: {self.max_video_duration}s")


def main():
    try:
        creator = FixedSequentialRedditVideoCreator(
            stories_file="viral_stories_full.yaml",
            background_videos_path="processed_backgrounds/",
            output_path="reddit_shorts/"
        )

        # Create limited videos for testing
        creator.create_limited_videos()

    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
        temp_manager.cleanup_all()
    except Exception as e:
        print(f"\n💥 Error: {e}")
        temp_manager.cleanup_all()
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
