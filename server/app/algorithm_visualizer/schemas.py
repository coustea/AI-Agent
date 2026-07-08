"""算法可视化模块 Pydantic 请求/响应模型。

当前设计：
1. 前端必须选择语言 language。
2. 前端必须选择算法模板 algorithm。
3. 后端根据 algorithm + language 返回可视化模板代码。
4. 用户基于模板修改代码和数据。
5. 后端只负责编译运行、读取 trace.json、校验事件流。
6. 当前阶段不接入 LLM，不自动插装普通代码。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class LanguageResponse(BaseModel):
    """语言信息响应。"""

    key: str
    label: str
    extension: str


class AlgorithmResponse(BaseModel):
    """算法信息响应。"""

    key: str
    name: str
    domain: str
    visualizerType: str = Field(..., alias="visualizer_type")
    difficulty: str
    supportedLanguages: List[str] = Field(..., alias="supported_languages")

    class Config:
        populate_by_name = True


class TemplateResponse(BaseModel):
    """代码模板响应。"""

    domain: str
    algorithm: str
    visualizerType: str = Field(..., alias="visualizer_type")
    language: str
    templateCode: str = Field(..., alias="template_code")
    defaultData: Dict[str, Any] = Field(..., alias="default_data")
    requiredEvents: List[str] = Field(..., alias="required_events")
    supportedLanguages: List[str] = Field(..., alias="supported_languages")

    model_config = ConfigDict(populate_by_name=True)


class RunRequest(BaseModel):
    """运行可视化请求。

    注意：
    当前阶段不做 LLM 自动插装。
    code 必须是已经包含 tracer 调用的可视化代码，通常来自模板接口。
    """

    domain: str = "all"
    algorithm: str
    visualizerType: Optional[str] = None
    language: str
    code: str
    inputData: Optional[str] = None


class TraceEventResponse(BaseModel):
    """TraceEvent 事件响应。"""

    id: str
    step: int
    domain: str
    visualizerType: Optional[str] = None
    type: str
    line: Optional[int] = None
    state: Dict[str, Any]
    targets: Optional[List[Any]] = None
    message: Optional[str] = None
    formula: Optional[str] = None


class RunSuccessResponse(BaseModel):
    """运行成功响应。"""

    domain: str
    algorithm: str
    visualizerType: str = Field(..., alias="visualizer_type")
    language: str
    events: List[TraceEventResponse]
    result: Any
    summary: str
    stdout: Optional[str] = None

    class Config:
        populate_by_name = True


class RunErrorResponse(BaseModel):
    """运行失败响应。"""

    errorType: str = Field(..., alias="error_type")
    message: str
    details: Optional[str] = None

    class Config:
        populate_by_name = True
