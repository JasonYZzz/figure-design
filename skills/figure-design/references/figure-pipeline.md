# 科研图运行契约

## 内容、构图与场景

| 契约 | 负责保存的内容 |
| --- | --- |
| SourceRef | 原始文档 SHA256、原文摘录和核验状态。`chars:start:end` 是提取文本中的 Unicode codepoint 左闭右开偏移。来源检查重新提取原件并逐字比较摘录。 |
| FigureContent | 目的、领域、研究状态、对象、任务、带来源的关系与正式标签。一个 Label 保存文字，一个 LabelInstance 代表一次独立放置；同一文本可有多个实例。 |
| CompositionPlan | 图文混合的路线、画幅、布局、主题、归一化区域、文字实例和连接端点。获准资产按 ID 绑定到区域，编译时检查资产与区域 owner 的对应关系。 |
| FigureScene | 渲染得出的文字、图像、连接线及其位置、层级、关联 ID，记录内容与计划 hash。 |

具体字段见 [内容契约](../schemas/figure-content.schema.json)、[构图契约](../schemas/composition-plan.schema.json) 和 [场景契约](../schemas/figure-scene-v1.1.schema.json)。

## 数据流与状态

`ingest → FigureContent → content-check → research-brief → refs-search → plan → asset-register/绑定 → preflight → render → qa → export`

- 简报初始状态为 `semantic_design_pending`，需要 Codex 填写科研叙事和图文分工。构图候选为 `draft`，可预检。被标记为 `rejected` 的计划会被拒绝渲染。
- 渲染绑定内容、构图、字体、资产字节、Chromium 版本与实现 hash。同一输出目录已存在时，CLI 只在既有文件完整且输入匹配时复用；变化后用新目录生成。
- 渲染报告为 `review_required`，机器门禁发现问题时为 `blocked`。质量报告列出实际素材放置、正式标签、关系图例和待审项。`qa` 对渲染目录校验文件与 render hash。
- 草稿导出标记 `review_required`。终稿导出需要匹配 render hash 的人审记录，导出包标记 `accepted`。改字重新排版并生成新的 render hash。

## 产物与追溯

图文渲染目录包含 `figure-content.json`、`composition-plan.json`、`scene.json`、`preview.svg`、`preview.png`、`preview.html`、`quality-report.json`、`artifact-manifest.json` 与本地来源和资产快照。质量报告记录实际素材位置和主题。分享用的 `export` ZIP 携带图、结构文件、质量报告和导出状态，终稿也携带验收记录。结构文件可能包含必要的原文摘录。定量图的 `data-provenance.json` 由 `data-chart` 单独生成。

纯文字的 `diagram-design.json` 是给宿主的交接文件，含图型偏好、内容路径和可选参考清单。宿主按上游 Skill 编写独立 HTML，`diagram-export` 对其校验并输出 HTML、SVG、PNG 和质量报告。详见 [纯文字工作流](standalone-workflow.md)。
