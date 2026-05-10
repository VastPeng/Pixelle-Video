from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class InvocationPoint(Enum):
    BEFORE_CONTENT_GENERATION = "before_content_generation"
    BEFORE_VISUAL_PLANNING = "before_visual_planning"
    DURING_NARRATION = "during_narration"
    DURING_IMAGE_GEN = "during_image_gen"
    DURING_TTS = "during_tts"
    AFTER_VIDEO_COMPLETE = "after_video_complete"
    AFTER_POST_PROCESSING = "after_post_processing"


class HttpMethod(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"


@dataclass
class ExternalServiceConfig:
    id: str
    name: str
    url: str
    method: HttpMethod = HttpMethod.POST
    headers: dict[str, str] = field(default_factory=dict)
    body_template: Optional[str] = None
    invocation_points: list[InvocationPoint] = field(default_factory=list)
    timeout: int = 30
    retry_count: int = 0
    retry_delay: float = 1.0
    enabled: bool = True
    description: str = ""


@dataclass
class ServiceInvocationResult:
    service_id: str
    success: bool
    status_code: Optional[int] = None
    response_data: Optional[dict] = None
    error_message: Optional[str] = None
    duration: float = 0.0
    invocation_point: Optional[InvocationPoint] = None
