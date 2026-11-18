# 开发与维护

## 修改范围

项目和 Skill 名均为 `scientific-figure-designer`。唯一源码在 `skills/scientific-figure-designer/`。`.agents/skills/scientific-figure-designer` 是相对符号链接。Skill 内资源一律相对自身目录解析。

运行代码放 Skill 的 `scripts/`，调用规则放 `SKILL.md`，详细流程放 `references/`，结构契约放 `schemas/`。根目录 `scripts/` 只处理仓库维护。测试和 fixtures 随 Skill 发布，验证独立安装行为。

## 检查和发布

1. 首次执行 `make setup`。依赖没有变化时复用现有虚拟环境，不升级无关依赖。
2. 修改后执行 `make check`、`make test`。涉及布局/字体/渲染时再运行 `make benchmark OUT=build/<新目录>` 并查看图像。
3. 涉及资源/安装/打包时，构建 ZIP，解压到临时目录，通过包内 `scripts/install.py` 安装到新的 skills 父目录；从仓库外运行 doctor、检索、测试和演示。
4. 版本定义在 Skill 的 `scripts/figure_common.py`。更新版本、入口说明和对应发布记录后重新打包。Skill 的 `LICENSE` 与仓库根目录许可证同步，安装包随附这份许可证和第三方声明。
5. `make package` 构建公开安装包。需要私用迁移时使用 `make package-private`，将原图随包保存在本地。

参考索引中的 `path` 始终相对 `assets/reference-library/images/`。增加/替换原图后，先运行 refs-index 并审查候选标注，再打包；打包器拒绝图库与索引不一致。候选标签不自动升级为人审，未知许可不自动升级为授权素材。

## 文档与输出

- 当前设计见 [架构](docs/ARCHITECTURE.md)、[开发计划](docs/DEVELOPMENT_PLAN.md) 和 [任务状态](docs/development/BACKLOG.csv)。
- 原始设计文档在 `docs/archive/design/`。旧验证日志和本机清理清单留在本地归档。
- 开发运行输出放 `build/`，可安装产物放 `dist/`，用户产物放 `outputs/`。知识库只提交当前 generation，旧 generation 可留在 `build/reference-knowledge-history/`。

当前 CI 在 Linux 安装 Chromium 后执行测试、构图基准、仓库检查和轻量打包。工作流定义存在不代表远程 CI 已实际通过。
