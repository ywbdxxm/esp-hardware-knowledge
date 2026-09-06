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
| 资料库 | 11 份文档，2750 个物理 PDF 页 |
| 黄金集 | 24 条，top-5 原文定位召回率 100%，身份泄漏 0 |

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

允许的来源只在 `config/documents.toml` 中以明确的厂商、系列、精确型号、文档类型、语言和
版本声明。当前包含：

```text
%USERPROFILE%\Desktop\AI-HRADWARE\docs\ESP32-C3
%USERPROFILE%\Desktop\AI-HRADWARE\docs\ESP32-S3
%USERPROFILE%\Desktop\AI-HRADWARE\docs\PMIC\bq2407x.pdf
```

schema-v2 不从文件名猜测身份，也不会自动纳入同目录的其他 PDF。克隆到其他目录时，把包含
这些相对路径的目录显式指定为来源基准：

```powershell
$env:ESPDOCS_SOURCE_BASE = "D:\path\to\AI-HRADWARE"
```

## 常用工作流

### 日常只读检索

Codex 和其他自动化调用优先使用已部署的稳定启动器，而不是依赖当前目录或全局
`espdocs` 命令。已知精确型号时，日常单问题路径为一次 readiness、一次 compact 精确搜索、
一次完整页查看，以及仅在证据门禁要求时执行的一次原页核验：

```powershell
$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE ".codex" }
$runner = Join-Path $codexHome "skills/hardware-document-research/scripts/invoke-espdocs.ps1"
& $runner doctor --json
& $runner search "GPIO_STRAP_REG" --vendor espressif --family esp32 `
  --part esp32-c3 --type technical_reference_manual --limit 5 --compact --json
& $runner show 123 --json
& $runner source 123 --json
```

只看 `doctor.readiness.query` 判断已有索引能否查询；GPU/Docling 不可用于入库时，健康索引
仍可检索。型号、系列或可用文档类型不明确时，在 search 前增加一次 `inventory --json`，
不要猜过滤值。compact 结果用于选择候选，`show` 读取完整证据单元；只有结果要求原文检查，
或结论涉及电气值、寄存器、引脚、时序、表格、图和脚注时才调用 `source`。

`verify` 是入库、配置迁移、源文件变化或疑似损坏后的维护门禁，不是每次只读查询的前置步骤。
可从任意目录执行整套机器验收：

```powershell
$repoRoot = [Environment]::GetEnvironmentVariable("ESP_HARDWARE_KNOWLEDGE_ROOT", "User")
$workflow = Join-Path $repoRoot "scripts/check-research-workflow.ps1"
powershell -NoProfile -ExecutionPolicy Bypass `
  -File $workflow -Launcher $runner
```

成功输出中的 `passed` 和五项 `checks` 均为 true。脚本不运行 ingest；只有
`doctor.readiness.verify_recommended=true` 时才追加完整 verify。

### 新增手册与维护

新增手册时保留原始文件，把它放到 `ESPDOCS_SOURCE_BASE` 下受控的资料目录，并在
`config/documents.toml` 增加 schema-v2 明确身份。路径保持相对于 source base，不写个人绝对
路径；型号、变体、语言和文档修订未知时明确写 `unknown`，不得从文件名猜测：

```toml
[[documents]]
path = "docs/PMIC/example.pdf"
vendor = "vendor-name"
family = "device-family"
parts = ["exact-part-number"]
document_type = "datasheet"
language = "en-US"
document_revision = "document-revision"
```

先执行 `ingest --dry-run --json` 核对身份与文件，再以
`ingest --document example.pdf --json` 更新语料和索引，最后运行 `verify --json` 和本节的
机器验收。非 PDF 格式只有在存在真实原始来源、格式适配器和对应黄金案例后才能加入。

源文件发生变化时，旧索引中的关键结论不能继续引用。`source` 会因 SHA-256 不匹配拒绝该页；
先确认替换文件仍对应相同精确器件和正确修订，再对该精确文件重新 ingest，并通过 verify 后
恢复使用。若替换是意外的，恢复原哈希文件比重写索引更安全。

### 入库与完整维护

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

仓库中的 `codex/AGENTS.md` 和以下三个目录是可版本化的 Codex 配置源：

```text
%USERPROFILE%\.codex\skills\hardware-document-research\
%USERPROFILE%\.codex\skills\esp32-ai-hardware-engineering\
%USERPROFILE%\.codex\skills\docling-local-document-engineering\
%USERPROFILE%\.codex\AGENTS.md
```

`hardware-document-research` 负责器件身份、来源选择和证据门禁；
`esp32-ai-hardware-engineering` 负责 ESP32/ESP-IDF 工程、版本匹配和架构约束；
`docling-local-document-engineering` 负责 PDF 原生文本、版面、OCR 和可复用语料处理。
涉及 ESP-IDF API、Kconfig、构建、迁移和示例时，先从项目文档、CI 或配置解析所需版本，
再验证 `$env:IDF_PATH` 和该版本一致；不得使用固定机器路径或静默引用其他版本。

新的 Docling Skill 是 PDF 阅读和资料工程的默认入口。它对短小、结构简单且原生文本可靠
的 PDF 使用轻量提取，对扫描件、复杂表格/图片、多栏和长文档使用本地 Docling；关键证据
仍回到原 PDF 页面。`pdf:pdf` 继续负责原页渲染、表单、PDF 创建/编辑和版面检查。

在另一台 Windows 机器部署时，先安装 uv 和所需工具。只需要通用 Docling CLI 时可使用：

```powershell
uv tool install docling
docling --version
```

要复现本仓库带 CUDA、RapidOCR 和 ESPDocs 的固定环境，使用前文的 `uv sync --dev`，不要
用通用 tool 环境替代项目 `.venv`。跨机器使用时，以 Windows 用户变量配置仓库根目录、
原始文档根目录和生成数据根目录：

```powershell
[Environment]::SetEnvironmentVariable(
    "ESP_HARDWARE_KNOWLEDGE_ROOT", "D:\path\to\esp-hardware-knowledge", "User"
)
[Environment]::SetEnvironmentVariable(
    "ESPDOCS_SOURCE_BASE", "D:\path\to\hardware-library", "User"
)
[Environment]::SetEnvironmentVariable(
    "ESPDOCS_DATA_ROOT", "D:\path\to\espdocs-data", "User"
)
```

安装匹配的 ESP-IDF 后，在其已验证环境中设置 `IDF_PATH`。部署前先从仓库根目录执行只读
检查；`-Check` 不创建目录或修改文件，目标缺失、不一致或 manifest 缺失时返回非零：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-codex-assets.ps1 -Check
powershell -ExecutionPolicy Bypass -File .\scripts\install-codex-assets.ps1
```

默认目标为 `$env:CODEX_HOME`，未设置时使用 `%USERPROFILE%\.codex`。测试其他目录或使用
自定义 Codex Home 时传入 `-CodexHome D:\path\to\.codex`。安装器先验证三个源 Skill，
对比当前源、目标和上次部署 manifest，只更新未被本地修改的受管文件；任一步失败都会恢复
先前的完整受管集合。目标漂移默认拒绝覆盖，只有确认目标改动已合并回仓库后才使用：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-codex-assets.ps1 -Force
```

部署记录位于 `%CODEX_HOME%\managed\esp-hardware-knowledge-assets.json`，包含受管相对路径与
SHA-256。安装器只替换三个同名 Skill 和全局 `AGENTS.md`，不会删除其他 Skill。PDF、语料、
SQLite、模型缓存和渲染页面仍保存在本机，不随 Git 同步。

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
