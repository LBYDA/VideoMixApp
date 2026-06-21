<template>
  <div class="home">
    <h1 class="welcome">欢迎使用视频混剪工具</h1>
    <p class="subtitle">智能批量视频处理工作站 — 选择一种混剪模式开始</p>

    <div class="cards">
      <router-link to="/category-mix" class="card">
        <div class="card-icon">G</div>
        <h3>分类混剪</h3>
        <p>按分类组组织视频素材，自动裁剪拼接，按目标时长输出成品视频。</p>
        <ul>
          <li>创建多个分类组</li>
          <li>自动分析视频元数据</li>
          <li>智能选取片段</li>
          <li>批量输出成品</li>
        </ul>
      </router-link>

      <router-link to="/ai-mix" class="card">
        <div class="card-icon">A</div>
        <h3>AI智能混剪</h3>
        <p>利用大语言模型分析文案和字幕，自动生成专业的混剪方案。</p>
        <ul>
          <li>语音转字幕 (ASR)</li>
          <li>LLM智能规划</li>
          <li>文案匹配片段</li>
          <li>TTS语音合成</li>
        </ul>
      </router-link>

      <router-link to="/video-mix" class="card">
        <div class="card-icon">V</div>
        <h3>视频混剪</h3>
        <p>高级视频合成引擎，支持画中画、转场、变速、调色等专业功能。</p>
        <ul>
          <li>多轨道合成</li>
          <li>画中画叠加</li>
          <li>变速控制</li>
          <li>FFmpeg滤镜图</li>
        </ul>
      </router-link>
    </div>
  </div>
</template>

<style scoped>
.home {
  max-width: 960px;
  margin: 0 auto;
  padding: 40px 0;
}

.welcome {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 8px;
}

.subtitle {
  color: var(--text-secondary);
  margin-bottom: 40px;
  font-size: 15px;
}

.cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}

.card {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 28px 24px;
  text-decoration: none;
  color: var(--text-primary);
  transition: all 0.2s;
}

.card:hover {
  border-color: var(--accent);
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
}

.card-icon {
  width: 48px;
  height: 48px;
  background: var(--accent);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  font-weight: 700;
  font-size: 20px;
  margin-bottom: 16px;
}

.card h3 {
  font-size: 16px;
  margin-bottom: 8px;
}

.card p {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 16px;
  line-height: 1.5;
}

.card ul {
  list-style: none;
  font-size: 12px;
  color: var(--text-secondary);
}

.card li {
  padding: 3px 0;
}

.card li::before {
  content: '✓ ';
  color: var(--success);
}

@media (max-width: 800px) {
  .cards {
    grid-template-columns: 1fr;
  }
}
</style>
