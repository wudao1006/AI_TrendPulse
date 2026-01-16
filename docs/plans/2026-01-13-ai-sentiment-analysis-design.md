# AI舆情分析系统设计文档

## 项目概述

输入一个关键词，系统自动去 Reddit/YouTube/X 抓取最新数据，并生成一份 AI 舆情分析报告。

## 技术选型

| 组件 | 技术方案 |
|------|---------|
| 后端框架 | FastAPI |
| 任务队列 | Celery + Redis |
| 数据库 | PostgreSQL |
| 数据采集 | PRAW (Reddit) + youtube-transcript-api + Playwright (X) |
| AI分析 | OpenAI SDK（Chat Completions 兼容接口） |
| 前端 | Flutter 3.x + Riverpod |

## 系统架构

### 三层异步架构

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Flutter App    │────▶│  FastAPI        │────▶│  PostgreSQL     │
│  (前端展示)      │     │  (REST API)     │     │  (数据持久化)    │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │  Redis          │◀───▶│  Celery Worker  │
                        │  (消息队列)      │     │  (异步任务)      │
                        └─────────────────┘     └─────────────────┘
```

### 核心组件

1. **Web API服务** (FastAPI)：接收用户请求、返回结果、提供轮询接口
2. **Celery Worker集群**：并发执行采集任务和AI分析任务
3. **APScheduler**：定时调度中心（单实例），处理订阅关键词的周期采集
4. **PostgreSQL**：存储采集数据、分析结果、用户订阅配置
5. **Redis**：Celery消息队列、任务状态缓存、结果临时存储

说明：
- 调度器建议只在一个 API 进程中运行；多进程/多实例时用 `SCHEDULER_ENABLED=false` 禁用其余实例。

## 数据采集模块

### Reddit采集器
- 技术：PRAW (Python Reddit API Wrapper)
- OAuth认证，官方API
- 采集：帖子标题、正文、作者、点赞数、热门评论

### YouTube采集器
- 技术：youtube-transcript-api + YouTube Data API v3
- 采集：视频元数据 + 完整字幕/transcript

### X平台采集器（后期）
- 技术：Playwright无头浏览器
- 采集：推文内容、转发数、点赞数

### 平台选择机制
- 用户可自由选择单个或多个平台组合
- 每个平台可独立配置采集参数（如 limit、Subreddit、字幕设置），前端可随时调整
- 采集器插件化注册机制，便于扩展

## AI分析模块

### 处理流程（预处理 + Map-Reduce混合）

1. **预处理阶段**
   - 脏数据过滤（广告、机器人、乱码）
   - 长度过滤、语言检测
   - 高赞内容优先提取

2. **Map阶段**（并发）
   - 分批处理（每批10-15条）
   - 提取情感得分、观点片段

3. **Reduce阶段**（聚合）
   - 加权平均情感得分
   - 观点聚类生成3个核心观点
   - 生成易读摘要
   - 生成Mermaid思维导图

## 数据库设计

### tasks 任务表
- id, keyword, language, limit_count, platforms (JSON), platform_configs (JSON)
- status, progress, celery_task_id, error_message
- created_at, updated_at

### raw_data 原始数据表
- id, task_id, platform, content_type
- source_id, title, content, author, url
- metrics (JSON), extra_fields (JSON)
- published_at, crawled_at

### analysis_results 分析结果表
- id, task_id, sentiment_score
- key_opinions (JSON), summary, mermaid_code
- heat_index, analyzed_at

### subscriptions 订阅表
- id, keyword, platforms (JSON), language, limit, platform_configs (JSON)
- interval_hours, alert_threshold, is_active
- last_run_at, next_run_at

### alerts 报警表
- id, subscription_id, task_id
- sentiment_score, alert_type, is_read
- created_at

## API设计

### 任务接口
- `POST /api/v1/tasks` - 提交分析任务（支持平台选择）
- `GET /api/v1/tasks/{id}` - 查询任务状态
- `GET /api/v1/tasks/{id}/result` - 获取分析结果
- `GET /api/v1/tasks/{id}/raw-data` - 获取原始数据

### 订阅接口
- `POST /api/v1/subscriptions` - 创建订阅
- `GET /api/v1/subscriptions` - 列出订阅
- `PUT /api/v1/subscriptions/{id}` - 更新订阅
- `DELETE /api/v1/subscriptions/{id}` - 删除订阅

### 报警接口
- `GET /api/v1/alerts` - 获取报警列表
- `PUT /api/v1/alerts/{id}/read` - 标记已读

### 平台接口
- `GET /api/v1/platforms` - 获取可用平台列表

## Flutter前端设计

### 页面结构
1. **首页** - 关键词输入、平台选择、语言和数量配置
2. **进度页** - 任务进度展示（轮询更新）
3. **仪表盘页** - 情感得分、热度、核心观点、摘要、思维导图
4. **源数据页** - 原始数据列表，支持平台筛选
5. **订阅页** - 订阅管理、报警通知

### 状态管理
- Riverpod

## 可扩展性设计

1. **采集器插件化** - BaseCollector抽象类 + 注册机制
2. **分析器模块化** - AnalysisPipeline + BaseAnalyzer
3. **LLM客户端抽象** - 支持多模型切换
4. **API版本管理** - /api/v1/ 路由前缀
5. **配置中心化** - 环境变量 + 平台独立配置

说明：
- LLM API 使用 OpenAI SDK，`LLM_API_BASE_URL` 需包含 `/v1`（如 `https://api.openai.com/v1`）。
- 配置统一从 `.env` 读取，运行时不使用代码内默认值。

## 开发里程碑

| 阶段 | 时间 | 内容 |
|------|------|------|
| M1 | Day 1-2 | 基础架构 + 数据采集 |
| M2 | Day 3 | AI分析模块 |
| M3 | Day 4-5 | API + Flutter核心页面 |
| M4 | Day 6-7 | 加分项 + 优化交付 |
