# 独立安装与端到端流程

## 安装

在源码项目中，直接从项目根打开 Codex，系统通过 `.agents/skills/scientific-figure-designer` 发现源码。用 `make setup && make doctor` 准备工具。跨项目使用时，解压发行 ZIP 后用 Python（3.10+，验证版本为 3.12）安装到用户级目录：

```bash
python3 /实际解压路径/scientific-figure-designer/scripts/install.py --to ~/.agents/skills
```

安装器验证包内全部 hash，并在目标已有同名 Skill 时停止。也可以安装到另一个项目的 `.agents/skills`。升级前，将旧副本移到发现目录之外保存，再安装新版本。项目内也可能同时发现用户级副本，出现同名入口时用 `doctor` 核对所选 Skill 的版本。完整私用包包含当前 161 张本地参考图，原图许可待核实。

为工具建立隔离环境，路径由当前机器选择（下方变量中的路径必须换成实际值）：

```bash
FIGURE_SKILL=/实际安装路径/scientific-figure-designer
python3 -m venv /实际环境目录/figure-venv
FIGURE_PY=/实际环境目录/figure-venv/bin/python
"$FIGURE_PY" -m pip install -r "$FIGURE_SKILL/requirements.txt"
"$FIGURE_PY" -m playwright install chromium
"$FIGURE_PY" "$FIGURE_SKILL/scripts/figure.py" doctor
```

Linux 若缺 Chromium 系统库，按 Playwright 提示安装系统依赖；不要默默使用未测量字体的替代截图。首次安装需要网络下载 Python 依赖/浏览器，之后本地处理不依赖网络。项目源码、第三方复用代码、字体和说明已随包提供，无 GitHub 下载器或兄弟 Skill 运行依赖。若需要整套运行环境离线部署，应另准备匹配操作系统的依赖 wheel 和 Chromium；当前 ZIP 不声称包含 Python/浏览器。随包提供 Noto CJK 字体及原许可证；导出 SVG 内嵌字体子集。

## 1. 提取与冻结内容

```bash
"$FIGURE_PY" "$FIGURE_SKILL/scripts/figure.py" ingest --input /输入/研究方案.docx --out /工作目录/sources
```

支持 UTF-8 TXT/MD、DOCX、可提取文字的 PDF。输出 `sources/<原文件SHA>/source.json` 和不可变原件。代码不自动发起 OCR。Codex 读取 `source.json.text`，按 `schemas/figure-content.schema.json` 写出 `content.json`：

- sources：`document_sha256` 取工具返回的值；`locator` 为 `chars:起点:终点`，使用 Python/Unicode codepoint 左闭右开偏移，`excerpt` 与切片逐字一致。不要猜测 hash 或位置。
- entities/tasks/relations：绑定 source_ids。关系至少支持 sequence、depends_on、parallel、tests、measures、supports、activates、inhibits、feedback、association。计划不得变成结果。
- labels：verbatim 必须确实出现在关联摘录；approved_summary 的概括必须保持含义、得到当前任务授权。`approved: true` 表示当前用于渲染的冻结文字，不代表用户已验收最终图片。
- label_instances：每个研究任务必须有 required 实例；重复术语保留多个独立 ID。条件标签必须有属于相应 relation 的实例。
- 实际用户批准的补充陈述也保存为原文 MD，再 ingest；禁止将模型猜测标为用户批准。

```bash
"$FIGURE_PY" "$FIGURE_SKILL/scripts/figure.py" content-check --content /工作目录/content.json --sources /工作目录/sources/HASH/source.json
```

检查会重新提取原件、核对文本/hash/跨度/引用。它不能判断摘要科学含义是否准确，Codex 仍需逐条审阅原文。

## 2. 科研设计简报、参考图与构图

纯文字用以下命令选择架构图或技术路线图。省略 `--diagram-type` 时，以步骤/依赖为主的图选 `roadmap`，其余选 `architecture`。

```bash
"$FIGURE_PY" "$FIGURE_SKILL/scripts/figure.py" plan --content /工作目录/content.json \
  --mode text --diagram-type architecture --out /工作目录/architecture-plans
"$FIGURE_PY" "$FIGURE_SKILL/scripts/figure.py" plan --content /工作目录/content.json \
  --mode text --diagram-type roadmap --out /工作目录/roadmap-plans
```

布局可按来源调整各区域和连线端点。随包的 Diagram Design 提供[架构图规则](../third_party/diagram-design/skills/diagram-design/references/type-architecture.md)、[流程图规则](../third_party/diagram-design/skills/diagram-design/references/type-flowchart.md)和 HTML 模板。纯文字可跳过以下图文简报与第 3 节，直接到第 4 节。

### 图文混合

先读 [scientific-design.md](scientific-design.md)，将来源绑定内容整理为设计工作表：

```bash
"$FIGURE_PY" "$FIGURE_SKILL/scripts/figure.py" research-brief --content /工作目录/content.json --sources /工作目录/sources/HASH/source.json --out /工作目录/research-brief.json
```

Codex 根据实际来源填写中心问题、面板职责、主证据与验证层次，在 `design_decisions.visual_concept` 记录主画面和各素材说明的对象或方法，再选构图。修改 FigureContent 后重新生成简报。图面用短标签，原文摘录留在来源记录；对照、关键参数和研究状态保留在图上。

```bash
"$FIGURE_PY" "$FIGURE_SKILL/scripts/figure.py" refs-search \
  --brief /工作目录/research-brief.json --query "图文混合 多任务并行" --limit 5 > /工作目录/references.json
"$FIGURE_PY" "$FIGURE_SKILL/scripts/figure.py" plan --content /工作目录/content.json \
  --references /工作目录/references.json --mode mixed --variant wide --out /工作目录/plans
```

默认使用随包 SQLite。检索返回候选标签、结构观察、`image_path` 和 `image_status`（verified/missing/modified）。打开 verified 的原图判断可迁移的构图。轻量包可加 `--images <本地图库>`；原图缺失时可以使用知识页的结构描述，并在简报记录原图未查看。参考检索只影响候选布局家族，素材仍需单独制作或绑定。

显式布局：`plan --layout center-hero-side-support --style biomedicine-academic --variant wide ...`。布局见 `assets/layout-registry.yaml`，12 个可执行入口、4 套样式；可选择 balanced/wide/portrait/landscape 及对应 mirrored 共 8 种画幅/方向变体。镜像仅改变区域位置，关系方向仍由事实 ID 决定。构图修饰词是设计词表，不是所有装饰均会自动实现。

选一个候选另存为 `plan.json`，按科研阅读顺序调整区域和画幅。图文模式为关键画面留出空间。计划保存用户指定的模式与图类型，预检、渲染和改字都读取该计划。原有只传 `--route` 的 CLI 脚本仍可运行。两项参数都省略时，CLI 使用 `text_structured`。Skill 在用户未选模式时会显式传 `--mode mixed`。

## 3. 本地示意、资产绑定与可选生图

先寻找合适的获准原图，或按简报绘制无字的本地 SVG。比如用并排的采样装置和读数界面说明测量过程，正式条件和连接线仍由 FigureContent 控制。可以用 `make demo` 查看从本地原创 SVG 到两种成图的完整例子。

有现成库先 `asset-search --library <目录> --type <类型> [--style <样式>]`。每个实际文件通过 `asset-register --input <图> --metadata <JSON> --out <库>` 注册。

metadata 必需：`id`, `scientific_type`, `style_family_id`, `rights: authorized_reuse`, `approval: production_approved`, `origin`, `source_content_ids`, `reviewer`, `review_note`, `contains_evidence`。填写真实来源和审核者，不能因为用户持有参考图就把版权自动提升。注册后文件与 metadata 固定，以新 ID 更新版本。

在 plan 的对应 region 添加 `asset_ids: ["ID"]`；render/preflight 加 `--assets <库/ID/asset.json> ...`。资产与该区域 owner 必须匹配。支持 PNG/JPEG/WebP 与经静态限制的 SVG；外部 SVG 脚本、引用和任意样式不执行。每个区域一个资产，可拆区域或使用审核过的 sheet。

需要原创插画时：

1. `image-request --content <content> --entity <ID> --prompt <客观对象描述> --operation-id <稳定ID> --budget <已批准上限> --out <operations>`，只准备请求。
2. 获得本次任务真实授权和可用工具后，`image-status --operation <operation.json> --status submitted --provider <实际工具/模型>`。
3. Codex 调用当前生图工具，提示词只含来源支持的可视对象、样式和“无字、无科学箭头、无实验结果”。它不是本地 CLI 的网络功能。
4. 成功时 `image-status ... --status succeeded --image <实际结果文件> --receipt <实际工具结果标识>`；超时记 unknown，查询原操作，不重复提交。
5. 审核科学对象和像素质量后注册。可用 `asset-sheet --input <sheet.png> --boxes <JSON数组> --out <候选目录>` 按 `{id,bounds:[x,y,w,h]}` 切分；裁片仍是 candidate，边缘统计不代替人工 QA。

费用未知保持 unknown。请求账本记录操作状态，费用以上游工具为准。缺少生图能力时优先复用获准资产或绘制本地示意。用户未指定模式且素材不足时，可用纯文字交付结构草稿并注明待补画面。

## 4. 四种路线、渲染与检查

- text_structured：纯文字默认路线，使用原生 SVG 标签和关系。
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

纯文字的预检和渲染命令都省略 `--assets`，并使用纯文字计划。图文混合至少绑定一份获准资产。用户选择高级 `--route` 时，`strict_scientific` 兼容两种模式，`image_first` 用于图文模式。

预检执行实际字体、字形、布局、资产与关系走线检查。失败时优先增加局部空间或重组布局。预检和质量报告都返回 `composition.mode`、`composition.route`、`composition.html_template` 和 `composition.asset_placements`。纯文字额外记录 `composition.diagram_type`。

渲染生成 `preview.svg`、`preview.png`、`preview.html`、内容、计划、Scene、质量报告、文件 hash 清单、本地来源与素材快照。网页内嵌同一 SVG、字体子集与已批准的插图，可单独离线打开。渲染目录不可覆盖，相同输入可缓存复用。写入使用临时目录再整体重命名。失败保留 failure.json，修正后用原目标路径重跑。进程被强制杀死留下 `.lock` 时先确认任务已退出，再移走该任务的锁。

Codex 打开 PNG 审查构图、阅读顺序、语义连接和图文遮挡，按原文复核所有实验条件。QA 的 pass 只证明列出的机器门禁，不是模型自签人类验收。

当前边界：复杂数学 TeX、自环、复杂矢量导入、不支持字形或无法无交叉排线会报错，需重构图/使用经核验的数学资产。不要把 unsupported/unknown 判为通过。数据图暂支持数值 x/y 的 line/bar，不模拟显微/Western blot/实验数值。

## 5. 修改、验收与导出

```bash
"$FIGURE_PY" "$FIGURE_SKILL/scripts/figure.py" patch-label --render /工作目录/render-v1 --expected-render-hash 实际HASH --label 实际LABEL_ID --text '获准的新文字' --reason '用户修订说明' --out /工作目录/render-v2
"$FIGURE_PY" "$FIGURE_SKILL/scripts/figure.py" export --render /工作目录/render-v2 --out /工作目录/figure-draft.zip
```

改字保留素材并重新渲染/QA，生图调用为 0；新意图或新增事实必须先改来源与内容。旧图验收不会继承。

只有实际人类验收后才创建 review JSON：`render_hash`, `decision: accepted`, `reviewer_kind: human`, `attestation`（原反馈/审核记录）、`scientific_review: true`, `visual_review: true`, `asset_review: true`；Image First 另需 `image_first_review: true`。随后 export 加 `--final --review <文件>`。这些声明由操作人员提供，CLI 不进行身份认证，Codex 不得虚构人类反馈。

导出 ZIP 携带 SVG、PNG、HTML、质量报告和可追溯的结构文件。旧版渲染目录可以直接导出，工具从已通过 hash 检查的 SVG 生成离线 HTML。导出仍包含必要摘录，请按项目保密要求分享。所有命令支持 `--dry-run` 描述请求且不执行，实际容量预检使用 preflight。

## 6. 测试、演示与重打包

从 Skill 目录运行：

```bash
FIGURE_RENDER_TESTS=1 python -m unittest discover -s tests -v
python scripts/benchmark.py --out /独立工作目录/benchmark
python scripts/demo.py --out /独立工作目录/illustrated-demo
python scripts/figure.py pack --out /独立发布目录/scientific-figure-designer.zip --references /用户授权的本地参考图目录
```

不指定 references 始终打轻量包，即使本地有原图也不自动收录。完整包需显式指定 `--references <Skill目录>/assets/reference-library/images`；打包前核对每个相对路径和 hash 与索引一致，包内保持相同目录。轻量包使用原图时通过 refs-search/refs-review 的 `--images` 绑定本地图库。benchmark 的 12+4 个案例都是虚构软件测试，不是专家盲评；demo 以相同内容和原创几何图标生成中心/泳道两张图。包内 `requirements.lock` 记录本次实测环境，运行依赖入口保持 `requirements.txt`。
