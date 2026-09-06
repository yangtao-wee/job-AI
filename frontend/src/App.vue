<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <span class="brand-mark">AI</span>

        <span class="brand-text">
          <strong>AI 招聘匹配</strong>
          <small>求职智能体 · 深链科技</small>
        </span>
      </div>

      <nav class="side-nav">
        <router-link to="/jobs">
          <svg viewBox="0 0 24 24">
            <rect x="3" y="7" width="18" height="13" rx="2" />
            <path d="M8 7V5h8v2M3 12h18" />
          </svg>
          岗位列表
        </router-link>

        <router-link to="/resumes">
          <svg viewBox="0 0 24 24">
            <path d="M7 3h7l5 5v13H6V4Z" />
            <path d="M14 3v5h5M9 13h6M9 17h6" />
          </svg>
          我的简历
        </router-link>
                <router-link to="/resume-print">
          <svg viewBox="0 0 24 24">
            <path d="M6 9V3h12v6M6 18H4v-6h16v6h-2" />
            <rect x="8" y="14" width="8" height="7" />
          </svg>
          简历生成
        </router-link>

        <router-link to="/rag">
          <svg viewBox="0 0 24 24">
            <path d="M21 12a8 8 0 1 1-3.4-6.5M21 4v5h-5" />
          </svg>
          知识问答
        </router-link>

        <router-link to="/agent">
          <svg viewBox="0 0 24 24">
            <path d="m12 3 2 5 5 2-5 2-2 5-2-5-5-2 5-2 2-5Z" />
          </svg>
          AI 助手
        </router-link>

        <router-link to="/assist">
          <svg viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="9" />
            <circle cx="12" cy="12" r="4" />
          </svg>
          定制建议
        </router-link>

        <router-link to="/applications">
          <svg viewBox="0 0 24 24">
            <path d="M22 2 11 13M22 2l-7 20-4-9-9-4 20-7Z" />
          </svg>
          投递管理
        </router-link>
      </nav>

      <BackendStatus />
    </aside>

    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import BackendStatus from './components/BackendStatus.vue'
</script>
