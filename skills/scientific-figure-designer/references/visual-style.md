# 参考图与主题设计

先确定结构，再定色。优先打开用户给出的参考图。其次从本地知识库查找布局匹配的原图，再用 Diagram Design 对应图型示例补充。记录实际看过的参考、迁移的阅读方向与分区，以及科研内容要求的调整。原文决定节点、关系和状态。

配色采用 [Astryx 的语义色彩原则](https://astryx.atmeta.com/docs/tokens) 和 [色彩强调规范](https://github.com/meta/astryx/blob/main/docs/design/color-emphasis.md)。按角色选择具体颜色。在参考图的冷暖、图面内容和用户品牌偏好之间做取舍。以中性色承载大面积背景，选一支强调色给一至两个焦点。文字、形状、箭头与线型表达状态，颜色作为辅助。绿可用于有明确含义的状态或用户指定的主题。

## 纯文字

按 [Diagram Design 原版 Skill](../third_party/diagram-design/skills/diagram-design/SKILL.md) 选择图型、模板和尺寸。沿用用户明确指定的项目 profile。其余情况将原版 Skill 目录复制到本次任务的工作目录，在副本的 `references/style-guide.md` 写入模型选定的纸面、主文字、次文字、边界和焦点颜色，并设为 `Font source: system`。以这个已定制的任务副本执行上游工作流。中文使用宿主具备的 CJK 系统字体，打开实际 PNG 核对字形。

## 图文混合

向选定的 CompositionPlan 写入 `theme`，明确纸面、节点面、主文字、辅助文字、强调和边界六个角色。说明参考图给了什么结构线索，以及为何选该强调色。以传感数据示意为例：

```json
{
  "paper": "#F8F8FC",
  "surface": "#FFFFFF",
  "ink": "#1C2941",
  "muted": "#485774",
  "accent": "#31598F",
  "border": "#BCC9DC",
  "rationale": "参考图采用中心对象与外围验证步骤，选冷蓝突出监测及数据记录。"
}
```

预检要求主文字、辅助文字和强调色与两种底色的对比度达到 4.5:1。质量报告记录实际颜色。插画构思使用同一组角色色，定量图可用 `data-chart --plan <plan.json>` 共用主题。素材自身的科学色标和授权边界按素材工作流程处理。CLI 在没有自定义主题时使用 `style_id` 对应的备用主题。
