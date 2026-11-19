---
reference_id: ref-74292ce6d9abf63bc93f
review_status: auto_proposed
sha256: 74292ce6d9abf63bc93f15729f9d320afd119a21cc44cfc50319ef917c40945e
source: images/stereo.png
---

# 双目视觉深度估计技术路线

[返回知识导航](../index.md)

<a href="../../../../images/stereo.webp">查看参考图</a> · <a href="../../../../images/stereo.png">外接 PNG 原件</a>（公开包需另配图库）。原件 SHA256：`74292ce6d9abf63bc93f15729f9d320afd119a21cc44cfc50319ef917c40945e`

审核：auto_proposed；分析版本：2.0；密度：medium

分类：{"density":"medium","domain":"cs-ai","layout":"comparative-panels","media":"illustrated","purpose":"roadmap","temporal_axis":"stages","topology":["comparison"]}

阅读顺序：左右视图对照同一场景，再比较局部匹配窗口。

<a id="overview"></a>
## overview

归一化区域：`[0, 0, 1, 1]`

左右视图对照同一场景，再比较局部匹配窗口。


<a id="focus"></a>
## focus

归一化区域：`[0.02, 0.28, 0.94, 0.43]`

左右视图对照同一场景，再比较局部匹配窗口。

可迁移设计（推断）：左右面板共用标线，保留对应物的位置。

## 限制与待核查

- 局部块相似不能代替左右视差一致性检验。
- 生成图，仅借鉴所列布局，技术关系须回查任务来源。

## 相关参考
