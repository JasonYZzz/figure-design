# 独立运行与可选宿主集成

Codex 和 DSH 都能载入当前 Agent Skill。纯文字由随包的原版 Diagram Design 负责撰写 HTML，`scripts/figure.py diagram-export` 调用其导出和校验命令。图文使用本项目的 `plan --mode mixed` 和 `render`。安装、能力检测和交付见 [standalone-workflow.md](standalone-workflow.md)。

图文内容和计划沿用 1.0 契约，Scene 使用 1.1。生成产物记录渲染器版本与实现 hash。修改内容、计划或素材后使用新的产物目录。

独立安装支持文件系统 Skill 发现和本地 Python。需要接入其他宿主服务时，以实际宿主 API 对接现有核心函数、质量报告和操作账本。
