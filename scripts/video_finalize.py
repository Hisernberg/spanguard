#!/usr/bin/env python3
"""Final assembly + subtitles + thumbnail.

1. Re-mux with exact A/V alignment: 0.8 s silence between narration scenes, frame
   durations matched (the original renderer drifted audio 0.8 s per scene early).
2. Emit SRT + VTT from chunk offsets (chunks.json) — one cue per TTS chunk.
3. Render a 1280x720 YouTube thumbnail.
"""
import json
import subprocess
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from video_render import SCENES, WORK, OUT, W, H  # noqa: E402

YT = Path("/home/z/my-project/download/yt-package")
PAUSE = 0.5


def dur(wav: Path) -> float:
    with wave.open(str(wav)) as w:
        return w.getnframes() / w.getframerate()


def wav_params(wav: Path) -> tuple:
    with wave.open(str(wav)) as w:
        return w.getframerate(), w.getnchannels(), w.getsampwidth()


def make_silence(path: Path, params: tuple) -> None:
    rate, ch, sw = params
    with wave.open(str(path), "wb") as w:
        w.setframerate(rate)
        w.setnchannels(ch)
        w.setsampwidth(sw)
        w.writeframes(b"\x00" * int(rate * PAUSE) * ch * sw)


def remux(state: dict) -> float:
    durations = state["durations"]
    rate, ch, sw = wav_params(WORK / "nar-0.wav")
    make_silence(WORK / "sil.wav", (rate, ch, sw))
    lines = []
    for i in range(len(SCENES)):
        lines.append(f"file 'nar-{i}.wav'")
        if i < len(SCENES) - 1:
            lines.append("file 'sil.wav'")
    (WORK / "nars.txt").write_text("\n".join(lines) + "\n")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", str(WORK / "nars.txt"), str(WORK / "narration.wav")],
                   capture_output=True, check=True)
    (WORK / "frames.txt").write_text("".join(
        f"file 'frames/f{i:02d}.png'\nduration {durations[str(i)] + PAUSE:.2f}\n"
        for i in range(len(SCENES))) + f"file 'frames/f{len(SCENES) - 1:02d}.png'\n")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(WORK / "frames.txt"),
         "-i", str(WORK / "narration.wav"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-r", "10", "-t", "174.45", str(OUT)], capture_output=True, check=True)
    return dur_of_video()


def dur_of_video() -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(OUT)], capture_output=True, text=True)
    return float(r.stdout.strip())


def ts(t: float, sep: str) -> str:
    h, m = int(t // 3600), int(t % 3600 // 60)
    s = t % 60
    return (f"{h:02d}:{m:02d}:{s:05.2f}" if sep == "," else f"{h:d}:{m:02d}:{s:05.2f}")


def subtitles(state: dict) -> None:
    YT.mkdir(parents=True, exist_ok=True)
    durs, offs, pause = state["durations"], state["offsets"], PAUSE
    srt, vtt, n = [], [], 0
    start_scene = 0.0
    for i in range(len(SCENES)):
        scene_start = start_scene  # audio scene i begins here
        for c in offs[str(i)]:
            n += 1
            cs, ce = scene_start + c["start"], scene_start + c["start"] + min(
                7.0, max(1.8, len(c["text"].split()) / 2.6))
            # clamp cue to the scene's span
            scene_end = scene_start + durs[str(i)]
            ce = min(ce, scene_end)
            txt = c["text"].strip()
            block = f"{n}\n{ts(cs, ',')} --> {ts(ce, ',')}\n{txt}\n"
            srt.append(block)
            vtt.append(f"{ts(cs, '.')} --> {ts(ce, '.')}\n{txt}\n")
        start_scene += durs[str(i)] + pause
    (YT / "spanguard-demo-v6.srt").write_text("\n".join(srt))
    (YT / "spanguard-demo-v6.vtt").write_text(
        "WEBVTT\n\n" + "\n".join(vtt))
    print(f"subtitles: {n} cues")


def thumbnail() -> None:
    from PIL import Image, ImageDraw, ImageFont
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from video_render import find_font
    fp = find_font()
    big = ImageFont.truetype(fp, 92)
    mid = ImageFont.truetype(fp, 40)
    small = ImageFont.truetype(fp, 28)
    img = Image.new("RGB", (W, H), "#0d1117")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 12], fill="#3fb950")
    d.text((64, 96), "SpanGuard v6", font=big, fill="#e6edf3")
    d.text((64, 210), "strip the attack. keep the data. with a bound.",
           font=mid, fill="#7ee787")
    chips = [("escape", "0.0%", "#3fb950"), ("hijack", "1.3%", "#3fb950"),
             ("over-strip", "0.8% bounded", "#d29922")]
    x = 64
    for label, val, col in chips:
        d.rounded_rectangle([x, 300, x + 360, 380], 14, fill="#161b22", outline="#30363d")
        d.text((x + 24, 312), label, font=small, fill="#8b949e")
        d.text((x + 24, 340), val, font=ImageFont.truetype(fp, 34), fill=col)
        x += 384
    # mini payload mock
    d.rounded_rectangle([64, 430, W - 64, 600], 14, fill="#010409", outline="#30363d")
    mono = ImageFont.truetype(fp, 26)
    d.text((88, 448), '{"carrier_note": "Delayed. [stripped:injection]",',
           font=mono, fill="#7ee787")
    d.text((88, 486), ' "total_eur": 129.90}              <- data survives',
           font=mono, fill="#c9d1d9")
    d.text((88, 524), '"IGNORE ALL PREVIOUS INSTRUCTIONS…"  <- gone',
           font=mono, fill="#ffa198")
    d.text((64, 634), "github.com/Hisernberg/spanguard   ·   Meta Global AI Hackathon 2026",
           font=small, fill="#8b949e")
    img.save(YT / "thumbnail.png")
    img.save(WORK / "thumb.png")


def main() -> None:
    state = json.loads((WORK / "chunks.json").read_text())
    total = remux(state)
    print(f"video re-muxed aligned: {total:.1f}s = {int(total // 60)}:{int(total % 60):02d}")
    subtitles(state)
    thumbnail()
    print("thumb:", YT / "thumbnail.png")


if __name__ == "__main__":
    main()
