"""
SkillsManager: 专门的 AI Agent 技能管理器。

负责从配置的 skills 目录下加载 SKILL.md 文件，将其解析为 LangChain Tools。
Agent 可以通过调用 `activate_skill` 工具来获取特定领域的专家指令。

用法：
    from app.utils.skills_manager import skills_manager

    # 加载所有技能
    skills_manager.load_all_skills()

    # 获取包含激活工具的列表，用于绑定到 LLM
    tools = skills_manager.get_langchain_tools()
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel

from app.core.logging import get_logger

logger = get_logger(__name__)

# 用于解析 Markdown Frontmatter 的正则表达式
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# 获取 server/ 根目录
SERVER_DIR = Path(__file__).resolve().parents[2]


class SkillConfig(BaseModel):
    """表示一个解析后的专家技能。"""

    name: str  # 技能唯一标识符，例如 "docx"
    description: str  # 技能的能力描述，用于提示 LLM 什么时候激活它
    location: str  # SKILL.md 所在绝对路径
    instructions: str  # 去除 frontmatter 之后的正文内容


class SkillsManager:
    """管理 Agent 的增强技能 (Prompt-based Skills)"""

    def __init__(self, base_dirs: List[Path] | None = None):
        """
        初始化 SkillsManager。

        Args:
            base_dirs: 技能根目录列表。若不传，则尝试从环境变量 SKILLS_DIR 读取（相对于 SERVER_DIR），
                       如果环境变量也没有，则默认回退到 [server/.agents/skills, server/app/modules/resource_generator/skills]。
        """
        if base_dirs:
            self.base_dirs = base_dirs
        else:
            self.base_dirs = []
            env_skills_dir = os.environ.get("SKILLS_DIR")
            if env_skills_dir:
                self.base_dirs.append(SERVER_DIR / env_skills_dir)
            
            # 默认包含的路径
            default_paths = [
                SERVER_DIR / ".agents" / "skills",
                SERVER_DIR / "app" / "modules" / "resource_generator" / "skills"
            ]
            for p in default_paths:
                if p.exists() and p not in self.base_dirs:
                    self.base_dirs.append(p)
                
        self._skills: Dict[str, SkillConfig] = {}

    def load_all_skills(self) -> None:
        """遍历所有配置的目录并解析所有的 SKILL.md。"""
        for base_dir in self.base_dirs:
            if not base_dir.exists():
                logger.warning(f"[SkillsManager] 技能目录不存在: {base_dir}")
                continue

            logger.info(f"[SkillsManager] 正在从目录加载技能: {base_dir}")
            # 遍历子目录寻找 SKILL.md
            for skill_dir in base_dir.iterdir():
                if not skill_dir.is_dir():
                    continue

                skill_md_path = skill_dir / "SKILL.md"
                if skill_md_path.exists():
                    self._parse_and_register(skill_md_path)

        logger.info(f"[SkillsManager] 共加载 {len(self._skills)} 个 Agent Skills.")

    def _parse_and_register(self, filepath: Path) -> None:
        """读取 SKILL.md 文件并分离 Frontmatter 和正文内容。"""
        try:
            content = filepath.read_text(encoding="utf-8")
            match = FRONTMATTER_RE.match(content)

            if not match:
                logger.warning(f"[SkillsManager] 缺少 Frontmatter: {filepath}")
                return

            # 解析 YAML Frontmatter
            frontmatter_text = match.group(1)
            try:
                frontmatter = yaml.safe_load(frontmatter_text)
            except yaml.YAMLError as e:
                logger.error(
                    f"[SkillsManager] 解析 Frontmatter 失败 ({filepath}): {e}"
                )
                return

            if not isinstance(frontmatter, dict):
                logger.error(
                    f"[SkillsManager] Frontmatter 格式无效，必须是字典 ({filepath})"
                )
                return

            instructions = content[match.end() :].strip()

            # 默认使用目录名作为技能名
            default_name = filepath.parent.name
            name = str(frontmatter.get("name", default_name))
            description = str(
                frontmatter.get("description", "No description provided.")
            )

            self._skills[name] = SkillConfig(
                name=name,
                description=description,
                location=str(filepath),
                instructions=instructions,
            )
            logger.debug(f"[SkillsManager] 成功注册技能: {name}")

        except Exception as e:
            logger.error(f"[SkillsManager] 处理技能 {filepath} 失败: {e}")

    def get_skill(self, name: str) -> Optional[SkillConfig]:
        """根据名称获取单个技能配置。"""
        return self._skills.get(name)

    def list_skills_summary(self, names: Optional[List[str]] = None) -> List[dict]:
        """
        获取技能的简要列表。

        Args:
            names: 可选。指定要包含的技能名称列表。如果未提供，则返回所有已加载技能。

        返回的列表适合注入到 Agent 的 System Prompt 中，
        提示 Agent 当前可用的技能及其用途。
        """
        return [
            {"name": s.name, "description": s.description}
            for k, s in self._skills.items()
            if not names or k in names
        ]

    def get_skill_instructions(self, names: List[str]) -> str:
        """
        根据技能名称列表，直接返回拼接好的技能指令 Prompt 文本。
        可以直接追加到 Agent 的 SystemMessage 中。
        """
        instructions = []
        for name in names:
            skill = self.get_skill(name)
            if skill:
                instructions.append(
                    f'<activated_skill name="{skill.name}">\n'
                    f"<instructions>\n{skill.instructions}\n</instructions>\n"
                    f"</activated_skill>"
                )
            else:
                logger.warning(f"[SkillsManager] 未找到请求的技能: {name}")
        
        return "\n\n".join(instructions)


# 导出一个全局单例，便于其他模块统一调用
skills_manager = SkillsManager()
