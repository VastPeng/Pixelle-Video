import json
import time
import uuid
from fastapi import APIRouter, HTTPException
from loguru import logger

from api.schemas.pipeline_node import (
    NodeExecuteRequest, NodeExecuteResponse,
    SessionCreateRequest, SessionResponse,
    NodeListResponse,
)
from api.dependencies import PixelleVideoDep

router = APIRouter(prefix="/pipeline/nodes", tags=["Pipeline Nodes"])

# In-memory session store with TTL and max size
_sessions: dict[str, dict] = {}
MAX_SESSIONS = 1000
SESSION_TTL_SECONDS = 3600  # 1 hour


def _cleanup_expired_sessions():
    """Remove expired sessions to prevent memory leak"""
    now = time.time()
    expired = [
        k for k, v in _sessions.items()
        if now - v.get("created_at", 0) > SESSION_TTL_SECONDS
    ]
    for k in expired:
        del _sessions[k]
    if expired:
        logger.debug(f"Cleaned up {len(expired)} expired sessions")


NODE_LIST = [
    {"name": "content_generate", "description": "Generate narration content from topic", "input": ["topic", "style", "n_scenes"], "output": ["narrations"]},
    {"name": "visual_plan", "description": "Plan visual scenes from narrations", "input": ["narrations", "style"], "output": ["image_prompts"]},
    {"name": "tts_generate", "description": "Generate speech audio from text", "input": ["text", "voice", "speed"], "output": ["audio_url"]},
    {"name": "image_generate", "description": "Generate image from prompt", "input": ["prompt", "width", "height"], "output": ["image_url"]},
    {"name": "video_compose", "description": "Compose video from frames and audio", "input": ["frames", "audio", "fps"], "output": ["video_url"]},
    {"name": "post_process", "description": "Post-process video with Coze tools", "input": ["video_url", "toolchain"], "output": ["output_video_url"]},
]


@router.get("/list", response_model=NodeListResponse)
async def list_nodes():
    return NodeListResponse(nodes=NODE_LIST)


@router.post("/session/create", response_model=SessionResponse)
async def create_session(request: SessionCreateRequest, pixelle_video: PixelleVideoDep):
    # Cleanup expired sessions before creating new one
    _cleanup_expired_sessions()
    if len(_sessions) >= MAX_SESSIONS:
        raise HTTPException(status_code=429, detail="Too many sessions. Please wait for expired sessions to be cleaned up.")

    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    session = {
        "session_id": session_id,
        "status": "created",
        "current_node": None,
        "completed_nodes": [],
        "output_data": {"topic": request.topic, "video_type": request.video_type},
        "config": request.config,
        "created_at": time.time(),
    }
    _sessions[session_id] = session
    return SessionResponse(**session)


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse(**session)


@router.post("/execute/{node_name}", response_model=NodeExecuteResponse)
async def execute_node(
    node_name: str,
    request: NodeExecuteRequest,
    pixelle_video: PixelleVideoDep,
):
    session_id = request.session_id
    input_data = request.input_data
    config = request.config

    if node_name not in {n["name"] for n in NODE_LIST}:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_name}")

    output_data = {}

    try:
        if node_name == "content_generate":
            topic = input_data.get("topic", "")
            style = input_data.get("style", "informative")
            n_scenes = input_data.get("n_scenes", 5)
            result = await pixelle_video.llm(
                f"Generate {n_scenes} narration segments about: {topic}\n"
                f"Style: {style}\nReturn as JSON array of strings.",
                temperature=0.7,
            )
            try:
                narrations = json.loads(result)
                if not isinstance(narrations, list):
                    narrations = [result]
            except json.JSONDecodeError:
                narrations = [result]
            output_data = {"narrations": narrations}

        elif node_name == "visual_plan":
            narrations = input_data.get("narrations", [])
            style = input_data.get("style", "minimalist")
            prompts = []
            for narration in narrations:
                result = await pixelle_video.llm(
                    f"Generate image prompt for: {narration}\nStyle: {style}\nReturn only the prompt.",
                    temperature=0.7,
                )
                prompts.append(result)
            output_data = {"image_prompts": prompts}

        elif node_name == "tts_generate":
            text = input_data.get("text", "")
            voice = input_data.get("voice", "zh-CN-YunjianNeural")
            speed = input_data.get("speed", 1.2)
            audio_path = await pixelle_video.tts(text=text, voice=voice, speed=speed)
            output_data = {"audio_url": audio_path}

        elif node_name == "image_generate":
            prompt = input_data.get("prompt", "")
            width = input_data.get("width", 1080)
            height = input_data.get("height", 1920)
            result = await pixelle_video.media(prompt=prompt, width=width, height=height)
            output_data = {"image_url": result}

        elif node_name == "video_compose":
            output_data = {"message": "Video compose requires full pipeline context"}

        elif node_name == "post_process":
            output_data = {"message": "Post-process requires video_url and toolchain"}

    except Exception as e:
        logger.error(f"Node {node_name} execution failed: {e}")
        return NodeExecuteResponse(
            session_id=session_id or "none",
            node_name=node_name,
            success=False,
            error_message=str(e),
        )

    # Update session if provided
    if session_id and session_id in _sessions:
        session = _sessions[session_id]
        session["completed_nodes"].append(node_name)
        session["output_data"].update(output_data)
        session["current_node"] = node_name

    return NodeExecuteResponse(
        session_id=session_id or "none",
        node_name=node_name,
        success=True,
        output_data=output_data,
    )
