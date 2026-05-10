from pydantic import BaseModel, Field
from typing import Optional


class ToolChainStepRequest(BaseModel):
    tool: str = Field(..., description="Coze tool name, e.g. add_subtitles")
    enabled: bool = Field(True, description="Whether this tool step is enabled")
    config: dict = Field(default_factory=dict, description="Tool-specific configuration")


class PostProcessingRequest(BaseModel):
    video_url: str = Field(..., description="Input video URL or local path")
    video_type: str = Field("standard", description="Video type: product_video, tutorial_video, marketing_video, news_video, standard")
    toolchain: Optional[list[ToolChainStepRequest]] = Field(None, description="Tool chain config, None for auto-decide")
    local_video_path: Optional[str] = Field(None, description="Local video file path (will upload to TOS)")


class PostProcessingResponse(BaseModel):
    success: bool
    input_video_url: str
    output_video_url: Optional[str] = None
    applied_tools: list[str] = Field(default_factory=list)
    processing_time: float = 0.0
    credits_used: int = 0
    error_message: Optional[str] = None


class AnalyzeRequest(BaseModel):
    video_path: str = Field(..., description="Local video file path to analyze")


class AnalyzeResponse(BaseModel):
    duration: float
    resolution: list[int] = Field(..., description="[width, height]")
    frame_rate: float
    has_audio: bool
    needs_upscale: bool
    needs_denoise: bool
    needs_frame_insert: bool
    recommended_tools: list[str] = Field(default_factory=list)
    recommendation_reason: str = ""


class DecideRequest(BaseModel):
    video_type: str = Field(..., description="Video type")
    analysis: dict = Field(..., description="VideoAssetAnalysis as dict")
    user_overrides: Optional[list[ToolChainStepRequest]] = None


class DecideResponse(BaseModel):
    toolchain: list[ToolChainStepRequest]
