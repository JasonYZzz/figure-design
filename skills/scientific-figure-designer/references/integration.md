# 独立运行与可选宿主集成

当前正式入口是 `scripts/figure.py`，运行在 Codex 中，不依赖 TypeScript 或 DSH。安装、能力检测、文档处理和输出规则以 [standalone-workflow.md](standalone-workflow.md) 为准。

原有 `inventory_refs.py`、`validate_contract.py` 和 `render_preview.py` 保留其基础接口与测试；最后一个仅为旧冒烟工具，不是正式渲染入口。内容/计划仍使用 1.0 契约，正式 Scene 是 1.1；生成产物记录 renderer_version 与实现 hash。修改内容/计划/素材需要新产物版本，不批量迁移历史文件。

未来接 CLI/DSH 时复用当前核心函数、质量报告与操作账本，检查实际宿主接口后再写适配器。不为假定的 src/job.ts、providers.ts 等文件生成空壳；外部宿主兼容性不是独立 Skill 的安装条件。
