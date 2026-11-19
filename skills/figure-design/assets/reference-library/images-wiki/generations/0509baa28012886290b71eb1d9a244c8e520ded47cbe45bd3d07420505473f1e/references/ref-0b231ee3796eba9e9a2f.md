---
reference_id: ref-0b231ee3796eba9e9a2f
review_status: auto_proposed
sha256: 0b231ee3796eba9e9a2fe351bc4795471ee6ac3edeaba5dd8c276ab3256b0ae5
source: images/robot.png
---

# 室内移动机器人定位与建图路线

[返回知识导航](../index.md)

<a href="../../../../images/robot.webp">查看参考图</a> · <a href="../../../../images/robot.png">外接 PNG 原件</a>（公开包需另配图库）。原件 SHA256：`0b231ee3796eba9e9a2fe351bc4795471ee6ac3edeaba5dd8c276ab3256b0ae5`

审核：auto_proposed；分析版本：2.0；密度：medium

分类：{"density":"medium","domain":"cs-ai","layout":"macro-micro-mechanism","media":"illustrated","purpose":"roadmap","temporal_axis":"stages","topology":["sequence"]}

阅读顺序：走廊观察与激光轮廓并列，随后出现位姿图和占据栅格。

<a id="overview"></a>
## overview

归一化区域：`[0, 0, 1, 1]`

走廊观察与激光轮廓并列，随后出现位姿图和占据栅格。


<a id="focus"></a>
## focus

归一化区域：`[0.02, 0.09, 0.58, 0.55]`

走廊观察与激光轮廓并列，随后出现位姿图和占据栅格。

可迁移设计（推断）：将环境、局部地图与离散栅格配对。

## 限制与待核查

- 回环边缺乏同地点重访的证据，不能复用其约束连法。
- 生成图，仅借鉴所列布局，技术关系须回查任务来源。

## 相关参考
