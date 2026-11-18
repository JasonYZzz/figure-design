# 本地复用与来源记录

所有生产代码均包含在当前 Skill 内；不会从 GitHub、本机其他项目或其他 Skill 路径动态导入。`sources.json` 记录本次读取的上游相对文件名、内容 hash 和复用方式，不要求这些上游路径在安装机器上存在。

## PPT Master

从用户已下载的本地项目中提取 `resource_paths.py` 的 SVG 资源闭包检查常量和函数，保留实现，去掉不使用的 PPT 项目路径/图标目录解析部分。位置：`scripts/vendor/ppt_master_svg_resources.py`，运行依赖仅为 Python 标准库。

Copyright (c) 2025-2026 Hugo He。适用 [MIT License](ppt-master/LICENSE)。用于素材注册和成图导出前的资源完整性检查；不包含 PPTX 转换器、在线搜图、自动更新器或外部模板下载逻辑。

## Diagram Design

`diagram-design/` 是用户本地仓库提交 `f6db0decea96de66b901331a0f79a8d4b147ebae` 的完整受版本控制快照，共 763 个文件。保留 [MIT License](diagram-design/LICENSE) 及[第三方许可](diagram-design/THIRD_PARTY_LICENSES.md)。Skill 在纯文字模式读取 [HTML 模板](diagram-design/skills/diagram-design/assets/template.html)和[架构](diagram-design/skills/diagram-design/references/type-architecture.md)、[流程图](diagram-design/skills/diagram-design/references/type-flowchart.md)规则。渲染时移除模板的远程字体引用，内嵌科研 SVG 与字体子集。项目快照随安装包复制，运行入口为 Scientific Figure Designer。

## nature 系列

分析本机 nature-figure 的 figure-contract / multipanel-evidence-architecture 和 nature-proposal-writer 的 evidence-table / argument-map。提取“问题或主张—证据—面板角色—限制条件”的设计方法，在 `scripts/figure_research.py` 和 `references/scientific-design.md` 独立实现。

没有复制 nature 的源码、外部样例图或整套提示词；未发现可覆盖全部这些材料的统一许可证，因此不把本机安装等同于再分发许可。当前包无需安装 nature skills。

## 字体

Noto CJK 字体文件已实际包含在 `assets/fonts/`，其许可证和 hash 说明也在同一目录。标准 XML namespace、JSON Schema dialect URI 和许可证中的网址是标识/原文，不是源码下载入口。
