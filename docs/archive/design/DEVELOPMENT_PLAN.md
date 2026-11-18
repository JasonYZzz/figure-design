> 历史工程计划与 1.1.0 状态快照。路径和命令保留当时语境；当前入口见 [开发计划](../../DEVELOPMENT_PLAN.md)。

# Scientific Figure Designer Skill：从 0 到 1 完整工程开发实施方案

**版本**：V1.0 工程建设包（2026-11-17）  
**面向**：Codex 执行、TypeScript/Ajv/Playwright/CLI/DSH 现有项目的渐进式集成  
**目标**：基于科研文档生成科研技术路线图，兼顾科研事实、中文文字绝对受控、高质量图文混排、可编辑修复、运行效率  
**当前交付状态（2026-11-17，1.1.0）**：独立 Codex Skill 已实现并打包；安装后 30 项测试、16 个合成构图案例通过，参考检索、四路渲染、SVG/PNG/PDF、修改与导出已验证。161 张原参考图随私用包提供。真实科研文档端到端、30 图人工金标、专家视觉盲评和在线供应商调用尚未验收，不能据此声明原计划全部验收通过。详见 [1.1 交付记录](../../releases/1.1.0.md) 和 [逐项任务状态](../../development/BACKLOG.csv)。[P0 报告](../p0/P0_TEST_REPORT.md) 仅保留为历史证据。

> **项目决策**：不再选择“整图生成 → OCR 全量擦字”作为唯一默认方案，也不让通用 HTML 行列自动布局决定最终艺术构图。采用 `Scientific Composition Grammar + FigureContent + Asset Library + FigureScene + 多路由 + 确定性文字和科学连接线`。

## 当前交付目标澄清（2026-11-17，以用户最新要求为准）

最终产品是**可独立打包并安装到 Codex 的完整 `scientific-figure-designer` Skill**。当前可安装版本为 `1.1.0`；原 `1.0.0-p0.1` 是历史基础包。功能交付与外部验收分别记录，不以目录存在或测试数量代替实际能力。

- **运行宿主**：Codex。利用 Codex 当前可用的文档读取、视觉理解和图像工具完成语义任务；随包脚本负责索引、契约、精确文字、几何、渲染、校验和打包。不得假定某个模型或工具一定存在，缺能力时提供明确状态和可执行回退。
- **独立性**：不依赖另一个 TypeScript 网站、CLI/DSH 服务或其历史任务。原计划有关旧系统兼容与 DSH 的条目移为可选接入，不能继续用缺少这些工程阻断独立 Skill 开发。实现语言沿用现有 Python；仅因验收需要才引入其他运行依赖。
- **范围**：继续完成 P1–P7 中适用于独立 Skill 的功能。逐阶段保存测试与产物，但不把“一次一阶段”作为完成 P0 后停止整个研发任务的理由。P7 的核心改为独立安装、依赖检测、可迁移资源路径、版本/恢复/指标、完整 ZIP 打包及干净环境端到端验收。
- **参考图使用**：161 张原图 → 可见结构分析和候选标签 → 可检索索引 → 可迁移构图规则/母版 → 按当前科研内容检索少量相关参考 → 生成不同构图候选 → 精确文字和科研连接线落图。当前已完成全部缩略图的粗粒度结构观察和候选分类；运行时仍需查看命中的原图，不将候选分类称为训练或专家金标。
- **参考与素材分开**：原图可作为用户本地设计参考；只有来源与用途获准的像素素材才进入可复用资产库。模型分类可以是候选，不能冒充人工金标。人工验收保留为实际待审事项，不得伪造完成。
- **交付**：一个版本化 Skill ZIP，含入口、按需参考文档、运行脚本、schema、可执行构图/样式配置、参考索引、允许随包提供的资源、测试与安装说明。原始参考图库采用可迁移的资源包或明确的本地目录绑定，禁止硬编码本机绝对路径。无需另启动服务即可在 Codex 调用。
- **完整验收**：在干净目录安装 ZIP，用真实科研文档跑通“读取 → 内容/来源绑定 → 参考检索 → 构图候选 → 正式渲染 → QA → 可编辑产物导出”；再验证改文字不重新生成插画、权限未知素材被阻断、缺工具有明确回退。最终至少包含 SVG、可查看预览、结构文件和质量/来源报告。示例冒烟图不能替代该验收。

以下旧计划保留为详细技术依据；与本节冲突的宿主假设、阶段停止条件和产品验收范围以本节为准。P0 报告是历史阶段记录，不是独立 Skill 的完成证明。

---

## 0. 原工程执行策略（历史技术依据，以当前交付范围为准）

1. 在实际项目根目录工作。先读取 `AGENTS.md`、`package.json`、当前 CLI/DSH、图形任务、渲染和测试目录，列出可复用模块及需要保留的兼容接口；**不要假设目录名或版本号确实存在**。
2. 将 `.agents/skills/scientific-figure-designer/` 安装到项目仓库，并从 `$scientific-figure-designer` 触发（Codex 支持项目级 `.agents/skills` 和 `SKILL.md`，见官方文档 https://learn.chatgpt.com/docs/build-skills）。确认当前环境能发现它。
3. 做本地离线测试（不联网、不付费），先将包内基础测试接入项目 CI，输出实际测试报告。
4. 依 `P0 → P1 → P2 → P3 → P4 → P5 → P6 → P7` 顺序实现。一个阶段完成后固定版本、运行测试并保存可审查产物，再进入下一阶段。失败须给出复现、日志、回退和下一阶段阻断项，不能用模糊的“功能完成”代替验收。
5. 模型生成、外部图片下载、资源复制和写入用户项目需要现有项目权限/付费闸门；未经许可只提交准备请求或 dry-run。既有历史任务及数据不能批量重写。
6. 本建设包里的示例 SVG 是**确定性工具链冒烟验证**，其图片不代表达到图2/图3质量；上线资格取决于专门的视觉盲评与科研 QA。

### 0.1 成功定义

- **内容**：图中每一项科研实体、实验条件、关系、假说、测量指标都有用户批准或原文可追溯的依据。研究计划不得冒充实验结果。
- **文字**：所有正式 `LabelInstance` 字符串与已批准文本严格一致；中文标点、单位、希腊字母、上下标字体实际渲染不缺失、不超出容器。
- **视觉**：不再只有全宽卡片与密集说明段，能对同一科学内容选择中心主视觉、四泳道、分层机制、放大、对照或非对称布局，专家盲看有明显提升。
- **资产**：支持高频素材复用、领域风格统一、合法来源和可审查的生成/分割/缓存记录。
- **性能**：能给出快速结构预览；正式耗时按 route 分解记录，重复改文字无需再调用图像生成模型。
- **工程**：一个 `FigureContent` 真值，版本、任务状态、QA 与产物 hash 贯穿；旧 v1–v4 继续可用并能回滚。

## 1. 目前已知现状与不确定性

从前期讨论与提交的 V2 设计资料可知，现有项目采用 TypeScript、Ajv、Playwright，已有文档处理、HTML/SVG 混合制图和 CLI/DSH 集成；描述涉及 `src/job.ts`、`src/providers.ts`、`src/render.ts`、`src/research-plan.ts`、`src/dsh.ts`。**这些路径和实现细节需要 Codex 在用户真实仓库中检查**，本交付包没有直接访问用户仓库，因此不认定当前目录已经存在或所有接口和版本准确。

本仓库已提供 `roadmap-references/`：P0 实测 161 张图，尺寸、SHA-256、dHash 和重复关联已记录于 [清单](../p0/artifacts/references.jsonl)。1.1 已补充粗粒度领域/构图候选；视觉近重复、专业图像质量、版权和可抽素材数量尚未人工审核。**清单不等于分类成果，不可虚构素材或人工金标。**

先前图1较偏文字密集的年度科研设计，图2是中心主链路+两侧支撑+底部研究进度，图3是顶部对象总览+四条研究内容泳道。不同科学内容不必、也不应该强制同一版式。

## 2. Skill 定位、生命周期与目录

正式 Skill 名称 `scientific-figure-designer`；单 Skill 路由不同任务，减少过多 Agent 之间的转写错误。官方推荐将 `SKILL.md` 做成短说明，把长文档放入 `references/`，支持按需读取而非每次加载全部内容。

```text
<PROJECT_ROOT>/.agents/skills/scientific-figure-designer/
  SKILL.md
  references/
    figure-pipeline.md           # FigureContent/状态机
    composition-grammar.md       # 科研构图语法
    reference-ingestion.md       # 161 图离线学习
    asset-governance.md          # 权利、素材、图像安全
    rendering-and-qa.md          # 路由/文字/绘图/QA
    reconstruction.md            # 参考图反向图层重建边界
    integration.md               # CLI/DSH 接入
    acceptance.md                # 质量与退出条件
  schemas/
    figure-content.schema.json
    composition-plan.schema.json
    figure-scene.schema.json
    reference-record.schema.json
    asset-record.schema.json
  assets/
    composition-primitives.yaml
    layouts/*.yaml
    styles/*.yaml
  scripts/
    inventory_refs.py           # 已实现：安全只读参考图清单
    validate_contract.py        # 已实现：JSON Schema + 基础引用校验
    render_preview.py           # 已实现：最小 SVG 冒烟预览
  tests/fixtures/*.json
  tests/test_skill.py
  requirements-dev.txt
```

Skill 在运行时只给出**当前任务所需**的设计与操作说明。模型负责分类、科学结构候选、构图候选和受限插画；专用工具负责来源校验、文字、几何、矢量、缓存和失败回退。

### 2.1 不纳入首版范围

- 不开发完整 PPTX 引擎，不复刻 PPT Master 的全部 90 个 P/M/A/C 构图参考条目；首期实现 12 个科学构图原型和 8 个常用变体即可。
- 不把图片中的显微照片、Western blot、试验曲线/数值或化学结构当成可自由改造的装饰插画；数据图必须来自真实数值或确切授权原图。
- 不建设复杂多 Agent 云平台、自动微调图像模型或单独新的向量集群；现有 161 图先用 SQLite/JSONL 和本地文件。
- 不以 OCR 识别所有文字后擦除为唯一安全出图路线；保留其为参考复刻和 Image-First 可选后处理。

## 3. 逻辑架构：离线资源学习 + 在线研究图生成

```mermaid
flowchart TB
  subgraph OFFLINE[离线参考图知识构建]
    R[161 张用户授权参考图] --> INV[盘点与许可状态]
    INV --> VLM[OCR/VLM 结构建议]
    VLM --> REVIEW[人工审校和去重]
    REVIEW --> LM[Layout Masters 版式母版]
    REVIEW --> GR[Composition Grammar 组合语法]
    REVIEW --> ST[Domain Design Systems]
    REVIEW --> AS[获准的科研资产库]
  end
  subgraph ONLINE[在线生成]
    DOC[科研文档] --> EX[提取与事实审查]
    EX --> FC[FigureContent 唯一科研事实]
    FC --> PLAN[Scientific Composition Planner]
    LM --> PLAN
    GR --> PLAN
    ST --> PLAN
    PLAN --> FIT[文字容量+关系预检]
    FIT --> RT{Route Selector}
    RT --> T[Text Structured]
    RT --> H[Asset Composite]
    RT --> I[Image First]
    RT --> S[Strict Scientific]
    AS --> H
    T --> SC[FigureScene/Composer]
    H --> SC
    I --> SC
    S --> SC
    SC --> QA[来源/文本/关系/几何/视觉 QA]
    QA --> OUT[PNG+SVG+结构+质量报告]
  end
```

**强边界**：`FigureContent` 是事实源；`CompositionPlan` 是布局意图；`FigureScene` 是派生绘制对象；生图结果是候选资产，不可反向改写科研事实。参考图中的机制和具体论文文字不得作为新研究的来源。

## 4. 离线资源中台（161 图）完整流程

### 4.1 S0：盘点与不可变原图

- 输入 `--input` 指定 161 图所在的真实目录；支持子目录、PNG/JPEG/WebP/TIFF，导出相对路径。
- 计算文件 SHA-256、实际 EXIF 方向后宽高、dHash64、重复关联、候选源路径、license_state。完全一致才记录 exact duplicate；视觉近似只发候选，不能自动删除。
- 原图只读且不覆盖；无权限字段默认 `unknown`，不得进入对外素材库。
- 检查目标数量及坏文件：期望 161 有差异时阻断“全量已完成”声明。
- 已提供可执行工具：`scripts/inventory_refs.py`。示例命令（替换真实路径）：

```bash
python .agents/skills/scientific-figure-designer/scripts/inventory_refs.py \
  --input ./research-references/originals \
  --out ./research-references/index/references.jsonl --expected-count 161
```

### 4.2 S1：多维分类与候选标签

每张图至少输出八组信息，分类可以多选：

| 维度 | 示例值 | 生成期意义 |
|---|---|---|
| domain | biomedicine / clinical / materials / cs-ai / earth / social / general | 领域图形语义 |
| figure_type | technical_route / mechanism / system / research_framework / graphical_abstract / comparison | 信息任务 |
| composition_primary | top-overview-multi-lane / center-hero-side-support / annual-stage-timeline ... | 核心阅读路径 |
| visual_treatment | image-as-canvas / inset / cutout / asymmetric / arrow-overlay | 可用构图手法 |
| density | text_count, box_count, occupied_area, low/medium/high | 排版与路由 |
| topology | sequential / parallel / fork-merge / network / feedback / multiscale | 科研图骨架 |
| asset_candidates | cell / mouse / microscope / algorithm / graph / molecule ... | 检索和抽取候选 |
| rights | unknown / style_only / authorized_reuse / restricted | 合法用途 |

**OCR 和 VLM 都只能提出候选**。产出 `observations`（图上可见）和 `hypotheses`（模型推断），再经审校进入生产索引。OCR 读到的文字只用于理解参考图片，不能作为新科研图的科学事实。

### 4.3 S2：金标审核与归纳

建议抽取 20–30 张跨领域、跨文字密度、跨布局的图片作为首轮 Gold Set；模型分类与人工标注做精确率、召回率和混淆分析，重点关注多泳道/流程/机制/图形摘要的错分。对剩余全部样本做批处理，自动低置信结果转人工待审。

### 4.4 S3：版式母版提炼

不要一图一模板。根据相近的主阅读路径、槽位语义、连接拓扑和容量约束归并：

- 首批 12 个构图原型：顶部总览多泳道、中心主线两侧支撑、年度分层、宏观-微观机制、并行汇合验证、矩阵流程融合、漏斗证据链、中心辐射、网络叠层、并排对照、实验装置、低文字图形摘要。
- 每个母版提供 2–3 种真实有用的变体，而非靠随机颜色产生重复方案。
- 每个 Slot 定义科学角色、边界、文字容量、优先级、可绑定资产类型、连接锚点、留白和图层冲突规则。
- **可迁移的空间组织**与**有版权约束的原图美术内容**分离。

### 4.5 S4：资产候选、授权与质量

从参考图提取来的对象先进入 `candidate`。有权利依据、科学对象本身可复用、边缘完整、足够清晰后进入 `production_approved`；否则只记录风格、结构和对象描述。可用原始专业图库、自己绘制的 SVG、或 ImageGen 全新原创插画补足。对同一风格系列生成 Sheet 切分素材，需要逐对象 QA。

禁止直接把图2/图3中的完整机制路径、特定组别或结果图移植到其他研究。插画的可用性不意味着该对象在当前科研内容中有事实来源。

### 4.6 S5：查询索引和数据存储

- `refs`: 原始图及多维审核标签；
- `layout_masters`: 布局语法模板和可执行 Slot；
- `composition_primitives`: 主构图 + 修饰器 + 图层组合词表；
- `assets`: 获批可用图片、版权、科学类型、风格；
- `domain_styles`: 领域视觉规范；
- `review_events`: 审核和授权变更记录。

初期 SQLite + JSONL + 文件对象存储即可；如果现有 ES/Milvus 可复用，允许作为高阶召回而非新部署前置。优先做结构过滤（图类型/拓扑/密度）→ 简单相似度 → 对 Top3/Top5 VLM 重排；不要让 161 图每次全部进入上下文。

## 5. 科研内容真值 FigureContent

`schemas/figure-content.schema.json` 是初始样例，Codex 需将其转为 TypeScript Ajv 可校验类型，同时建立跨字段约束。

- `SourceRef`: source_id、source_hash、文本定位、原文摘录、确认为真/待查状态；注意 Unicode codepoint vs UTF-16 偏移；
- `Entity`: object type、名称和 sourceRefs；
- `Task`: 研究模块、状态、目标与验证对象；
- `Relation`: from/to/type/condition/evidence_state/sourceRefs/critical；
- `Label`: approved string、来源、允许的编辑性归纳/缩写；
- `LabelInstance`: labelId、ownerId、role、出现次数和必要性；支持同一术语多处出现。

### 5.1 核心关系和状态语义

关系至少区分：`sequence`, `depends_on`, `parallel`, `tests`, `measures`, `activates`, `inhibits`, `feedback`, `supports`, `association`。不能用同一种箭头表达互相冲突的科学语义。提出的研究步骤 `planned` 不等于已有结果 `validated`。非因果关联不能用机制激活箭头画出因果。

### 5.2 事实完整性检查

1. 每个重要科研实体、关系、指标有来源或用户批准的 Statement；
2. 关键边必须存在于 FigureContent 中；
3. 术语简写/否定词/量纲/对照条件必须得到批准；
4. `FigureContent` 更改才触发源内容审核，不因更改样式、图片或排版重复调用科学分析模型；
5. 不将 `VLM` 的构图建议转化为无来源科学事实。

## 6. 科研构图语法与 Composition Planner

### 6.1 设计来源

借鉴 PPT Master 中 `P`（主构图）、`M`（视觉修饰）、`A`（资产处理）之间的职责分离，以及 layout 与 style 独立的原则。只实现对科研图有明确语义价值的组合，拒绝机械照抄大而全的 90 个构图条目。可参考其源码：
- https://github.com/hugohe3/ppt-master/blob/main/skills/ppt-master/references/image-layout-patterns.md
- https://github.com/hugohe3/ppt-master/blob/main/skills/ppt-master/references/image-layout-spec.md
- https://github.com/hugohe3/ppt-master/blob/main/skills/ppt-master/workflows/create-template/create-layout.md
- https://github.com/hugohe3/ppt-master/blob/main/skills/ppt-master/workflows/create-template/create-style.md

### 6.2 Planner 分两层

**科学叙事规划**：从 FigureContent 找出读图主问题、主路径、跨尺度对象、并行/汇合、研究状态、必须展示与可以移至图注的内容。

**美术构图规划**：在不改变科研拓扑前提下，对比 Top2 布局：每个目标图一主视觉焦点、区域比例、插画位置、文字安全区域、读图顺序、留白及修饰组合。两个候选共享相同 FigureContent hash，不能因为参考图带有某个对象就加到当前图。

### 6.3 Planner 的输出 JSON

`CompositionPlan` 应含：
- `canvas` 及印刷尺寸/字体策略；
- `grammar.primary`, `modifiers[]`, `asset_treatments[]`；
- `regions[]`: role、bounds、visualPriority、labelInstanceIds、asset requests、safe text areas；
- `edges[]` 与 Relation ID 精确绑定；
- style ID、参考理由、非法模仿/增补警告、候选评分以及可读性负担。

在**生成新插画之前**执行 preflight：区域容纳所有必须标签、字体/术语不被自动压缩、关键连线有端点空间、同等实验对照有可比尺度。失败应修改候选布局或切到较严格路线，不能靠随机缩小字号掩盖。

### 6.4 可追踪性

每个视觉元素携带 `sourceContentIds`、`labelInstanceId`、`relationId` 或 `assetId`；这样用户改一个标签只失效文字和相关 QA，不重新生成整图。通用 SVG 结构字段应与可见中文文字分离，避免 `ZONE_1`, `nodeId` 这种元数据泄漏到图片。

## 7. 渲染路线的选择

| Route | 默认条件 | 责任分配 | 关键门禁 |
|---|---|---|---|
| `text_structured` | 高文字量、流程/架构为主 | 程序精确结构与文字；少量图形点缀 | 布局质量、文字溢出、连接端点 |
| `asset_composite` | 中等及偏高文字，科研对象插画重要 | 组合语法+素材库+必要的局部 AI 插画；文字与关键线由程序绘制 | 视觉一致性+精确文字+科学关系 |
| `image_first` | 用户偏好概念画或文字极少 | 整图美术生成，可选分层校字；结果初始为草稿 | 任何无法验证的文字/科学线不能自动判终稿 |
| `strict_scientific` | 公式、定量图、严格因果/实验数据 | 数据绘图/矢量图优先，AI 只做不承载证据的辅助 | 精确数据/单位/原文关系 |

路由必须根据评分和硬门禁，不仅按“字数是否少于 N”选择。用户有明确方式要求时优先遵守，不能绕过硬性真实性约束。

## 8. 文字准确性工程

### 8.1 TextSafeSurface Contract

生成前计算区域的可用宽高、内边距、字号范围、CJK 断行、最大行数、容纳度、插画与箭头碰撞边界。校验实际字体在最终机器上可用，科学符号/希腊字母/上下标需要按 run/math 分别处理。无准确数学排版器时标 `unsupported_math`, 不让普通 Unicode 直接冒充数学排版完成。

### 8.2 正式文字绘制

从冻结 LabelInstance 获得原文字符串，不读图片 OCR 结果；DOM / SVG 必须使用安全 XML 转义。字体渲染使用项目固定字体族和实际 Chromium / shaping 度量。标签系统应保留每个实例独立 ID；重复字串不是重复实例，不能用集合比较掩盖漏图。

### 8.3 后验 QA

- `ExactLabelManifest`: 已绘制的 label instance 集合与必须集合相等，实际文本严格等于其 approved string；
- Glyph check：所需字形存在、没有 tofu 方框、符号完整；
- Text fit：实际渲染 bbox 不溢出，不遮挡科学箭头/对象；
- Image-first：检查额外文字、伪字、残留原生错误文字，无法证明清洁则 `review_required`。

### 8.4 为什么避免默认“整图 OCR → 擦字”

OCR 存在漏字、重复位置、术语混合；正确文字宽度与错误文字不匹配；inpainting 可破坏边框、箭头甚至科学结构。保留该路径给参考复刻、低文字 Image-First 和人工确认的特殊场景，不作为主产品链强制运行。

## 9. 科研图形资产与 ImageGen

1. 查询已获批准素材：科学对象类型、专业风格家族、轮廓方向、透明通道、图中目标尺度。
2. 无资产时生成请求只包含来源批准的**客观可视对象**和风格，不允许创造新的科研假说、实验结论、图标标签或箭头。
3. 优先批量同风格简单 Icon Sheet，然后拆分、做 alpha/边缘/一致性检查；复杂器官、装置、精确机制独立绘制和审核。
4. 记录模型/版本/Prompt/hash/cost/许可与质检结论；同风格资产多图共享，局部文字变更不触发生图。
5. 图中的数据曲线、显微图、Western blot 等实验事实必须来自真实用户提供的证据或源数据绘制，不得用纯生成图模拟结果。

**PPT Master 参考实现**：
- https://github.com/hugohe3/ppt-master/blob/main/skills/ppt-master/references/image-generator.md
- https://github.com/hugohe3/ppt-master/blob/main/skills/ppt-master/scripts/slice_images.py
- https://github.com/hugohe3/ppt-master/blob/main/skills/ppt-master/scripts/image_layers.py

## 10. FigureScene & 渲染器

`FigureScene` 是统一渲染中间对象层：`id`、`type`、bounds、zIndex、sourceContentIds、labelInstanceId/relationId/assetId、style/material、transform、clip/focus、dependencyFingerprint。

要求：
- Scene 不存重新编造的科研内容；只能引用 FigureContent；
- 背景/底板/科研插画/容器/关键连接/文字分层；
- 对元素使用稳定 ID，使 UI 微调和局部 Patch 可控；
- 一次计算布局后锁定画布，并先预览实际 SVG 再输出 PNG/PDF，避免重复截图造成样式不一致；
- 并不要求所有图元最终都是矢量：含位图插画的 SVG 标记 hybrid 格式，绝不假称纯矢量。

PPT Master 采用 SVG→DrawingML 作为其 PPTX 中间层。你们只需参考 SVG authoring discipline，不必实现 PowerPoint XML。HTML 用于工具工作台/UI，不应成为唯一全局布局决策者。

## 11. Scientific & Visual QA

### 11.1 硬门禁（全部必须通过）

| 门禁 | 判定逻辑 | 失败时 |
|---|---|---|
| Evidence | 所有 critical content/relations 指向受核验来源 | blocked_content |
| Research State | planned/hypothesized 不变成已证实结果 | revise_content_or_label |
| Content Coverage | 必需科研任务/实验组/测量项未丢失 | revise_composition |
| Relation Fidelity | source-target/type/condition 与 FigureContent 相符 | patch_relation 或回退设计 |
| Exact Text | approved label strings、出现次数、单位精确 | patch_text |
| Glyph/Fit | 实际字形、文本 bbox、坐标不超界 | reflow_or_other_layout |
| Rights | 所有用到的素材有可用权利和来源 | replace_asset |

### 11.2 软评分（不能掩盖硬错误）

- 构图主次与读图路径；
- 图文比例和专业性；
- 图形对象是否解释真实科研任务，而非装饰；
- 和基线图相比是否减少同质卡片；
- 配色、视觉层次、留白、线宽、科普插画与报告审美区别。

### 11.3 局部修复与防漂移

标签 Patch 只影响文字 layer + overlap QA。新资产只失效对应局部场景和组合 QA。科研关系更改必须重新走 evidence gate 与相关 Scene 连接。整图构图切换不改变 FigureContent。任何付费操作需预算和幂等键；未知响应不得自动重复提交。

## 12. 现有 TypeScript 工程对接方案（以实际扫描为准）

建议新增 9 组职责，**不是强制创建 9 个空壳文件**：

| 模块 | 作用 | 预计复用 |
|---|---|---|
| `figure-content-v5` | 内容/来源/标签/科学关系 schema | existing research-plan / quote binding |
| `figure-reference-catalog` | 参考元数据、授权与候选查询 | existing file/cache tools |
| `figure-composition-grammar` | 母版与 P/M/A 类组合规则 | asset YAML + layout code |
| `figure-composition-planner` | 输出 2 个计划并执行验证 | LLM adapter |
| `figure-scene` | scene graph 和局部 Patch | existing SVG shape primitives |
| `figure-text-fit` | 真实字体测量/换行 | existing Playwright render engine |
| `figure-render-routes` | 4 路策略+能力检测+预算 | providers.ts |
| `figure-quality` | deterministic QA + VLM visual assessment | current validation infrastructure |
| `figure-runtime` | resume/queue/cancel/hash/status/metrics | DiagramJob + DSH |

**兼容策略**：新增 feature flag `scientific_figure_v1`；旧运行的 schema/Plan 数据、产物和结算语义原样保留。只在实际测试通过后引入新的 CLI/DSH route。任何 provider 是否支持 Mask/分层/编辑，必须是 Adapter 做完真实能力测试之后才设置为 `verified`。

### 12.1 建议 CLI（尚未实现）

```sh
figure refs inventory --input <ref-dir> --out <index.jsonl>
figure refs classify --index <index.jsonl> --review-manifest <review.json>
figure plan --source <source-file> --out <composition.json>
figure preview --content <content.json> --plan <composition.json>
figure qa --scene <scene.json> --out <qa.json>
figure export --render-hash <verified-hash>
```

保证 `--dry-run`、输出隔离、幂等任务 ID 和预算闸门。DSH 复用同一核心方法，不另写一套不同的科学检查规则。

## 13. 状态、哈希与产物树

```text
<work>/figures/<figureId>/
  sources/immutable/<source_sha>/...
  content/<contentHash>/figure-content.json
  designs/<compositionHash>/composition-plan.json
  assets/<assetHash>/...
  scenes/<sceneHash>/scene.json
  renders/<renderHash>/preview.svg, preview.png
  reviews/<renderHash>/quality-report.json
  operations/<operationId>/request.json, response.json, receipt.json
  current-state.json
  exports/<exportId>/...
```

`contentHash` 由科研内容和 SourceRefs 导出；`compositionHash` 含 layout master/style/grammar/slots；`sceneHash` 含实例和素材映射；`renderHash` 含字体/渲染版本和素材字节。哈希由程序计算，不能让模型任意生成。写入采用原子替换与 expectedStateHash 检查。`reviewed` 与用户 `accepted` 不同，用户真实验收不能由模型代签。

## 14. 性能设计

**关键路径**：源文解析 → 一次内容结构提取与校验 → 简化 Planner → 结构预览；资产 cache 与参考检索可以尽早并行但不能先于内容许可、语义确认擅自生图。

- 参考图库分类在离线执行，在线只检索有限候选；
- 类似小鼠、细胞、通用架构块等素材按风格复用并记录来源；
- 不为每张图重复分割 161 张图；
- 已满足的插画资产不重复调用图像模型；
- 重排文字不重生图；
- VLM 全图美学审查做一次；硬错误局部修复再审受影响区域；
- 图像生成请求只提交必要的局部资产，不强行整图多轮抽卡；
- 首屏结构预览早于耗时插画完成（产品 UI 可渐进式更新，但最终评审必须针对完整图）。

记录 `ingest_ms`, `extraction_ms`, `plan_ms`, `retrieve_ms`, `asset_queue_ms`, `asset_generate_ms`, `render_ms`, `qa_ms`, `repair_ms`, `total_wall_ms`, `paid_calls`, `cost_receipt`, `cache_hit`。无法获取账单的模型成本标 unknown，而不是零。

## 15. 研发阶段与依赖（按现有代码复用程度调整）

| 阶段 | 任务 | 代码交付 | 强制退出条件 | 建议团队时间预算 |
|---|---|---|---|---|
| P0 | 仓库盘点、Skill 安装、现有基线、测试预备 | existing flow map; smoke tests; baseline | 旧功能无回归、能力清单可信、所有旧版本可读 | 2–4 工作日 |
| P1 | 161 图清单、标签体系、许可金标 | inventory、schema、review samples、SQLite/JSONL | 确认真实数量；30 图初始审校；授权状态不被自动提升 | 5–8 日 |
| P2 | Layout/Style/Grammar 中台 | 12 primary、8 变体、4 style 系统、可加载配置 | 两种目标图能产生不同结构，母版有测量与连接槽 | 5–8 日 |
| P3 | FigureContent/Composition Planner | Typed schemas、strict binding、top-2 candidates、text capacity gate | 关键科研关系不变、全部标签有处、溢出能发现 | 6–10 日 |
| P4 | SVG Scene & routes 1/4 | renderer、label/edge mapping、geometry QA | 中文字符精确、SVG 单图可预览、修改文字不调用生图 | 6–9 日 |
| P5 | Asset Composite 主路由 | approved asset search、AI adapter、icon sheets、zIndex composition | 图2/3风格目标案例主视觉明显改进，素材审核可追踪 | 6–10 日 |
| P6 | 可选 Image First + 深层 QA | limited direct-image, optional layer/ocr, complete QA, edit patches | 不成功不标终稿，科学硬门禁始终工作 | 5–8 日 |
| P7 | CLI/DSH + benchmark/canary | route flag、resume、metrics、bundle、rollback | 实测质量/文字/速度/成本过门禁，未过不切默认 | 5–8 日 |

开发时间是工程估算而非系统生成延迟或既定工期承诺。允许 P4 与经授权的素材库制作部分并行；P5/P6 不应阻断 P3/P4 的结构性验收。

## 16. 专门验收 Benchmark

### 16.1 数据集

- 参考图 Gold：20–30 张，覆盖文字型、混合型、中心机制、泳道、年度、对照和结构图。
- 科研内容样例：至少 12 个，按真实领域和科研表达类别分层；含中英文、长标签、重复标签、复杂符号、多分支关系、弱证据与反事实场景；另保留 4+ 样本作为独立 holdout。
- 对照 A：当前 HTML/SVG 混合；B：纯整图生图；C：新 Grammar + SVG；D：新 Grammar + approved assets（主推）。统一内容、输入画幅和模型预算。

### 16.2 指标及阻断条件

| 指标 | 计算方式 | 初始门禁建议 |
|---|---|---|
| ExactLabelInstanceRate | 正式标签实例逐字符/次数一致 | 交付终稿 100% |
| RelationFidelity | 必要科学边方向、条件和类型 | 已知关键错误 0；unknown 不能作为通过 |
| UnsupportedClaimRate | 无证据主张数/应查主张数 | 通过终稿 0 |
| RenderedTextOverflow | 真正渲染后的出界/重叠 | 严重错误 0 |
| AssetRightsCompliance | 被使用资产生产权限合格 | 100% |
| CompositionPreference | 学科专家对同内容 A/B 盲评 | 先以 ≥70% 偏好新方案作为实验目标 |
| AutomaticSuccess | 不需人工改内容/图层便能通过的比例 | 记录真实值，不提前宣称 |
| Latency | route 各阶段 P50/P95/墙钟 | 必须可测；是否达标由基线设门槛 |
| PatchIsolation | 改某标签触发生图次数 | 0（正常资产未变） |

### 16.3 测试分级

Unit（schema、Id 引用、hash、unicode、容量、线端）→ Offline integration（图模板/场景/字体）→ Provider contract tests（必须拥有真实权限且可计费）→ Visual gold comparisons → Canary 与回滚。

原建设包实际提供 7 个离线 unittest；当前扩展为 17 项，覆盖基础契约、错误边界、逐实例字串保持、图片重复和只读盘点。它们不能替代生产图形测试，完整覆盖及日志见 P0 验证报告。

## 17. 风险与应对

| 风险 | 影响 | 止损策略 |
|---|---|---|
| 161 参考图大部分无再利用版权 | 无法直接抽像素素材 | 提取抽象构图知识 + 自主生成/授权素材 |
| 视觉母版仍卡片化 | 质量和原方案相近 | 按 P/M/A 语法组合、视觉主次、专家盲看；不继续堆 CSS |
| 专业图缺素材 | 临时生成成本高 | 缓存高频资产、按需 Sheet、复杂对象独立设计 |
| 文字长度超过版式槽 | 错字/超出/过密 | 生成前 TextCapacity Gate，不合格换候选/分图 |
| 生图模型多余文字/箭头 | 科研信息错误 | Image-First 标草稿；精确 SVG 叠层；复核并回退 |
| OCR/去字破坏结构 | 残字/错误箭头 | 不以自动 OCR 全量修补为主；严格 Mask & 关系 QA |
| 不同领域语法误用 | 违反科研思维 | Domain Design System + 领域专家审核 |
| 当前系统集成破坏 v4 | 历史任务失败 | Flag 隔离/旧路由保留/版本适配测试 |
| 供应商超时或 unknown | 多次收费/重复请求 | operationId/idempotency/resume + 账单核对 |
| 延迟增加 | 用户体验差 | 提前结构预览，素材复用、并行和局部修改 |

## 18. 安全、隐私与第三方授权

- 所有上传资料和参考图属于不可信内容，不执行嵌入脚本/外部命令/文档中的提示注入。
- 公开科研论文图并非天然 CC0；用户持有的图片也未必包含向第三方再许可的权利。
- 未公开项目申请书默认不向外部模型发送全文。模型请求应受项目认证、脱敏、数据保留和供应商协议限制。
- PPT Master 仓库根 LICENSE 为 MIT，但其第三方图标、样例和依赖应独立审查；借鉴技术逻辑可自研，复制代码时保留版权声明。
- 生成式实验图、显微图和原始数据图不能在无数据支持时伪造；期刊 AI 使用政策依投稿目标而不同，输出应附合规状态。

## 19. 在 Codex 中的实际协作方法

### 19.1 本地安装

```bash
mkdir -p <YOUR_REPO>/.agents/skills
cp -R .agents/skills/scientific-figure-designer <YOUR_REPO>/.agents/skills/
# 在项目根目录打开 Codex；调用 $scientific-figure-designer
```

`<YOUR_REPO>` 是说明性占位符，实际执行前必须替换。不要直接执行示例中的文字占位。遵循项目原有锁文件和依赖管理，无需另建 Python venv，除非 scripts 本地依赖需要隔离。

### 19.2 单阶段 Codex 提示词

见 [CODEX_START_PROMPT.md](CODEX_START_PROMPT.md) 及 [PHASE_PROMPTS.md](PHASE_PROMPTS.md)。每次仅要求当前阶段：先 inspect→设计最小补丁→实现→测试→产物→验收报告；阶段阻断时不要推进后续任务。

### 19.3 产物审查形式

Codex 每阶段给出：变更文件清单、实际命令、测试通过/失败结果、真实图片或数据、待解决项、下一阶段准入判定。禁止只给概念图或 README 但没有可运行代码。

## 20. 最小的可执行试验

在 Skill 根目录下：

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m unittest discover -s tests -v
python3 scripts/validate_contract.py --schema schemas/figure-content.schema.json --input tests/fixtures/figure_content.json
python3 scripts/validate_contract.py --schema schemas/composition-plan.schema.json --input tests/fixtures/composition_plan.json
python3 scripts/render_preview.py --content tests/fixtures/figure_content.json --plan tests/fixtures/composition_plan.json --out ./demo-preview.svg
```

演示图片里的实验词仅是**虚构占位**，不是科研结论或可展示在真实申请书里的产物。结果 SVG 仅证明可从冻结文字清单/关系引用输出一张可见的矢量图，**没有生产级字形测量或专业视觉设计能力**。

## 21. 参考依据与可复用范围

- OpenAI Codex Skills 目录、SKILL.md 与按需加载： https://learn.chatgpt.com/docs/build-skills
- Skill Creator 设计原则（progressive disclosure、短入口+references）： https://github.com/openai/codex/blob/main/codex-rs/skills/src/assets/samples/skill-creator/SKILL.md
- PPT Master P/M/A/C 组合式构图： https://github.com/hugohe3/ppt-master/blob/main/skills/ppt-master/references/image-layout-patterns.md
- PPT Master 图形尺寸/裁剪： https://github.com/hugohe3/ppt-master/blob/main/skills/ppt-master/references/image-layout-spec.md
- PPT Master 图片 OCR 与分层： https://github.com/hugohe3/ppt-master/blob/main/skills/ppt-master/scripts/image_ocr.py 及 image_layers.py
- PPT Master 文字容量： https://github.com/hugohe3/ppt-master/blob/main/skills/ppt-master/scripts/svg_quality/slot_capacity.py
- Nature Skills： https://github.com/Yuan1z0825/nature-skills
- PaperBanana： https://github.com/dwzhu-pku/PaperBanana
- Happy Figure Skill： https://github.com/BAIKEMARK/happy-figure-skill

对外部项目的借鉴是架构层、方法层和代码级参考，**不宣称已将它们完整移植或完成相同画质**。授权条件对每个实际复制的子目录和素材分别适用。

## 22. 可执行行动顺序（必须保留）

**第一轮不要直接做完整多路由 Agent。** 先让 Codex：检查当前项目、安装 Skill、验证现有工具链、盘点真实 161 图、人工审校 30 图、完成图2/图3两个高质量母版，并用同一 FigureContent 做出可靠 SVG/素材的视觉比较。只有证明布局明显改善，再增加大规模科研素材生产和 Image-First 备用路线。

**终极目标**：让 AI 学会设计科研图，而不是填模板；让程序保证可验证文本和科研连接，而不是依赖图像模型碰运气；让资源库沉淀可组合的专业构图知识，而不是复制 161 张图片。
