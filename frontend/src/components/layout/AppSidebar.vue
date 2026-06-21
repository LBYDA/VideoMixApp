<template>
  <aside class="sidebar">
    <div class="logo">
      <span class="logo-icon">MV</span>
      <span class="logo-text">视频混剪</span>
    </div>

    <nav class="nav">
      <router-link to="/" class="nav-item" exact-active-class="active">
        <span class="nav-icon">~</span>
        <span>首页</span>
      </router-link>
      <router-link to="/category-mix" class="nav-item" active-class="active">
        <span class="nav-icon">G</span>
        <span>分类混剪</span>
      </router-link>
      <router-link to="/ai-mix" class="nav-item" active-class="active">
        <span class="nav-icon">A</span>
        <span>AI智能混剪</span>
      </router-link>
      <router-link to="/video-mix" class="nav-item" active-class="active">
        <span class="nav-icon">V</span>
        <span>视频混剪</span>
      </router-link>
      <router-link to="/jobs" class="nav-item" active-class="active">
        <span class="nav-icon">H</span>
        <span>任务历史</span>
      </router-link>
      <router-link to="/settings" class="nav-item" active-class="active">
        <span class="nav-icon">*</span>
        <span>设置</span>
      </router-link>
    </nav>

    <div class="sidebar-footer">
      <span class="version">v0.1.0</span>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: 240px;
  background: var(--bg-sidebar);
  display: flex;
  flex-direction: column;
  z-index: 100;
}

.logo {
  padding: 20px 24px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}

.logo-icon {
  width: 36px;
  height: 36px;
  background: var(--accent);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  font-weight: 700;
  font-size: 14px;
}

.logo-text {
  font-size: 16px;
  font-weight: 600;
  color: white;
}

.nav {
  flex: 1;
  padding: 12px 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 24px;
  color: var(--text-sidebar);
  text-decoration: none;
  font-size: 14px;
  transition: all 0.2s;
  border-left: 3px solid transparent;
}

.nav-item:hover {
  background: rgba(255,255,255,0.05);
  color: white;
}

.nav-item.active {
  background: rgba(74, 144, 217, 0.15);
  color: var(--accent);
  border-left-color: var(--accent);
}

.nav-icon {
  width: 20px;
  text-align: center;
  font-weight: 700;
}

.sidebar-footer {
  padding: 16px 24px;
  border-top: 1px solid rgba(255,255,255,0.1);
}

.version {
  font-size: 12px;
  color: #666;
}
</style>
