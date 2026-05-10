import asyncio
import json
import os
from loguru import logger
from pixelle_video.models.post_processing import VideoAssetAnalysis


class AssetAnalyzer:
    """Analyzes video assets to determine post-processing needs"""

    async def analyze(self, video_path: str) -> VideoAssetAnalysis:
        if not os.path.isfile(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Run ffprobe in a thread to avoid blocking the event loop
        return await asyncio.to_thread(self._analyze_sync, video_path)

    def _analyze_sync(self, video_path: str) -> VideoAssetAnalysis:

        file_size = os.path.getsize(video_path)
        duration = 0.0
        resolution = (0, 0)
        frame_rate = 0.0
        has_audio = False
        audio_duration = 0.0
        audio_quality = "unknown"
        has_speech = False
        has_subtitle = False
        subtitle_language = None

        try:
            import subprocess
            result = subprocess.run(
                [
                    "ffprobe", "-v", "quiet", "-print_format", "json",
                    "-show_format", "-show_streams", video_path,
                ],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                import json
                info = json.loads(result.stdout)
                fmt = info.get("format", {})
                duration = float(fmt.get("duration", 0))
                for stream in info.get("streams", []):
                    codec_type = stream.get("codec_type", "")
                    codec_name = stream.get("codec_name", "")
                    if codec_type == "video":
                        w = int(stream.get("width", 0))
                        h = int(stream.get("height", 0))
                        resolution = (w, h)
                        r = stream.get("r_frame_rate", "0/1")
                        if "/" in r:
                            num, den = r.split("/")
                            frame_rate = float(num) / float(den) if float(den) > 0 else 0
                    elif codec_type == "audio":
                        has_audio = True
                        audio_duration = float(stream.get("duration", duration))
                        # Detect speech vs music by codec and channel count
                        channels = int(stream.get("channels", 1))
                        bit_rate = int(stream.get("bit_rate", 0))
                        if codec_name in ("opus", "aac", "mp3") and channels == 1:
                            has_speech = True
                        # Quality assessment based on bit rate
                        if bit_rate > 0:
                            if bit_rate < 64000:
                                audio_quality = "low"
                            elif bit_rate < 128000:
                                audio_quality = "normal"
                            else:
                                audio_quality = "high"
                        else:
                            audio_quality = "normal"
                    elif codec_type == "subtitle":
                        has_subtitle = True
                        subtitle_language = stream.get("language", stream.get("tags", {}).get("language", None))
        except Exception as e:
            logger.warning(f"ffprobe analysis failed for {video_path}: {e}")

        needs_upscale = resolution[0] > 0 and resolution[0] < 1920
        needs_denoise = has_audio and audio_quality in ("low", "unknown")
        needs_frame_insert = frame_rate > 0 and frame_rate < 24

        recommended_tools = []
        reasons = []
        if needs_upscale:
            recommended_tools.append("video_super_resolution")
            reasons.append("分辨率低于1080p")
        if needs_denoise:
            recommended_tools.append("audio_denoise")
            reasons.append("音频质量低")
        if needs_frame_insert:
            recommended_tools.append("insert_frame")
            reasons.append("帧率低于24fps")
        if has_audio and not has_subtitle:
            recommended_tools.append("audio_to_subtitle")
            reasons.append("有音频但无字幕")

        return VideoAssetAnalysis(
            duration=duration,
            resolution=resolution,
            frame_rate=frame_rate,
            file_size=file_size,
            has_audio=has_audio,
            audio_duration=audio_duration,
            audio_quality=audio_quality,
            has_speech=has_speech,
            has_subtitle=has_subtitle,
            subtitle_language=subtitle_language,
            needs_upscale=needs_upscale,
            needs_denoise=needs_denoise,
            needs_frame_insert=needs_frame_insert,
            recommended_tools=recommended_tools,
            recommendation_reason="; ".join(reasons),
        )
