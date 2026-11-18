> 原研发包的历史提示词，已被当前开发计划取代；不要作为本次执行指令。

# Codex 分阶段提示词（P0–P7）

> 每阶段单独发给 Codex，不要一次性全发要求它全部实施。先读 `docs/DEVELOPMENT_PLAN.md` 和 Skill 入口。所有阶段遵守项目原有安全与权限规定，不能用伪造模型结果代替测试。

## P0 — 库内盘点与 Skill 验收

使用项目中的 `docs/CODEX_START_PROMPT.md`；已有 P0 报告时先阅读，避免重复安装与开发。

## P1 — 离线参考图分类与权限

你现在只执行 P1。读取已完成的 P0 报告、`references/reference-ingestion.md`、`references/asset-governance.md`、三个相关 JSON Schema。扫描真实 161 图；不存在则产生可明确重试的输入阻断，不造数据。实现只读 inventory CLI / 后端适配、SQLite+JSONL 数据模型、完整 rights 状态、批量 OCR/VLM 结构化候选接口（可 dry-run）、人工复核表和 30 图标注工作流。不能把自动候选直接标为人审通过。交付验证命令和实际 161 图/错误/重复统计，反例测试：坏图、近重复、未知版权、注入文本。

## P2 — 科研构图语法和母版

只执行 P2。读取 P1 的经审核参考元数据和 `references/composition-grammar.md`。建立 12 个科研 Primary Grammar 的词表和可执行约束，先完成图2中心型、图3多泳道型、图1年度改进型 3 个主母版；完成 8 个有真实差异的构图修饰组合，布局与领域风格独立。每个母版必须定义区域角色、准确文字容量、图层顺序和关系端口，不可用原图截图当背景模板。输出 2 个由同一科研内容产生的不同布局候选与对照图，含结构关系覆盖报告。

## P3 — FigureContent + Composition Planner

只执行 P3。以现有科研来源抽取为唯一事实基础，实现 FigureContent Ajv/TS 类型、SourceRef 严格校验、重复 LabelInstance、Relation 状态管理和 CompositionPlan 结构化输出；候选最多 2 个，不允许构图 Agent 新增科研事实。实现 TextCapacity 预检、两个计划的硬约束筛选、清晰失败报告；添加否定、对照、状态、相同词多次出现、超长中文字和未授权关系的负例测试。

## P4 — Text/Strict 路线和 SVG Scene

只执行 P4。实现最小有效 FigureScene、SVG native text/connector、字体实际测量、遮挡/越界/端点检查，以及 Text-Structured/Strict 两条路由。HTML 只用于交互，不允许普通卡片网格代替科研构图设计；同一个 FigureContent 产生不同视觉层级。保证字串、标签实例出现次数、科学箭头正确。局部文字修改不得调用生图。把产物 PNG 与 SVG 进行实图审核；实验原始图片不能当生成纹理。

## P5 — Asset-Composite 主路由

只执行 P5。读取 asset-governance 与已有获批素材库，提供资产检索、专业视觉分组、风格 ID、透明图层、缓存与权限门禁。实现 ImageGen Adapter（仅在现有授权和预算下实际调用）、缺失资产任务、图标 Sheet 分割/单图质量诊断、图层配准和素材不能遮挡正式标签的约束。用与 P4 完全相同的科研事实生成图2/图3型高质量图文混排；盲评对照当前基线，报告质量和耗时，不达标优先修复 Composition Planner，而不是无限生图。

## P6 — Image-First 试验与全面 QA

只执行 P6。增加 Image-First 的精确能力声明和可选原生图层拆分/OCR / clean-base 试验，但不是默认路线。未经证实的图中文字和箭头必须标识 draft/review_required。实现源证据、关系、标签、字体、几何、资产权利和 VLM 视觉多层 QA；有明确错误时局部修复并有限次重试。保留所有失败候选到审计目录，不能偷偷重生图绕过预算。

## P7 — CLI/DSH 集成与灰度发布

只执行 P7。在前述模块通过后新增 feature flag 和 CLI/DSH 调用路由；保留旧 v1–v4 任务与 schema 兼容、预算/归属状态、provider unknown 恢复、哈希快照和回滚策略。以 12+4 个分层任务建立评测集，同输入同画幅对比旧混合、纯图片、新 Composition+Text、新 Composition+Asset；指标包含文字字符串、科研关系、完整墙钟、成本、专家偏好、人工修复率。全部结果写成可复现报告；达不到硬性安全/质量门禁不能改默认路线。
