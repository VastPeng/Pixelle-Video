import asyncio
import ipaddress
import json
import re
import time
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from loguru import logger

from pixelle_video.models.external_service import (
    InvocationPoint, ExternalServiceConfig, ServiceInvocationResult,
)
from pixelle_video.exceptions import ExternalServiceError


def validate_service_url(url: str) -> tuple[bool, str]:
    """Validate service URL to prevent SSRF attacks.

    Returns (is_valid, error_message).
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False, f"Unsupported URL scheme: {parsed.scheme}. Only http/https allowed."

        host = parsed.hostname
        if not host:
            return False, "URL must have a hostname"

        # Block internal/private IPs
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False, f"Internal/private IP not allowed: {host}"
        except ValueError:
            # Not an IP, it's a domain name - allow it
            pass

        # Block common internal hostnames
        blocked_hosts = {"localhost", "127.0.0.1", "0.0.0.0", "::1",
                        "metadata.google.internal", "169.254.169.254"}
        if host.lower() in blocked_hosts:
            return False, f"Blocked hostname: {host}"

        return True, ""
    except Exception as e:
        return False, f"Invalid URL: {e}"


def safe_format_template(template: str, context: dict[str, Any]) -> str:
    """Safely format a template string with context variables.

    Uses simple ${var} or {var} replacement instead of Python's str.format()
    to prevent format string injection attacks.
    """
    # Replace ${var} style
    result = re.sub(r'\$\{(\w+)\}', lambda m: str(context.get(m.group(1), '')), template)
    # Replace {var} style (but only for simple identifiers)
    result = re.sub(r'\{(\w+)\}', lambda m: str(context.get(m.group(1), '')), result)
    return result


class ExternalServiceManager:
    """Manages external service invocations across the pipeline lifecycle"""

    def __init__(self, services: Optional[list[ExternalServiceConfig]] = None):
        self._services: dict[str, ExternalServiceConfig] = {}
        self._client: Optional[httpx.AsyncClient] = None
        if services:
            for svc in services:
                self.register(svc)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create shared httpx client for connection pooling"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def close(self):
        """Close the httpx client"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def register(self, service: ExternalServiceConfig) -> None:
        # Validate URL before registering
        is_valid, error = validate_service_url(service.url)
        if not is_valid:
            raise ValueError(f"Invalid service URL '{service.url}': {error}")
        self._services[service.id] = service
        logger.info(f"Registered external service: {service.id} ({service.name})")

    def unregister(self, service_id: str) -> None:
        if service_id in self._services:
            del self._services[service_id]

    def get_service(self, service_id: str) -> Optional[ExternalServiceConfig]:
        return self._services.get(service_id)

    def list_services(self) -> list[ExternalServiceConfig]:
        return list(self._services.values())

    def get_services_for_point(self, point: InvocationPoint) -> list[ExternalServiceConfig]:
        return [
            svc for svc in self._services.values()
            if svc.enabled and point in svc.invocation_points
        ]

    async def invoke(
        self,
        service_id: str,
        context: dict[str, Any],
        invocation_point: Optional[InvocationPoint] = None,
    ) -> ServiceInvocationResult:
        service = self._services.get(service_id)
        if not service:
            return ServiceInvocationResult(
                service_id=service_id,
                success=False,
                error_message=f"Service not found: {service_id}",
                invocation_point=invocation_point,
            )
        if not service.enabled:
            return ServiceInvocationResult(
                service_id=service_id,
                success=False,
                error_message=f"Service disabled: {service_id}",
                invocation_point=invocation_point,
            )
        return await self._invoke_service(service, context, invocation_point)

    async def invoke_all(
        self,
        point: InvocationPoint,
        context: dict[str, Any],
    ) -> list[ServiceInvocationResult]:
        services = self.get_services_for_point(point)
        results = []
        for svc in services:
            result = await self.invoke(svc.id, context, point)
            results.append(result)
        return results

    async def _invoke_service(
        self,
        service: ExternalServiceConfig,
        context: dict[str, Any],
        invocation_point: Optional[InvocationPoint],
    ) -> ServiceInvocationResult:
        start_time = time.time()
        try:
            body = self._build_body(service, context)
            headers = {"Content-Type": "application/json", **service.headers}

            async with httpx.AsyncClient(timeout=service.timeout) as client:
                response = await client.request(
                    method=service.method.value,
                    url=service.url,
                    headers=headers,
                    json=body,
                )

            duration = time.time() - start_time
            try:
                response_data = response.json()
            except Exception:
                response_data = {"raw": response.text}

            if response.status_code >= 400:
                return ServiceInvocationResult(
                    service_id=service.id,
                    success=False,
                    status_code=response.status_code,
                    response_data=response_data,
                    error_message=f"HTTP {response.status_code}",
                    duration=duration,
                    invocation_point=invocation_point,
                )

            return ServiceInvocationResult(
                service_id=service.id,
                success=True,
                status_code=response.status_code,
                response_data=response_data,
                duration=duration,
                invocation_point=invocation_point,
            )
        except Exception as e:
            duration = time.time() - start_time
            return ServiceInvocationResult(
                service_id=service.id,
                success=False,
                error_message=str(e),
                duration=duration,
                invocation_point=invocation_point,
            )

    def _build_body(self, service: ExternalServiceConfig, context: dict[str, Any]) -> dict:
        if service.body_template:
            try:
                return json.loads(service.body_template.format(**context))
            except (KeyError, json.JSONDecodeError):
                pass
        return context
