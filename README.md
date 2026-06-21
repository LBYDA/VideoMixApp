# VideoMixApp - 智能视频混剪工具

从 [ECutAuto](https://github.com) 提取混剪功能并重新实现的独立桌面应用。

## 功能

### 分类混剪
按分类组组织视频素材，自动裁剪拼接，输出成品视频。
- 创建多个分类组（每组对应一个素材文件夹）
- 自动分析视频元数据（ffprobe）
- 智能选取片段，避免重复
- 支持质量优先/均衡/速度三种预设

### AI 智能混剪
利用大语言模型分析文案和字幕，自动生成专业混剪方案。
- **带货直播切片** — 黄金钩子→暴力说服→终极行动
- **Vlog 剪辑** — 叙事弧识别（悬念→冲突→高潮→收尾）
- **通用混剪** — 噪声过滤→自由编排→信息密度优先
- **文案改写** — 拆解重构→多角度叙事

### 视频混剪
高级视频合成，支持多轨道编辑和 FFmpeg 滤镜图构建。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python FastAPI |
| 前端 | Vue.js 3 + TypeScript + Pinia |
| 桌面框架 | pywebview (Edge WebView2) |
| 视频处理 | FFmpeg (bundled) |
| AI/ML | OpenAI 兼容 API + faster-whisper |

## 快速开始

### 开发环境

```bash
# 后端依赖
cd backend
pip install -r requirements.txt

# 前端依赖
cd frontend
npm install

# 启动（一键）
python scripts/dev.py

# 或分别启动
cd backend && python -m uvicorn app.main:app --port 51234
cd frontend && npm run dev
```

### 打包

```bash
# 1. 构建前端
cd frontend && npm run build

# 2. 打包 exe
cd ..
pyinstaller package/build.spec

# 产物: dist/VideoMixApp.exe (~75MB, 含FFmpeg)
```

### 配置

- 设置文件: `%APPDATA%/video-mix-app/settings.json`
- FFmpeg 自动检测，无需手动配置
- AI 混剪需要配置 LLM API Key（支持 OpenAI/火山引擎等兼容接口）

## 项目结构

```
video-mix-app/
├── backend/
│   ├── app/
│   │   ├── api/            # REST API + WebSocket
│   │   ├── services/       # 业务逻辑 + 4种AI Prompt
│   │   ├── models/         # 数据模型
│   │   ├── core/           # FFmpeg 封装
│   │   ├── config.py       # 配置管理
│   │   └── main.py         # 入口（pywebview窗口）
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── views/          # 6个页面组件
│       ├── stores/         # Pinia 状态管理
│       ├── components/     # 共享组件
│       └── router/         # Vue Router
├── package/build.spec      # PyInstaller 打包配置
└── scripts/                # 开发/分析脚本
```

## License

MIT
