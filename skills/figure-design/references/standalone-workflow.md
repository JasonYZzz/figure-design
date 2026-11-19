# 独立安装与端到端流程

## 安装

源码位于 `skills/figure-design/`。在仓库根目录运行 `make setup`、`make doctor`、`make package`。解压发行 ZIP 后，用 Python（3.11+，验证版本为 3.12）安装到用户级目录：

```bash
python3 /实际解压路径/figure-design/scripts/install.py --to ~/.agents/skills
```

安装器验证包内全部 hash，并在目标已有同名 Skill 时停止。更新时先把现有 Skill 目录移到技能搜索目录之外备份，再使用同一个安装器。重新打开会话后调用 `figure-design`，并用 `doctor` 核对名称和版本。私用包包含当前 111 张本地参考图，原图许可待核实。

Codex 使用 `$figure-design`，DSH 使用 `/figure-design`。需要项目级部署时，也可把独立安装包安装到目标项目的 `.agents/skills/`。

通过 `.tgz` 安装 DSH 插件时使用 `/dsh-figure-design`。CLI 的 `web` Profile 使用 npm 安装的 DSH 命令。桌面端的 `desktop` Profile 由桌面应用管理，先正常退出应用，再用其自带 CLI 安装并重新打开应用。版本条件见 [插件安装说明](https://github.com/JasonYZzz/figure-design/tree/main/plugins/dsh-figure-design#dsh-版本与运行环境)。以会话提供的资源目录作为 `FIGURE_SKILL`，接着配置下方的 Python 环境。

为工具建立隔离环境，路径由当前机器选择（下方变量中的路径必须换成实际值）：

```bash
FIGURE_SKILL=/实际安装路径/figure-design
python3 -m venv /实际环境目录/figure-venv
FIGURE_PY=/实际环境目录/figure-venv/bin/python
"$FIGURE_PY" -m pip install -r "$FIGURE_SKILL/requirements.txt"
"$FIGURE_PY" -m playwright install chromium
"$FIGURE_PY" "$FIGURE_SKILL/scripts/figure.py" doctor
```

Linux 若缺 Chromium 系统库，按 Playwright 提示安装系统依赖；不要默默使用未测量字体的替代截图。首次安装需要网络下载 Python 依赖/浏览器，之后本地处理不依赖网络。项目源码、第三方复用代码、字体和说明已随包提供，无 GitHub 下载器或兄弟 Skill 运行依赖。若需要整套运行环境离线部署，应另准备匹配操作系统的依赖 wheel 和 Chromium；当前 ZIP 不声称包含 Python/浏览器。随包提供 Noto CJK 字体及原许可证；导出 SVG 内嵌字体子集。

## 纯文字架构图与技术路线图

先打开本包的 [Diagram Design 原版 Skill](../third_party/diagram-design/skills/diagram-design/SKILL.md)，将原始文档、用户要求及参考材料直接交给宿主，由宿主执行随包工作流。CLI 需要留交接记录时可运行：

```bash
"$FIGURE_PY" "$FIGURE_SKILL/scripts/figure.py" plan --source /输入/研究方案.md \
  --mode text --diagram-type roadmap --out /工作目录/roadmap-handoff
```

架构图用 `--diagram-type architecture`。省略该参数时由 Diagram Design 按来源选择。打开交接文件 `diagram-design.json` 中的 `skill` 和 `source`。已有 FigureContent 可继续用 `--content <JSON>`，并可携带与其绑定的 `--references` 清单。两种交接均返回 `delegated`，由宿主执行以下同一流程。

### 从原文到图面

1. **确定读图任务。** 根据用途和读者，写出主图需要回答的核心问题。按用户给出的插入宽度设计，缺省时用随包 Diagram Design 对应用途的尺寸预设。用户参考图提供阅读方向、层级和布局线索，研究内容以原文为依据。
2. **核对节点与关系。** 在工作笔记中为关键节点记录名称、职责或产出和来源。为每条关键边记录起点、终点、方向、关系类型、交接物或触发条件，以及来源。定位用页码、章节或原文行号。保留影响理解的单位、否定、对照和计划／假说／观测／已验证状态。若核心关系因缺失或冲突而无法确定，先向用户确认该处并继续处理可确定部分。原文明确提出的待验证关系按假说表达。无法判断是否存在的关系留在审阅记录。
3. **按关系选图型。** 若行为或状态决定图的含义，先按随包规则选语义模式，再读所选图型的参考。用下表决定优先保留哪些原文信息。

   | 图的用途 | 主图解释的问题 | 有原文依据时补充 |
   | --- | --- | --- |
   | 架构图 | 组件及其协作 | 职责、边界、接口、传递对象、依赖或反馈 |
   | 技术路线图 | 推进路径、各步交付与验证 | 阶段产出、真实依赖、并行评测、分支条件、对照或判据 |
   | 机理示意图 | 对象间的作用及其成立条件 | 作用方向、区室或尺度、替代解释、证据状态 |

4. **按使用尺寸排版。** 核心节点优先写短标题和一到两条有辨识度的信息。把交接物放在关键箭头或邻近节点，把触发条件放在对应分支。章节或年度顺序只有在原文明确表示执行关系时才画成流程。按上游图型的复杂度和字号规范排版。空间不足时先调整分组、方向或画幅，再考虑局部展开或总览加细节。只交一张图时，详细参数和次要说明可记入审阅记录，影响理解的条件保留在图内。
5. **用随包模板编写 HTML。** 按 Diagram Design 的图型、主题和模板规则绘制内联 SVG，使用可编辑文字、形状和连线。需要出现在三种格式中的标题、注释和图例写在内联 SVG 内。

### 导出与审阅

导出时运行：

```bash
"$FIGURE_PY" "$FIGURE_SKILL/scripts/figure.py" diagram-export --input /工作目录/diagram.html --out /工作目录/deliver-text
```

命令调用同一随包 Skill 的 `self_check.py --offline`、`verify_geometry.py`、`export_svg.py --system-fonts` 和 `export_png.py`，交付 HTML、SVG、PNG 与质量报告。打开实际 HTML 和 PNG，按 [纯文字审阅](acceptance.md#纯文字审阅) 核对并记录结果。语义错误回到原文和节点关系，版面问题回到 Diagram Design 构图。编辑时修改原 HTML，再导出到新目录。

## 图文混合

### 1. 提取与冻结内容

```bash
"$FIGURE_PY" "$FIGURE_SKILL/scripts/figure.py" ingest --input /输入/研究方案.docx --out /工作目录/sources
```

支持 UTF-8 TXT/MD、DOCX、可提取文字的 PDF。输出 `sources/<原文件SHA>/source.json` 和不可变原件。代码不自动发起 OCR。宿主 Agent 读取 `source.json.text`，按 `schemas/figure-content.schema.json` 写出 `content.json`：

- sources：`document_sha256` 取工具返回的值；`locator` 为 `chars:起点:终点`，使用 Python/Unicode codepoint 左闭右开偏移，`excerpt` 与切片逐字一致。不要猜测 hash 或位置。
- entities/tasks/relations：绑定 source_ids。关系至少支持 sequence、depends_on、parallel、tests、measures、supports、activates、inhibits、feedback、association。计划不得变成结果。
- labels：verbatim 必须确实出现在关联摘录；approved_summary 的概括必须保持含义、得到当前任务授权。`approved: true` 表示当前用于渲染的冻结文字，不代表用户已验收最终图片。
- label_instances：每个研究任务必须有 required 实例；重复术语保留多个独立 ID。条件标签必须有属于相应 relation 的实例。
- 实际用户批准的补充陈述也保存为原文 MD，再 ingest；禁止将模型猜测标为用户批准。

```bash
"$FIGURE_PY" "$FIGURE_SKILL/scripts/figure.py" content-check --content /工作目录/content.json --sources /工作目录/sources/HASH/source.json
```

检查会重新提取原件、核对文本/hash/跨度/引用。它不能判断摘要科学含义是否准确，宿主 Agent 仍需逐条审阅原文。

### 2. 科研设计简报、参考图与构图

有用户上传设计参考时先走 [上传参考与整图迁移](reference-design.md) 的入口，再直接规划。此处的图库命令用于无上传设计参考的任务。

先读 [scientific-design.md](scientific-design.md)，将来源绑定内容整理为设计工作表：

```bash
"$FIGURE_PY" "$FIGURE_SKILL/scripts/figure.py" research-brief --content /工作目录/content.json --sources /工作目录/sources/HASH/source.json --out /工作目录/research-brief.json
```

宿主 Agent 根据实际来源填写中心问题、面板职责、主证据与验证层次，在 `design_decisions.visual_concept` 记录主画面和各素材说明的对象或方法，再选构图。修改 FigureContent 后重新生成简报。图面用短标签，原文摘录留在来源记录；对照、关键参数和研究状态保留在图上。

```bash
"$FIGURE_PY" "$FIGURE_SKILL/scripts/figure.py" refs-search \
  --brief /工作目录/research-brief.json --query "图文混合 多任务并行" --require media=illustrated --limit 5 > /工作目录/references.json
```

打开候选图或知识页，在简报的 `reference_choices_with_reasons` 记录实际选用的区域与手法，再生成候选。

```bash
"$FIGURE_PY" "$FIGURE_SKILL/scripts/figure.py" plan --content /工作目录/content.json \
  --references /工作目录/references.json --brief /工作目录/research-brief.json \
  --mode mixed --variant wide --out /工作目录/plans
```

默认使用随包 SQLite。检索返回候选标签、结构观察、`image_path` 和 `image_status`（verified/missing/modified）。打开 verified 的原图判断可迁移的构图。轻量包可加 `--images <本地图库>`；原图缺失时可以使用知识页的结构描述，并在简报记录原图未查看。参考检索提供候选布局家族。通过整图迁移记录把参考区域、图文层级和色样落实到最终计划；素材仍需单独制作或绑定。

显式布局可用 `plan --layout center-hero-side-support --style biomedicine-academic --variant wide ...`。布局见 `assets/layout-registry.yaml`。镜像仅改变区域位置，关系方向仍由事实 ID 决定。绑定插图的区域可用 `asset_fraction` 调整图片高度占比，默认 `0.44`，上限 `0.85`，需要为该区域的正式文字保留测量空间。

选一个候选另存为 `plan.json`。按参考图编排画面，在 `theme` 写入本次图文配色及依据，再绑定素材。新图文计划写入 `mode: mixed`。高级选项 `--route strict_scientific` 和 `--route image_first` 仍要求绑定获准资产。

### 3. 本地示意、资产绑定与可选生图

先寻找合适的获准原图，或按简报绘制无字的本地 SVG。比如用并排的采样装置和读数界面说明测量过程，正式条件和连接线仍由 FigureContent 控制。可以用 `make demo` 查看从本地原创 SVG 到两种成图的完整例子。

有现成库先 `asset-search --library <目录> --type <类型> [--style <样式>]`。每个实际文件通过 `asset-register --input <图> --metadata <JSON> --out <库>` 注册。

metadata 必需：`id`, `scientific_type`, `style_family_id`, `rights: authorized_reuse`, `approval: production_approved`, `origin`, `source_content_ids`, `reviewer`, `review_note`, `contains_evidence`。填写真实来源和审核者，不能因为用户持有参考图就把版权自动提升。注册后文件与 metadata 固定，以新 ID 更新版本。

在 plan 的对应 region 添加 `asset_ids: ["ID"]`；render/preflight 加 `--assets <库/ID/asset.json> ...`。资产与该区域 owner 必须匹配。支持 PNG/JPEG/WebP 与经静态限制的 SVG；外部 SVG 脚本、引用和任意样式不执行。每个区域一个资产，可拆区域或使用审核过的 sheet。

需要原创插画时：

1. `image-request --content <content> --entity <ID> --prompt <客观对象描述> --operation-id <稳定ID> --budget <已批准上限> --out <operations>`，只准备请求。
2. 获得本次任务真实授权和可用工具后，`image-status --operation <operation.json> --status submitted --provider <实际工具/模型>`。
3. 宿主 Agent 调用当前已配置的生图工具，提示词只含来源支持的可视对象、样式和“无字、无科学箭头、无实验结果”。
4. 成功时 `image-status ... --status succeeded --image <实际结果文件> --receipt <实际工具结果标识>`；超时记 unknown，查询原操作，不重复提交。
5. 审核科学对象和像素质量后注册。可用 `asset-sheet --input <sheet.png> --boxes <JSON数组> --out <候选目录>` 按 `{id,bounds:[x,y,w,h]}` 切分；裁片仍是 candidate，边缘统计不代替人工 QA。

费用未知保持 unknown。请求账本记录操作状态，费用以上游工具为准。缺少生图能力时优先复用获准资产或绘制本地示意。用户未指定模式且素材不足时，可用纯文字交付结构草稿并注明待补画面。

### 4. 图文路线、渲染与检查

- asset_composite：图文混合默认路线，至少绑定一份获准资产，使用原生 SVG 文字和连接。
- strict_scientific：同一原生准确性链，保留明确关系。定量图可先 `data-chart --input <真实CSV> --x <列名> --y <列名> --title <标题> --kind line|bar --out <目录>`，数值完整记录于 provenance；审查坐标单位后注册图形资产。
- image_first：需要一张真实底图，程序叠加受控标签/连接。底图可能含文字或科研箭头，必须额外复核，不能自动认定为终稿。

```bash
cd /工作目录
"$FIGURE_PY" "$FIGURE_SKILL/scripts/figure.py" preflight \
  --content content.json --plan plan.json --sources sources/HASH/source.json \
  --assets assets/ASSET_ID/asset.json
"$FIGURE_PY" "$FIGURE_SKILL/scripts/figure.py" render \
  --content content.json --plan plan.json --sources sources/HASH/source.json \
  --assets assets/ASSET_ID/asset.json --out render-v1
"$FIGURE_PY" "$FIGURE_SKILL/scripts/figure.py" qa --render /工作目录/render-v1
```

图文混合至少绑定一份获准资产。预检执行实际字体、字形、布局、资产、主题对比度与关系走线检查。失败时优先增加局部空间或重组布局。预检和质量报告包含模式、路线、实际素材及其位置和实际主题。

渲染生成 `preview.svg`、`preview.png`、`preview.html`、内容、计划、Scene、质量报告、文件 hash 清单、本地来源与素材快照。网页内嵌同一 SVG、字体子集与已批准的插图，可单独离线打开。渲染目录不可覆盖，相同输入可缓存复用。写入使用临时目录再整体重命名。失败保留 failure.json，修正后用原目标路径重跑。进程被强制杀死留下 `.lock` 时先确认任务已退出，再移走该任务的锁。

宿主 Agent 打开 PNG 审查构图、阅读顺序、语义连接和图文遮挡，按原文复核所有实验条件。QA 的 pass 只证明列出的机器门禁，不是模型自签人类验收。

当前边界：复杂数学 TeX、自环、复杂矢量导入、不支持字形或无法无交叉排线会报错，需重构图/使用经核验的数学资产。不要把 unsupported/unknown 判为通过。数据图暂支持数值 x/y 的 line/bar，不模拟显微/Western blot/实验数值。

### 5. 图文修改、验收与导出

```bash
"$FIGURE_PY" "$FIGURE_SKILL/scripts/figure.py" patch-label --render /工作目录/render-v1 --expected-render-hash 实际HASH --label 实际LABEL_ID --text '获准的新文字' --reason '用户修订说明' --out /工作目录/render-v2
"$FIGURE_PY" "$FIGURE_SKILL/scripts/figure.py" export --render /工作目录/render-v2 --out /工作目录/figure-draft.zip
```

改字保留素材并重新渲染/QA，生图调用为 0；新意图或新增事实必须先改来源与内容。旧图验收不会继承。

只有实际人类验收后才创建 review JSON：`render_hash`, `decision: accepted`, `reviewer_kind: human`, `attestation`（原反馈/审核记录）、`scientific_review: true`, `visual_review: true`, `asset_review: true`；Image First 另需 `image_first_review: true`。随后 export 加 `--final --review <文件>`。这些声明由操作人员提供，CLI 不进行身份认证，宿主 Agent 不得虚构人类反馈。

导出 ZIP 携带 SVG、PNG、HTML、质量报告和可追溯的结构文件。旧版渲染目录可以直接导出，工具从已通过 hash 检查的 SVG 生成离线 HTML。导出仍包含必要摘录，请按项目保密要求分享。所有命令支持 `--dry-run` 描述请求且不执行，实际容量预检使用 preflight。

## 6. 测试、演示与重打包

从 Skill 目录运行：

```bash
FIGURE_RENDER_TESTS=1 python -m unittest discover -s tests -v
python scripts/benchmark.py --out /独立工作目录/benchmark
python scripts/demo.py --out /独立工作目录/illustrated-demo
python scripts/figure.py pack --out /独立发布目录/figure-design.zip --references /用户授权的本地参考图目录
```

两种包都提供 Diagram Design 模板、规则、示例和当前科研参考索引。需要包内原图时用 `make package-private` 或显式传 `pack --references <Skill目录>/assets/reference-library/images`。打包前核对每张图的路径及 SHA-256，私用包优先包含经过逐像素校验的无损 WebP。检索结果中的 path、sha256 标识原件，image_path、image_file_sha256 指向实际验证的文件。外接旧 PNG/JPEG 图库仍可按原件哈希校验。轻量包可用 `--images` 绑定本地图库。benchmark 的 12+4 个案例均为合成校验，demo 使用原创几何图标。依赖通过 `requirements.txt` 安装。

经授权的本地复现包使用 `export --include-sources`，一次归档源快照与资产。用可重复的 `--source-file FILE` 按需加入获准的简报和 SVG 源文件。提供 `--review` 时，ZIP 内质量报告也含审阅结论。复现包的 `artifact-manifest.json` 覆盖所有其他条目，CLI 返回最终 ZIP 的 SHA-256。默认分享包只含成图、结构文件和显式传入的审阅。

PDF 个别页出现非法 Unicode 时，工具会用可用的本机 Poppler 重提异常页，并在 `pdf_fallback` 标出恢复不完整的页。引用受影响的页前，按原页核对并保存为 UTF-8 文本，用 `ingest --input REPORT.pdf --pdf-page-text 56=page-56.txt --out NEW-SOURCES` 建立新快照。可逐页重复传入 `--pdf-page-text`。快照记录转录及原 PDF 摘要。在新快照上重新定位摘录，再运行 `content-check`。
