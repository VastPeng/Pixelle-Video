from fastapi import APIRouter, HTTPException

from api.schemas.external_service import (
    ExternalServiceCreateRequest, ExternalServiceResponse,
    ServiceInvokeRequest, ServiceInvokeResponse,
)
from pixelle_video.models.external_service import (
    InvocationPoint, HttpMethod, ExternalServiceConfig,
)
from pixelle_video.services.external_service_manager import ExternalServiceManager

router = APIRouter(prefix="/external-services", tags=["External Services"])

_manager = ExternalServiceManager()


@router.get("/services", response_model=list[ExternalServiceResponse])
async def list_services():
    services = _manager.list_services()
    return [
        ExternalServiceResponse(
            id=s.id, name=s.name, url=s.url, method=s.method.value,
            invocation_points=[p.value for p in s.invocation_points],
            enabled=s.enabled, description=s.description,
        )
        for s in services
    ]


@router.post("/register")
async def register_service(request: ExternalServiceCreateRequest):
    invocation_points = []
    for p in request.invocation_points:
        try:
            invocation_points.append(InvocationPoint(p))
        except ValueError:
            pass

    config = ExternalServiceConfig(
        id=request.id,
        name=request.name,
        url=request.url,
        method=HttpMethod(request.method),
        headers=request.headers,
        body_template=request.body_template,
        invocation_points=invocation_points,
        timeout=request.timeout,
        retry_count=request.retry_count,
        enabled=request.enabled,
        description=request.description,
    )
    _manager.register(config)
    return {"status": "registered", "id": request.id}


@router.delete("/services/{service_id}")
async def delete_service(service_id: str):
    svc = _manager.get_service(service_id)
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")
    _manager.unregister(service_id)
    return {"status": "deleted", "id": service_id}


@router.post("/invoke", response_model=ServiceInvokeResponse)
async def invoke_service(request: ServiceInvokeRequest):
    invocation_point = None
    if request.invocation_point:
        try:
            invocation_point = InvocationPoint(request.invocation_point)
        except ValueError:
            pass

    result = await _manager.invoke(
        request.service_id, request.context, invocation_point
    )
    return ServiceInvokeResponse(
        service_id=result.service_id,
        success=result.success,
        status_code=result.status_code,
        response_data=result.response_data,
        error_message=result.error_message,
        duration=result.duration,
    )


@router.get("/invocation-points")
async def get_invocation_points():
    return [{"name": p.value} for p in InvocationPoint]
