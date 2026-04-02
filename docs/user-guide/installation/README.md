# ShadowClaude 安装指南

本文档指导您在不同平台上安装 ShadowClaude。

## 目录

1. [系统要求](#系统要求)
2. [快速安装](#快速安装)
3. [macOS 安装](#macos-安装)
4. [Linux 安装](#linux-安装)
5. [Windows 安装](#windows-安装)
6. [Docker 安装](#docker-安装)
7. [源码安装](#源码安装)
8. [验证安装](#验证安装)

---

## 系统要求

### 最低要求

- **操作系统**: macOS 12+, Ubuntu 20.04+, Windows 10+
- **内存**: 4GB RAM
- **磁盘**: 2GB 可用空间
- **网络**: 互联网连接（用于 LLM API）

### 推荐配置

- **操作系统**: macOS 14+, Ubuntu 22.04+, Windows 11
- **内存**: 8GB+ RAM
- **磁盘**: 5GB+ 可用空间（SSD 推荐）
- **CPU**: 4 核以上

---

## 快速安装

### 使用安装脚本

```bash
curl -fsSL https://shadowclaude.dev/install.sh | bash
```

### 使用 Homebrew (macOS/Linux)

```bash
brew tap shadowclaude/tap
brew install shadowclaude
```

### 使用 pip

```bash
pip install shadowclaude
```

### 使用 Cargo

```bash
cargo install shadowclaude
```

---

## macOS 安装

### 使用 Homebrew（推荐）

```bash
# 添加 tap
brew tap shadowclaude/tap

# 安装
brew install shadowclaude

# 验证
shadowclaude --version
```

### 手动安装

```bash
# 下载最新版本
curl -L -o shadowclaude.tar.gz \
  https://github.com/shadowclaude/shadowclaude/releases/latest/download/shadowclaude-macos.tar.gz

# 解压
tar -xzf shadowclaude.tar.gz

# 移动到 PATH
sudo mv shadowclaude /usr/local/bin/

# 验证
shadowclaude --version
```

### Apple Silicon 特别说明

对于 M1/M2/M3 Mac：

```bash
# 确保 Rosetta 2 已安装（可选）
softwareupdate --install-rosetta --agree-to-license

# 或使用原生 ARM64 版本
brew install shadowclaude --arch=arm64
```

---

## Linux 安装

### Ubuntu/Debian

```bash
# 添加仓库
curl -fsSL https://shadowclaude.dev/gpg.key | sudo gpg --dearmor -o /usr/share/keyrings/shadowclaude.gpg

echo "deb [signed-by=/usr/share/keyrings/shadowclaude.gpg] https://shadowclaude.dev/apt stable main" | \
  sudo tee /etc/apt/sources.list.d/shadowclaude.list

# 安装
sudo apt update
sudo apt install shadowclaude
```

### CentOS/RHEL/Fedora

```bash
# Fedora
sudo dnf config-manager --add-repo https://shadowclaude.dev/fedora/shadowclaude.repo
sudo dnf install shadowclaude

# CentOS/RHEL
sudo yum-config-manager --add-repo https://shadowclaude.dev/centos/shadowclaude.repo
sudo yum install shadowclaude
```

### Arch Linux

```bash
# 使用 AUR
yay -S shadowclaude

# 或手动

git clone https://aur.archlinux.org/shadowclaude.git
cd shadowclaude
makepkg -si
```

### 通用 Linux 安装

```bash
# 下载
curl -L -o shadowclaude.tar.gz \
  https://github.com/shadowclaude/shadowclaude/releases/latest/download/shadowclaude-linux-x64.tar.gz

# 解压
tar -xzf shadowclaude.tar.gz

# 安装
sudo install -m 755 shadowclaude /usr/local/bin/

# 验证
shadowclaude --version
```

---

## Windows 安装

### 使用 winget

```powershell
# Windows 10/11
winget install ShadowClaude.ShadowClaude
```

### 使用 Chocolatey

```powershell
choco install shadowclaude
```

### 使用 Scoop

```powershell
scoop bucket add shadowclaude https://github.com/shadowclaude/scoop-bucket
scoop install shadowclaude
```

### 手动安装

1. 下载 Windows 版本:
   ```powershell
   Invoke-WebRequest -Uri "https://github.com/shadowclaude/shadowclaude/releases/latest/download/shadowclaude-windows.zip" -OutFile "shadowclaude.zip"
   ```

2. 解压:
   ```powershell
   Expand-Archive -Path "shadowclaude.zip" -DestinationPath "C:\Program Files\ShadowClaude"
   ```

3. 添加到 PATH:
   ```powershell
   [Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Program Files\ShadowClaude", [EnvironmentVariableTarget]::User)
   ```

---

## Docker 安装

### 使用 Docker

```bash
# 拉取镜像
docker pull shadowclaude/shadowclaude:latest

# 运行
docker run -it \
  -e ANTHROPIC_API_KEY=your_key \
  -v $(pwd):/workspace \
  shadowclaude/shadowclaude
```

### 使用 Docker Compose

创建 `docker-compose.yml`:

```yaml
version: '3.8'

services:
  shadowclaude:
    image: shadowclaude/shadowclaude:latest
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./workspace:/workspace
      - shadowclaude_data:/data
    ports:
      - "8080:8080"

volumes:
  shadowclaude_data:
```

运行:

```bash
docker-compose up -d
```

---

## 源码安装

### 克隆仓库

```bash
git clone https://github.com/shadowclaude/shadowclaude.git
cd shadowclaude
```

### 安装 Rust 工具链

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env
```

### 安装 Python（可选）

```bash
# macOS/Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 构建

```bash
# 构建 Rust 组件
cargo build --release

# 构建 Python 包（可选）
cd python
pip install -e .
```

### 安装

```bash
# 安装二进制文件
sudo cp target/release/shadowclaude /usr/local/bin/

# 验证
shadowclaude --version
```

---

## 验证安装

### 检查版本

```bash
shadowclaude --version
# 输出: shadowclaude 1.0.0
```

### 运行诊断

```bash
shadowclaude doctor
```

输出示例:

```
✓ Binary: found at /usr/local/bin/shadowclaude
✓ Config: found at ~/.config/shadowclaude/config.yaml
✓ LLM API: connected (anthropic)
✓ Memory: connected (vector DB)
✓ Tools: 42 tools available
✓ All systems operational
```

### 测试查询

```bash
shadowclaude query "Hello, can you hear me?"
```

---

## 配置

### 初始化配置

```bash
shadowclaude init
```

这将创建默认配置文件在 `~/.config/shadowclaude/config.yaml`。

### 设置 API 密钥

```bash
# 环境变量
export ANTHROPIC_API_KEY=your_key_here

# 或在配置文件中
echo "llm:
  provider: anthropic
  api_key: your_key_here" > ~/.config/shadowclaude/config.yaml
```

---

## 故障排除

### 常见问题

#### 命令未找到

```bash
# 检查 PATH
echo $PATH | grep shadowclaude

# 或重新安装到标准路径
sudo ln -sf /usr/local/bin/shadowclaude /usr/bin/shadowclaude
```

#### 权限错误

```bash
# 修复权限
chmod +x /usr/local/bin/shadowclaude

# 或重新安装
sudo install -m 755 shadowclaude /usr/local/bin/
```

#### 链接错误

```bash
# macOS: 安装命令行工具
xcode-select --install

# Linux: 安装依赖
sudo apt install build-essential libssl-dev pkg-config
```

### 获取帮助

```bash
# 查看帮助
shadowclaude --help
shadowclaude query --help

# 查看日志
shadowclaude --verbose query "test"

# 提交问题
shadowclaude bug-report
```

---

*文档版本: 1.0.0 | 最后更新: 2026-04-02*
