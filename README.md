# Figure Design

`figure-design` 是一个将论文、开题报告、基金申请和研究方案转成科研技术路线图、研究框架或机制示意图的 Agent Skill。宿主 Agent 提炼科研内容并审阅图面，Python 本地工具校验来源、排版并导出可编辑 SVG、PNG、可离线打开的 HTML 和质量报告。

## 快速开始

在项目根目录运行以下命令准备 Python 环境、检查 Chromium 并构建安装包。

```bash
make setup
make doctor
make package
```

解压安装包，用包内安装器安装到用户技能目录。重新打开会话并附上文档后，就可调用 Skill。需要随包参考原图时使用 `make package-private`。详见 [安装说明](skills/figure-design/references/standalone-workflow.md#安装)。

> 使用 $figure-design，根据这份研究方案生成纯文字技术路线图，使用 mode=text，交付 SVG、PNG、HTML 和质量报告。

| 模式 | 用途 | CLI 规划参数 |
| --- | --- | --- |
| 纯文字 | 随包的原版 Diagram Design 直接分析文档并绘制架构图或技术路线图 | `plan --source <原文> --mode text` 可记录交接，图型可选 `architecture` 或 `roadmap` |
| 图文混合 | 用 [Three.js 空间图例](skills/figure-design/references/threejs-legends.md)、原创 SVG 示意或获准插图解释研究对象、方法与验证场景 | `--mode mixed` |

Skill 与 CLI 默认采用纯文字。用户可说「带插图」或指定 `mode=mixed` 来选择图文。两种模式均交付 `preview.svg`、`preview.png`、`preview.html` 和 `quality-report.json`。

跨项目使用可从 ZIP 安装。安装路径、环境配置和逐条 CLI 命令见 [独立安装与端到端流程](skills/figure-design/references/standalone-workflow.md)。

## DeepSeek Harness 插件

在仓库根目录执行 `make setup` 和 `make package-dsh`，生成 `dist/dsh-figure-design-1.11.0.tgz`，再安装到实际使用的 DSH CLI Profile。

```bash
export FIGURE_PY="$PWD/.venv/bin/python"
dsh plugin --profile web add "$PWD/dist/dsh-figure-design-1.11.0.tgz"
dsh web
```

在对话中使用 `/dsh-figure-design`。兼容版本、预构建包安装与依赖配置见 [DSH 插件说明](plugins/dsh-figure-design/README.md)。

## 从文档到成图

- **纯文字**。宿主直接打开 [随包 Diagram Design](skills/figure-design/third_party/diagram-design/skills/diagram-design/SKILL.md)，从原文分析关系、选择图型和主题，使用上游模板编写 HTML。项目的 `diagram-export` 调用上游检查与导出。
- **图文混合**。使用 FigureContent 绑定原文，借助科研简报和参考图构图，绑定获准插图后用本项目的 `preflight`、`render` 和 `qa` 生成与校验图文产物。
- **审查与交付**。打开实际 PNG 按原文核对语义、视觉层级和条件，默认交付待审图。

计划、渲染和离线资源的关系见 [架构与流程](docs/ARCHITECTURE.md)。

## 项目结构

```text
figure-design/
├── skills/figure-design/   可独立安装的唯一 Skill 源码
│   ├── SKILL.md                         触发条件和执行规则
│   ├── agents/                          Codex 显示元数据
│   ├── scripts/                         CLI、安装器、演示和基准
│   ├── references/                      工作流程和设计手册
│   ├── assets/                          样式、字体和参考知识库
│   ├── schemas/                         内容、构图和 Scene 数据契约
│   ├── tests/                           可随包验证的测试和夹具
│   └── third_party/                     复用代码及其许可
├── docs/                                架构、研发状态和历史记录
├── plugins/dsh-figure-design/            DSH 插件入口与元数据
├── scripts/                             仓库维护检查
├── .github/workflows/                   CI
└── Makefile                             安装、测试、演示和打包
```

仓库名、Skill 名、调用名和安装包内目录名统一使用 `figure-design`。构建、发行包和用户生成结果分别放在本地 `build/`、`dist/` 和 `outputs/`。

## 演示与开发

```bash
make demo OUT=build/example-001       # 本地 SVG 插画和两种图文布局，使用虚构研究
make check                           # 目录、文档链接和参考库完整性
make test                            # 包含 Chromium 渲染集成测试
make benchmark OUT=build/layout-001
make package                         # 轻量 ZIP，包含索引、完整 Diagram Design Skill 及上游许可证
make package-private                 # 本机私用 ZIP，另附 111 张经哈希校验的参考图，全部使用等尺寸无损 WebP
```

重复运行用新的 `OUT` 或 `DIST`。仓库与轻量 ZIP 提供参考索引和知识库，可通过 `--images` 绑定本地图库。项目代码采用 [MIT 许可证](LICENSE)。随包字体、第三方代码和本地参考原图的许可分别见 [第三方资源与许可](THIRD_PARTY_NOTICES.md)。

[贡献与维护](CONTRIBUTING.md) · [开发状态](docs/DEVELOPMENT_PLAN.md) · [参考图 Wiki](skills/figure-design/assets/reference-library/images-wiki/index.md) · [参考库维护](skills/figure-design/references/reference-knowledge.md) · [1.11.0 变更](docs/releases/1.11.0.md)
