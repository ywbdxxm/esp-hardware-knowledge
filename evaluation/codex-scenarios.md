# Codex Hardware Research Acceptance Scenarios

这些场景用于从 ESPDocs 仓库以外的项目启动全新 Codex 任务，验收 Skill 路由、精确器件
隔离和原始来源门禁。除非场景另有说明，正常的单问题查询目标为 1 次 `doctor`、1 次精确
`search`、最多 1 次 `show` 和 1 次按需 `source`。调用次数不包含读取当前项目配置。

## 1. ESP32-C3 寄存器

**用户原话：** `ESP32-C3 的 GPIO_STRAP_REG 在哪里定义，回答前核对原始手册。`

**预期 Skill 路由：** 先用 `esp32-ai-hardware-engineering` 确定芯片和项目上下文，再用
`hardware-document-research` 执行精确检索；原页渲染与视觉核对使用 `pdf:pdf`。

**最多正常调用序列：** `doctor` -> 精确 compact `search` -> `show` -> `source`，共 4 次
ESPDocs 调用。

**身份与来源证据：** 命中必须是 `vendor=espressif`、`family=esp32`、
`part=esp32-c3`、`document_type=technical_reference_manual`；记录 `source_ref`、文档版本和
物理页码，并视觉核对哈希匹配的原始 PDF 页面。

**禁止的回退：** 不得使用 ESP32-S3、其他 ESP32 芯片、网络片段或生成 Markdown 直接回答
寄存器地址、位域或复位值；精确范围无结果时不得移除型号过滤器。

**通过/失败观察：** 正确芯片、TRM 身份、哈希和物理页均明确且答案来自已检查原页为通过；
出现跨芯片结果、缺少原页检查或把 `page_id` 当作 PDF 页码为失败。

## 2. 项目匹配的 ESP-IDF API

**用户原话：** `这个项目使用 ESP-IDF 的哪个版本？用对应版本说明这个 API。`

**预期 Skill 路由：** 使用 `esp32-ai-hardware-engineering`，先读最近的 `AGENTS.md`、项目文档、
CI、锁定配置和相关源码，再按项目解析出的 ESP-IDF 修订版查本地文档或该版本源码。

**最多正常调用序列：** 读取项目约束 -> 解析版本证据 -> 验证 `IDF_PATH` 一致性 -> 查询该版本
API 定义，正常最多 4 个步骤；若“这个 API”在上下文中无法唯一确定，则停止并询问一次。

**身份与来源证据：** 报告项目要求的 ESP-IDF 版本或提交、`IDF_TARGET`、版本证据所在文件，
以及同一版本的 API 文档或源码位置；环境中的全局版本只作为一致性证据。

**禁止的回退：** 不得把当前 shell、EIM 全局选择、最新安装版本或旧构建目录当作项目版本；
不得用其他 ESP-IDF 版本的 API 行为静默代替。

**通过/失败观察：** 项目版本与 API 来源一致且冲突证据被说明为通过；版本不明时明确限制或
询问上下文也可通过。未解析项目版本便直接回答，或引用随机已安装版本，为失败。

## 3. BQ24075 ISET

**用户原话：** `BQ24075 的 ISET 电阻如何决定充电电流？核对原始数据手册。`

**预期 Skill 路由：** 使用 `hardware-document-research` 解析精确器件和证据门禁；PDF 原页的
公式、引脚表和脚注使用 `docling-local-document-engineering` 定位并由 `pdf:pdf` 视觉核对。

**最多正常调用序列：** `doctor` -> 精确 compact `search` -> `show` -> `source`，共 4 次
ESPDocs 调用。

**身份与来源证据：** 命中必须是 `vendor=texas-instruments`、`family=bq2407x`、
`part=bq24075`、`document_type=datasheet`；核对 `source_ref`，并检查物理第 25 页的
Charge Current Translator 公式。需要引脚范围时再检查物理第 8 页。

**禁止的回退：** 不得返回 ESP32 文档、相似 PMIC、分销商摘要或只引用生成 Markdown；不得
在 BQ24075 精确范围无结果后移除 part/family 过滤器。

**通过/失败观察：** TI 精确系列无身份泄漏，公式、变量和页码均来自哈希匹配原页为通过；
任何跨系列命中、未核对公式页或猜测常数为失败。

## 4. 模糊丝印

**用户原话：** `我只有一个模糊丝印 ABC123，能直接按相似芯片给出绝对最大额定值吗？`

**预期 Skill 路由：** 使用 `hardware-document-research`，先从原理图、BOM、封装、厂商标识和
项目上下文补全身份；无法唯一确定时明确证据不足。

**最多正常调用序列：** 读取项目身份线索 -> 可选 `doctor` -> 可选 `inventory`，最多 3 步；
在没有精确型号前不执行会被误解为权威结论的宽范围搜索。

**身份与来源证据：** 列出已知丝印、封装、候选厂商与仍缺失的精确订货型号；绝对最大额定值
只有在型号、封装/变体和权威数据手册均匹配后才能引用。

**禁止的回退：** 不得把相似名称、同封装、搜索结果排名、分销商页面或家族型号当作精确
器件；不得给出无来源限定的绝对最大额定值。

**通过/失败观察：** 回答明确说当前不能给出权威额定值，并给出最小补证清单为通过；选择
“最像”的器件后输出具体极限值为失败。

## 5. CUDA 不可用但查询可用

**用户原话：** `CUDA 当前不可用，已有手册索引还能不能查？`

**预期 Skill 路由：** 使用 `hardware-document-research` 的 readiness 规则；若问题处于 ESP32
工程上下文，同时加载 `esp32-ai-hardware-engineering`，但查询判定仍以 ESPDocs readiness 为准。

**最多正常调用序列：** 仅 `doctor --json` 1 次；只有 `verify_recommended=true` 才允许追加
`verify`。

**身份与来源证据：** 读取 `readiness.query`、`readiness.source`、`readiness.ingest` 和
`reasons`；预期健康索引为 query true，CUDA 缺失时 ingest false。

**禁止的回退：** 不得依据 legacy `healthy=false` 宣布查询不可用，不得为了只读查询安装或
切换 Python/Docling/CUDA，也不得运行 ingest。

**通过/失败观察：** 正确区分“已有索引可查”和“当前不能入库”为通过；把 GPU 故障等同于
索引故障，或触发转换，为失败。

## 6. 源 PDF 已被替换

**用户原话：** `数据手册文件被替换后，旧索引中的电气参数还能直接引用吗？`

**预期 Skill 路由：** 使用 `hardware-document-research`，对关键电气参数执行原始来源哈希门禁；
需要判断 PDF 处理状态时使用 `docling-local-document-engineering`。

**最多正常调用序列：** `doctor` -> 精确 compact `search` -> `source`，最多 3 次 ESPDocs 调用；
确认哈希变化后停止，不继续扩展搜索。

**身份与来源证据：** `source` 必须重新计算当前 PDF SHA-256，并与索引中的 `source_ref` 比较；
出现 `SourceChangedError` 或退出码 4 时，旧页只能作为失效定位线索。

**禁止的回退：** 不得直接引用旧索引中的电气参数，不得把同名新文件视作同一修订版，也不得
只更新 manifest/hash 而跳过重新入库和验证。

**通过/失败观察：** 拒绝关键结论，要求审核新文档身份后重新 ingest 并 verify 为通过；在哈希
不匹配时仍引用旧数值，或静默接受替换文件，为失败。

## 7. 表格与脚注

**用户原话：** `解释这张数据手册表格，并检查原始页面与脚注。`

**预期 Skill 路由：** 使用 `hardware-document-research` 确认器件身份和来源，使用
`docling-local-document-engineering` 处理表格结构，并强制使用 `pdf:pdf` 渲染和视觉检查原页。

**最多正常调用序列：** `doctor` -> 精确 compact `search` -> `show` -> `source`，共 4 次
ESPDocs 调用；表格或脚注跨页时最多追加 1 个相邻物理页检查。

**身份与来源证据：** 报告精确器件、文档标题/修订、`source_ref`、表号或章节、物理页码，
并检查表头、单位、合并单元格、条件列、脚注标记及必要的相邻页。

**禁止的回退：** 不得只根据 OCR/Markdown 重排后的表格作答，不得省略限制条件、单位、脚注
或把生成页序号当作物理 PDF 页码。

**通过/失败观察：** 解释保留表格条件与脚注语义，且明确已视觉检查哈希匹配原页为通过；
表格列错位、遗漏脚注、无原页检查或来源身份不明为失败。
