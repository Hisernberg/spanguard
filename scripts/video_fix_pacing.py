#!/usr/bin/env python3
"""Fix TTS pacing: regenerate slow scenes (pick shortest of N candidates),
trim edge silence on all narration wavs, re-assemble the video, and dump
durations.json for SRT generation."""
import json
import shutil
import subprocess
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from video_render import SCENES, WORK, OUT  # noqa: E402

SLOW = {3, 7}          # scenes whose TTS read too slowly
WPS = 2.4              # expected words/sec


def dur(wav: Path) -> float:
    with wave.open(str(wav)) as w:
        return w.getnframes() / w.getframerate()


def trim(wav: Path) -> None:
    tmp = wav.with_suffix(".trim.wav")
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(wav), "-af",
         "silenceremove=start_periods=1:start_threshold=-45dB,"
         "areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse",
         str(tmp)], capture_output=True, check=True)
    tmp.replace(wav)


def main() -> None:
    # 1. regenerate slow scenes, keep the candidate closest to WPS
    for i in SLOW:
        best, best_d = None, 1e9
        target = len(SCENES[i]["prompt"].split()) / WPS
        for k in range(5):
            c = WORK / f"nar-{i}-cand{k}.wav"
            r = subprocess.run(["z-ai", "tts", "-i", SCENES[i]["prompt"], "-o", str(c)],
                               capture_output=True, text=True, timeout=180)
            if r.returncode != 0 or not c.exists():
                continue
            d = dur(c)
            print(f"scene {i} cand {k}: {d:.1f}s (target {target:.0f}s)", flush=True)
            if abs(d - target) < abs(best_d - target):
                best, best_d = c, d
        if best is None:
            raise RuntimeError(f"tts regeneration failed for scene {i}")
        best.replace(WORK / f"nar-{i}.wav")
        for c in WORK.glob(f"nar-{i}-cand*.wav"):
            c.unlink()

    # 2. trim edge silence everywhere, rebuild duration table
    durations = []
    for i in range(len(SCENES)):
        trim(WORK / f"nar-{i}.wav")
        durations.append(max(dur(WORK / f"nar-{i}.wav") + 0.8, 4.0))
        print(f"scene {i}: {durations[-1]:.1f}s", flush=True)
    total = sum(durations)
    print(f"total: {total:.1f}s = {int(total // 60)}:{int(total % 60):02d}")

    # 3. re-assemble
    (WORK / "nars.txt").write_text(
        "".join(f"file 'nar-{i}.wav'\n" for i in range(len(SCENES))))
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", str(WORK / "nars.txt"), str(WORK / "narration.wav")],
                   capture_output=True, check=True)
    (WORK / "frames.txt").write_text("".join(
        f"file 'frames/f{i:02d}.png'\nduration {durations[i]:.2f}\n"
        for i in range(len(SCENES))) + f"file 'frames/f{len(SCENES) - 1:02d}.png'\n")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(WORK / "frames.txt"),
         "-i", str(WORK / "narration.wav"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-shortest", str(OUT)], capture_output=True, check=True)
    (WORK / "durations.json").write_text(json.dumps(durations))
    print("video:", OUT, f"{OUT.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
