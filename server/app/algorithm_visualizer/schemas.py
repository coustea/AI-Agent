"""算法可视化模块 Pydantic 请求/响应模型。

当前设计：
1. 前端必须选择语言 language。
2. 前端必须选择算法模板 algorithm。
3. 后端根据 algorithm + language 返回干净模板代码（无 tracer）。
4. 用户基于模板修改代码和数据。
5. 运行时后端自动插装 tracer 调用，编译运行，读取 trace.json，校验事件流。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# 支持的语言信息响应模型
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

    code 可以是干净算法代码（无 tracer），后端会自动插装。
    也可以是已包含 tracer 调用的代码，后端直接执行。
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
