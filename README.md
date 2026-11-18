# Scientific Figure Designer

`scientific-figure-designer` 是一个将论文、开题报告、基金申请和研究方案转成科研技术路线图、研究框架或机制示意图的 Agent Skill。Codex 提炼科研内容并审阅图面，Python 本地工具校验来源、排版并导出可编辑 SVG、PNG、可离线打开的 HTML 和质量报告。

## 快速开始

从项目根目录打开 Codex。首次使用时，运行以下命令准备 Python 环境和 Chromium。

```bash
make setup
make doctor
```

附上文档即可给出简单指令：

> 使用 $scientific-figure-designer，根据这份研究方案生成纯文字技术路线图，使用 mode=text，交付 SVG、PNG、HTML 和质量报告。

| 模式 | 用途 | CLI 规划参数 |
| --- | --- | --- |
| 纯文字 | 用随包的 Diagram Design 模板生成架构图或技术路线图，图内使用可编辑的标签和连线 | `--mode text --diagram-type architecture` 或 `--mode text --diagram-type roadmap` |
| 图文混合 | 用原创 SVG 示意或获准插图解释研究对象、方法与验证场景 | `--mode mixed` |

Skill 默认采用图文混合。用户也可以说「只用文字和连线」或「带插图」来选择模式。`mode` 随计划保存，预检、渲染和改字沿用该选择。两种模式都交付 `preview.svg`、`preview.png`、`preview.html` 和 `quality-report.json`。

跨项目使用可从 ZIP 安装。安装路径、环境配置和逐条 CLI 命令见 [独立安装与端到端流程](skills/scientific-figure-designer/references/standalone-workflow.md)。

## 从文档到成图

1. **提取与溯源**。读取 DOCX、可提取文字的 PDF、TXT 或 Markdown。Codex 依据原文建立 FigureContent，保留关键条件、对照、单位、研究状态和有证据的关系。扫描件需要先转录。
2. **设计与参考**。写出主视觉解释的问题，为各面板分配科研职责。检索书面结构和可用原图，选择构图方向。参考图提供布局线索。
3. **构图与素材**。形成一至两个布局起点。纯文字模式按架构或路线图安排节点。图文模式把至少一份原创示意或获准素材绑定到相应区域，预检核实素材及其来源。
4. **预检与渲染**。Chromium 测量实际字形，按计划生成 SVG、PNG、HTML、内容契约、构图计划、Scene 和质量报告。HTML 内嵌同一 SVG 及所用字体和插图，报告记录模式、模板与素材位置。
5. **审查与交付**。打开 PNG 核对科研语义、视觉层级和图文关系。默认输出待审图。有绑定到本次渲染的人审记录后，可以导出终稿。

计划、渲染和离线资源的关系见 [架构与流程](docs/ARCHITECTURE.md)。

## 项目结构

```text
scientific-figure-designer/
├── skills/scientific-figure-designer/   可独立安装的唯一 Skill 源码
│   ├── SKILL.md                         触发条件和执行规则
│   ├── agents/                          Codex 显示元数据
│   ├── scripts/                         CLI、安装器、演示和基准
│   ├── references/                      工作流程和设计手册
│   ├── assets/                          样式、字体和参考知识库
│   ├── schemas/                         内容、构图和 Scene 数据契约
│   ├── tests/                           可随包验证的测试和夹具
│   └── third_party/                     复用代码及其许可
├── .agents/skills/                      指向唯一源码的 Codex 发现入口
├── docs/                                架构、研发状态和历史记录
├── scripts/                             仓库维护检查
├── .github/workflows/                   CI
└── Makefile                             安装、测试、演示和打包
```

仓库名、Skill 名、调用名和安装包内目录名统一使用 `scientific-figure-designer`。构建、发行包和用户生成结果分别放在本地 `build/`、`dist/` 和 `outputs/`。

## 演示与开发

```bash
make demo OUT=build/example-001       # 本地 SVG 插画和两种图文布局，使用虚构研究
make check                           # 目录、文档链接和参考库完整性
make test                            # 包含 Chromium 渲染集成测试
make benchmark OUT=build/layout-001
make package                         # 轻量 ZIP，包含参考知识和索引
make package-private                 # 私用 ZIP，包含已核对的本地参考原图
```

重复运行用新的 `OUT` 或 `DIST`。仓库与轻量 ZIP 提供参考索引和知识库，可通过 `--images` 绑定本地图库。项目代码采用 [MIT 许可证](LICENSE)。随包字体、第三方代码和本地参考原图的许可分别见 [第三方资源与许可](THIRD_PARTY_NOTICES.md)。

[贡献与维护](CONTRIBUTING.md) · [开发状态](docs/DEVELOPMENT_PLAN.md) · [参考库维护](skills/scientific-figure-designer/references/reference-knowledge.md) · [1.5.0 变更](docs/releases/1.5.0.md)
