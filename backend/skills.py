"""SKILL.md parser following the Agent Skills specification (agentskills.io).

A skill is markdown with an optional YAML frontmatter block:
    ---
    name: docx-writing
    description: Use when the user asks to draft or polish Word documents.
    ---

    # docx-writing
    ...
"""
import re
import unicodedata

import yaml

NAME_PATTERN = r'^[a-z0-9\u4e00-\u9fff][a-z0-9\u4e00-\u9fff\-_]{0,63}$'

_FRONTMATTER_RE = re.compile(r'^---\s*\n(.*?)\n---\s*\n?', re.DOTALL)


class SkillValidationError(ValueError):
    """Raised when skill content cannot be parsed as a valid SKILL.md."""


def slugify(text: str, max_len: int = 64) -> str:
    """Turn arbitrary text into a slug usable as a skill name (keeps CJK chars)."""
    out = re.sub(r'[^a-z0-9\u4e00-\u9fff]+', '-', text.strip().lower()).strip('-')
    return (out or 'skill')[:max_len].rstrip('-')


def parse_skill_markdown(raw: str, fallback_name: str = "") -> dict:
    """Parse SKILL.md into {name, description, meta, body}.

    Tolerant mode: missing frontmatter falls back to `fallback_name` (from the
    upload filename) and the first non-empty line of the body as description.
    Raises SkillValidationError when neither frontmatter nor fallback is usable.
    """
    if not raw or not raw.strip():
        raise SkillValidationError("技能内容为空")

    fm = _FRONTMATTER_RE.match(raw)
    meta = {}
    if fm:
        try:
            parsed = yaml.safe_load(fm.group(1)) or {}
        except yaml.YAMLError as exc:
            raise SkillValidationError(f"frontmatter 不是有效的 YAML: {exc}")
        if not isinstance(parsed, dict):
            raise SkillValidationError("frontmatter 必须是键值对")
        meta = {k: v for k, v in parsed.items() if v is not None}
        body = raw[fm.end():].strip()
    else:
        body = raw.strip()

    name = str(meta.get("name") or "").strip() if meta.get("name") is not None else ""
    if not name and fallback_name:
        name = fallback_name

    description = str(meta.get("description") or "").strip() if meta.get("description") is not None else ""
    if not description:
        for line in body.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                description = line[:120]
                break

    if not name:
        raise SkillValidationError("缺少技能名称（frontmatter 的 name 字段）")
    if not re.match(NAME_PATTERN, name):
        raise SkillValidationError("技能名称只能包含小写字母、数字、连字符和下划线（1-64 字符）")
    if not description:
        raise SkillValidationError("缺少技能描述（frontmatter 的 description 字段）")

    return {
        "name": name,
        "description": description,
        "meta": meta,
        "body": body,
    }


def build_skill_markdown(name: str, description: str, body: str) -> str:
    """Assemble a canonical SKILL.md from form fields (used by manual creation)."""
    body = (body or "").strip()
    if not body:
        raise SkillValidationError("技能正文（指令内容）不能为空")
    meta_lines = ["---", f"name: {name}", f"description: {description}", "---"]
    return "\n".join(meta_lines) + "\n\n" + body + "\n"


BUILTIN_SKILLS: list[dict] = [
    {
        "name": "docx-writing",
        "description": "专业撰写与润色 Word 文档（.docx）：报告、方案、会议纪要、公文与合同等。当用户提到 Word 文档、报告、方案、会议纪要或需要正式书面表达时使用。",
        "source": "builtin",
        "meta": {"license": "MIT"},
        "content": """---
name: docx-writing
description: 专业撰写与润色 Word 文档（.docx）：报告、方案、会议纪要、公文与合同等。当用户提到 Word 文档、报告、方案、会议纪要或需要正式书面表达时使用。
license: MIT
---

# docx-writing

## Overview

本技能用于撰写和润色正式的 Word 文档。它规范了文档结构、语言风格与交付方式，确保输出可直接用于工作场景。

## Instructions

### 1. 明确文档类型与受众

- 先确认文档类型：报告 / 方案 / 会议纪要 / 公文 / 合同 / 其他
- 确认受众与用途，据此决定语气（正式、中性、亲和）与详略

### 2. 遵循标准结构

- **报告/方案**：标题 → 背景与目的 → 现状分析 → 方案/结论 → 计划与风险 → 附录
- **会议纪要**：时间地点参会人 → 议题回顾 → 结论 → 待办事项（含责任人/截止时间）
- **公文**：按现行公文格式（标题、主送、正文、落款、日期）

### 3. 语言规范

- 使用简洁、准确的中文书面语，避免口语化与冗余
- 数字、日期、金额书写一致；专有名词前后一致
- 段落长度适中，善用小标题与列表提升可读性

### 4. 交付

- 直接输出完整文档内容（Markdown），并说明每个章节的用途
- 如用户需要 .docx 文件，告知用户可复制内容到 Word，或请求后续工具支持导出
""",
    },
]