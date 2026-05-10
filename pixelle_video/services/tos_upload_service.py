import asyncio
import os
from datetime import date
from typing import Optional
from urllib.parse import urlparse

from loguru import logger
from pixelle_video.exceptions import TosUploadError


_MIME_MAP = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "gif": "image/gif", "webp": "image/webp",
    "mp4": "video/mp4", "webm": "video/webm",
    "mov": "video/quicktime", "avi": "video/x-msvideo",
    "wav": "audio/wav", "mp3": "audio/mpeg",
    "srt": "text/srt", "ass": "text/ass",
    "aac": "audio/aac", "flac": "audio/flac", "mkv": "video/x-matroska",
}


class TosUploadService:
    """火山引擎 TOS 上传服务（S3 兼容接口）

    Coze 插件要求公网可访问视频 URL，本服务将本地视频上传到 TOS 获取公网 URL。
    TOS 必须使用 virtual-hosted addressing style，否则报 InvalidPathAccess。
    """

    def __init__(
        self,
        access_key: str = "",
        secret_key: str = "",
        bucket: str = "video-edit",
        endpoint: str = "https://tos-s3-cn-shanghai.volces.com",
        region: str = "cn-shanghai",
        key_prefix: str = "pixelle",
    ):
        self.access_key = access_key.strip()
        self.secret_key = secret_key.strip()
        self.bucket = bucket.strip() or "video-edit"
        self.endpoint = endpoint.strip() or "https://tos-s3-cn-shanghai.volces.com"
        self.region = region.strip() or "cn-shanghai"
        self.key_prefix = key_prefix.strip() or "pixelle"
        self._client = None
        self.enabled = bool(self.access_key and self.secret_key)

    def _get_client(self):
        if self._client is not None:
            return self._client
        if not self.enabled:
            return None
        try:
            import boto3
            from botocore.config import Config

            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint,
                region_name=self.region,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                config=Config(
                    signature_version="s3v4",
                    s3={"addressing_style": "virtual"},
                ),
            )
            return self._client
        except ImportError as e:
            logger.warning(f"TOS 客户端初始化失败: boto3 未安装 - {e}")
            return None
        except Exception as e:
            logger.warning(f"TOS 客户端初始化失败: {e}")
            return None

    def _content_type(self, path: str) -> str:
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        return _MIME_MAP.get(ext, "application/octet-stream")

    def _build_public_url(self, key: str) -> str:
        """Build public URL using configured endpoint and bucket"""
        # Extract host from endpoint (e.g., "tos-s3-cn-shanghai.volces.com")
        parsed = urlparse(self.endpoint)
        host = parsed.netloc
        return f"https://{self.bucket}.{host}/{key}"

    async def upload_file(
        self, local_path: str, key_prefix: Optional[str] = None
    ) -> tuple[Optional[str], Optional[str]]:
        """Upload local file to TOS, returns (public URL, error message)"""
        # Run sync upload in thread to avoid blocking event loop
        return await asyncio.to_thread(self._upload_file_sync, local_path, key_prefix)

    def _upload_file_sync(
        self, local_path: str, key_prefix: Optional[str] = None
    ) -> tuple[Optional[str], Optional[str]]:
        """Synchronous upload implementation"""
        prefix = key_prefix or self.key_prefix
        client = self._get_client()
        if not client:
            return None, "TOS 未配置（缺少 AccessKey/SecretKey）"

        local_path = os.path.abspath(os.path.normpath(local_path.strip()))
        if not os.path.isfile(local_path):
            return None, f"文件不存在: {local_path}"

        name = os.path.basename(local_path)
        today = date.today().isoformat()
        # Add UUID suffix to prevent key collision
        import uuid
        unique_suffix = uuid.uuid4().hex[:8]
        name_parts = name.rsplit(".", 1)
        if len(name_parts) == 2:
            key = f"{prefix}/{today}/{name_parts[0]}_{unique_suffix}.{name_parts[1]}"
        else:
            key = f"{prefix}/{today}/{name}_{unique_suffix}"
        content_type = self._content_type(local_path)

        try:
            client.upload_file(
                local_path,
                self.bucket,
                key,
                ExtraArgs={"ContentType": content_type},
            )
            url = self._build_public_url(key)
            logger.info(f"TOS 上传成功: {name} -> {url}")
            return url, None
        except Exception as e:
            err_msg = str(e).strip() or "上传失败"
            logger.error(f"TOS 上传失败 {local_path}: {e}")
            return None, f"上传失败: {err_msg}"

    def upload_and_get_url(self, local_path: str) -> str:
        """Upload file and return URL, raises TosUploadError on failure"""
        import asyncio
        url, error = asyncio.get_event_loop().run_until_complete(self.upload_file(local_path))
        if error:
            raise TosUploadError(local_path=local_path, message=error)
        return url
