# 将简报落实到画面

将下面字段写入 research-brief 生成的 design_decisions。以下为字段示例，ID 和数值须替换成已绑定的实际原文。候选保留 design_bindings；在候选上修改区域坐标、留白和素材比例。没有来源依据的事实不补写。

```json
{
  "hero_owner_id": "artifact",
  "main_paths": [
    {"input":"input","intermediate":"artifact","output":"use","relation_ids":["r1","r2"],"source_ids":["s1"]}
  ],
  "visual_concept": {
    "object_trace": [
      {"owner_id":"artifact","label_instances":{"before":"i-old","basis":"i-check","after":"i-new","next_action":"i-act"}}
    ],
    "evidence_displays": [
      {"owner_id":"trial","display":"paired-dot","asset_id":"trial-pairs","metric":"平均读数","unit":"分","baseline":"对照条件","scope":"指定任务子集","value_kind":"level","rows":[
        {"category":"组甲","condition":"对照","value":2,"source_id":"s2"},
        {"category":"组甲","condition":"处理","value":3,"source_id":"s2"}
      ]}
    ]
  }
}
```

- 每个路径的三个值都是 FigureContent 已展示的实体或任务 ID。中间项是交接物。直接路径可用终点作 intermediate。relation_ids 按连接顺序排列，源和终点一致。结果区域绑定独立的 owner。手工指定参考位置优先，路径和结果仍需检查。
- 四个状态字段通过 owner 的正式文字实例对应到成图。也可以将部分字段写进同一条 trace 的 asset_features，并用 asset_id 绑定实际插图，例如 before 和 after 的可见标签与颜色；这部分在目标宽度逐项看像素复核。旧简报的自由文字照常保留并标为待审。
- paired-dot 以 category 分组，每个类别恰有两个相同命名的条件。horizontal-bar 每个类别一个数值，条件可省略。每行引用包含该数值的原文摘录。相同单位及分母才能共用坐标。原有增益下降请用 value_kind=delta，并在 metric 中写出具体变化量、在 baseline 中写出差值的参照。分组和数值来自同一条记录。只画原文支持的值。
- plan 为证据区域绑定 asset_id，preflight/render 从 rows 自动绘制、校验和登记 SVG，render 将其随包保存。该区域须留出图形空间；通过 asset_fraction 调整比例。一个区域已有方法示意图时，为证据增加独立 owner。手工重新分区后保留比较资产在正确 owner 上。对图中自写的解释、案例箭头、数据定义仍需核对原文。
- 只能文字表达的实验使用 display=text_readout，填写 owner_id、metric、comparator、unit、scope、reason_if_text（如量纲或适用人群不同）。同单位对照优先选一种代表性的比较画出来。其他证据可用已有严格数据图或经审阅的资产，并在记录中注明对应 asset_id。
- 单独从 CSV 生成证据图使用 data-chart --kind paired-dot --x 类别列 --condition 条件列 --y 数值列 --unit 单位 --baseline 基准 --scope 范围 --title 指标 --input 输入.csv --out 新目录。分类横条用 --kind horizontal-bar；变化量另传 --value-kind delta。源 CSV 哈希及读数保存在 data-provenance.json。
- 对最终方案运行 preflight --brief 简报，随后 render --brief 同一简报。检查 quality-report.json 的 composition.design_review，沿 relation_ids 定位交接，逐项确认 before、basis、after、next_action 和各实验口径。用 1000 px 宽预览和源尺寸复核 readability，记录待修订项及 render_hash。

报告中的 visible_text 抄录了成图的来源绑定标签。对照原文找到同一对象的旧值、新值、核对依据与下一步。在同一区域放置的其他对象的文字不能代替它。min_font_px_at_1000 按固定 SVG 的实际显示比例换算，适合横向核对不同画幅；位图字和遮挡仍需打开缩放图查看。
