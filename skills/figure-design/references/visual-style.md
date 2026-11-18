# 参考图与主题设计

## 纯文字

按 [Diagram Design 原版 Skill](../third_party/diagram-design/skills/diagram-design/SKILL.md) 选择主题、图型、模板和尺寸。离线交付按上游的系统字体设置执行，中文打开实际 PNG 核对字形。

## 图文混合

先确定结构，再定色。优先查看用户参考图，再从本地知识库找布局匹配的原图。记录实际看过的参考、迁移的阅读方向与分区，以及科研内容要求的调整。原文决定节点、关系和状态。

配色采用 [Astryx 的语义色彩原则](https://astryx.atmeta.com/docs/tokens) 和 [色彩强调规范](https://github.com/meta/astryx/blob/main/docs/design/color-emphasis.md)。以中性色承载大面积背景，选一支强调色给一至两个焦点。文字、形状、箭头与线型表达状态，颜色作为辅助。

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
