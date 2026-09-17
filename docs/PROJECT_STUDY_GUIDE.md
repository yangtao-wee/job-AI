# AI Job Agent 项目复习手册

> 目标岗位：深圳 AI应用开发工程师 / Python后端开发工程师 / 偏后端的Agent全栈工程师  
> 使用方式：先回答问题，再看代码；先画数据路线，再运行测试；每个模块通过“讲清、改动、排错、重写”四项才算掌握。  
> 资料依据：当前项目代码、Git记录、`docs/LEARNING_PROGRESS.md`，以及实际项目版简历《直聘简历-未命名 (2).pdf》。测试用 `demo_resume.pdf` 不作为个人经历依据。

---

## 0. 当前结论

### 项目完成度与个人掌握度必须分开

- 项目代码：已经覆盖登录、简历、岗位匹配、RAG、Agent、Redis、MySQL、Vue、测试和本地容器化。
- 当前验证：后端 `199 passed, 1 skipped`；前端生产构建成功，113个模块完成转换。
- 独立掌握：学习记录中的主要模块仍是 🟡，即“跟着做过，但还需要脱离答案重写和排错”。
- 当前重点：不继续堆功能，先把简历上已经写出的能力变成自己能解释、能重写、能排错的能力。

### 三条诚实边界

1. **容器化不等于正式上线。** 当前能证明的是 Docker Compose 本地多服务联调；域名、HTTPS、云服务器和生产监控尚未完成最终验收。
2. **浏览器扩展属于受控实验。** 已经出现招聘平台账号风控，复习时只做本地语法、DOM样例和人工确认流程，不再进行无人值守批量投递。
3. **性能数字必须可复现。** 简历写了 Embedding 从0.42秒降到0.03秒，Git能证明做过批量去重优化，但面试前必须重新保存基准命令、输入规模和输出结果。

---

## 1. 简历能力与项目证据对照表

| 简历能力 | 项目证据 | 当前状态 | 你必须补上的独立能力 |
|---|---|---:|---|
| Python / FastAPI / REST API | `backend/app/main.py`、`backend/app/routers/` | 🟡 | 不看答案写一个带依赖注入和错误响应的接口 |
| Pydantic结构化校验 | `backend/app/schemas.py`、`llm_service.py` | 🟡 | 解释请求模型、响应模型、LLM输出校验的区别 |
| SQLAlchemy / MySQL | `database.py`、`models.py`、各Service | 🟡 | 独立写用户隔离查询、事务提交和回滚 |
| JWT认证 | `utils/security.py`、`dependencies.py`、`routers/users.py` | 🟡 | 画出登录、鉴权、全端退出的数据路线 |
| PDF解析与上传安全 | `routers/resumes.py`、`resume_parser.py` | 🟡 | 重写5MB流式限制和异常清理 |
| LLM API / Prompt | `llm_service.py`、`ai_*_service.py` | 🟡 | 解释统一适配层、超时、重试和备用模型 |
| JSON + Pydantic结构化输出 | `call_structured()`及各Schema | 🟡 | 处理模型返回非法结构的情况 |
| RAG / BGE Embedding | `rag_service.py`、`semantic_service.py` | 🟡 | 从切分开始完整重写最小RAG链路 |
| Tool Calling / Agent | `agent_service.py` | 🟡 | 解释每一种消息角色和 `tool_call_id` |
| 可解释岗位匹配 | `matching_service.py`、固定评测集 | 🟡 | 解释五层评分、误匹配原因和评测方法 |
| Redis缓存、限流、锁 | `cache_service.py`、`rate_service.py` | 🟡 | 区分缓存、限流、分布式锁解决的问题 |
| Vue 3 / Axios / Router | `frontend/src/` | 🟡 | 独立完成一个页面到API的完整数据流 |
| pytest | `backend/tests/` | 🟡 | 独立写正常、异常、边界、越权四类测试 |
| Alembic | `backend/alembic/` | 🟡 | 独立说明为什么 `create_all` 不能代替迁移 |
| Docker Compose / Nginx | `compose.yaml`、Dockerfile、`nginx.conf` | 🟡 | 不看答案画出容器网络和同源代理 |
| Git | Git提交历史 | 🟡 | 能按功能精确提交，不混入无关改动 |

---

## 2. 一张图说清整个项目

```text
用户
  ↓
Vue 页面 ── Axios拦截器携带JWT ──→ FastAPI Router
                                      ↓
                              Pydantic校验输入输出
                                      ↓
                                  Service层
                     ┌────────────────┼────────────────┐
                     ↓                ↓                ↓
               SQLAlchemy/MySQL   Redis缓存/限流    LLM适配层
                     ↓                                 ↓
              简历/岗位/报告                     Structured Output
                                                       ↓
                              RAG ← BGE向量检索 → Agent Tool Calling
```

你必须能回答：

1. Vue为什么不直接操作数据库？
2. Router和Service为什么要分开？
3. Pydantic在哪两个不同位置保护系统？
4. Redis故障时哪些功能应降级，哪些功能应拒绝？
5. 为什么LLM不能直接决定岗位总分？

---

## 3. 六条必须背熟的数据路线

### 3.1 登录与鉴权

```text
用户名密码
→ POST /users/login
→ 查询User
→ bcrypt验证密码
→ 签发包含user_id、token_version、exp的JWT
→ Vue保存access_token
→ Axios后续请求加入Authorization: Bearer ...
→ get_current_user解码并查询用户
→ Router得到当前用户
```

失败点：用户名不存在、密码错误、Token过期、Token被修改、用户已删除、`token_version`变化。

### 3.2 PDF上传与分析

```text
Vue选择PDF
→ multipart/form-data
→ FastAPI检查扩展名和MIME
→ 分块读取并累计真实大小
→ 写入.part临时文件
→ 检查PDF文件头
→ 临时文件转为正式文件
→ 数据库保存Resume
→ 解析PDF文字
→ LLM输出ResumeAIAnalysis
→ 保存ResumeAnalysis
```

失败点：伪PDF、超过5MB、空文件、数据库提交失败、磁盘删除失败、模型结构错误。

### 3.3 完整岗位匹配

```text
简历分析 + 岗位JD + 城市薪资偏好
→ 技能分35
→ 经历证据分30
→ 城市薪资分15
→ 关键词分10
→ 岗位方向分10
→ BGE语义分仅作参考
→ LLM生成解释
→ 后端用真实证据覆盖模型引用
```

关键原则：规则负责给分，模型负责抽取和解释；没有简历原文证据就不能声称候选人具备该能力。

### 3.4 RAG

```text
知识库文本
→ 300字符切分、50字符重叠
→ BGE Embedding
→ 查询与片段点积相似度
→ Top-3
→ 0.6阈值过滤
→ 拼接ctx
→ LLM结构化回答
→ 后端强制覆盖真实sources
```

资料为空时必须提前拒答，不能为了“像AI”而自由发挥。

### 3.5 Agent

```text
用户目标 + 最近10条history
→ system消息约束
→ 模型判断是否调用find_kb、find_jobs、get_job或get_resume
→ 后端校验工具白名单
→ 注入登录用户编号并执行知识库或岗位池查询
→ 用tool_call_id回传tool消息
→ 模型根据观察继续判断
→ 最多3轮后返回结果或停止
```

Agent与普通Chat的区别：不是“提示词更长”，而是模型能够选择工具，后端执行工具并把观察结果送回循环。`find_jobs`和`get_resume`的`user_id`只能由JWT认证后的后端注入，不能由模型填写。岗位要求只有在简历`skills`或编号`proofs`中找到证据时才能称为“已具备”；否则只能说当前简历未发现。

### 3.6 生产请求链路

```text
浏览器
→ Nginx提供Vue静态文件
→ /api同源代理
→ FastAPI容器
→ MySQL容器保存业务数据
→ Redis容器保存缓存、限流计数和锁
→ 外部LLM API
```

当前只完成本地Compose验证；正式HTTPS链路还不能当作已完成事实。

---

## 4. 复习优先级

### P0：必须能独立讲清和重写

1. HTTP、FastAPI、Pydantic、Router/Service分层。
2. JWT、密码哈希、用户数据隔离。
3. SQLAlchemy查询、事务、MySQL、Alembic。
4. LLM统一调用、结构化输出、异常降级。
5. RAG完整链路。
6. Agent Tool Calling循环。
7. 岗位匹配、错误案例与评测。
8. pytest与Debug证据链。

### P1：必须理解并能排错

1. Redis缓存、限流和锁。
2. Vue Router、Axios拦截器、前后端联调。
3. Docker Compose、容器网络、卷和非root权限。
4. Nginx静态文件、History回退和反向代理。
5. 日志、Token用量和成本估算。

### P2：知道边界，需要时查资料

1. 浏览器扩展DOM适配。
2. 正式域名、HTTPS和云服务器运维。
3. 更复杂的向量数据库、异步队列和监控。

暂时不要学习Kubernetes、微服务、多Agent编排或从零训练模型。

---

## 5. 十二个模块的学习卡

### 模块1：HTTP + FastAPI + Pydantic

- 代码入口：`backend/app/main.py`、`backend/app/routers/users.py`、`backend/app/schemas.py`。
- 必会：GET/POST/PATCH/DELETE、状态码、请求体、查询参数、路径参数、响应模型、依赖注入。
- 实操：不看答案写一个“读取当前用户岗位统计”的接口。
- 故障练习：把请求字段名写错，观察422；删除Token，观察401。
- 通过标准：能从浏览器Network面板一路定位到具体Router和Schema。
- 面试题：FastAPI为什么能自动生成Swagger？422和400有什么区别？

### 模块2：JWT + 权限

- 代码入口：`utils/security.py`、`dependencies.py`、`routers/users.py`。
- 必会：hash与加密的区别、JWT三部分、过期时间、Bearer Token、`token_version`。
- 实操：独立解释 `/logout-all` 为什么能让旧Token失效。
- 故障练习：删除JWT中的 `tv`，观察鉴权结果。
- 通过标准：任何读取简历、报告、岗位池的查询都能指出 `user_id` 隔离位置。
- 面试题：JWT为什么不能保存密码？JWT主动失效有哪些方案？

### 模块3：SQLAlchemy + MySQL + 事务

- 代码入口：`database.py`、`models.py`、`lead_service.py`、`report_service.py`。
- 必会：Engine、Session、Model、主键、外键、唯一约束、索引、commit、flush、rollback。
- 实操：不看答案重写 `update_status()` 的用户隔离查询。
- 故障练习：让commit抛错，确认rollback后数据没变。
- 通过标准：能解释报告保存与岗位关联为什么要一次事务完成。
- 面试题：`flush()`和`commit()`有什么区别？索引为什么不是越多越好？

### 模块4：文件上传安全

- 代码入口：`routers/resumes.py`、`resume_parser.py`。
- 必会：MIME不可信、扩展名不可信、必须检查真实字节、临时文件和补偿清理。
- 实操：独立写5MB分块累计判断。
- 故障练习：把TXT改名成PDF；模拟数据库提交失败。
- 通过标准：能分别描述“数据库回滚”和“删除磁盘文件”为什么不是同一件事。
- 面试题：为什么不能只读取 `file.size`？怎样防止路径穿越？

### 模块5：LLM统一适配与结构化输出

- 代码入口：`llm_service.py`、`ai_resume_service.py`、`ai_job_service.py`。
- 必会：Client、model、Prompt、JSON Schema、Pydantic二次校验、Timeout、Retry、备用模型。
- 实操：不看答案画出 `call_structured()` 输入和输出。
- 故障练习：让模型少返回一个必填字段，观察校验失败。
- 通过标准：能解释为什么业务层不应该到处直接创建OpenAI客户端。
- 面试题：结构化输出为什么仍需要Pydantic？什么错误适合重试？

### 模块6：RAG

- 代码入口：`rag_service.py`、`semantic_service.py`、`kb_service.py`。
- 必会：Chunk、Overlap、Embedding、Vector、Similarity、Top-K、Threshold、Context。
- 实操：用3段固定文字手算检索输入输出，再运行测试对照。
- 故障练习：把阈值从0.6改成0.99，解释为什么所有问题都拒答。
- 通过标准：能不看代码写出 `split_text()` 和最小 `search()`。
- 面试题：为什么切分要重叠？Top-K太大会有什么问题？

### 模块7：Agent + Tool Calling

- 代码入口：`agent_service.py`、`routers/agent.py`。
- 必会：system/user/assistant/tool四种消息、工具Schema、白名单、参数解析、观察、循环上限。
- 实操：画出一次 `find_kb` 工具调用的完整消息序列。
- 故障练习：模型请求不存在的工具，确认后端拒绝。
- 通过标准：能说明直接回答、调用一次工具、连续调用、超过4轮四条分支。
- 面试题：Agent为什么必须限制步数？工具白名单解决什么安全问题？

### 模块8：岗位匹配与评测

- 代码入口：`backend/app/services/matching_service.py`、`backend/tests/data/match_cases.json`。
- 必会：规则分与语义分边界、正负样本、权重、阈值、误报、漏报、回归测试。
- 实操：解释“AI剪辑师为什么曾得到70分”，并重写修复逻辑。
- 故障练习：删除 `BLOCK_WORDS` 检查测试是否能抓住回归。
- 通过标准：能用5个以上真实岗位组成小评测集，记录修改前后排名。
- 面试题：为什么不能只用LLM评分？如何衡量推荐质量？

### 模块9：Redis

- 代码入口：`cache_service.py`、`rate_service.py`、`dependencies.py`。
- 必会：缓存、TTL、Cache Key、限流、锁、故障降级。
- 实操：分别解释岗位分析缓存1小时、报告缓存24小时、精判锁180秒。
- 故障练习：关闭Redis，观察RAG/Agent限流和普通缓存分别怎样表现。
- 通过标准：能回答“Redis删光后哪些数据会丢，哪些能重建”。
- 面试题：缓存穿透是什么？为什么锁必须在finally释放？

### 模块10：Vue + Axios

- 代码入口：`frontend/src/router/index.js`、`api/request.js`、各View。
- 必会：组件状态、`ref`、生命周期、Router Guard、Axios拦截器、loading/error状态。
- 实操：从 `LeadView.vue` 的按钮追踪到FastAPI接口，再追踪响应如何更新页面。
- 故障练习：把 `/api` 改错，使用Network面板判断前端、代理还是后端问题。
- 通过标准：能独立做一个列表页的加载、错误、空状态和分页。
- 面试题：路由守卫和后端鉴权为什么都需要？响应拦截器为什么还要继续reject？

### 模块11：测试与Debug

- 代码入口：`backend/tests/`。
- 必会：Arrange-Act-Assert、fixture、monkeypatch、Mock、正常/异常/边界/权限测试。
- 实操：为一个Service独立补四类测试。
- Debug顺序：错误关键词 → 判断层级 → 提出假设 → 最小验证 → 修改 → 回归。
- 通过标准：不看答案解释最近三个Bug的证据如何排除了其他层。
- 面试题：Mock测试的价值和缺点是什么？测试全部通过为什么仍可能有线上Bug？

### 模块12：Docker Compose + Nginx + Alembic

- 代码入口：`compose.yaml`、`compose.prod.yaml`、两个Dockerfile、`frontend/nginx.conf`、`backend/alembic/`。
- 必会：镜像、容器、服务名网络、端口映射、命名卷、健康检查、多阶段构建、反向代理、迁移。
- 实操：不看配置画出浏览器到MySQL的链路。
- 故障练习：把容器内数据库地址改成localhost，解释为什么连接失败。
- 通过标准：能讲清开发Compose与生产覆盖文件的区别。
- 面试题：命名卷为什么不是备份？为什么生产环境不公开MySQL端口？

---

## 6. 14天巩固安排

每天建议90分钟：15分钟口述、30分钟读代码、30分钟重写或排错、15分钟记录。每天只记不超过5个新英文词。

| 天数 | 主题 | 必做产出 | 验收方式 |
|---:|---|---|---|
| 1 | 项目地图、HTTP | 手画总架构和登录请求 | 3分钟不看稿讲清 |
| 2 | FastAPI、Pydantic | 重写一个小接口和Schema | 正常、422测试 |
| 3 | JWT、用户隔离 | 画登录与鉴权路线 | 删除Token、跨用户测试 |
| 4 | SQLAlchemy、MySQL | 重写隔离查询 | commit失败回滚测试 |
| 5 | PDF上传 | 重写大小校验 | PDF、伪PDF、超限三测 |
| 6 | LLM适配层 | 画结构化调用路线 | 非法模型输出测试 |
| 7 | RAG | 重写切分和检索核心 | 空资料、阈值边界测试 |
| 8 | Agent | 手画工具调用消息序列 | 直接答、工具答、超步数 |
| 9 | 岗位匹配 | 建10条正负岗位集 | 修改前后排名表 |
| 10 | Redis | 画缓存/限流/锁对比表 | 关闭Redis观察行为 |
| 11 | Vue、Axios | 追踪一个按钮全链路 | Network面板排错 |
| 12 | pytest、Debug | 独立补四类测试 | 故意制造并修复错误 |
| 13 | Docker、Nginx | 画容器网络和卷 | Compose配置解释 |
| 14 | 项目答辩 | 3分钟介绍+20题模拟面试 | 不看稿、能追问三层 |

---

## 7. 第一轮脱离AI重写清单

按顺序完成，一次只做一个：

- [ ] `get_db()`：会话创建与关闭。
- [ ] `get_current_user()`：Token解析与用户查询。
- [ ] 一个按 `user_id` 隔离的SQLAlchemy查询。
- [ ] 一个Pydantic请求模型和响应模型。
- [ ] PDF分块读取和5MB限制。
- [ ] `split_text()`：带Overlap的切分。
- [ ] `search()`：批量向量、排序、Top-K。
- [ ] `run_tool()`：工具白名单和JSON返回。
- [ ] `run_agent()`：最多4轮的工具循环。
- [ ] 一个技能评分函数和一个负样本测试。
- [ ] 一个Redis限流函数的伪代码。
- [ ] 一个Vue页面的loading/error/empty三种状态。

每项必须完成四个动作：

```text
不看答案写
→ 运行测试
→ 主动制造一个错误并修复
→ 用中文解释输入、输出和数据路线
```

---

## 8. 高频面试题库

### Python与后端

1. `yield db` 为什么能保证数据库会话最终关闭？
2. `async def` 与普通 `def` 有什么区别？当前项目哪些操作真正需要异步？
3. FastAPI的 `Depends` 解决了什么问题？
4. Pydantic验证失败为什么通常返回422？
5. Router、Service、Model、Schema各自负责什么？

### 安全与数据库

6. 密码为什么使用bcrypt，而不是可逆加密？
7. JWT如何生成、携带、验证和失效？
8. 前端路由守卫能不能代替后端权限校验？
9. 项目如何保证用户只能读取自己的简历和报告？
10. `flush`、`commit`、`rollback` 分别是什么？
11. 为什么简历删除涉及数据库与磁盘的一致性？
12. Alembic解决什么问题？

### AI应用

13. 普通LLM请求与Structured Output有什么区别？
14. JSON Schema和Pydantic为什么要同时存在？
15. Prompt Injection在简历和JD场景中如何发生？
16. 哪些模型错误适合重试，哪些不适合？
17. 如何记录Token成本，为什么要按实际模型记录？

### RAG与Agent

18. 请完整讲述RAG的数据路线。
19. Chunk太大或太小分别有什么问题？
20. Embedding相似度高是否等于事实正确？
21. 没检索到资料时系统为什么应该拒答？
22. Agent与普通Chat有什么本质区别？
23. Tool Calling为什么需要白名单和参数Schema？
24. 为什么Agent必须限制最大执行轮数？

### 推荐、Redis与部署

25. 为什么岗位匹配不能只靠LLM？
26. “AI剪辑师70分”是如何产生和修复的？
27. 如何设计正负样本评测岗位匹配？
28. Redis缓存、限流和锁有什么区别？
29. Docker Compose中的服务为什么使用服务名互相访问？
30. Nginx在项目里负责什么？为什么需要History回退？
31. 命名卷与数据库备份有什么区别？
32. 测试199项通过，为什么仍不能直接宣称可以上线？

---

## 9. 答题自检模板

每个面试题都按下面六句回答：

```text
1. 它是什么。
2. 当前项目为什么需要它。
3. 数据从哪里来。
4. 数据经过哪些代码层。
5. 失败时如何排查。
6. 当前方案的边界和升级方向。
```

判断是否真的掌握：

- 🔴 只能说名词，无法指向代码。
- 🟡 能结合项目解释，但不能独立实现或排错。
- 🟢 能不看答案重写核心代码、补测试、制造并修复错误，并能说明替代方案。

---

## 10. 项目面试故事

### 30秒版本

我做了一个AI求职助手，后端使用FastAPI、MySQL和Redis，前端使用Vue。系统能够解析PDF简历、结构化分析JD，并结合规则评分、BGE语义检索和LLM解释判断岗位匹配。为了降低幻觉，我没有让模型直接决定总分，而且会把模型引用重新映射到简历原文；项目还实现了RAG、Tool Calling Agent、Token成本记录和Docker Compose本地部署。

### 3分钟版本结构

1. **问题：** 大量岗位难筛选，LLM直接打分容易编造理由。
2. **方案：** 规则给分、Embedding辅助检索、LLM负责结构化抽取和解释。
3. **可靠性：** Pydantic验证、证据回查、资料不足拒答、模型异常降级。
4. **工程化：** JWT隔离、MySQL事务、Redis缓存/限流/锁、pytest、Docker Compose。
5. **真实Bug：** AI销售和AI剪辑因动态分母获得60-70分；通过真实数据查询定位，加入负向规则、固定权重、回归测试，并回填83条历史错误分数。
6. **边界：** 当前完成本地容器化，尚未完成正式HTTPS部署；浏览器扩展因平台规则只保留受控辅助模式。

### 最值得讲的三个Bug

1. **推荐误匹配：** AI宽泛词 + 动态分母 → 错误高分 → 负向规则、权重修正、历史回填。
2. **跨存储删除：** 先删文件后提交数据库 → 提交失败造成记录指向空文件 → 调整顺序并补回滚测试。
3. **容器模型缺失：** 宿主机能跑、容器500 → 堆栈定位本地Embedding缓存不存在 → 构建阶段打包模型并验证离线加载。

---

## 11. 简历表述复核清单

面试或继续投递前逐条确认：

- [ ] “MySQL”能现场写出一次ORM查询和事务。
- [ ] “Redis”能区分缓存、限流和锁。
- [ ] “RAG”能不看稿画出8步链路。
- [ ] “Agent”能画出assistant tool_calls与tool消息。
- [ ] “结构化输出”能解释JSON Schema与Pydantic二次校验。
- [ ] “Docker Compose本地编排”不夸大为已经正式公网部署。
- [ ] “0.42秒降到0.03秒”重新生成可保存的基准测试证据。
- [ ] 浏览器扩展只描述岗位采集、辅助筛选和受控人工确认，不宣传绕过平台规则或无人值守批量投递。
- [ ] 工作经历只使用真实运营经历，不把项目学习内容包装成虚构公司开发经历。

---

## 12. 每日复习记录模板

```text
日期：
今日模块：
我能独立讲清的数据路线：
我亲手重写的函数：
我主动制造的错误：
错误证据：
修复方法：
通过的测试：
仍说不清的问题：
掌握状态：🔴 / 🟡 / 🟢
下一次唯一任务：
```

完成一项后，把结果追加到 `docs/LEARNING_PROGRESS.md`。只有连续两次不看答案完成，才从🟡升级到🟢。
