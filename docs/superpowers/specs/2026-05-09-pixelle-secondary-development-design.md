# Pixelle-Video 二次开发设计方案

> 版本: 1.0
> 日期: 2026-05-09
> 状态: 待审核

---

## 一、项目概述

### 1.1 背景

基于 Pixelle-Video (AIDC-AI) 进行二次开发，增强以下能力：
- 集成 Coze 视频剪辑工具插件，提升后期合成能力
- 支持外部服务/业务接口集成，贯穿视频生成全流程
- 重新设计 Web UI 和 API 接口，供 OpenClaw Agent 调用

### 1.2 设计范围

| 模块 | 说明 | 优先级 |
|------|------|--------|
| Coze 插件集成 | 视频后期处理能力增强 | P0 |
| 外部服务集成 | 个人业务接口全流程支持 | P0 |
| API 节点化设计 | 管线拆解为可独立调用的节点 | P0 |
| Web UI 调整 | 后期处理配置、外部服务管理界面 | P1 |
| 数据模型与配置 | 持久化与配置结构设计 | P2 |

### 1.3 不在范围内

- 双算力模式（RunningHub + Selfhost）：Pixelle 已有能力，不在本次设计范围
- MCP Server：暂不设计，后续迭代考虑

---

## 二、整体架构

### 2.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                      OpenClaw Agent                              │
│  (任务调度、节点编排、外部服务注入)                                  │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST API
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Pipeline Node API Layer                        │
├─────────────────────────────────────────────────────────────────┤
│  /content          /visual          /assets          /compose   │
│  ├─ generate       ├─ plan          ├─ tts           ├─ concat │
│  └─ split          └─ storyboard    ├─ image         └─ bgm    │
│                                     ├─ video-clip              │
│                                     └─ frame                   │
├─────────────────────────────────────────────────────────────────┤
│  /post-process                                                   │
│  ├─ analyze      (资产分析)                                       │
│  ├─ decide       (工具链决策)                                     │
│  └─ execute      (执行剪辑)                                       │
├─────────────────────────────────────────────────────────────────┤
│  /workflow                                                       │
│  ├─ create       (创建工作流)                                     │
│  ├─ execute      (执行工作流)                                     │
│  └─ status       (查询状态)                                       │
├─────────────────────────────────────────────────────────────────┤
│  /external-services                                              │
│  ├─ services      (服务列表)                                       │
│  ├─ register      (注册服务)                                       │
│  └─ invoke        (调用服务)                                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Core Services  │ │  Coze Plugin    │ │ External APIs   │
│  (现有能力)      │ │  (后期剪辑)      │ │ (个人业务)       │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### 2.2 核心模块职责

| 模块 | 职责 |
|------|------|
| **PostProcessingManager** | 后期处理总控，协调资产分析、工具决策、执行调度 |
| **AssetAnalyzer** | 分析视频资产（分辨率、时长、音频质量、字幕状态等） |
| **ToolChainDecider** | 基于规则+LLM混合决策，推荐最优工具链 |
| **CozePluginClient** | 封装 Coze MCP 插件 API 调用 |
| **ExternalServiceManager** | 管理外部服务的注册、发现、调用 |
| **ServiceRegistry** | 存储外部服务配置（URL、认证、调用时机等） |
| **ServiceInvoker** | 执行外部服务调用，处理错误和重试 |

---

## 三、Coze 插件集成设计

### 3.1 集成方式

**方案选择**: Pixelle 内部集成，在管线中直接调用 Coze 插件 API 作为后期合成步骤。

**定位**: 可选后处理模块，用户可选择是否启用 Coze 剪辑能力。

### 3.2 工具链决策策略（混合模式）

结合配置预设 + 智能补充：

1. **基础规则**: 配置文件定义默认工具链
2. **智能增强**: LLM 分析资产特征，在默认链基础上增减工具
3. **用户覆盖**: UI 层面允许用户手动调整最终工具链

### 3.3 工具链配置结构

```yaml
# config/post_processing.yaml
coze_plugin:
  enabled: true
  api_token: ${COZE_API_TOKEN}
  plugin_id: "7514607540051640360"
  mcp_url: "https://mcp.coze.cn/v1/plugins/7514607540051640360"

toolchain_presets:
  product_video:
    name: "产品视频"
    default_tools:
      - tool: add_subtitles
        config:
          font_size: 24
          position: bottom
      - tool: video_super_resolution
        config:
          target_resolution: "1080P"
    conditions:
      - if: "duration > 60"
        then_add: [video_speed]
  
  tutorial_video:
    name: "教程视频"
    default_tools:
      - tool: add_subtitles
        config:
          font_size: 28
      - tool: audio_denoise

  marketing_video:
    name: "营销视频"
    default_tools:
      - tool: concat_videos
        config:
          transition: fade
      - tool: add_text
      - tool: video_hdr

  news_video:
    name: "新闻视频"
    default_tools:
      - tool: add_subtitles
      - tool: video_speed
        config:
          speed: 1.1

smart_decision:
  enabled: true
  llm_model: "gpt-4o-mini"
  analysis_features:
    - resolution
    - duration
    - has_audio
    - has_subtitle
    - audio_quality
    - frame_rate
```

### 3.4 资产分析输出结构

```python
@dataclass
class VideoAssetAnalysis:
    """视频资产分析结果"""
    # 基础信息
    duration: float              # 时长(秒)
    resolution: tuple[int, int]  # 分辨率
    frame_rate: float            # 帧率
    file_size: int               # 文件大小
    
    # 音频特征
    has_audio: bool
    audio_duration: float
    audio_quality: str           # "high", "medium", "low"
    has_speech: bool             # 是否有人声
    
    # 字幕特征
    has_subtitle: bool
    subtitle_language: str | None
    
    # 质量评估
    needs_upscale: bool          # 是否需要超分
    needs_denoise: bool          # 是否需要降噪
    needs_frame_insert: bool     # 是否需要插帧
    
    # 推荐工具链
    recommended_tools: list[str]
    recommendation_reason: str   # LLM决策理由
```

### 3.5 工具链执行流程

```
视频生成完成
    │
    ▼
┌─────────────────────────────────┐
│ 1. 资产分析                      │
│    AssetAnalyzer.analyze(video) │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 2. 工具链决策                     │
│    ├─ 加载预设配置                │
│    ├─ LLM智能补充/调整            │
│    └─ 用户手动覆盖(如有)          │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 3. 工具链执行                     │
│    for tool in toolchain:       │
│      result = execute(tool)     │
│      update_context(result)     │
└─────────────────────────────────┘
    │
    ▼
输出最终视频
```

### 3.6 Coze 插件 API 调用封装

```python
class CozePluginClient:
    """Coze MCP插件客户端"""
    
    def __init__(self, api_token: str, plugin_id: str):
        self.base_url = "https://mcp.coze.cn/v1/plugins"
        self.headers = {"Authorization": f"Bearer {api_token}"}
        self.plugin_id = plugin_id
    
    async def add_subtitles(
        self,
        video_url: str,
        subtitle_url: str | None = None,
        text_list: list | None = None,
        subtitle_config: dict | None = None
    ) -> str:
        """添加字幕"""
        ...
    
    async def concat_videos(
        self,
        videos: list[str],
        transitions: list[dict]
    ) -> str:
        """视频拼接"""
        ...
    
    async def video_super_resolution(
        self,
        video_url: str,
        target_resolution: str
    ) -> str:
        """视频超分辨率"""
        ...
    
    # 其他20+工具方法...
```

### 3.7 Coze 插件可用工具列表

| 工具 | 功能 | 抵扣系数(1080P) |
|------|------|-----------------|
| add_subtitles | 添加字幕 | 6 |
| concat_videos | 视频拼接+转场 | 6 |
| compile_video_audio | 音视频合成 | 6 |
| compile_image_audio | 图片+音频合成视频 | 6 |
| video_super_resolution | 视频超分辨率 | 150 |
| video_hdr | SDR转HDR | 150 |
| insert_frame | 视频插帧 | 150 |
| audio_to_subtitle | 语音转字幕 | 5 |
| audio_separate | 音频分离 | 7 |
| audio_denoise | 音频降噪 | 6 |
| video_trim | 视频裁剪 | 6 |
| video_speed | 调整播放速度 | 6 |
| video_fps | 转换帧率 | 6 |
| video_flip | 视频翻转 | 6 |
| add_subvideo | 添加水印 | 6 |
| add_text | 添加文字水印 | 6 |
| image_to_video | 图片转视频 | 6 |
| audio_mix | 音频混音 | 6 |
| ajust_audio_volume | 调整音量 | 6 |
| ajust_video_resolution | 调整分辨率 | 6 |
| audio_loudness_normalization | 音量均衡 | 6 |

---

## 四、外部服务集成设计

### 4.1 服务调用时机

外部 API 调用贯穿全流程：

| 阶段 | 调用时机点 | 说明 |
|------|-----------|------|
| 输入阶段 | BEFORE_CONTENT_GENERATION | 内容生成前，获取内容源 |
| 输入阶段 | BEFORE_VISUAL_PLANNING | 视觉规划前 |
| 处理阶段 | DURING_NARRATION | 解说词生成时，可替换LLM |
| 处理阶段 | DURING_IMAGE_GEN | 图像生成时，查询素材库 |
| 处理阶段 | DURING_TTS | TTS生成时，自定义TTS |
| 输出阶段 | AFTER_VIDEO_COMPLETE | 视频完成后，推送存储 |
| 输出阶段 | AFTER_POST_PROCESSING | 后期处理后，发布平台 |

### 4.2 服务注册结构

```yaml
# config/external_services.yaml
services:
  # 输入阶段服务
  content_source:
    name: "内容源服务"
    url: "https://your-api.com/content"
    method: "GET"
    auth:
      type: "bearer"
      token: ${CONTENT_API_TOKEN}
    timeout: 30
    retry: 3
    invocation_points:
      - "before_content"
    response_mapping:
      title: "data.title"
      content: "data.body"
  
  # 处理阶段服务
  custom_llm:
    name: "自定义LLM"
    url: "https://your-llm.com/v1/chat"
    method: "POST"
    auth:
      type: "bearer"
      token: ${CUSTOM_LLM_TOKEN}
    invocation_points:
      - "during_narration"
  
  # 输出阶段服务
  storage_service:
    name: "存储服务"
    url: "https://your-storage.com/upload"
    method: "POST"
    auth:
      type: "bearer"
      token: ${STORAGE_TOKEN}
    invocation_points:
      - "after_post"
```

### 4.3 服务调用器设计

```python
@dataclass
class ServiceConfig:
    """外部服务配置"""
    name: str
    url: str
    method: str
    auth: dict
    timeout: int = 30
    retry: int = 3
    request_template: dict | None = None
    response_mapping: dict | None = None

class ServiceInvoker:
    """服务调用器"""
    
    async def invoke(
        self,
        service: ServiceConfig,
        context: dict,
        invocation_point: ServiceInvocationPoint
    ) -> dict:
        """
        调用外部服务
        
        Args:
            service: 服务配置
            context: 当前管线上下文
            invocation_point: 调用时机点
        
        Returns:
            服务响应数据
        """
        # 1. 构建请求（模板替换）
        request_data = self._build_request(service, context)
        
        # 2. 发送请求（带认证、超时、重试）
        response = await self._send_request(service, request_data)
        
        # 3. 映射响应数据
        mapped_data = self._map_response(service, response)
        
        return mapped_data
```

### 4.4 管线集成点

```
LinearVideoPipeline 8步生命周期
    │
    ├── Phase 1: setup_environment
    │       └─ [调用点] BEFORE_CONTENT_GENERATION
    │
    ├── Phase 2: generate_content
    │       └─ [调用点] DURING_NARRATION
    │
    ├── Phase 3: plan_visuals
    │       └─ [调用点] BEFORE_VISUAL_PLANNING
    │
    ├── Phase 4: produce_assets
    │       ├─ [调用点] DURING_IMAGE_GEN
    │       └─ [调用点] DURING_TTS
    │
    ├── Phase 5: post_production
    │       └─ (现有FFmpeg处理)
    │
    ├── Phase 6: Coze后期处理 (新增，可选)
    │       └─ PostProcessingManager.execute()
    │
    ├── Phase 7: finalize
    │       ├─ [调用点] AFTER_VIDEO_COMPLETE
    │       ├─ [调用点] AFTER_POST_PROCESSING
    │       └─ 输出最终结果
    │
    └── Phase 8: cleanup
```

---

## 五、API 接口设计

### 5.1 管线节点 API

```
/api/pipeline/nodes
│
├── /content
│   ├── POST /generate      # 生成解说词
│   └── POST /split         # 拆分场景
│
├── /visual
│   ├── POST /plan          # 规划视觉
│   └── POST /storyboard    # 创建分镜
│
├── /assets
│   ├── POST /tts           # TTS生成音频
│   ├── POST /image         # 图像生成
│   ├── POST /video-clip    # 视频片段生成
│   └── POST /frame         # 帧渲染
│
├── /compose
│   ├── POST /concat        # 视频拼接
│   └── POST /bgm           # 添加BGM
│
└── /post-process
    ├── POST /analyze       # 资产分析
    ├── POST /decide        # 工具链决策
    └── POST /execute       # 执行剪辑
```

### 5.2 工作流编排 API

```
/api/pipeline/workflow
├── POST /create            # 创建工作流实例
├── GET  /{workflow_id}     # 获取工作流状态
├── POST /{workflow_id}/execute  # 执行工作流
└── POST /{workflow_id}/abort    # 中止工作流
```

### 5.3 外部服务 API

```
/api/external-services
├── GET  /services          # 获取已注册服务列表
├── POST /register          # 注册新服务
├── PUT  /services/{id}     # 更新服务配置
├── DELETE /services/{id}   # 删除服务
├── POST /invoke/{id}       # 手动调用服务
└── GET  /invocation-points # 获取可用调用时机点
```

### 5.4 节点请求/响应示例

**POST /api/pipeline/nodes/content/generate**

```json
// Request
{
  "topic": "新款智能手机功能介绍",
  "style": "informative",
  "n_scenes": 5,
  "min_words": 50,
  "max_words": 100,
  "external_content": null
}

// Response
{
  "narrations": [
    "这款智能手机搭载了最新的处理器...",
    "拍照功能方面...",
    "..."
  ],
  "titles": ["性能", "拍照", "续航", "屏幕", "总结"],
  "total_words": 450
}
```

**POST /api/pipeline/nodes/post-process/analyze**

```json
// Request
{
  "video_url": "https://.../output/xxx/final.mp4",
  "video_type": "product_video"
}

// Response
{
  "analysis": {
    "duration": 45.2,
    "resolution": [1280, 720],
    "frame_rate": 24.0,
    "has_audio": true,
    "audio_quality": "medium",
    "has_subtitle": false,
    "needs_upscale": true
  },
  "recommended_tools": [
    {
      "tool": "add_subtitles",
      "reason": "视频无字幕，建议添加",
      "config": {"font_size": 24}
    },
    {
      "tool": "video_super_resolution",
      "reason": "当前720P，建议提升至1080P",
      "config": {"target_resolution": "1080P"}
    }
  ],
  "estimated_cost": {
    "credits": 45,
    "duration_minutes": 2
  }
}
```

### 5.5 工作流编排示例

```python
# OpenClaw Agent 调用示例

# 1. 创建工作流
workflow = await client.post("/api/pipeline/workflow/create", {
    "name": "产品视频生成",
    "steps": [
        {
            "node": "content.generate",
            "params": {"topic": "新款智能手机功能介绍", "n_scenes": 5},
            "external_service": "product_db"
        },
        {
            "node": "visual.plan",
            "params": {"style": "tech"},
            "depends_on": ["step_0"]
        },
        {
            "node": "assets.tts",
            "params": {},
            "depends_on": ["step_0"]
        },
        {
            "node": "assets.image",
            "params": {},
            "depends_on": ["step_1"]
        },
        {
            "node": "compose.concat",
            "params": {},
            "depends_on": ["step_2", "step_3"]
        },
        {
            "node": "post-process.analyze",
            "params": {},
            "depends_on": ["step_4"]
        },
        {
            "node": "post-process.execute",
            "params": {"tools": "auto"},
            "depends_on": ["step_5"]
        }
    ],
    "on_complete": {
        "external_service": "publish_platform",
        "params": {"platform": "douyin"}
    }
})

# 2. 执行工作流
result = await client.post(f"/api/pipeline/workflow/{workflow.id}/execute")

# 3. 查询状态
status = await client.get(f"/api/pipeline/workflow/{workflow.id}")
```

---

## 六、Web UI 设计

### 6.1 UI 整体布局

```
┌─────────────────────────────────────────────────────────────────┐
│  🎬 Pixelle-Video                              [语言] [设置]     │
├─────────────────────────────────────────────────────────────────┤
│  [标准视频] [素材视频] [数字人] [图生视频] [动作迁移]              │
├──────────────────────────┬──────────────────────────────────────┤
│      视频生成配置          │        后期处理配置 (新增)            │
│                          │                                      │
│  文案输入:                │  Coze剪辑: [开关]                     │
│  ┌────────────────────┐  │  ├─ 预设: [下拉选择]                  │
│  │ [主题] 正文内容...   │  │  │   产品视频 / 教程视频 / ...        │
│  │ /选择主题...         │  │  ├─ 智能决策: [开关]                 │
│  └────────────────────┘  │  ├─ 工具链预览:                       │
│                          │  │   ✓ add_subtitles                   │
│  场景数: [5]             │  │   ✓ video_super_resolution          │
│  模板: [下拉选择]        │  │   ○ audio_denoise                   │
│                          │  │   [手动调整]                        │
│                          │  └─ 输出分辨率: [1080P]                │
│                          │    预估费用: 45积分                    │
├──────────────────────────┴──────────────────────────────────────┤
│                    外部服务配置 (新增)                            │
│  [输入阶段] [处理阶段] [输出阶段]                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ 已注册服务:                                                │ │
│  │  • 内容源服务 [配置] [测试]                                 │ │
│  │  • 产品数据库 [配置] [测试]                                 │ │
│  │  • 存储服务   [配置] [测试]                                 │ │
│  │ [+ 添加新服务]                                             │ │
│  └────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  [生成视频]                                                       │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 补充说明

> 在后续开发任务拆分时，可参考现有 web UI 进行设计，保持风格一致性。

### 6.3 主题选择功能

文案输入框支持 `/` 触发主题选择：

```
格式: [主题] 正文内容

示例:
  / → 弹出主题选择器
  选择"人工智能" → [人工智能] 介绍一下人工智能的发展历史...
```

后端解析逻辑：
```python
def parse_topic_content(text: str) -> tuple[str | None, str]:
    """解析主题和正文"""
    import re
    match = re.match(r'\[([^\]]+)\]\s*(.*)', text)
    if match:
        return match.group(1), match.group(2)
    return None, text
```

---

## 七、数据模型与配置

### 7.1 核心数据模型

```python
# pixelle_video/models/post_processing.py

class VideoType(Enum):
    PRODUCT = "product_video"
    TUTORIAL = "tutorial_video"
    MARKETING = "marketing_video"
    NEWS = "news_video"
    STANDARD = "standard"

class CozeTool(Enum):
    ADD_SUBTITLES = "add_subtitles"
    CONCAT_VIDEOS = "concat_videos"
    VIDEO_SUPER_RESOLUTION = "video_super_resolution"
    # ... 其他工具

@dataclass
class ToolChainConfig:
    tool: CozeTool
    enabled: bool = True
    config: dict = field(default_factory=dict)
    condition: Optional[str] = None

@dataclass
class PostProcessingPreset:
    name: str
    display_name: str
    video_type: VideoType
    default_tools: list[ToolChainConfig]
    description: str = ""

@dataclass
class PostProcessingResult:
    success: bool
    input_video_url: str
    output_video_url: Optional[str] = None
    applied_tools: list[str] = field(default_factory=list)
    processing_time: float = 0.0
    credits_used: int = 0
    error_message: Optional[str] = None
```

```python
# pixelle_video/models/external_service.py

class ServiceStage(Enum):
    INPUT = "input"
    PROCESSING = "processing"
    OUTPUT = "output"

class AuthType(Enum):
    BEARER = "bearer"
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    NONE = "none"

class InvocationPoint(Enum):
    BEFORE_CONTENT_GENERATION = "before_content"
    BEFORE_VISUAL_PLANNING = "before_visual"
    DURING_NARRATION = "during_narration"
    DURING_IMAGE_GEN = "during_image"
    DURING_TTS = "during_tts"
    AFTER_VIDEO_COMPLETE = "after_video"
    AFTER_POST_PROCESSING = "after_post"

@dataclass
class ExternalServiceConfig:
    id: str
    name: str
    url: str
    method: str = "GET"
    stage: ServiceStage = ServiceStage.PROCESSING
    auth: AuthConfig = field(default_factory=AuthConfig)
    timeout: int = 30
    retry: int = 3
    invocation_points: list[InvocationPoint] = field(default_factory=list)
    enabled: bool = True
```

### 7.2 数据库模型（任务持久化）

> 注：数据模型与配置部分后期迭代，本次设计暂不实现。

```python
# api/tasks/models.py 增强

class WorkflowTask(Base):
    __tablename__ = "workflow_tasks"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    status = Column(String, default="pending")
    workflow_definition = Column(JSON)
    current_step = Column(String)
    completed_steps = Column(JSON, default=list)
    step_results = Column(JSON, default=dict)
    
    # 后期处理
    post_processing_enabled = Column(Boolean, default=False)
    post_processing_preset = Column(String)
    post_processing_tools = Column(JSON)
    post_processing_result = Column(JSON)
    
    # 外部服务
    service_invocations = Column(JSON, default=list)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # 结果
    output_video_url = Column(String)
    duration = Column(Float)
    credits_used = Column(Float, default=0)
    error_message = Column(String)
```

---

## 八、错误处理与测试

### 8.1 异常类定义

```python
# pixelle_video/exceptions.py

class PixelleVideoError(Exception):
    """基础异常"""
    pass

class CozePluginError(PixelleVideoError):
    """Coze插件调用异常"""
    def __init__(self, tool: str, message: str, credits_charged: int = 0):
        self.tool = tool
        self.message = message
        self.credits_charged = credits_charged

class ExternalServiceError(PixelleVideoError):
    """外部服务调用异常"""
    def __init__(self, service_id: str, message: str, retry_count: int = 0):
        self.service_id = service_id
        self.message = message
        self.retry_count = retry_count

class WorkflowExecutionError(PixelleVideoError):
    """工作流执行异常"""
    def __init__(self, workflow_id: str, step: str, message: str):
        self.workflow_id = workflow_id
        self.step = step
        self.message = message
```

### 8.2 重试策略

```python
from tenacity import retry, stop_after_attempt, wait_exponential

def coze_retry(max_attempts: int = 3):
    """Coze插件调用重试"""
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )

def service_retry(max_attempts: int = 3):
    """外部服务调用重试"""
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        reraise=True
    )
```

### 8.3 测试清单

```markdown
## Coze插件集成
- [ ] add_subtitles工具调用
- [ ] video_super_resolution工具调用
- [ ] concat_videos工具调用
- [ ] 工具链顺序执行
- [ ] 工具链失败回滚
- [ ] 费用预估准确性

## 外部服务集成
- [ ] 服务注册/注销
- [ ] Bearer认证
- [ ] API Key认证
- [ ] 服务调用超时处理
- [ ] 服务调用重试
- [ ] 响应映射正确性

## 工作流执行
- [ ] 单节点执行
- [ ] 多节点顺序执行
- [ ] 节点依赖解析
- [ ] 外部服务注入
- [ ] 工作流中止
- [ ] 工作流状态查询

## 端到端测试
- [ ] 标准视频生成+后期处理
- [ ] 产品视频预设工作流
- [ ] 教程视频预设工作流
- [ ] 外部服务全流程集成
```

---

## 九、附录

### 9.1 Coze 视频剪辑工具插件信息

- **插件 ID**: 7514607540051640360
- **MCP URL**: https://mcp.coze.cn/v1/plugins/7514607540051640360
- **QPS 限额**: 1次/秒
- **计费方式**: 基准计费项 × 抵扣系数 × 时长(分钟)

### 9.2 参考文档

- Coze 视频剪辑工具插件文档: https://docs.coze.cn/guides/video_Editing_plugin
- Pixelle-Video 项目路径: /home/vastpeng/projects/Pixelle-Video/
- 项目记忆库: ~/.claude/projects/-home-vastpeng-projects-Pixelle-Video/memory/

### 9.3 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0 | 2026-05-09 | 初始设计版本 |

---

## 十、待办事项

> 后续迭代考虑：

1. MCP Server 设计（供 OpenClaw 直接调用）
2. 数据模型与配置持久化实现
3. 移动端 UI 适配
4. 批量视频生成能力
5. 视频模板市场
