from loguru import logger
from pixelle_video.models.post_processing import (
    VideoType, CozeTool, ToolChainConfig, VideoAssetAnalysis,
)


class ToolChainDecider:
    """Decides post-processing tool chain based on video type and asset analysis"""

    PRESETS = {
        VideoType.PRODUCT: [
            ToolChainConfig(tool=CozeTool.ADD_SUBTITLES, config={"font_size": 24}),
            ToolChainConfig(tool=CozeTool.VIDEO_SUPER_RESOLUTION, config={"resolution": "1080p"}),
        ],
        VideoType.TUTORIAL: [
            ToolChainConfig(tool=CozeTool.ADD_SUBTITLES, config={"font_size": 28}),
            ToolChainConfig(tool=CozeTool.AUDIO_DENOISE),
        ],
        VideoType.MARKETING: [
            ToolChainConfig(tool=CozeTool.CONCAT_VIDEOS, config={"transitions": ["fade"]}),
            ToolChainConfig(tool=CozeTool.ADD_TEXT),
            ToolChainConfig(tool=CozeTool.VIDEO_HDR),
        ],
        VideoType.NEWS: [
            ToolChainConfig(tool=CozeTool.ADD_SUBTITLES),
            ToolChainConfig(tool=CozeTool.VIDEO_SPEED, config={"speed": 1.1}),
        ],
        VideoType.STANDARD: [
            ToolChainConfig(tool=CozeTool.ADD_SUBTITLES),
        ],
    }

    def decide(
        self,
        video_type: VideoType,
        analysis: VideoAssetAnalysis,
        user_overrides: list[ToolChainConfig] | None = None,
    ) -> list[ToolChainConfig]:
        preset_tools = list(self.PRESETS.get(video_type, self.PRESETS[VideoType.STANDARD]))
        toolchain = self._apply_conditions(preset_tools, analysis)
        toolchain = self._apply_smart_adjustments(toolchain, analysis)
        if user_overrides is not None:
            toolchain = user_overrides
        return toolchain

    def _apply_conditions(
        self, tools: list[ToolChainConfig], analysis: VideoAssetAnalysis
    ) -> list[ToolChainConfig]:
        if analysis.duration > 60:
            has_speed = any(t.tool == CozeTool.VIDEO_SPEED for t in tools)
            if not has_speed:
                tools.append(ToolChainConfig(tool=CozeTool.VIDEO_SPEED, config={"speed": 1.1}))
        return tools

    def _apply_smart_adjustments(
        self, tools: list[ToolChainConfig], analysis: VideoAssetAnalysis
    ) -> list[ToolChainConfig]:
        tool_names = {t.tool for t in tools}
        if analysis.needs_upscale and CozeTool.VIDEO_SUPER_RESOLUTION not in tool_names:
            tools.append(ToolChainConfig(tool=CozeTool.VIDEO_SUPER_RESOLUTION, config={"resolution": "1080p"}))
        if analysis.needs_denoise and CozeTool.AUDIO_DENOISE not in tool_names:
            tools.append(ToolChainConfig(tool=CozeTool.AUDIO_DENOISE))
        if analysis.needs_frame_insert and CozeTool.INSERT_FRAME not in tool_names:
            tools.append(ToolChainConfig(tool=CozeTool.INSERT_FRAME))
        if not analysis.has_subtitle and CozeTool.ADD_SUBTITLES not in tool_names:
            tools.insert(0, ToolChainConfig(tool=CozeTool.ADD_SUBTITLES))
        return tools
