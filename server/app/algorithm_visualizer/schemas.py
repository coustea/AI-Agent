"""算法可视化模块 Pydantic 请求/响应模型。
 * api.py 使用 RunRequest；service.py 返回 dict 自动序列化。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


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
    visualizer_type: str
    difficulty: str
    supported_languages: List[str]


class TemplateResponse(BaseModel):
    """代码模板响应。"""

    domain: str
    algorithm: str
    visualizer_type: str
    language: str
    template_code: str
    default_data: Dict[str, Any]


class RunRequest(BaseModel):
    """运行可视化请求。api.py 直接使用。"""

    domain: str = "data_structure"
    algorithm: str
    visualizer_type: Optional[str] = None
    visualizerType: Optional[str] = None
    language: str
    code: str



class TraceEventResponse(BaseModel):
    """TraceEvent 事件响应。run_result_parser.py 使用。"""

    id: str
    step: int
    domain: str
    visualizer_type: str
    type: str
    line: Optional[int] = None
    state: Dict[str, Any]
    targets: Optional[List[Any]] = None
    message: Optional[str] = None
    formula: Optional[str] = None


class RunSuccessResponse(BaseModel):
    """运行成功响应。service.py 返回 dict 自动序列化。"""

    domain: str
    algorithm: str
    visualizer_type: str
    language: str
    events: List[TraceEventResponse]
    result: Any
    summary: str


class RunErrorResponse(BaseModel):
    """运行失败响应。service.py 返回 dict 自动序列化。"""

    error_type: str
    message: str
    details: Optional[str] = None
