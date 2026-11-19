# 参考知识工作流（2.0 数据契约）

活跃目录保存 111 张原尺寸参考图并使用裁定后的 catalog。`analyses/<ref-id>.json` 是逐图权威记录；`patterns.json` 是带区域来源的设计归纳；`taxonomy.yaml` 定义中英别名与分面。知识页与 SQLite 查询投影位于 `images-wiki/generations/<hash>/`，由 `current.json` 指向当前代。[Markdown 索引](../assets/reference-library/images-wiki/index.md) · [离线导航](../assets/reference-library/images-wiki/index.html)

111 张保留逐图观察、近似重点区域、迁移建议和限制。1.8.0 两轮筛查共从原 161 张中移出 51 张重复、低可读性或模板参考。1.10.0 又移出 11 张，保留 2 张用户供图，撤下首批 10 张计算机示例；重绘的 10 张均收录。其中 8 张仅供指定构图参考，逐图的 limitations 记录技术问题。全部是 `auto_proposed`。整体阅读摘要是观察；迁移建议是推断；未知数量、颜色测量、文字占比和逐条连接端点保持未知，不能从文件名或旧标签补齐。年份区别于阶段编号。变体关系由逐图观察提出，未视为人工金标。

收录新路线图时，先与同领域参考原图并排查看。沿一个具体对象核对采集、方法、中间表示和验证之间的对应关系，再缩小检查标签与图例。发现技术表达错误时记入 limitations，并指明可借鉴的局部。图形关系应回到本次科研来源核对。

## 检索与构图

```sh
python scripts/figure.py refs-search --query '三条并行研究任务，汇合后进行验证'
python scripts/figure.py refs-search --query '图文混合 生物医药' --require domain=biomedicine --require media=illustrated
python scripts/figure.py refs-search --query '四年技术路线图' --require duration_years=4
python scripts/figure.py research-brief --content content.json --sources source.json --reference-query '图文方法与独立验证' --out brief.json
python scripts/figure.py refs-search --brief brief.json > suggestions.json
python scripts/figure.py plan --mode mixed --content content.json --references suggestions.json --brief brief.json --out plans
```

普通查询返回兼容的记录列表；`--brief` 返回绑定 `source_content_hash` 的候选封装。简报的 `reference_requirements` 支持 `query`、`require`；关系类型和任务数是容量提示，不自动变成硬约束。`--require` 接受领域、构图、拓扑、图文、密度、时间类型、目的以及 `columns/task_lanes/duration_years`。未知值不满足精确约束。自然语言中的数字只影响软评分，并返回 match/mismatch/unknown。

中文二元词、英文词、中英别名与结构分面共同评分。输出包括词法、结构、容量分项，命中字段、未满足偏好、分析 hash、来源区域、知识页和原图状态。多样性对人工尚未确认的同构变体组及重复布局减分，不能当作真实近似重复准确率。活跃库采用内存评分，SQLite 只存可重建投影，无外部服务或新增依赖。

空查询仍全量枚举，供打包和审核兼容调用。旧库无知识代时保留原检索；已有知识代失效或损坏会明确报错，要求重建。轻量包可检索文字；`missing` 不能称为视觉核验。`modified` 不能用于构图建议。

查看 3–5 张候选，选择最多两个主要参考区域。简报的 `design_decisions.reference_choices_with_reasons` 每条填写 `id`、候选分析的 `region_id`、具体迁移手法 `use`，以及 `basis`（已实际看图用 `original`，只读分析用 `knowledge`）。选用记录随 `plan --brief` 进入 `selection.json`，只有明确选用的参考可改变构图候选优先级。未审阅候选只提供查阅线索。保持 FigureContent 的来源绑定，容量失败先调整构图，再验实图。

## 增补、修订与恢复

```sh
python scripts/figure.py refs-analyze-import --annotations analysis-changes.json
python scripts/figure.py refs-build
python scripts/figure.py refs-lint
python scripts/figure.py refs-review --out review-work --count 30
```

全量分析替换封装为 `{reviewer, reviewer_kind, attestation?, records:[{analysis, expected_previous_hash}]}`。新记录前值为 null；更新用原分析的 canonical JSON SHA256。先验证整个批次，再逐文件原子写入，并保存完整 analysis-events。重复提交相同内容幂等；部分中断可重试同一请求。模型不能改成人审，也不能覆盖既有人审分析。旧 refs-annotate 保持原来的全量字段替换语义，避免破坏既有调用。

refs-review 按领域、构图、图文、密度均衡选择，输出原图 HTML、旧标注模板和 `analysis-review.json`。模板不是审核结果；只有实际人审者填写身份与 attestation 后才能导入。批次状态通过成功记录和不可变事件恢复；不维护第二套任务队列。

构建先在临时目录生成整代 SQLite、知识页和 manifest，验证依赖未变后原子切换 current。相同依赖复用整代；小库有变动时重建整代，尚未实现按单页依赖的增量编译。失败不切换旧代，但源内容变动会阻止旧代用于新检索。历史代本地保留，包仅携带当前代。外部图片状态在 lint 或候选解析时核对。打包采用无损 WebP 的记录保留原始 path 和 sha256，并在 lossless_webp 中登记交付文件路径及哈希。已有分析仍绑定原件。

## 反馈与评估

`refs-feedback --input feedback.json --out task-work/feedback-v1.json` 保存任务内记录。输入含 source_content_hash、reviewer、reviewer_kind、query、candidates（ID 列表）、selected、changes、preflight、outcome；人审额外提供 attestation。禁止写入共享图库，不会自动把用户文档或任务反馈带入发行包。

`benchmark_references.py --out evaluation` 对冻结 60 查询运行旧描述旧检索、新描述旧检索、新检索以及无多样性消融。输出覆盖率、进程内延迟及待填写的候选池 judgments。覆盖率不等于相关性。提供实际人审 `--judgments` 后才计算逐查询候选池 nDCG 和 Hit；这不是全库 Recall。初始查询集存在跨分组的语义近邻，不能宣称严格独立留出泛化。

用户供图授权状态仍为 unknown。轻量包排除原图、裁片、缩略图、嵌图审阅目录、反馈和临时产物；知识导航 HTML 保存文字与相对原图引用；有本地原图时可展开预览，轻量包显示缺图，不嵌入图片字节。
