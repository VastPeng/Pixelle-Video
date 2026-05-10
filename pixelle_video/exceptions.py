class PixelleVideoError(Exception):
    """Pixelle-Video base exception"""
    pass


class CozePluginError(PixelleVideoError):
    """Coze plugin invocation error"""
    def __init__(self, tool: str, message: str, credits_charged: int = 0):
        self.tool = tool
        self.message = message
        self.credits_charged = credits_charged
        super().__init__(f"Coze plugin [{tool}] failed: {message}")


class ExternalServiceError(PixelleVideoError):
    """External service invocation error"""
    def __init__(self, service_id: str, message: str, retry_count: int = 0):
        self.service_id = service_id
        self.message = message
        self.retry_count = retry_count
        super().__init__(f"External service [{service_id}] failed: {message}")


class TosUploadError(PixelleVideoError):
    """TOS upload error"""
    def __init__(self, local_path: str, message: str):
        self.local_path = local_path
        self.message = message
        super().__init__(f"TOS upload [{local_path}] failed: {message}")


class WorkflowExecutionError(PixelleVideoError):
    """Workflow execution error"""
    def __init__(self, workflow_id: str, step: str, message: str):
        self.workflow_id = workflow_id
        self.step = step
        self.message = message
        super().__init__(f"Workflow [{workflow_id}] step [{step}] failed: {message}")
