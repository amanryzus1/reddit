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

        # PERFECT SYNC PARAMETERS - Final corrected version
        self.text_start_delay = 0.0  # No delay - text starts with voice
        self.text_duration_factor = 0.95  # Use 95% of audio duration for text
        self.text_transition_gap = 0.05  # Minimal gap between text overlays

        # Voice settings - no artificial pauses for natural flow
        self.use_artificial_voice_pauses = False
        self.voice_pause_duration = 0.3  # Only used if artificial pauses enabled

        self.wrap_chars_per_line = 22
        self.words_per_minute = 250
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
        if not self.use_artificial_voice_pauses:
            return
        from pydub import AudioSegment
        silence_duration_ms = int(self.voice_pause_duration * 1000)
        silence_audio = AudioSegment.silent(duration=silence_duration_ms)
        silence_audio.export(self.silence_path, format="wav")
        print(f"✅ Created silence file: {self.silence_path} ({self.voice_pause_duration} seconds)")

    def debug_timing_info(self, overlays_info):
        """Debug method to display detailed timing information"""
        if not self.debug_mode:
            return

        print("\n🔍 DEBUG: Perfect Sync Timing Information")
        print("=" * 70)
        total_duration = 0
        text_chunks = 0

        for i, timing in enumerate(overlays_info):
            if timing['chunk']:  # Only show text chunks
                text_start = timing['start'] + self.text_start_delay
                text_end = text_start + timing['text_duration']
                audio_end = timing['start'] + timing['audio_duration']

                print(
                    f"#{i + 1:2d} | VOICE: {timing['start']:6.2f}s → {audio_end:6.2f}s | TEXT: {text_start:6.2f}s → {text_end:6.2f}s")
                print(f"     Content: {timing['chunk'][:50]}...")
                text_chunks += 1
                total_duration = max(total_duration, audio_end)

        print("=" * 70)
        print(f"📊 Total text chunks: {text_chunks}")
        print(f"📊 Total duration: {total_duration:.2f} seconds")
        print(f"📊 Text start delay: {self.text_start_delay} seconds")
        print(f"📊 Text duration factor: {self.text_duration_factor}")

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

        # Generate perfect sync timing information
        timings = []
        t = 0.0
        from moviepy.editor import AudioFileClip

        for idx, (chunk, wav) in enumerate(zip(chunks, wavfiles)):
            audio_clip = AudioFileClip(str(wav))
            actual_audio_duration = audio_clip.duration

            # Calculate optimized text duration for perfect sync
            text_duration = actual_audio_duration * self.text_duration_factor

            timings.append({
                'chunk': chunk,
                'audio_path': wav,
                'start': t,  # Voice start time
                'text_duration': text_duration,  # Optimized text duration
                'audio_duration': actual_audio_duration
            })

            # Move timeline forward by actual audio duration + small gap
            t += actual_audio_duration + self.text_transition_gap
            audio_clip.close()

        # Debug timing information
        self.debug_timing_info(timings)

        return timings

    def create_overlay_clip(self, text, duration, start, color='yellow'):
        import textwrap
        display_text = textwrap.fill(text, width=self.wrap_chars_per_line)

        # Apply perfect sync timing adjustments - CORRECTED
        adjusted_start = start + self.text_start_delay  # Now 0.0 for simultaneous start
        adjusted_duration = max(0.1, duration)  # Ensure minimum duration

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
            .set_start(adjusted_start).set_duration(adjusted_duration)
        return tc

    def create_video(self, story, video_index=1):
        print(f"\n🎬 Creating PERFECTLY SYNCED Reddit Video {video_index}...")

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
            # Add audio files for voice track
            audio_files_to_use.append(t['audio_path'])

            # Create perfectly timed text overlays
            if t['start'] < bg_duration:
                print(
                    f"PERFECT SYNC - Voice: {t['start']:.2f}s→{t['start'] + t['audio_duration']:.2f}s | Text: {t['start'] + self.text_start_delay:.2f}s→{t['start'] + self.text_start_delay + t['text_duration']:.2f}s")
                print(f"Content: {t['chunk'][:50]}...")

                end_time = min(t['start'] + t['text_duration'] + self.text_start_delay, bg_duration)
                dur = end_time - (t['start'] + self.text_start_delay)

                if dur > 0:
                    final_overlays.append(self.create_overlay_clip(
                        t['chunk'],
                        duration=t['text_duration'],
                        start=t['start'],
                        color='yellow'
                    ))

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
        out_fn = self.output_path / f"shorts_FINAL_SYNC_{video_index:02d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        print(f"💾 Exporting FINAL SYNCED video: {out_fn}")
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
        print("✅ All videos created with FINAL PERFECT voice-text synchronization!")


def main():
    creator = VisibleSyncRedditVideoCreator(
        stories_file="viral_stories_full.yaml",
        background_videos_path="processed_backgrounds/",
        output_path="shorts_fulltext_bigfont/"
    )
    creator.create_multiple_videos(max_videos=1, start_index=0)


if __name__ == "__main__":
    main()
