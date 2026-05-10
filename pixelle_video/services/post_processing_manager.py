import time
from loguru import logger
from pixelle_video.services.coze_client import CozePluginClient
from pixelle_video.services.tos_upload_service import TosUploadService
from pixelle_video.services.asset_analyzer import AssetAnalyzer
from pixelle_video.services.toolchain_decider import ToolChainDecider
from pixelle_video.models.post_processing import (
    VideoType, ToolChainConfig, VideoAssetAnalysis, PostProcessingResult,
)


class PostProcessingManager:
    """Orchestrates post-processing: upload(TOS) -> analyze -> decide -> execute"""

    def __init__(
        self,
        coze_client: CozePluginClient | None = None,
        tos_service: TosUploadService | None = None,
    ):
        self.coze_client = coze_client
        self.tos_service = tos_service
        self.analyzer = AssetAnalyzer()
        self.decider = ToolChainDecider()

    async def analyze(self, video_path: str) -> VideoAssetAnalysis:
        return await self.analyzer.analyze(video_path)

    def decide(
        self,
        video_type: VideoType,
        analysis: VideoAssetAnalysis,
        user_overrides: list[ToolChainConfig] | None = None,
    ) -> list[ToolChainConfig]:
        return self.decider.decide(video_type, analysis, user_overrides)

    async def execute(
        self,
        video_url: str,
        toolchain: list[ToolChainConfig],
        local_video_path: str | None = None,
    ) -> PostProcessingResult:
        if not toolchain or self.coze_client is None:
            return PostProcessingResult(
                success=True,
                input_video_url=video_url,
                output_video_url=video_url,
            )

        # If video is local file, upload to TOS first to get public URL
        current_url = video_url
        if local_video_path and self.tos_service and self.tos_service.enabled:
            try:
                logger.info(f"Uploading local video to TOS: {local_video_path}")
                tos_url, tos_error = self.tos_service.upload_file(local_video_path)
                if tos_error:
                    logger.warning(f"TOS upload failed: {tos_error}, using original URL")
                else:
                    current_url = tos_url
                    logger.info(f"TOS upload success: {tos_url}")
            except Exception as e:
                logger.warning(f"TOS upload exception: {e}, using original URL")

        start_time = time.time()
        applied_tools = []
        total_credits = 0

        for step in toolchain:
            if not step.enabled:
                continue
            try:
                logger.info(f"Executing tool: {step.tool.value}")
                args = {"video": current_url, **step.config}
                result = await self.coze_client.call_tool(step.tool.value, args)
                output_url = result.get("video_url", result.get("url", current_url))
                current_url = output_url
                applied_tools.append(step.tool.value)
                logger.info(f"Tool {step.tool.value} completed, output: {output_url}")
            except Exception as e:
                logger.error(f"Tool {step.tool.value} failed: {e}")
                return PostProcessingResult(
                    success=False,
                    input_video_url=video_url,
                    output_video_url=current_url,
                    applied_tools=applied_tools,
                    processing_time=time.time() - start_time,
                    error_message=str(e),
                )

        return PostProcessingResult(
            success=True,
            input_video_url=video_url,
            output_video_url=current_url,
            applied_tools=applied_tools,
            processing_time=time.time() - start_time,
            credits_used=total_credits,
        )
