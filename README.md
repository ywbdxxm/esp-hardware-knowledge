# ESP Hardware Knowledge

本项目为本机 ESP32-C3/S3 官方 PDF 提供可追溯的资料层和确定性检索层。Docling 与 RapidOCR 在本地解析文档，SQLite FTS5 负责中英文关键词检索；每个结果都保留原 PDF 文件、SHA-256 和物理页码。Markdown 只用于定位候选证据，原 PDF 始终是最终权威来源。

## 当前基线

截至 2026-08-16，本机已验证：

| 项目 | 状态 |
| --- | --- |
| Python | CPython 3.13.15，由 uv 项目环境隔离 |
| GPU | NVIDIA GeForce RTX 5070 Ti，16303 MiB |
| PyTorch | CUDA 13.0 可用 |
| ONNX Runtime | `CUDAExecutionProvider` 可用 |
| Docling / RapidOCR | 2.120.1 / 3.9.2 |
| 资料库 | 10 份文档，2697 个物理 PDF 页 |
| 黄金集 | 23 条，top-5 原文定位召回率 100% |

基线是本机快照，不替代 `doctor` 和 `verify` 的实时结果。

## 安装与同步

前提是 Windows 11、uv 和支持当前 CUDA 运行时的 NVIDIA 驱动已经安装。项目不使用系统 Python，也不复用 ESP-IDF 的 Python 环境。

```powershell
cd $env:USERPROFILE\Desktop\AI-HRADWARE\esp-hardware-knowledge
uv python install 3.13
uv sync --dev
uv run espdocs doctor --json
```

`pyproject.toml` 和 `uv.lock` 固定 Python 依赖；PyTorch 从项目声明的 CUDA 13.0 wheel 索引安装。默认 `ESPDOCS_DEVICE=cuda`，如果 PyTorch CUDA 或 ONNX CUDA 不可用，转换会直接失败，避免无提示地退回 CPU。只有明确排障时才临时启用 CPU：

```powershell
$env:ESPDOCS_DEVICE = "cpu"
uv run espdocs doctor --json
```

关闭该 PowerShell 窗口即可清除临时环境变量。日常完整入库应保持 CUDA 模式。

## 文档来源

允许的来源只在 `config/documents.toml` 中声明：

```text
%USERPROFILE%\Desktop\AI-HRADWARE\docs\ESP32-C3
%USERPROFILE%\Desktop\AI-HRADWARE\docs\ESP32-S3
```

发现逻辑只递归扫描这两个目录，未能按已审核文件名规则分类的 PDF 会报错，不会猜测类型。克隆到其他目录时，可把包含 `docs\ESP32-C3` 和 `docs\ESP32-S3` 的目录显式指定为来源基准：

```powershell
$env:ESPDOCS_SOURCE_BASE = "D:\path\to\AI-HRADWARE"
```

## 常用工作流

先查看本次会处理哪些文件：

```powershell
uv run espdocs ingest --dry-run --json
```

入库全部文档，或只处理一个精确文件名：

```powershell
uv run espdocs ingest --json
uv run espdocs ingest --document esp32-c3_datasheet_cn.pdf --json
```

入库按 SHA-256 增量执行。未变化的文档跳过 OCR，但索引仍会从当前语料原子重建。大 PDF 每 32 页保存一个与源哈希绑定的完成标记，中断后可继续。新语料先写入 `corpus\.staging`，通过页数、UTF-8、图片引用和内容检查后才替换正式目录；替换失败会恢复旧语料。

检索、查看完整 Markdown 页、再核验原 PDF：

```powershell
uv run espdocs search "GPIO_STRAP_REG" --chip esp32-c3 --type technical_reference_manual --limit 5 --json
uv run espdocs show 123 --json
uv run espdocs source 123 --json
```

`show` 和 `source` 接收的是 `search` 返回的 `page_id`，不是直接输入 PDF 页码。`source` 会重新计算源 PDF 的 SHA-256；文件发生变化时拒绝渲染，避免把旧索引对应到新文件。

发布或更新资料库后运行完整门禁：

```powershell
uv run espdocs doctor --json
uv run espdocs verify --json
```

`verify` 同时检查 SQLite 完整性、语料与索引计数、Markdown 和本地图片引用、至少 20 条黄金案例、top-5 召回率不低于 95%、芯片隔离，以及原文检查标志。

## 证据规则

检索结果按以下等级处理：

| 等级 | 含义 |
| --- | --- |
| A | 已重新核验源 PDF 哈希并渲染对应物理页 |
| B | 页映射和语料检查通过，且没有强制原文核验条件 |
| C | 只能作为定位线索，必须查看原 PDF |

以下情况必须执行 `espdocs source <page_id>`：

- 寄存器地址、位域、复位值和保留位
- 电压、电流、功耗、额定值、阻抗和射频参数
- 时序、频率、延时、引脚、启动和 strap 配置
- eFuse、安全启动、加密、烧录和 Flash 操作
- 表格、框图、图片、OCR 警告或未知文档版本
- Markdown 与原 PDF 存在任何差异或上下文不足

涉及硬件安全、不可逆 eFuse、供电和烧录决策时，应同时检查相邻页、芯片型号、文档版本和勘误，不得根据检索片段直接执行。

## 本地数据

运行数据不进入 Git：

```text
%USERPROFILE%\Desktop\AI-HRADWARE\docs\esp-hardware-knowledge-data\
  corpus\                 分页 Markdown、图片、manifest 和 Docling 诊断数据
  index\espdocs.sqlite3   当前原子发布的 FTS5 索引
  renders\                哈希核验后的原 PDF 页面渲染
  cache\                  本地缓存
  logs\                   运行日志目录
  backups\                人工维护操作的可恢复备份
```

数据位置按以下顺序解析：用户或进程级 `ESPDOCS_DATA_ROOT`、同时包含 C3/S3 来源的
`docs\esp-hardware-knowledge-data`、最后才是兼容旧安装的
`%LOCALAPPDATA%\esp-hardware-knowledge`。本机使用显式用户级配置：

```powershell
[Environment]::SetEnvironmentVariable(
    "ESPDOCS_DATA_ROOT",
    "$env:USERPROFILE\Desktop\AI-HRADWARE\docs\esp-hardware-knowledge-data",
    "User"
)
```

设置后，新启动的 PowerShell、Codex Desktop 和 Codex CLI 会读取该值；当前已运行的进程
需要重启或临时设置同名 `$env:` 变量。

2026-08-16 的旧图片路径迁移备份位于 `backups\markdown-pre-image-fix-20260816-052940`。确认后续多次 `verify` 均通过后可手工归档或删除；它不参与索引。

Git 只跟踪代码、配置、测试、黄金定位案例和文档。PDF、语料、模型缓存、渲染图片和 SQLite 数据库均留在本机。

## Codex 集成

仓库中的 `codex/AGENTS.md`、`skills/esp32-ai-hardware-engineering` 和
`skills/docling-local-document-engineering` 是可版本化的 Codex 配置源。本机部署位置分别是：

```text
%USERPROFILE%\.codex\skills\esp32-ai-hardware-engineering\
%USERPROFILE%\.codex\skills\docling-local-document-engineering\
%USERPROFILE%\.codex\AGENTS.md
```

全局 `AGENTS.md` 要求 Codex 遇到 ESP32/ESP-IDF 的代码、资料查询、硬件参数、编译、
烧录或调试任务时先加载该 Skill。涉及本地 PDF 时，Skill 会先使用 `espdocs` 定位，再按
证据规则回到原 PDF。ESP-IDF API、Kconfig、构建、迁移和示例优先使用项目同版本的本地
ESP-IDF 文档与源码：先解析项目确认的 IDF 根目录，再检查 `$env:IDF_PATH`，最后才把
`C:\esp\v6.0.2\esp-idf` 作为 v6.0.2 的本机回退；版本不匹配时不得静默引用。

新的 Docling Skill 是 PDF 阅读和资料工程的默认入口。它对短小、结构简单且原生文本可靠
的 PDF 使用轻量提取，对扫描件、复杂表格/图片、多栏和长文档使用本地 Docling；关键证据
仍回到原 PDF 页面。`pdf:pdf` 继续负责原页渲染、表单、PDF 创建/编辑和版面检查。

在另一台 Windows 机器部署时，先安装 uv 和所需工具。只需要通用 Docling CLI 时可使用：

```powershell
uv tool install docling
docling --version
```

要复现本仓库带 CUDA、RapidOCR 和 ESPDocs 的固定环境，使用前文的 `uv sync --dev`，不要
用通用 tool 环境替代项目 `.venv`。安装匹配的 ESP-IDF 后，在其导出终端中设置 `IDF_PATH`，
再从仓库根目录部署两个 Skill 和全局规则：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-codex-assets.ps1
```

默认目标为 `$env:CODEX_HOME`，未设置时使用 `%USERPROFILE%\.codex`。测试其他目录或使用
自定义 Codex Home 时传入 `-CodexHome D:\path\to\.codex`。安装器只替换本仓库管理的两个
同名 Skill 和全局 `AGENTS.md`，不会删除其他 Skill。PDF、语料、SQLite、模型缓存和渲染
页面仍保存在本机，不随 Git 同步。当前仓库不包含 Claude Code、OpenCode 或 Hermes 适配。

## JSON 与错误处理

所有自动化入口都支持 `--json`，成功响应包含 `schema_version: 1`。调用方应按字段读取，不解析终端展示文本。主要退出码为：

| 退出码 | 含义 |
| --- | --- |
| 0 | 成功 |
| 1 | 门禁未通过或未分类的意外错误 |
| 2 | 配置、过滤器或参数错误 |
| 3 | 运行环境、索引或依赖不可用 |
| 4 | 原 PDF 缺失、页码无效或哈希变化 |
| 5 | 转换、入库或索引构建失败 |

## 排障

`doctor` 显示 GPU 不可用时，先确认 NVIDIA 驱动、`torch.cuda.is_available()` 和 ONNX providers；不要仅凭任务管理器默认的“3D”曲线判断 CUDA 是否工作。可在任务管理器 GPU 图表中切换到 CUDA/Compute，或运行：

```powershell
uv run python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0), torch.version.cuda)"
uv run python -c "import onnxruntime as ort; print(ort.get_available_providers())"
```

`verify` 报 `missing_image` 或 `escaping_image` 时，不要继续使用该语料回答图片或表格问题；重新入库对应 PDF。`source` 报哈希变化时，先运行 `ingest --document <文件名>` 重建语料和索引。检索无结果时，先确认芯片和文档类型过滤器，再补充经过审核的术语别名；本阶段不通过语义模型静默扩大查询。
