# AI Analysis Pipeline Guide

**Version**: 1.0.0  
**Module**: AI Analysis Core (`app/analyzers`, `app/workers/analyze_tasks.py`)

---

## 1. Overview (架构总览)

本系统的 AI 分析管道基于 **Map-Reduce** 思想设计，旨在从海量、非结构化的社交媒体数据中提炼出结构化的洞察。系统不仅关注分析的准确度，更在工程实践中极大地优化了**成本控制 (Cost Engineering)** 和**信噪比 (SNR)**。

### 核心流程图
```mermaid
graph LR
    Input[Raw Data Stream] --> Filter[Preprocessor Filter]
    Filter --> Heap[Min-Heap (Top-N Selection)]
    Heap --> Sample[Semantic Sampling (Embedding)]
    Sample --> LLM_S[LLM: Sentiment Analysis]
    LLM_S --> LLM_C[LLM: Opinion Clustering]
    LLM_C --> Viz[Mermaid/Report Generation]
```

---

## 2. 数据处理与信噪比优化 (Data Cleaning & SNR Optimization)

在 AI 舆情分析中，原始数据通常包含大量“噪声”。直接将其输入 LLM 不仅会显著增加 Token 成本，还会干扰模型对核心观点的提取精度。

### 2.1 流式预处理 (Streaming Preprocessing)
为了应对热门话题可能产生数万条评论的情况，系统采用了流式处理架构：
*   **Server-side Cursor**: 使用 SQLAlchemy 的 `yield_per(500)`，每次只拉取 500 条记录，确保内存占用恒定。
*   **Min-Heap (最小堆)**: 维护一个固定大小（默认 200）的最小堆，通过 `engagement_score` 实时筛选高价值样本，实现 O(N) 复杂度的 Top-K 提取。

### 2.2 数据清洗策略 (Noise Reduction)
系统通过 `DataPreprocessor` 类执行多级清洗流水线：
1.  **Token 压缩**: 自动移除文本中的 URL、HTML 标签及特殊控制字符。这能为单条记录平均节省 15% - 20% 的 Token。
2.  **Bot 过滤**: 建立基于作者特征和回复频率的黑名单，剔除 `Automoderator` 及类似的机器生成内容。
3.  **垃圾信息识别**: 利用经过优化的正则表达式库，动态识别推广语、优惠码等商业垃圾信息。
4.  **文本规范化**: 强制进行语种对齐 (`langdetect`)，并过滤掉长度不足（小于 10 字符）或重复率极高的“灌水”言论。

### 2.3 热度加权算法 (Engagement Scoring)
系统根据以下公式计算每条数据的权重，以决定其进入分析管道的优先级：
```python
# 互动指标加权求和
score = upvotes + (num_comments * 2) + (likes * 10) + (views / 1000)
```
*   `upvotes`/`likes`: 基础认可度。
*   `num_comments`: 讨论热度（权重更高）。
*   `views`: 曝光度（权重较低）。

---

## 3. Intelligent Sampling (智能采样)

在筛选出 Top-N 高热度数据后，系统会进行**语义去重**，防止大量重复的“刷屏”言论占据分析配额。

### 技术原理
*   **模型**: `intfloat/multilingual-e5-small` (本地运行，零成本)。
*   **向量化**: 将每条评论转换为 384 维稠密向量。

### 采样逻辑 (`EmbeddingSampler`)
1.  **聚类抽样**: 使用 **K-Means** 聚类（K值动态计算），从每个簇中心提取代表性样本。
2.  **异常检测 (Outlier Retention)**: 保留约 10% 的离群点数据，确保不遗漏独特的边缘观点（长尾舆论）。
3.  **结果**: 仅输出最终送入 LLM 的 **Target N** 条精选数据。
    *   **📝 参数调控**: 默认 50 条。
    *   **配置位置**: `backend/.env` 中的 `SEMANTIC_SAMPLING_TARGET_COUNT`。
    *   **调整建议**: 增加该值可提升观点覆盖率，但会线性增加 LLM 成本；减小该值可节省 Token。

---

## 4. Engineering for Cost Control (核心降本策略)

### 4.1 本地化计算 (Local Computation)
*   **Embedding 零成本**: 所有向量化和聚类去重均在本地服务器完成。我们不调用 OpenAI 的 `embeddings` 接口，这使得预处理阶段的 API 成本为 **0**。
*   **大规模筛选**: 即使原始数据有 10,000 条，经过本地预处理后，只有约 **50 条 (可配置)** 的“信息精华”会发往 LLM。
    *   *注: 可在 `.env` 中修改 `SEMANTIC_SAMPLING_TARGET_COUNT` 进行调控。*

### 4.2 Prompt Batching (批量化处理)
*   **请求合并**: 在情感分析阶段，我们将 10 条评论打包进一个独立 Prompt。
*   **减少冗余**: 这极大减少了 System Prompt 的重复发送开销。

### 4.3 视频转录绕过 (Transcription Bypass)
*   **策略**: 对于视频内容，系统优先利用 YouTube 的字幕 API。
*   **成本对比**: 相比使用 OpenAI Whisper 进行音视频转录（约 $0.006/min），字幕 API 几乎是 **免费且瞬时** 的，彻底规避了高昂的 ASR 处理成本。

### 4.4 令牌级联优化 (Token Cascade)
*   **按需截断**: 系统在送入 LLM 前会对单条内容进行 200 字（可配置）的物理截断。经测试，社交媒体评论的核心观点通常出现在前段，此举有效防止了长篇大论导致的 Token 浪费。

---

## 5. Prompt Engineering (Prompt 设计)

### 5.1 情感分析 (Sentiment Analysis)
*   **System Prompt**: 强制输出紧凑的 JSON。
*   **User Prompt**: 包含上下文关键词，帮助 LLM 理解特定领域的情绪（如技术讨论中的 slang）。

### 5.2 观点聚类 (Opinion Clustering)
*   **策略**: **Chain-of-Thought (CoT)**。要求 LLM 先提炼观点 Title，再从输入原文中提取证据点 (Points)。
*   **Summary**: 最终生成 4-6 句的执行摘要，涵盖整体趋势、分歧点及情绪平衡度。

---

## 6. Self-Correction Mechanism (自愈机制)

系统内置了自动修复回路，针对 LLM 偶尔生成的无效 JSON 进行闭环处理。

### 修复流程
1.  **Parse**: 尝试解析 JSON。
2.  **Repair**: 若失败，自动构造包含错误信息的 `Repair Prompt` 发送回 LLM。
    ```text
    The previous output is invalid.
    Error: {error_message}
    Raw output: {raw_output}
    Return corrected JSON only.
    ```
3.  **Validation**: 最终数据必须通过 Pydantic Schema 的强类型校验。

---

## 7. Visualization Data (可视化数据)

### 7.1 Mermaid Mindmap
系统要求 LLM 直接生成 Mermaid 语法，用于前端动态渲染思维导图。

### 7.2 Heat Index (热度指数)
结合了**时间半衰期 (24h)** 的动态热度公式，确保分析结果具备时效性：
$$ Weight = e^{-\frac{\ln(2)}{24} \times Age_{hours}} $$

---
*End of Guide*
