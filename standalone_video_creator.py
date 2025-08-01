import os
import random
import yaml
import textwrap
import json
from datetime import datetime
from pathlib import Path
import nltk
from nltk.tokenize import sent_tokenize
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, concatenate_audioclips
from moviepy.config import change_settings

from pydub import AudioSegment  # Make sure pydub is installed

# ----------- 1. IMAGEMAGICK DYNAMIC PATH CHECK ------------
IMAGEMAGICK_PATH = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
if not os.path.exists(IMAGEMAGICK_PATH):
    print(f"❌ ImageMagick not found at: {IMAGEMAGICK_PATH}")
    raise SystemExit("Please verify and correct the ImageMagick path at the top of the script.")
change_settings({"IMAGEMAGICK_BINARY": IMAGEMAGICK_PATH})
print(f"✅ Using ImageMagick at: {IMAGEMAGICK_PATH}")


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


# ------------------------------------------------

class VisibleSyncRedditVideoCreator:
    def __init__(self, stories_file="viral_stories_full.yaml",
                 background_videos_path="processed_backgrounds/",
                 output_path="shorts_fulltext_bigfont/"):
        self.stories_file = Path(stories_file)
        self.background_path = Path(background_videos_path)
        self.output_path = Path(output_path)
        self.temp_path = Path("temp_bigfont")
        self.output_path.mkdir(exist_ok=True, parents=True)
        self.temp_path.mkdir(exist_ok=True, parents=True)
        self.fontsize_sentence = 90
        self.textblock_width = 850
        self.min_sentence_duration = 3.5

        # Text overlay transition time (overlap between text chunks)
        self.text_transition_gap = 0.1  # Small gap between text overlays

        # Voice settings - no artificial pauses, let TTS handle natural rhythm
        self.use_artificial_voice_pauses = False  # Set to True if you want artificial pauses
        self.voice_pause_duration = 0.3  # Only used if use_artificial_voice_pauses = True

        self.wrap_chars_per_line = 22
        self.words_per_minute = 250  # Speed of TTS voice
        self.default_font = "Arial-Bold"

        # Debug mode flag
        self.debug_mode = True

        # Prepare silence file only if needed
        if self.use_artificial_voice_pauses:
            self.silence_path = self.temp_path / "silence.wav"
            self._create_silence_file()
        else:
            self.silence_path = None

    def _create_silence_file(self):
        from pydub import AudioSegment
        silence_duration_ms = int(self.voice_pause_duration * 1000)
        silence_audio = AudioSegment.silent(duration=silence_duration_ms)
        silence_audio.export(self.silence_path, format="wav")
        print(f"✅ Created silence file: {self.silence_path} ({self.voice_pause_duration} seconds)")

        # Debug: Verify silence file was created correctly
        if self.debug_mode:
            self.debug_silence_file()

    def debug_silence_file(self):
        """Debug method to verify silence file creation"""
        if not self.silence_path:
            print("🔍 DEBUG: No silence file created (artificial pauses disabled)")
            return
        try:
            from pydub import AudioSegment
            silence_check = AudioSegment.from_file(self.silence_path)
            actual_duration = len(silence_check) / 1000
            print(f"🔍 DEBUG: Silence file actual duration: {actual_duration:.3f} seconds")
            print(f"🔍 DEBUG: Expected duration: {self.voice_pause_duration} seconds")
            if abs(actual_duration - self.voice_pause_duration) > 0.01:
                print("⚠️  DEBUG: Duration mismatch detected!")
        except Exception as e:
            print(f"❌ DEBUG: Error checking silence file: {e}")

    def debug_timing_info(self, overlays_info):
        """Debug method to display detailed timing information"""
        if not self.debug_mode:
            return

        print("\n🔍 DEBUG: Timing Information")
        print("=" * 60)
        total_duration = 0
        text_chunks = 0
        silence_chunks = 0

        for i, timing in enumerate(overlays_info):
            chunk_type = "SILENCE" if not timing['chunk'] else "TEXT"
            print(
                f"#{i + 1:2d} | {chunk_type:7s} | Start: {timing['start']:6.2f}s | Duration: {timing['duration']:6.2f}s | End: {timing['start'] + timing['duration']:6.2f}s")

            if timing['chunk']:
                print(f"     Text: {timing['chunk'][:50]}...")
                text_chunks += 1
            else:
                silence_chunks += 1

            total_duration = max(total_duration, timing['start'] + timing['duration'])

        print("=" * 60)
        print(f"📊 Total chunks: {len(overlays_info)} (Text: {text_chunks}, Silence: {silence_chunks})")
        print(f"📊 Total duration: {total_duration:.2f} seconds")
        print(f"📊 Text transition gap: {self.text_transition_gap} seconds")
        print(f"📊 Artificial voice pauses: {'Enabled' if self.use_artificial_voice_pauses else 'Disabled'}")
        if self.use_artificial_voice_pauses:
            print(f"📊 Voice pause setting: {self.voice_pause_duration} seconds")

    def debug_audio_files(self, audio_files_to_use):
        """Debug method to check audio file durations"""
        if not self.debug_mode:
            return

        print("\n🔍 DEBUG: Audio Files Information")
        print("=" * 50)
        total_audio_duration = 0

        for i, audio_file in enumerate(audio_files_to_use):
            try:
                audio_clip = AudioFileClip(audio_file)
                duration = audio_clip.duration
                total_audio_duration += duration
                file_type = "SILENCE" if "silence.wav" in audio_file else "TTS"
                print(f"#{i + 1:2d} | {file_type:7s} | {duration:6.2f}s | {Path(audio_file).name}")
                audio_clip.close()
            except Exception as e:
                print(f"❌ Error reading {audio_file}: {e}")

        print("=" * 50)
        print(f"📊 Total audio duration: {total_audio_duration:.2f} seconds")

    def load_stories(self):
        f = self.stories_file
        if f.suffix == ".yaml":
            with open(f, 'r', encoding='utf-8') as h:
                return yaml.safe_load(h)
        elif f.suffix == ".json":
            with open(f, 'r', encoding='utf-8') as h:
                return json.load(h)
        raise Exception(f"Story file suffix not recognized: {f}")

    def get_background_videos(self):
        videos = []
        for ext in ('.mp4', '.avi', '.mov', '.mkv', '.wmv'):
            videos += list(Path(self.background_path).glob(f"*{ext}"))
        if not videos:
            print(f"No videos found in {self.background_path}")
            raise SystemExit("Background video folder empty!")
        return videos

    def split_and_sync_chunks(self, story_text):
        sentences = [s.strip() for s in sent_tokenize(story_text) if s.strip()]
        min_length = 6
        chunks = []
        buffer = ""
        for s in sentences:
            if len(buffer.split()) < min_length:
                buffer = (buffer + " " + s).strip()
            else:
                chunks.append(buffer)
                buffer = s
        if buffer:
            chunks.append(buffer)

        if self.debug_mode:
            print(f"\n🔍 DEBUG: Split into {len(chunks)} text chunks")
            for i, chunk in enumerate(chunks, 1):
                print(f"Chunk {i}: {chunk[:60]}...")

        return [c for c in chunks if c]

    def generate_tts_chunks_and_durations(self, chunks):
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', self.words_per_minute)
        engine.setProperty('volume', 0.93)
        # Select female voice if available
        for voice in engine.getProperty('voices'):
            if 'zira' in voice.name.lower() or 'female' in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break

        wavfiles = []
        for i, chunk in enumerate(chunks, 1):
            chunk_path = self.temp_path / f"tts_chunk_{i}_{datetime.now().strftime('%H%M%S_%f')}.wav"
            engine.save_to_file(chunk, str(chunk_path))
            wavfiles.append(str(chunk_path))
        engine.runAndWait()

        # Generate timing information for perfect sync
        timings = []
        t = 0.0
        from moviepy.editor import AudioFileClip

        # Get silence clip duration if using artificial pauses
        silence_duration = 0
        if self.use_artificial_voice_pauses and self.silence_path:
            silence_clip = AudioFileClip(str(self.silence_path))
            silence_duration = silence_clip.duration
            silence_clip.close()

        for idx, (chunk, wav) in enumerate(zip(chunks, wavfiles)):
            audio_clip = AudioFileClip(str(wav))
            actual_audio_duration = audio_clip.duration

            # Use actual audio duration (no minimum duration enforcement for natural flow)
            display_duration = actual_audio_duration

            timings.append({
                'chunk': chunk,
                'audio_path': wav,
                'start': t,
                'duration': display_duration,
                'audio_duration': actual_audio_duration
            })

            # Move timeline forward by actual audio duration
            t += actual_audio_duration

            # Add artificial pause only if enabled and not the last chunk
            if self.use_artificial_voice_pauses and idx < len(chunks) - 1 and silence_duration > 0:
                timings.append({
                    'chunk': '',
                    'audio_path': str(self.silence_path),
                    'start': t,
                    'duration': silence_duration,
                    'audio_duration': silence_duration
                })
                t += silence_duration
            # Add small natural gap for text transition even without artificial pauses
            elif not self.use_artificial_voice_pauses and idx < len(chunks) - 1:
                t += self.text_transition_gap

            audio_clip.close()

        # Debug timing information
        self.debug_timing_info(timings)

        return timings

    def create_overlay_clip(self, text, duration, start, color='yellow'):
        import textwrap
        display_text = textwrap.fill(text, width=self.wrap_chars_per_line)
        tc = TextClip(
            txt=display_text,
            fontsize=self.fontsize_sentence,
            font=self.default_font,
            color=color,
            stroke_color='black', stroke_width=5,
            method='caption',
            size=(self.textblock_width, None),
            align='center'
        ).set_position(('center', 'center')) \
            .set_start(start).set_duration(duration)
        return tc

    def create_video(self, story, video_index=1):
        print(f"\n🎬 Creating Reddit Mobile-Optimized Video {video_index}...")

        title = story.get('title', '')[:120]
        content = story.get('full_story', '')
        full_script = f"{title}. {content}"
        chunks = self.split_and_sync_chunks(full_script)
        overlays_info = self.generate_tts_chunks_and_durations(chunks)
        if not overlays_info:
            print("❌ No overlays for this story.")
            return None

        videos = self.get_background_videos()
        bg = random.choice(videos)
        bg_clip = VideoFileClip(str(bg))
        bg_duration = bg_clip.duration

        final_overlays = []
        audio_files_to_use = []

        for t in overlays_info:
            # Add all audio files to the audio track for proper sequencing
            if self.use_artificial_voice_pauses or t['chunk']:  # Include silence only if using artificial pauses
                audio_files_to_use.append(t['audio_path'])

            # Create text overlays only for non-empty chunks
            if not t['chunk']:
                continue

            if t['start'] < bg_duration:
                print(
                    f"Overlay: {t['chunk'][:35]}... START: {t['start']:.2f}s DURATION: {t['duration']:.2f}s END: {t['start'] + t['duration']:.2f}s")
                end_time = min(t['start'] + t['duration'], bg_duration)
                dur = end_time - t['start']
                final_overlays.append(self.create_overlay_clip(
                    t['chunk'], duration=dur, start=t['start'], color='yellow',
                ))

        # Debug audio files
        self.debug_audio_files(audio_files_to_use)

        from moviepy.editor import concatenate_audioclips
        overlay_audio_clips = [AudioFileClip(f) for f in audio_files_to_use]
        if overlay_audio_clips:
            narration_clip = concatenate_audioclips(overlay_audio_clips)
        else:
            print("❌ No audio overlays available.")
            return None
        final_duration = min(narration_clip.duration, bg_duration)

        all_clips = [bg_clip.set_duration(final_duration)] + final_overlays
        final = CompositeVideoClip(all_clips).set_audio(narration_clip.subclip(0, final_duration))
        out_fn = self.output_path / f"shorts_big_{video_index:02d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        print(f"💾 Exporting: {out_fn}")
        final.write_videofile(
            str(out_fn),
            fps=30,
            codec='libx264',
            audio_codec='aac',
            bitrate='9000k',
            verbose=False,
        )
        # Clean up
        try:
            narration_clip.close()
            for clip in overlay_audio_clips:
                clip.close()
                # Only remove TTS files, keep silence file for reuse
                if self.silence_path and "silence.wav" not in clip.filename:
                    os.remove(clip.filename)
                elif not self.silence_path:  # Remove all temp files if no silence file
                    try:
                        os.remove(clip.filename)
                    except:
                        pass
            bg_clip.close()
            final.close()
        except Exception:
            pass
        return str(out_fn)

    def create_multiple_videos(self, max_videos=1, start_index=0):
        stories = self.load_stories()
        for idx, story in enumerate(stories[start_index:start_index + max_videos], start=1):
            self.create_video(story, idx)
        print("✅ All videos created with PERFECT voice-text synchronization. Review output for mobile appearance.")


def main():
    creator = VisibleSyncRedditVideoCreator(
        stories_file="viral_stories_full.yaml",
        background_videos_path="processed_backgrounds/",
        output_path="shorts_fulltext_bigfont/"
    )
    creator.create_multiple_videos(max_videos=1, start_index=0)


if __name__ == "__main__":
    main()
cd