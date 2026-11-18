# 当前架构与目录决策

## 本地独立实现

项目标识、Skill 目录、`SKILL.md` 的 name、调用名和 ZIP 顶层目录统一为 `scientific-figure-designer`。`skills/scientific-figure-designer/` 是唯一源码，`.agents/skills/scientific-figure-designer` 是 Codex 发现入口。ZIP 直接收录 Skill 文件。项目布局参考 [Agent Skills 规范](https://agentskills.io/specification) 和 [Codex Skill 发现方式](https://learn.chatgpt.com/docs/build-skills)。

PPT Master 的 SVG 资源闭包检查以 MIT 许可复制到 Skill。纯文字模式使用随包的 Diagram Design HTML 模板、架构与流程布局规则。Diagram Design 的完整受版本控制快照包含在 Skill 内，两种模式均从当前包读取运行资源。具体来源、提交和许可见 [本地复用记录](../skills/scientific-figure-designer/third_party/README.md)。

仓库根目录的 `skills/` 放可安装源码，`scripts/`、Makefile 和 CI 放开发工具，`docs/` 放当前说明与历史记录。`build/`、`dist/` 和 `outputs/` 是本地目录。

## 文档如何变成路线图

| 阶段 | Codex 的判断 | Python 的输入和输出 |
| --- | --- | --- |
| 1. 固定来源 | 选取相关段落，检查扫描件的转录 | `ingest` 将文档提取为带原文件 SHA256 的来源快照 |
| 2. 整理科研内容 | 提炼任务、正式标签、条件、对照和有依据的关系，区分研究计划与结果 | `content-check` 重读原件并核对 FigureContent 的原文跨度、引用和状态契约 |
| 3. 设计图文 | 写出主视觉解释的问题，确定各面板的证据分工，打开可用参考图核对可迁移布局 | `research-brief` 提供设计工作表；`refs-search --brief` 返回与当前内容绑定的候选 |
| 4. 编排构图 | 设计区域位置和阅读顺序，图文模式制作或选择获准素材 | `plan --mode text\|mixed` 持久化选择并编排区域；`asset-register` 固定素材及来源元数据 |
| 5. 编译与渲染 | 按实际预览调整空间、文字层级和图文关系 | `preflight` 做实际字体测量、关系走线和资产检查；`render` 输出 Scene、SVG、PNG、HTML 和报告 |
| 6. 审查和导出 | 核对科学语义、图像内容和可读性，收集实际验收 | `qa` 核对渲染包 hash；`export` 打包待审图，终稿需绑定 render hash 的人审记录 |

### 模式与输出

- **纯文字**使用 Diagram Design 的 HTML 版式。架构图按组件和关系选择分组构图，技术路线图按步骤与分支选择阶段构图。Scientific Figure Designer 编译科研标签、节点和关系，沿用原文字形与证据绑定检查。
- **图文混合**默认使用 `asset_composite`，预检要求计划至少绑定一份审核通过的资产。报告记录图文素材及其所在区域。
- **三种格式**从同一 SVG 生成。HTML 内嵌字体和插图，Chromium 对网页中的实际文字执行检查并生成 PNG。模板内容参与实现 hash，导出的 HTML 参与产物 hash。

完整命令和兼容路线见 [工作流程](../skills/scientific-figure-designer/references/standalone-workflow.md)。

## 运行模块

| 入口/模块 | 职责 |
|---|---|
| `SKILL.md` | 指导 Codex 理解文档、查看参考图、设计与审查 |
| `scripts/figure.py` | CLI 调度、任务缓存、改字/导出、版本化打包 |
| `figure_sources.py` | 本地文档提取、原件/hash/原文跨度校验 |
| `figure_research.py` | 科研设计简报、来源与任务/面板映射；科学判断由 Codex 完成 |
| `scripts/vendor/ppt_master_svg_resources.py` | 本地嵌入 SVG/CSS/图像资源完整性校验 |
| `figure_catalog.py` | 参考库身份索引、检索调度、均衡抽样和审阅记录 |
| `figure_knowledge.py` / `figure_retrieval.py` | 逐图分析、原子知识代、中文结构检索与任务反馈 |
| `figure_plan.py` | 模式与图类型、可执行几何母版、样式和内容绑定 |
| `figure_render.py` / `figure_geometry.py` | 实际字体测量、Scene、原生文字、连接线、SVG/PNG/HTML |
| `figure_common.py` / `third_party/diagram-design/` | 生成独立 HTML、复用纯文字页面模板，记录上游快照 |
| `figure_assets.py` / `figure_data.py` | 许可元数据、素材与请求状态、真实数值图表 |
| `install.py` | 校验包内 hash 后安装，不覆盖旧版本 |

以上模块均在 [Skill scripts](../skills/scientific-figure-designer/scripts/) 中。所有资源以 `figure_common.ROOT`（解析后的 Skill 路径）为基准，不查找项目外的开发源码。

## 参考库与打包

```text
assets/reference-library/
├── catalog.sqlite    161 条候选记录、图片相对路径/hash、标注历史
├── library.json      数量、来源、分类方法、审核和许可状态
├── analyses/         161 份逐图分析，版本化 JSON
├── analysis-events/  不可变修订事件
├── taxonomy.yaml     中英别名和多维分类
├── patterns.json     带区域来源的设计归纳
├── knowledge/        current 指针和可重建的知识代
└── images/           原图唯一存放位置；Git 忽略
```

`refs-search` 使用中文词法、别名、结构与显式数量约束检索；旧库无知识代时兼容原关键词匹配。详见 [知识工作流](../skills/scientific-figure-designer/references/reference-knowledge.md)。结果中的 `path` 是库内相对路径，`image_path` 是运行时解析的绝对路径，`image_status` 标明 hash 校验情况。轻量安装没有图片时明确返回 missing；可以用 `--images` 指向同一批原图。

`pack` 以允许的目录集合选择 Skill 文件，但始终排除本地 `images/`。只有显式提供 `--references` 时才盘点图片、与目录索引比对并加入 ZIP，目标路径仍是 `assets/reference-library/images/`。仅携带当前知识代，排除裁片、缩略图、嵌图审阅页和任务反馈。不重复复制、不嵌入开发机路径，不把 build/docs/.venv 混入 Skill 包。

新增图库内容时先更新索引并保留候选/人工状态，再打包；不允许把旧索引配上另一批图片。参考原图不自动成为获准的生产素材。

## 文档与验证边界

- [开发计划](DEVELOPMENT_PLAN.md) 和 [任务状态](development/BACKLOG.csv) 描述当前工作；`docs/archive/` 保存原始设计和当时证据，不驱动当前执行。
- `tests/` 随 Skill 迁移，安装后仍可运行；仓库检查在根目录 `scripts/check_repository.py`。
- `build/` 包含审校、基准、演示与临时安装，`dist/` 仅放当前发行包；二者不进入源码包。
- 机器检查覆盖文件、字形、文本、关系绑定和部分几何；科研含义、像素内容、版权真实性及审美仍需实际审阅。
