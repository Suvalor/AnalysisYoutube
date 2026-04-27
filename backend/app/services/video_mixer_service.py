"""Video mixer service — slice, shuffle, normalize and merge video clips with a new audio track.

Uses ``ffmpeg-python`` (wrapper around the ``ffmpeg`` CLI) so that all heavy
processing stays inside ffmpeg's streaming pipeline — no full video data is
ever loaded into Python memory.

Typical usage::

    from app.services.video_mixer_service import mix_videos

    mix_videos(
        source_video_paths=["/data/raw/a.mp4", "/data/raw/b.mp4"],
        new_audio_path="/data/tts/narration.mp3",
        output_path="/data/processed/result.mp4",
    )
"""

from __future__ import annotations

import logging
import random
from pathlib import Path

import ffmpeg

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

# Target resolution (width x height).  Change to (1920, 1080) for landscape.
DEFAULT_TARGET_WIDTH = 1080
DEFAULT_TARGET_HEIGHT = 1920
DEFAULT_FPS = 30

# Slice length range in seconds.
SLICE_DURATION_MIN = 3
SLICE_DURATION_MAX = 5

# Safety limits.
MAX_CLIPS = 500
MAX_REASONABLE_DURATION = 86400  # 24 hours — sanity check for probe values
FFMPEG_TIMEOUT_SECONDS = 300     # 5 minutes — prevents indefinite hangs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _probe_duration(path: str) -> float:
    """Return duration of a media file in seconds using ffprobe."""
    probe = ffmpeg.probe(path)
    # Try the format container first (works for most audio files).
    duration = float(probe.get("format", {}).get("duration", 0))
    if duration > 0:
        if duration > MAX_REASONABLE_DURATION:
            raise RuntimeError(f"Suspect duration {duration}s for {path!r}")
        return duration
    # Fallback: look at individual streams (some containers omit format.duration).
    for stream in probe.get("streams", []):
        d = float(stream.get("duration", 0))
        if d > 0:
            if d > MAX_REASONABLE_DURATION:
                raise RuntimeError(f"Suspect duration {d}s for {path!r}")
            return d
    raise RuntimeError(f"Cannot determine duration of {path!r}")


def _probe_video_duration(path: str) -> float:
    """Return duration of the *video stream* in a file."""
    probe = ffmpeg.probe(path, select_stream="v")
    for stream in probe.get("streams", []):
        # Prefer duration from the stream metadata.
        d = float(stream.get("duration", 0))
        if d > 0:
            if d > MAX_REASONABLE_DURATION:
                raise RuntimeError(f"Suspect video duration {d}s for {path!r}")
            return d
        # Fallback: compute from nb_frames / r_frame_rate.
        nb_frames = stream.get("nb_frames")
        r_frame_rate = stream.get("r_frame_rate")
        if nb_frames and r_frame_rate:
            num, den = map(int, r_frame_rate.split("/"))
            if den:
                # Duration = frames / fps = frames * den / num
                return int(nb_frames) * den / num
    raise RuntimeError(f"Cannot determine video duration of {path!r}")


def _normalize_clip(
    input_path: str,
    start: float,
    duration: float,
    target_w: int,
    target_h: int,
    fps: int,
) -> ffmpeg.Stream:
    """Return an ffmpeg *Stream* for a single normalized video slice.

    Pipeline (each filter explained inline)::

        input → trim → setpts → scale → pad → fps → setsar

    All filters operate on the video stream only; audio is discarded.
    """
    # 1. Read the source file. ``an=None`` generates the ffmpeg ``-an`` flag
    #    which discards the audio stream entirely.
    in_stream = ffmpeg.input(input_path, ss=start, t=duration, an=None)

    # 2. ``trim``: extract the time window [start, start+duration).
    #    ``setpts=PTS-STARTPTS``: reset presentation timestamps so the clip
    #    starts from 0 — required after trim, otherwise concat will misalign.
    trimmed = in_stream.video.trim(start=0, duration=duration).setpts("PTS-STARTPTS")

    # 3. ``scale``: resize to fit within target_w x target_h while preserving
    #    aspect ratio.  ``force_original_aspect_ratio=decrease`` ensures the
    #    video never exceeds the target dimensions.
    #    ``pad``: fill any remaining area with black bars (letterboxing) so the
    #    output is *exactly* target_w x target_h — concat requires identical
    #    dimensions.
    scaled = trimmed.filter(
        "scale",
        target_w,
        target_h,
        force_original_aspect_ratio="decrease",
    ).filter(
        "pad",
        target_w,
        target_h,
        x="(ow-iw)/2",   # center horizontally
        y="(oh-ih)/2",   # center vertically
        color="black",
    )

    # 4. ``fps``: normalize frame rate to a fixed value so streams are
    #    concat-compatible.
    fps_filtered = scaled.filter("fps", fps=fps)

    # 5. ``setsar``: force the Sample Aspect Ratio to 1:1 so that all clips
    #    report the same SAR — prevents "different SAR" concat errors.
    normalized = fps_filtered.filter("setsar", sar="1")

    return normalized


# ---------------------------------------------------------------------------
# Core mixer
# ---------------------------------------------------------------------------


def mix_videos(
    source_video_paths: list[str],
    new_audio_path: str,
    output_path: str | None = None,
    target_width: int = DEFAULT_TARGET_WIDTH,
    target_height: int = DEFAULT_TARGET_HEIGHT,
    fps: int = DEFAULT_FPS,
    seed: int | None = None,
    highlights: dict[str, list[tuple[float, float]]] | None = None,
) -> str:
    """Slice, shuffle, normalize and merge video clips with a new audio track.

    Args:
        source_video_paths: Local paths of source videos to slice from.
        new_audio_path: Path of the new narration / TTS audio.
        output_path: Destination path.  Defaults to ``<cwd>/data/processed/result.mp4``.
        target_width: Output width in pixels.
        target_height: Output height in pixels.
        fps: Output frame rate.
        seed: Optional random seed for reproducible slice selection.
        highlights: Optional mapping of source video path to list of (start_sec, end_sec)
            highlight segments. When provided, highlight segments are used first before
            falling back to random slicing for remaining duration.

    Returns:
        Absolute path of the generated video file.

    Raises:
        FileNotFoundError: If any input file does not exist.
        RuntimeError: If ffmpeg processing fails or inputs are invalid.
    """
    if seed is not None:
        random.seed(seed)

    # -- Validate inputs --------------------------------------------------
    for p in source_video_paths:
        if not Path(p).is_file():
            raise FileNotFoundError(f"Source video not found: {p}")
    if not Path(new_audio_path).is_file():
        raise FileNotFoundError(f"Audio file not found: {new_audio_path}")

    if output_path is None:
        output_path = str(Path("data") / "processed" / "result.mp4")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # -- Step 1: Get audio duration (the target total length) -------------
    audio_duration = _probe_duration(new_audio_path)
    logger.info("Audio duration: %.2f s — target total clip length", audio_duration)

    # -- Step 2: Slice extraction (highlights first, then random) --
    video_durations: list[float] = []
    for vp in source_video_paths:
        d = _probe_video_duration(vp)
        if d <= 0:
            raise RuntimeError(f"Source video {vp!r} has zero/negative duration ({d}s)")
        video_durations.append(d)

    clips: list[ffmpeg.Stream] = []
    accumulated = 0.0

    # Phase A: Use highlights first (if available)
    if highlights:
        for vp in source_video_paths:
            vp_highlights = highlights.get(vp, [])
            for start, end in vp_highlights:
                if accumulated >= audio_duration:
                    break
                duration = min(end - start, audio_duration - accumulated)
                if duration <= 0:
                    continue
                logger.info(
                    "Highlight clip #%d: src=%s start=%.2f len=%.2f (accumulated=%.2f/%.2f)",
                    len(clips), Path(vp).name, start, duration,
                    accumulated + duration, audio_duration,
                )
                normalized = _normalize_clip(vp, start, duration, target_width, target_height, fps)
                clips.append(normalized)
                accumulated += duration

    # Phase B: Fill remaining duration with random slices
    while accumulated < audio_duration and len(clips) < MAX_CLIPS:
        slice_len = random.uniform(SLICE_DURATION_MIN, SLICE_DURATION_MAX)
        idx = random.randint(0, len(source_video_paths) - 1)
        src_path = source_video_paths[idx]
        src_dur = video_durations[idx]

        if src_dur <= slice_len:
            start = 0.0
            actual_len = src_dur
        else:
            start = random.uniform(0, src_dur - slice_len)
            actual_len = slice_len

        remaining = audio_duration - accumulated
        if actual_len > remaining + SLICE_DURATION_MAX:
            actual_len = remaining

        if actual_len <= 0:
            continue

        logger.info(
            "Clip #%d: src=%s start=%.2f len=%.2f (accumulated=%.2f/%.2f)",
            len(clips), Path(src_path).name, start, actual_len,
            accumulated + actual_len, audio_duration,
        )

        normalized = _normalize_clip(src_path, start, actual_len, target_width, target_height, fps)
        clips.append(normalized)
        accumulated += actual_len

    if len(clips) >= MAX_CLIPS:
        logger.warning("Reached MAX_CLIPS=%d limit; video may be shorter than audio", MAX_CLIPS)

    if not clips:
        raise RuntimeError("No video clips were generated — check source videos")

    # -- Step 3: Concat normalized clips ----------------------------------
    # ``v=1:a=0`` tells concat to expect 1 video stream and 0 audio streams
    # per input segment.
    concatenated = ffmpeg.concat(*clips, v=1, a=0)

    # -- Step 4: Trim to exact audio length & merge audio -----------------
    # If the concatenated video is slightly longer than the audio, trim it.
    video_final = concatenated.trim(end=audio_duration).setpts("PTS-STARTPTS")

    # Read the new audio track.
    audio_in = ffmpeg.input(new_audio_path).audio

    # Merge video + audio into a single output.
    out = ffmpeg.output(
        video_final,
        audio_in,
        output_path,
        vcodec="libx264",
        acodec="aac",
        # Use fast preset for server-side processing; quality is acceptable.
        preset="fast",
        crf=23,
        # Ensure moov atom is at the start for streaming-friendly playback.
        movflags="+faststart",
    )

    # -- Step 5: Run ffmpeg -----------------------------------------------
    logger.info("Starting ffmpeg mix — output: %s", output_path)
    try:
        out.run(
            overwrite_output=True,
            capture_stdout=True,
            capture_stderr=True,
            cmd_timeout=FFMPEG_TIMEOUT_SECONDS,
        )
    except ffmpeg.Error as exc:
        # Clean up partial output file to avoid serving corrupted content.
        partial = Path(output_path)
        if partial.exists():
            partial.unlink()
        stderr = exc.stderr.decode(errors="replace") if exc.stderr else ""
        raise RuntimeError(f"ffmpeg failed:\n{stderr}") from exc

    logger.info("Mix complete: %s (%.2f s)", output_path, audio_duration)
    return str(Path(output_path).resolve())