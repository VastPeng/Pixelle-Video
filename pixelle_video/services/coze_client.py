import json
from typing import Any, Optional
import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from pixelle_video.exceptions import CozePluginError


class CozePluginClient:
    """Coze MCP Plugin Client for video editing tools"""

    def __init__(self, api_token: str, plugin_id: str = "7514607540051640360"):
        self.api_token = api_token
        self.plugin_id = plugin_id
        self.base_url = f"https://mcp.coze.cn/v1/plugins/{plugin_id}"
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }
        self._tools_cache: Optional[list[dict]] = None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    async def _send_request(self, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(self.base_url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()

    async def list_tools(self) -> list[dict]:
        if self._tools_cache is not None:
            return self._tools_cache
        payload = {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
        result = await self._send_request(payload)
        self._tools_cache = result.get("result", {}).get("tools", [])
        return self._tools_cache

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict:
        logger.info(f"Coze plugin: calling {tool_name}")
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
            "id": 2,
        }
        try:
            result = await self._send_request(payload)
            content = result.get("result", {}).get("content", [])
            for item in content:
                if item.get("type") == "text":
                    try:
                        return json.loads(item["text"])
                    except json.JSONDecodeError:
                        return {"text": item["text"]}
            return result.get("result", {})
        except Exception as e:
            raise CozePluginError(tool=tool_name, message=str(e))

    # Convenience methods for common tools
    async def add_subtitles(
        self,
        video_url: str,
        subtitle_url: Optional[str] = None,
        text_list: Optional[list[dict]] = None,
        subtitle_config: Optional[dict] = None,
    ) -> dict:
        args = {"video": video_url}
        if subtitle_url:
            args["subtitle_url"] = subtitle_url
        if text_list:
            args["text_list"] = text_list
        if subtitle_config:
            args["subtitle_config"] = subtitle_config
        return await self.call_tool("add_subtitles", args)

    async def video_super_resolution(
        self, video_url: str, resolution: str = "1080p"
    ) -> dict:
        return await self.call_tool("video_super_resolution", {
            "video": video_url,
            "resolution": resolution,
        })

    async def concat_videos(
        self, videos: list[str], transitions: Optional[list[str]] = None
    ) -> dict:
        args = {"videos": videos}
        if transitions:
            args["transitions"] = transitions
        return await self.call_tool("concat_videos", args)

    async def audio_denoise(self, video_url: str) -> dict:
        return await self.call_tool("audio_denoise", {"video": video_url})

    async def video_speed(self, video_url: str, speed: float) -> dict:
        return await self.call_tool("video_speed", {"video": video_url, "speed": speed})

    async def video_hdr(self, video_url: str) -> dict:
        return await self.call_tool("video_hdr", {"video": video_url})

    async def insert_frame(self, video_url: str) -> dict:
        return await self.call_tool("insert_frame", {"video": video_url})

    async def audio_to_subtitle(
        self, video_url: str, subtitle_type: str = "srt"
    ) -> dict:
        return await self.call_tool("audio_to_subtitle", {
            "source": video_url,
            "subtitle_type": subtitle_type,
        })
