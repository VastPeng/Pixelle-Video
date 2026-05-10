from pydantic import BaseModel, Field
from typing import Optional, Any


class NodeExecuteRequest(BaseModel):
    """Request to execute a single pipeline node"""
    session_id: Optional[str] = Field(None, description="Session ID for stateful execution")
    input_data: dict = Field(default_factory=dict, description="Node input data")
    config: dict = Field(default_factory=dict, description="Node-specific configuration")


class NodeExecuteResponse(BaseModel):
    """Response from a single pipeline node execution"""
    session_id: str
    node_name: str
    success: bool
    output_data: dict = Field(default_factory=dict)
    error_message: Optional[str] = None


class SessionCreateRequest(BaseModel):
    """Request to create a new pipeline session"""
    topic: str = Field(..., description="Video topic/prompt")
    video_type: str = Field("standard", description="Video type")
    config: dict = Field(default_factory=dict, description="Pipeline configuration overrides")


class SessionResponse(BaseModel):
    """Pipeline session info"""
    session_id: str
    status: str
    current_node: Optional[str] = None
    completed_nodes: list[str] = Field(default_factory=list)
    output_data: dict = Field(default_factory=dict)


class NodeListResponse(BaseModel):
    """Available pipeline nodes"""
    nodes: list[dict[str, Any]]
