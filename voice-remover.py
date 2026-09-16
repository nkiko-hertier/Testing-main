#!/usr/bin/env python3
"""
Voice Remover - Strips vocals from a video/audio file, keeping effects & music.
Uses Demucs (Meta AI) for source separation.
"""

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path


def check_ffmpeg():
    """Make sure ffmpeg is available (needed to extract/remux audio)."""
    if shutil.which("ffmpeg") is None:
        print("Error: ffmpeg not found. Install it with: brew install ffmpeg")
        sys.exit(1)


def extract_audio(input_path: Path, audio_path: Path):
    """Pull the audio track out of a video file as a WAV."""
    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2",
        str(audio_path)
    ]
    subprocess.run(cmd, check=True)


def run_demucs(audio_path: Path, output_dir: Path):
    """Run Demucs separation. Produces vocals.wav, drums.wav, bass.wav, other.wav."""
    cmd = [
        "python3", "-m", "demucs",
        "-n", "htdemucs",          # good general-purpose model
        "-o", str(output_dir),
        str(audio_path)
    ]
    subprocess.run(cmd, check=True)


def combine_non_vocal_stems(stems_dir: Path, output_path: Path):
    """Mix drums + bass + other together into one effects-only track."""
    stem_files = ["drums.wav", "bass.wav", "other.wav"]
    inputs = []
    for stem in stem_files:
        stem_path = stems_dir / stem
        if stem_path.exists():
            inputs.extend(["-i", str(stem_path)])

    filter_str = f"amix=inputs={len(stem_files)}:duration=longest"
    cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", filter_str, str(output_path)]
    subprocess.run(cmd, check=True)


def remux_video(original_video: Path, new_audio: Path, output_path: Path):
    """Attach the effects-only audio back onto the original video."""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(original_video),
        "-i", str(new_audio),
        "-c:v", "copy", "-map", "0:v:0", "-map", "1:a:0",
        "-shortest",
        str(output_path)
    ]
    subprocess.run(cmd, check=True)


def main():
    parser = argparse.ArgumentParser(description="Remove vocals from a video, keep effects/music.")
    parser.add_argument("input", help="Path to input video or audio file")
    parser.add_argument("-o", "--output", help="Output video path", default=None)
    args = parser.parse_args()

    check_ffmpeg()

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"Error: file not found: {input_path}")
        sys.exit(1)

    work_dir = input_path.parent / f"{input_path.stem}_voice_removed_tmp"
    work_dir.mkdir(exist_ok=True)

    extracted_audio = work_dir / "extracted.wav"
    print("Step 1/4: Extracting audio...")
    extract_audio(input_path, extracted_audio)

    demucs_out = work_dir / "demucs_output"
    print("Step 2/4: Separating vocals from effects (this can take a few minutes)...")
    run_demucs(extracted_audio, demucs_out)

    stems_dir = demucs_out / "htdemucs" / extracted_audio.stem
    effects_audio = work_dir / "effects_only.wav"
    print("Step 3/4: Combining effects/music stems...")
    combine_non_vocal_stems(stems_dir, effects_audio)

    output_path = Path(args.output) if args.output else input_path.parent / f"{input_path.stem}_no_voice.mp4"
    print("Step 4/4: Rebuilding video with new audio...")
    remux_video(input_path, effects_audio, output_path)

    shutil.rmtree(work_dir)
    print(f"\nDone! Saved to: {output_path}")


if __name__ == "__main__":
    main()