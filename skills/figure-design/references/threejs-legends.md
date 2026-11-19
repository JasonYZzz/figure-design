# 空间结构图例

在图文混合模式中，只有层级、遮挡、占用位置或几何尺度有助于解释原文时才加入三维图例。二维主图继续承载正式标签、连线、证据和数据。分层特征图、体素网格和分层存储各有可编辑的场景样例。

`plan --mode mixed` 和 `render` 不会启动三维渲染器。宿主在简报选定空间关系后显式执行 `legend-3d`，把生成的 SVG 登记并绑定到区域，最终图以静态矢量形式嵌入。题目含有“层级”并不等于存在有意义的空间结构。以记忆系统为例，读写顺序与检索对照可用二维路径和数据图表达。

从 Skill 根目录运行以下命令，使用与 render 相同的 Python 和 Chromium。Three.js 矢量渲染器已随包提供。

```sh
python scripts/figure.py legend-3d --scene assets/legends/feature-stack.json --out work/features.svg
```

可替换为 [稀疏体素](../assets/legends/voxel-grid.json) 或 [分层存储](../assets/legends/storage-tiers.json)。复制 [特征层级场景](../assets/legends/feature-stack.json) 后修改对象，即可制作新的图例。场景包含可访问标题 `title` 与 1–128 个 `objects`。每个对象指定以下字段。

| 字段 | 含义 |
| --- | --- |
| shape | box、sphere 或 cylinder |
| position | 对象中心的 x、y、z 坐标，各轴范围 −1000 至 1000，y 轴向上 |
| size | x、y、z 三轴外径，各轴范围 0.001 至 1000。圆柱的轴沿 y |
| color | 按当前主题指定的 #RRGGBB 基色。明暗用于区分朝向 |

渲染器采用固定正交视角和柔和的定向光，根据全部对象取景。输出透明、可缩放的 SVG；在目标使用尺寸检查对象遮挡、小间隙与颜色。SVGRenderer 采用面片排序，相交几何可能需要分离后再投影。正式图例文字写在主图中。几何尺寸涉及真实数值时需提供来源及刻度。

使用已有的 `asset-register --input work/features.svg --metadata ... --out ...` 登记已审阅的素材，将 `source_content_ids` 指向原文支持的实体或任务。类型、图意、权利及审阅意见按 [素材工作流](asset-governance.md) 填写，然后将生成的 asset.json 传给图文 preflight 和 render。
