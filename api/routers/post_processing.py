import os
from fastapi import APIRouter, HTTPException
from loguru import logger

from api.schemas.post_processing import (
    PostProcessingRequest, PostProcessingResponse,
    AnalyzeRequest, AnalyzeResponse,
    DecideRequest, DecideResponse, ToolChainStepRequest,
)
from pixelle_video.models.post_processing import (
    VideoType, CozeTool, ToolChainConfig, VideoAssetAnalysis,
)
from pixelle_video.services.asset_analyzer import AssetAnalyzer
from pixelle_video.services.toolchain_decider import ToolChainDecider
from pixelle_video.services.post_processing_manager import PostProcessingManager
from pixelle_video.services.coze_client import CozePluginClient
from pixelle_video.services.tos_upload_service import TosUploadService

router = APIRouter(prefix="/post-processing", tags=["Post Processing"])

_analyzer = AssetAnalyzer()
_decider = ToolChainDecider()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_video(request: AnalyzeRequest):
    analysis = await _analyzer.analyze(request.video_path)
    return AnalyzeResponse(
        duration=analysis.duration,
        resolution=list(analysis.resolution),
        frame_rate=analysis.frame_rate,
        has_audio=analysis.has_audio,
        needs_upscale=analysis.needs_upscale,
        needs_denoise=analysis.needs_denoise,
        needs_frame_insert=analysis.needs_frame_insert,
        recommended_tools=analysis.recommended_tools,
        recommendation_reason=analysis.recommendation_reason,
    )


@router.post("/decide", response_model=DecideResponse)
async def decide_toolchain(request: DecideRequest):
    video_type = VideoType(request.video_type)
    analysis_data = request.analysis
    analysis = VideoAssetAnalysis(**analysis_data)
    toolchain = _decider.decide(video_type, analysis)
    return DecideResponse(
        toolchain=[
            ToolChainStepRequest(tool=t.tool.value, enabled=t.enabled, config=t.config)
            for t in toolchain
        ]
    )


@router.post("/execute", response_model=PostProcessingResponse)
async def execute_post_processing(request: PostProcessingRequest):
    api_token = os.environ.get("COZE_API_TOKEN", "")
    if not api_token:
        raise HTTPException(status_code=500, detail="COZE_API_TOKEN not configured")

    coze_client = CozePluginClient(api_token=api_token)

    tos_service = None
    tos_ak = os.environ.get("TOS_ACCESS_KEY", "")
    tos_sk = os.environ.get("TOS_SECRET_KEY", "")
    if tos_ak and tos_sk:
        tos_service = TosUploadService(access_key=tos_ak, secret_key=tos_sk)

    manager = PostProcessingManager(coze_client=coze_client, tos_service=tos_service)

    if request.toolchain:
        toolchain = []
        for step in request.toolchain:
            try:
                tool_enum = CozeTool(step.tool)
                toolchain.append(ToolChainConfig(tool=tool_enum, enabled=step.enabled, config=step.config))
            except ValueError:
                logger.warning(f"Unknown tool: {step.tool}, skipping")
    else:
        analysis = await _analyzer.analyze(request.video_url)
        video_type = VideoType(request.video_type)
        toolchain = _decider.decide(video_type, analysis)

    result = await manager.execute(
        video_url=request.video_url,
        toolchain=toolchain,
        local_video_path=request.local_video_path,
    )
    return PostProcessingResponse(
        success=result.success,
        input_video_url=result.input_video_url,
        output_video_url=result.output_video_url,
        applied_tools=result.applied_tools,
        processing_time=result.processing_time,
        credits_used=result.credits_used,
        error_message=result.error_message,
    )


@router.get("/presets")
async def get_presets():
    presets = {}
    for vt in VideoType:
        tools = _decider.PRESETS.get(vt, [])
        presets[vt.value] = [
            {"tool": t.tool.value, "config": t.config} for t in tools
        ]
    return presets


@router.get("/tools")
async def get_available_tools():
    return [{"name": t.value} for t in CozeTool]
