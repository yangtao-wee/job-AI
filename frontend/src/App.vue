<template>
  <h1>AI 招聘匹配系统</h1>

  <nav>
    <router-link to="/jobs">岗位列表</router-link>
    |
    <router-link to="/resumes">我的简历</router-link>
    |
    <router-link to="/rag">知识问答</router-link>
    |
    <router-link to="/agent">AI助手</router-link>
    |
    <router-link to="/assist">定制建议</router-link>
    |
    <router-link to="/applications">投递管理</router-link> 
  </nav>

  <BackendStatus />
  <router-view />
</template>

<script setup>
import BackendStatus from './components/BackendStatus.vue';
import {RouterView} from 'vue-router'
import router from './router/index.js';
</script>
