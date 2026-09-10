<template>
  <section class="home">
    <header class="hero">
      <p class="eyebrow">AI Job Agent</p>
      <h1>把找工作里重复的部分自动化，<br>判断权留给自己</h1>
      <p class="lead">
        浏览器插件在真实招聘页面抓取岗位，本地规则免费粗筛打分，
        由我人工挑出值得细看的，再调大模型做精判，最后标记好的岗位统一投递。
        <strong>便宜的操作全量跑，昂贵的操作只跑筛过的。</strong>
      </p>

      <div class="demo">
        <span class="demo-t">演示账号</span>
        <code>demo</code>
        <span class="demo-t">密码</span>
        <code>demo2026</code>
        <router-link to="/login" class="demo-go">去登录 →</router-link>
      </div>
    </header>

    <div class="figures">
      <div class="fig"><b>52</b><span>真实岗位，本人求职时抓取</span></div>
      <div class="fig"><b>11</b><span>份精判报告，逐条核对依据</span></div>
      <div class="fig"><b>20×</b><span>粗筛提速 0.88→0.04 秒</span></div>
      <div class="fig"><b>199</b><span>个 pytest 测试</span></div>
    </div>

    <h2 class="sec">按这个顺序看</h2>
    <ol class="guide">
      <li>
        <router-link to="/resumes">
          <span class="n">1</span>
          <span class="body">
            <b>我的简历</b>
            <em>上传 PDF，模型提取技能、经历和推荐方向。演示账号里已有一份。</em>
          </span>
        </router-link>
      </li>
      <li>
        <router-link to="/assist">
          <span class="n">2</span>
          <span class="body">
            <b>定制建议</b>
            <em>
              粘贴一段岗位 JD，逐条对照简历。简历按行编号后只把编号给模型，
              模型输出只能引用编号，后端回查原文——查不到就丢弃该条并标记「缺依据」。
              模型碰不到原文，编不出来。
            </em>
          </span>
        </router-link>
      </li>
      <li>
        <router-link to="/leads">
          <span class="n">3</span>
          <span class="body">
            <b>岗位池</b>
            <em>
              粗筛分数（只看职位名和技能标签，本地算、零成本）＋ 精判结果
              （几条有依据、几条部分支持、共几条要求）。
            </em>
          </span>
        </router-link>
      </li>
      <li>
        <router-link to="/applications">
          <span class="n">4</span>
          <span class="body">
            <b>投递管理</b>
            <em>标记为「待投递」的岗位由插件按队列执行，每 10 秒一个，投完回写状态。</em>
          </span>
        </router-link>
      </li>
    </ol>

    <div class="note">
      <b>关于 Chrome 插件</b>
      <p>
        岗位池的数据由插件在<strong>我自己打开的</strong>招聘页面上采集——它不自动翻页、
        不在后台发请求，权限只申请了本地存储。演示环境展示的是预置数据，
        采集与投递的完整过程请看录屏。
      </p>
      <p class="thin">
        另有「知识问答」（RAG：检索 Top-3 资料后作答，无相关资料直接拒答）与
        「AI 助手」（Tool Calling：由模型决定是否调用工具，后端按白名单执行）——
        这两块是独立模块，不在求职主链路上。
      </p>
    </div>
  </section>
</template>

<script setup>
</script>

<style scoped>
.home { max-width: 900px; padding-bottom: 64px; }

.hero { padding: 8px 0 36px; }
.eyebrow {
  margin: 0 0 12px; font-size: 12px; letter-spacing: .22em;
  text-transform: uppercase; color: var(--cyan);
}
.hero h1 {
  margin: 0 0 18px; font-size: 34px; line-height: 1.35;
  font-weight: 700; letter-spacing: -.01em;
}
.lead { margin: 0; max-width: 62ch; color: var(--muted); line-height: 1.85; }
.lead strong { color: var(--text); }

.demo {
  margin-top: 26px; display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  padding: 14px 18px; border: 1px solid var(--border);
  border-radius: 14px; background: var(--panel);
}
.demo-t { color: var(--muted); font-size: 13px; }
.demo code {
  padding: 3px 10px; border-radius: 7px; background: var(--panel-strong);
  color: var(--cyan); font-size: 14px; letter-spacing: .04em;
}
.demo-go {
  margin-left: auto; color: var(--primary);
  text-decoration: none; font-size: 14px; white-space: nowrap;
}
.demo-go:hover { color: var(--cyan); }

.figures {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 14px; margin-bottom: 44px;
}
.fig {
  padding: 18px 20px; border: 1px solid var(--border);
  border-radius: 16px; background: var(--panel);
}
.fig b {
  display: block; font-size: 27px; line-height: 1.2;
  color: var(--text); font-variant-numeric: tabular-nums;
}
.fig span { display: block; margin-top: 6px; font-size: 12.5px; color: var(--muted); }

.sec { margin: 0 0 18px; font-size: 19px; }

.guide { list-style: none; margin: 0 0 44px; padding: 0; display: flex; flex-direction: column; gap: 10px; }
.guide a {
  display: flex; gap: 18px; padding: 20px 22px;
  border: 1px solid var(--border); border-radius: 16px;
  background: var(--panel); text-decoration: none;
  transition: border-color .15s, background .15s;
}
.guide a:hover { border-color: var(--primary); background: var(--panel-strong); }
.guide .n {
  flex: 0 0 34px; height: 34px; display: grid; place-items: center;
  border-radius: 11px; background: var(--panel-strong);
  color: var(--cyan); font-weight: 700; font-size: 15px;
}
.guide a:hover .n { background: var(--primary); color: #06111d; }
.guide .body { display: block; min-width: 0; }
.guide b { display: block; margin-bottom: 7px; color: var(--text); font-size: 15px; }
.guide em { display: block; font-style: normal; color: var(--muted); font-size: 13.5px; line-height: 1.8; }

.note {
  padding: 22px 24px; border: 1px solid var(--border);
  border-left: 3px solid var(--salary); border-radius: 16px; background: var(--panel);
}
.note b { display: block; margin-bottom: 10px; color: var(--text); }
.note p { margin: 0 0 10px; color: var(--muted); font-size: 13.5px; line-height: 1.85; max-width: 68ch; }
.note p:last-child { margin-bottom: 0; }
.note strong { color: var(--text); }
.note .thin { padding-top: 10px; border-top: 1px solid var(--border); font-size: 13px; }

@media (max-width: 640px) {
  .hero h1 { font-size: 26px; }
  .guide a { flex-direction: column; gap: 12px; }
  .demo-go { margin-left: 0; }
}
</style>
