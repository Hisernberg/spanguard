#!/usr/bin/env python3
"""Cap-proof TTS: split each scene's narration into <=22-word sentence chunks,
synthesize per chunk (z-ai tts caps ~30s/call), trim edges, concat per scene.
Writes chunk offsets to chunks.json for SRT cue timing, re-assembles video."""
import json
import re
import subprocess
import time
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from video_render import SCENES, WORK, OUT  # noqa: E402

MAX_WORDS = 22


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


def chunks(text: str) -> list[str]:
    sents = re.findall(r"[^.!?]+[.!?]+(?:\s|$)|[^.!?]+$", text)
    groups, cur = [], ""
    for s in sents:
        s = s.strip()
        if not s:
            continue
        if len((cur + " " + s).split()) <= MAX_WORDS or not cur:
            cur = (cur + " " + s).strip()
        else:
            groups.append(cur)
            cur = s
    if cur:
        groups.append(cur)
    return groups


def main() -> None:
    offsets, durations = {}, {}
    state_p = WORK / "chunks.json"
    state = json.loads(state_p.read_text()) if state_p.exists() else {"offsets": {}, "durations": {}}
    for i, scene in enumerate(SCENES):
        if (WORK / f"nar-{i}.wav").exists() and (WORK / f"chunked-{i}").exists():
            offsets[i] = state["offsets"][str(i)]
            durations[i] = state["durations"][str(i)]
            print(f"scene {i}: resume {durations[i]:.1f}s", flush=True)
            continue
        parts = chunks(scene["prompt"])
        wavs = []
        for k, part in enumerate(parts):
            c = WORK / f"nar-{i}-{k}.wav"
            ok = False
            for attempt in range(5):
                r = subprocess.run(["z-ai", "tts", "-i", part, "-o", str(c)],
                                   capture_output=True, text=True, timeout=180)
                if r.returncode == 0 and c.exists() and dur(c) > 0.5:
                    ok = True
                    break
                print(f"scene {i} chunk {k} retry {attempt}: {r.stderr[:60]}", flush=True)
                time.sleep(75)
            if not ok:
                raise RuntimeError(f"tts failed scene {i} chunk {k}")
            trim(c)
            wavs.append(c)
            time.sleep(25)
        # concat scene wav
        lst = WORK / f"nar-{i}-list.txt"
        lst.write_text("".join(f"file '{w.name}'\n" for w in wavs))
        out = WORK / f"nar-{i}.wav"
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                        str(out)], capture_output=True, check=True)
        trim(out)
        # chunk offsets (seconds) within the scene wav
        off, offs = 0.0, []
        for w in wavs[:-1]:
            offs.append(off)
            off += dur(w)
        offs.append(off)
        offsets[i] = [{"text": t, "start": s} for t, s in zip(parts, offs)]
        durations[i] = dur(out)
        (WORK / f"chunked-{i}").write_text("ok")
        state["offsets"][str(i)], state["durations"][str(i)] = offsets[i], durations[i]
        state_p.write_text(json.dumps(state))
        print(f"scene {i}: {durations[i]:.1f}s ({len(parts)} chunks)", flush=True)
    total = sum(durations.values()) + 0.8 * len(SCENES)
    print(f"total: {total:.1f}s = {int(total // 60)}:{int(total % 60):02d}")
    (WORK / "chunks.json").write_text(json.dumps(
        {"offsets": offsets, "durations": durations, "pause": 0.8}))
    # re-assemble video
    (WORK / "nars.txt").write_text(
        "".join(f"file 'nar-{i}.wav'\n" for i in range(len(SCENES))))
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", str(WORK / "nars.txt"), str(WORK / "narration.wav")],
                   capture_output=True, check=True)
    (WORK / "frames.txt").write_text("".join(
        f"file 'frames/f{i:02d}.png'\nduration {durations[i] + 0.8:.2f}\n"
        for i in range(len(SCENES))) + f"file 'frames/f{len(SCENES) - 1:02d}.png'\n")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(WORK / "frames.txt"),
         "-i", str(WORK / "narration.wav"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-shortest", str(OUT)], capture_output=True, check=True)
    print("video:", OUT, f"{OUT.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
