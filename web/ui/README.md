# ShadowClaude Web UI

基于 React + TypeScript 的 ShadowClaude Web 界面，提供类似 Claude Code 的交互体验。

## 功能特性

1. **文件浏览器** - VS Code 风格的侧边栏文件树，支持展开/折叠文件夹
2. **代码编辑器** - 集成 Monaco Editor，支持语法高亮和代码编辑
3. **对话界面** - ChatGPT 风格的聊天 UI，支持实时消息流
4. **终端模拟器** - 基于 xterm.js 的终端，支持命令输入输出
5. **工具调用可视化** - 实时显示工具调用状态和详细信息
6. **Agent Swarm 状态面板** - 监控多 Agent 状态和任务进度

## 技术栈

- React 18
- TypeScript
- Tailwind CSS
- Monaco Editor (@monaco-editor/react)
- xterm.js + @xterm/addon-fit + @xterm/addon-web-links
- Zustand (状态管理)
- react-resizable-panels (可调整面板)
- WebSocket (实时通信)

## 项目结构

```
src/
├── components/          # UI 组件
│   ├── FileBrowser.tsx      # 文件浏览器
│   ├── CodeEditor.tsx       # 代码编辑器
│   ├── Chat.tsx             # 对话界面
│   ├── Terminal.tsx         # 终端模拟器
│   ├── ToolVisualizer.tsx   # 工具调用可视化
│   ├── AgentPanel.tsx       # Agent Swarm 面板
│   └── Layout.tsx           # 主布局组件
├── stores/             # 状态管理
│   └── appStore.ts     # Zustand 全局状态
├── hooks/              # 自定义 Hooks
│   └── useWebSocket.ts # WebSocket 通信
├── types/              # TypeScript 类型定义
│   └── index.ts
└── styles/             # 全局样式
    └── globals.css
```

## 安装与运行

```bash
# 安装依赖
npm install

# 开发模式
npm run dev

# 生产构建
npm run build

# 预览构建
npm run preview
```

## 环境变量

```bash
VITE_WS_URL=ws://localhost:8080/ws  # WebSocket 服务器地址
```

## 界面预览

界面采用深色主题，配色参考 GitHub Dark 主题：

- 背景色: #0d1117 (shadow-900)
- 次级背景: #161b22 (shadow-800)
- 边框: #30363d (shadow-600)
- 强调色: #58a6ff (accent-blue)

## 许可证

MIT