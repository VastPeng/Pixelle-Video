from pydantic import BaseModel, Field
from typing import Optional


class ExternalServiceCreateRequest(BaseModel):
    id: str = Field(..., description="Unique service ID")
    name: str = Field(..., description="Service display name")
    url: str = Field(..., description="Service endpoint URL")
    method: str = Field("POST", description="HTTP method: GET, POST, PUT, PATCH")
    headers: dict[str, str] = Field(default_factory=dict)
    body_template: Optional[str] = Field(None, description="JSON body template with {variable} placeholders")
    invocation_points: list[str] = Field(default_factory=list, description="List of invocation points")
    timeout: int = Field(30, description="Request timeout in seconds")
    retry_count: int = Field(0, description="Number of retries on failure")
    enabled: bool = Field(True)
    description: str = ""


class ExternalServiceResponse(BaseModel):
    id: str
    name: str
    url: str
    method: str
    invocation_points: list[str]
    enabled: bool
    description: str


class ServiceInvokeRequest(BaseModel):
    service_id: str = Field(..., description="Service ID to invoke")
    context: dict = Field(default_factory=dict, description="Context data to pass to the service")
    invocation_point: Optional[str] = Field(None, description="Invocation point for this call")


class ServiceInvokeResponse(BaseModel):
    service_id: str
    success: bool
    status_code: Optional[int] = None
    response_data: Optional[dict] = None
    error_message: Optional[str] = None
    duration: float = 0.0
