# 用户参考与整图迁移

先识别附件用途。设计参考与科研证据分别处理。用户提供设计参考时，整个任务跳过图库、SQLite 和 Wiki 检索。将本地图片路径传给简报，支持多图。

```bash
python scripts/figure.py research-brief --content content.json --sources sources/.../source.json \
  --reference-image reference-a.png reference-b.jpg --out brief.json
python scripts/figure.py plan --mode mixed --content content.json --brief brief.json --out plans
```

填写简报后运行第二条命令。路径和失败原因保留在本次任务的简报。打开所有可读上传图，依据用户指定或实际内容选一张主参考，其余补充局部。损坏图保留失败记录。仅使用可用的上传图；全部失败且必须贴近参考时，要求用户补传。纯文字路线用 `plan --mode text --source ... --reference-image ...`，随后向 Diagram Design 明确传递上传参考与相应设计要求。

无用户参考时，通过 `refs-search --brief` 查图库并审阅原图，再用 `--references references.json --brief brief.json` 规划。将采用的图库图像写入原有选择字段。图库不可用时，保留简报并直接运行 `plan --mode mixed --brief brief.json`，由领域预设补齐配色。上传模式不使用图库选择字段。

## 先看全图，再转成可执行坐标

看主视觉、画幅、留白、分组、栏位及相对大小，追踪标题、插图、正文、阶段和验证带的阅读顺序。将适合新内容的结构写入 `design_decisions.reference_design`。先从简报的 `composition_owners` 和 FigureContent 确定目标，常见为 title、owner-1 等。参考图坐标和成图坐标分别归一化为 `[左, 上, 宽, 高]`。保留科学内容和连线语义。

```json
{
  "primary_id": "upload-1",
  "layout": "top-overview-multi-lane",
  "canvas": {"width": 1800, "height": 1100},
  "display_width_px": 1050,
  "placements": {
    "owner-1": {"bounds": [0.05, 0.20, 0.90, 0.32], "role": "hero", "appearance": "plain"},
    "owner-2": {"bounds": [0.05, 0.64, 0.42, 0.24], "role": "validation", "appearance": "band", "tone": "secondary"}
  },
  "features": [
    {
      "reference_id": "upload-1",
      "source_bounds": [0.05, 0.15, 0.90, 0.68],
      "target_regions": ["owner-1", "owner-2"],
      "observation": "横向主视觉与下方验证带形成两层阅读路径",
      "check": "全图缩至目标宽度后仍能识别主视觉和下方验证带",
      "adaptation": "验证区给新内容保留双行宽度"
    }
  ],
  "color_samples": {"paper": [0.005, 0.005, 0.02, 0.02], "accent": [0.12, 0.64, 0.04, 0.008]},
  "observed_colors": {"secondary": "#714573"}
}
```

可指定 `layout` 选取基础模板。未声明 `canvas` 时，上传图宽高比作为候选画幅的起点。为足够数量的目标区写入布局；参考坐标应按内容容量调整。区域可使用 panel、plain 或 band，tone 可指定 accent、secondary 或 tertiary。插图按参考需要设为 asset_position 的 top、left 或 right。调整计划时保留特征与目标区的绑定，合理偏离记录在 adaptation。需要比较第二个方案时，对同一内容使用另一份构图设计记录，对比结构取舍。上传原图在简报中用文件摘要绑定，最终计划记录 ID、摘要和特征。

用 `groups` 给分立的文字和插图区域绘制一个共用底板。例如 `{"id":"validation-band","regions":["validation-a","validation-b"],"tone":"secondary"}` 会在两个区域外画一条连续验证带。组内区域默认使用透明底。给参考特征填 `target_group: "validation-band"` 和 `target_regions`，给涉及读序的特征补 `target_relations`。连线的 `tone` 可用同一套角色色，其方向、标签与标记仍依据科研关系。

## 配色与图面审阅

角色采样框覆盖纸面、主体区域、线条或图例中的确切色块。避免用照片区域推断全图主题。栅格参考可采样 PNG、JPEG、WebP 等。安全 SVG 参考可在宿主看图后用 observed_colors 填入实测色。用户指定 `plan --theme theme.json` 或 `--style <预设 ID>` 时优先采用指定色。参考色达到对比度需调整时，质量报告保留观察色与实用色。

用户要求保留黑白时设 `palette_mode: monochrome`。默认 `auto` 会在纸面、强调色及其他已知角色都为灰阶时按灰阶补齐。参考仅负责构图时设 `palette_mode: domain`。科学色标与实物本色可作为固定颜色保留在素材内。

原创 SVG 使用 `{{figure:accent}}`、`{{figure:secondary}}` 等主题颜色值，可加 -light 或 -pale 生成与纸面融合的浅色，再通过 `asset-register --plan plan.json` 一次解析与注册。固定科研色标与实物本色直接写其颜色值。成图后在目标显示宽度并排核对主参考原图与 PNG。把实际结果写入以下格式，并通过 `qa --review review.json` 校验。

```json
{
  "render_hash": "<质量报告中的实际值>",
  "display_width_px": 1440,
  "reflow_count": 1,
  "reference_checks": [{"feature": 1, "result": "retained", "note": "主图与横向验证带在缩小后均可定位"}],
  "palette_note": "纸面与阶段色继承自参考，正文对比度按输出条件调整"
}
```

每个特征按计划中的顺序从 1 开始编号。结果可用 `retained`、`adapted`、`needs_rework`。共享组拆开时，审阅需用 `note` 标出位置、用 `reason` 解释差异。对用户明确要求保留的组，给特征设 `required: true`，组缺失时最终导出会被拦截。`reflow_count` 记录因容量或线路问题重排的次数，质量报告统计保留、适配、返工与未核实数。填写 `display_width_px` 后预检会在同一宽度测量浏览器溢出与最小实际字号。在真实人类验收后再追加发布所需声明。
