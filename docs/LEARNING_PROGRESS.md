# AI Job Agent 学习进度

## 2026-08-27

- 完成功能：Git基线版本、岗位技能匹配、JD关键词匹配、岗位JD结构化Schema、Prompt、Mock/真实模型分流、受JWT保护的岗位分析接口。
- 用户亲手完成：匹配函数、结构化Schema、岗位AI Service、岗位分析Router及Debug修复。
- AI生成内容：本学习记录与技术决策记录。
- 🟡 正在学习：Git、FastAPI路由、Pydantic Structured Output、Mock Mode、HTTP状态码。
- 🔴 未掌握：RAG、Agent、Tool Calling、MySQL、Redis、自动化测试、Docker部署。
- Bug：`Job.id == job.id`在变量赋值前读取`job`，导致接口返回500。
- 修复：改为使用路径参数`Job.id == job_id`，验收结果为200、401、404。
- 项目证据：首次Commit `ff96549`；岗位分析接口三分支测试通过。
- 下一步：从Vue通过Axios调用岗位分析接口并展示结构化结果。

## 2026-08-28

- 完成功能：Vue通过Axios调用岗位分析接口，JobCard使用Props和Emit完成父子通信，并展示岗位职责、必备技能、经验、学历和加分项。
- 用户亲手完成：`analyzeJob` API函数、`handleAnalyze`页面函数、分析按钮、加载状态和五类结果模板。
- AI生成内容：更新本学习记录；执行编译、接口和浏览器运行时验收。
- 🟡 正在学习：Vue Props/Emit、异步状态、前后端字段映射、运行时Debug。
- Bug：`requirements`单复数不一致、`responsibilities`拼写错误、字段中文标签映射错误。
- 修复：统一字段名称与标签；生产编译通过；浏览器真实点击后五类结果正确显示，控制台无错误。
- 项目证据：岗位分析前端闭环、200/401/404接口测试、真实页面运行结果。
- 下一步：把结构化岗位要求加入多维岗位匹配评分。
