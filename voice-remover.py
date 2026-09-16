#!/usr/bin/env python3
"""
Voice Remover - Strips vocals from a video/audio file, keeping effects & music.
Uses Demucs (Meta AI) for source separation, called directly as a library
(not via subprocess) so this works correctly once packaged with PyInstaller.
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
        print("Error: ffmpeg not found. Install it and make sure it's on your PATH.")
        sys.exit(1)


def extract_audio(input_path: Path, audio_path: Path):
    """Pull the audio track out of a video file as a WAV."""
    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2",
        str(audio_path)
    ]
    subprocess.run(cmd, check=True)


def run_demucs(audio_path: Path, output_dir: Path) -> Path:
    """
    Run Demucs separation using the Python API directly (no subprocess to
    a separate python3 interpreter -- that interpreter won't have demucs
    installed once this script is packaged into a standalone executable).
    Returns the directory containing the separated stems.
    """
    from demucs.api import Separator, save_audio

    print("Loading Demucs model (first run may take a moment)...")
    separator = Separator(model="htdemucs")

    print("Running separation...")
    origin, separated = separator.separate_audio_file(str(audio_path))

    stems_dir = output_dir / "htdemucs" / audio_path.stem
    stems_dir.mkdir(parents=True, exist_ok=True)

    for stem_name, stem_audio in separated.items():
        stem_path = stems_dir / f"{stem_name}.wav"
        save_audio(stem_audio, str(stem_path), samplerate=separator.samplerate)

    return stems_dir


def combine_non_vocal_stems(stems_dir: Path, output_path: Path):
    """Mix drums + bass + other together into one effects-only track."""
    stem_files = ["drums.wav", "bass.wav", "other.wav"]
    inputs = []
    count = 0
    for stem in stem_files:
        stem_path = stems_dir / stem
        if stem_path.exists():
            inputs.extend(["-i", str(stem_path)])
            count += 1

    if count == 0:
        print("Error: no non-vocal stems found to combine.")
        sys.exit(1)

    filter_str = f"amix=inputs={count}:duration=longest"
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
    stems_dir = run_demucs(extracted_audio, demucs_out)

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
