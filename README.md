# VRChat OSC 调试工具

基于 VRChat Wiki 官方参数规范的 OSC 调试工具，支持自动加载角色自定义参数。

## 功能特性

- **官方参数支持** - 完整的 VRChat Wiki OSC 参数（输入、输出、相机、追踪等）
- **Web 控制面板** - 现代化的网页界面，实时控制参数
- **自动加载** - 切换 VRChat 模型时自动加载自定义参数
- **实时同步** - WebSocket 实时同步参数状态
- **参数过滤** - 自动过滤与系统参数重复的自定义参数

## 安装

### 环境要求
- Python >= 3.11

### 方式一：使用 uv（推荐）

```bash
# 安装依赖
uv sync

# 启动程序
uv run python main.py
```

### 方式二：使用 pip

```bash
# 通过 pyproject.toml 安装依赖
pip install -e .

# 启动程序
python main.py
```

### 2. 打开浏览器

访问 http://localhost:8080

### 3. 配置 VRChat

确保 VRChat 的 OSC 功能已开启：
- 进入 VRChat 设置 → OSC
- 启用 "Enable OSC"

## 界面说明

### Input 面板（左）
- 可控制的输入参数（摇杆、按钮等）
- 滑块控制数值型参数
- 开关控制布尔型参数

### Output 面板（右）
- 实时显示 VRChat 发送的状态
- 角色状态、手势、追踪数据等

### 自定义参数
- 切换模型时自动加载
- 显示为金色分隔区域
- 仅显示该模型独有的参数

## 技术栈

- **后端**: Python + aiohttp
- **OSC 通信**: python-osc
- **实时通信**: WebSocket
- **前端**: 原生 HTML/CSS/JS

## 文件说明

```
├── main.py           # 主程序
├── static/
│   └── index.html    # 前端界面
├── pyproject.toml    # 项目配置
└── README.md         # 说明文档
```

## 注意事项

1. 程序会自动扫描 `%USERPROFILE%\AppData\LocalLow\VRChat\VRChat\OSC` 目录加载角色参数
2. 确保 VRChat 和本程序在同一台电脑上运行
3. 如果端口被占用，修改 `main.py` 中的 `WEB_PORT` 和 `OSC_RECEIVE_PORT`

## License

MIT
