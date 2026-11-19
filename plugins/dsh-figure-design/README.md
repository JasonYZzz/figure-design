# Figure design · DeepSeek Harness 插件

在 DSH 对话中用 `/dsh-figure-design` 将论文、开题报告、基金申请或研究方案转换为科研图。默认生成纯文字技术路线图或架构图。要求带插图时，可使用原创 SVG 或已获准使用的素材。交付可编辑 SVG、PNG、离线 HTML 和质量报告。

## 安装与使用

兼容范围为 `^0.2.1-rc.3 || ^0.2.2-rc.3`。在 figure-design 仓库根目录用 Python 3.10+、Node.js 22.19+（22.x）或 24+、npm 和项目依赖构建插件包，再安装到实际使用的 Profile。以下以 CLI 的 `web` Profile 为例。

```bash
make setup
make package-dsh
export FIGURE_PY="$PWD/.venv/bin/python"
dsh plugin --profile web add "$PWD/dist/dsh-figure-design-1.8.0.tgz"
dsh web
```

已使用 DeepSeek Harness 桌面版时，用桌面版提供的 `dsh` CLI，并在退出桌面应用后执行 `dsh plugin --profile desktop add <插件包绝对路径>`。随后重新打开桌面客户端，从「插件 → 已安装」查看「科研图设计」。

拿到预构建 `.tgz` 时可直接用绝对路径安装。渲染环境需要 Python 依赖和 Playwright Chromium。若尚未准备，在会话中让 Agent 给出已加载 Skill 的资源目录，然后在独立虚拟环境中执行以下命令。`FIGURE_SKILL` 取会话报告的绝对路径，`FIGURE_PY` 取虚拟环境的 Python 绝对路径。

```bash
"$FIGURE_PY" -m pip install -r "$FIGURE_SKILL/requirements.txt"
"$FIGURE_PY" -m playwright install chromium
"$FIGURE_PY" "$FIGURE_SKILL/scripts/figure.py" doctor
```

启动 DSH 前可在终端导出 `FIGURE_PY`，也可把解释器绝对路径随任务一起告诉 Agent。以下示例中的 Markdown 文件需先放到会话工作区中，或作为附件提供。

> /dsh-figure-design 根据研究方案.md 画一张纯文字技术路线图，导出 SVG、PNG、离线 HTML 和质量报告。

插件使用 `/dsh-figure-design`，以便与独立安装版的 `/figure-design` 并存。

包内提供参考索引、随包 Diagram Design、字体和许可证。离线参考导航位于 Skill 资源目录的 `assets/reference-library/images-wiki/index.html`。公开包的分析页可独立查阅。本地图集可用 `refs-search --images <目录>` 绑定。图文模式可另外绑定获准素材，外部生图工具在宿主中单独配置。卸载用 `dsh plugin --profile web remove dsh-figure-design`。

## 维护

- [DSH Bundle 规范](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/preset/agent-preset/skills/dsh-doc/references/host-plugin.md)定义 `dsh.bundle.patch`、Cordis 入口和插件元数据。本插件通过 `ctx.skills.register()` 注册工作流，资源路径相对于安装包定位。DSH 管理启用和卸载时的注册生命周期。 [Skill 注册接口](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/skills.md)
- 构建借鉴 `dsh-image-gen` 的预构建 npm 包安装方式。`make package-dsh` 从公开 Skill 打包流程取资源，并从同一源码读取版本和 Skill 元数据。插件源码目录用于构建，安装使用生成的 `.tgz`。 [dsh-image-gen](https://github.com/shanliuling/dsh-image-gen#快速开始)
- DSH Market 从独立目录读取市场条目。要对外分发，可发布预构建包后向该目录提交条目。 [市场收录说明](https://github.com/dsh-market/dsh-market#submit-your-plugin)
