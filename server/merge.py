"""영상 합성: 한 기록의 2초 클립들을 퀘스트/순서대로 1개 mp4로 이어붙인다.

0625 LetsPaw merge.py를 alpha-blip(솔로 단일페인)에 맞게 단순화. 서버 ffmpeg는
imageio-ffmpeg 번들 바이너리(시스템 설치 불필요). 브라우저 MediaRecorder webm은 컨테이너
duration이 N/A라 fps 정규화로 안정화한 뒤 동일 규격으로 재인코딩 후 concat copy 한다.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
W, H = 640, 360
FPS = "30"
ENC = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", FPS, "-an", "-preset", "veryfast"]


def _run(args: list[str]) -> None:
    p = subprocess.run([FFMPEG, "-y", *args], capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr[-800:])


def _scale_clip(src: str, out: str) -> None:
    vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS}"
    _run(["-fflags", "+genpts", "-i", src, "-vf", vf, *ENC, out])


def build_record_video(clip_paths: list[str], out_path: str) -> str:
    """clip_paths(순서대로)를 하나의 mp4로 합성해 out_path에 쓰고 그 경로를 반환."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        scenes = []
        for i, src in enumerate(clip_paths):
            if not src or not Path(src).exists():
                continue
            scene = td / f"s_{i:03d}.mp4"
            try:
                _scale_clip(src, str(scene))
                scenes.append(scene)
            except Exception:
                continue  # 손상 클립 장면은 건너뛴다(전체 합성은 계속)
        if not scenes:
            raise RuntimeError("합성할 클립이 없습니다")
        if len(scenes) == 1:
            _run(["-i", str(scenes[0]), "-c", "copy", str(out)])
        else:
            listfile = td / "list.txt"
            listfile.write_text("".join(f"file '{s.as_posix()}'\n" for s in scenes), encoding="utf-8")
            _run(["-f", "concat", "-safe", "0", "-i", str(listfile), "-c", "copy", str(out)])
    return str(out)
