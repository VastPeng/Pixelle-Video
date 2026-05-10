from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class VideoType(Enum):
    PRODUCT = "product_video"
    TUTORIAL = "tutorial_video"
    MARKETING = "marketing_video"
    NEWS = "news_video"
    STANDARD = "standard"


class CozeTool(Enum):
    ADD_SUBTITLES = "add_subtitles"
    CONCAT_VIDEOS = "concat_videos"
    COMPILE_VIDEO_AUDIO = "compile_video_audio"
    COMPILE_IMAGE_AUDIO = "compile_image_audio"
    VIDEO_SUPER_RESOLUTION = "video_super_resolution"
    VIDEO_HDR = "video_hdr"
    INSERT_FRAME = "insert_frame"
    AUDIO_TO_SUBTITLE = "audio_to_subtitle"
    AUDIO_SEPARATE = "audio_seperate"
    AUDIO_DENOISE = "audio_denoise"
    VIDEO_TRIM = "video_trim"
    VIDEO_SPEED = "video_speed"
    VIDEO_FPS = "video_fps"
    VIDEO_FLIP = "video_flip"
    ADD_SUBVIDEO = "add_subvideo"
    ADD_TEXT = "add_text"
    IMAGE_TO_VIDEO = "image_to_video"
    AUDIO_MIX = "audio_mix"
    AJUST_AUDIO_VOLUME = "ajust_audio_volume"
    AJUST_VIDEO_RESOLUTION = "ajust_video_resolution"
    AUDIO_LOUDNESS_NORMALIZATION = "audio_loudness_normalization"


@dataclass
class ToolChainConfig:
    tool: CozeTool
    enabled: bool = True
    config: dict = field(default_factory=dict)
    condition: Optional[str] = None


@dataclass
class PostProcessingPreset:
    name: str
    display_name: str
    video_type: VideoType
    default_tools: list[ToolChainConfig]
    description: str = ""

    def get_tool_names(self) -> list[str]:
        return [t.tool.value for t in self.default_tools if t.enabled]


@dataclass
class PostProcessingResult:
    success: bool
    input_video_url: str
    output_video_url: Optional[str] = None
    applied_tools: list[str] = field(default_factory=list)
    processing_time: float = 0.0
    credits_used: int = 0
    error_message: Optional[str] = None


@dataclass
class VideoAssetAnalysis:
    duration: float
    resolution: tuple[int, int]
    frame_rate: float
    file_size: int
    has_audio: bool
    audio_duration: float
    audio_quality: str
    has_speech: bool
    has_subtitle: bool
    subtitle_language: Optional[str]
    needs_upscale: bool
    needs_denoise: bool
    needs_frame_insert: bool
    recommended_tools: list[str] = field(default_factory=list)
    recommendation_reason: str = ""
