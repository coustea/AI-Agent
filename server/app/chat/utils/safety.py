"""内容安全与防幻觉过滤模块。"""
import re
from typing import NamedTuple

class SafetyResult(NamedTuple):
    has_violation: bool
    sanitized_text: str

class ContentSafetyFilter:
    def __init__(self):
        # 简单的规则库，可扩展
        self.sensitive_patterns = [
            re.compile(r"色情|赌博|毒品|暴力", re.IGNORECASE)
        ]
        
    async def check(self, text: str) -> SafetyResult:
        """检查文本内容并返回处理后的结果。"""
        if not text:
            return SafetyResult(has_violation=False, sanitized_text=text)
            
        sanitized = text
        has_violation = False
        
        for pattern in self.sensitive_patterns:
            if pattern.search(sanitized):
                has_violation = True
                # 简单替换屏蔽词
                sanitized = pattern.sub("***", sanitized)
                
        return SafetyResult(has_violation=has_violation, sanitized_text=sanitized)

safety_filter = ContentSafetyFilter()
