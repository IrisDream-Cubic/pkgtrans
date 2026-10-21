# pkgtrans

```text
 _ __  | |__    __ _  _     _ __  __ _   _ __   ___
| '_ \ | / /   / _` || |_  | '__|/ _` | | '_ \ / __|
| |_) ||  \   | (_| ||  _| | |   | (_| || | | |\__ \
| .__/ | |\ \  \__, | \__| |_|    \__,_||_| |_||___/
|_|    |_| \_\ |___/
```

给包管理器的**搜索结果描述**接上 AI 翻译。

- 翻译**成功** → 描述文字显示为 <span style="color:red">**红色**</span>
- 翻译**失败** → 描述文字显示为 <span style="color:gold">**黄色**</span>（原样回退，绝不影响包管理器本身）

支持 **12 个命令、7 种输出方言**，覆盖 Arch / Debian / Fedora / openSUSE / macOS /
Windows——它们的语法和格式各不相同（旗标式 / 子命令式、单行 / 缩进 / 折行 / TSV /
表格），工具会各自解析，**并且只列出当前系统真正适用的命令**：

| 平台 | 命令 | 输出形态 |
| --- | --- | --- |
| Arch / Manjaro | `pacman` `yay` `paru` | `仓库/名字 版本` + 4 空格缩进描述 |
| Arch / Manjaro | `pamac` | `名字 版本 …右对齐仓库` + **折行**描述 |
| Debian / Ubuntu | `apt` | `名字/仓库 版本 架构` + 2 空格缩进描述 |
| Debian / Ubuntu | `apt-cache` | 单行 `名字 - 描述` |
| Fedora / RHEL | `dnf` `yum` | ` 名字.架构`**TAB**描述 |
| openSUSE | `zypper` | 表格 |
| macOS | `brew` | `brew info` 的描述行、`brew search --desc` 的 `名字: 描述` |
| Windows | `winget` | `winget show` 的 `Description:` 字段 |
| 通用 | `flatpak` | **TSV**，描述是其中一列 |

信息类命令也支持：`pacman -Si`、`pacman -Qi`、`pamac info`、`apt show`、
`dnf info`、`brew info`、`winget show`（字段值折行、缩进续行都会正确合并再翻译）。

> `brew search` 和 `winget search` 的输出里**本来就没有描述**（前者只有包名，
> 后者只有 Name / Id / Version / Match / Source 五列），所以对这两个命令的
> `search` 是原样透传——真正带描述的是 `brew info` 和 `winget show`。

```
$ pacman -Ss neovim
extra/neovim 0.12.5-1
    Vim 的分支，致力于改进用户体验、插件和图形界面      ← 红色 = 翻译成功
extra/neovim-qt 0.2.20-1
    Neovim 的图形界面                                  ← 红色
aur/some-pkg 1.0-1
    Some package description                           ← 黄色 = 翻译失败，原样显示

$ pamac search neovim                                ← 描述会折行的也支持
writedoc  2.1-2                                              AUR
    一种无需定义文件路径即可使用 neovim 快速创建和编辑笔记的方式

$ flatpak search neovim                              ← TSV 只动 description 列
Neovim  ⇥ 融合了可扩展性和可用性的 Vim 分支 ⇥ io.neovim.nvim ⇥ 0.12.5 ⇥ stable ⇥ flathub

$ pkgtrans                                   ← 打开配置页，目标语言随时可换
extra/neovide 0.16.2-2
    Rust 打造的正經 Neovim 客戶端
```

## 文件位置

| 路径 | 说明 |
| --- | --- |
| `~/.local/share/pkgtrans/pkgtrans` | 主程序（单文件，只用 Python 标准库，无第三方依赖） |
| `~/.local/bin/pkgtrans` | 指向上面那个文件的软链接（`~/.local/bin` 在 PATH 里） |
| `~/.config/pkgtrans/config` | 配置文件（带注释，所有可调项都在里面） |
| `~/.config/pkgtrans/keys.json` | 密钥库，权限 600，由 `keyadd` / `keyprefer` 等维护 |
| `~/.cache/pkgtrans/cache.json` | 翻译缓存，可随时删 |
| `~/.local/share/pkgtrans/run_tests.py` | 自测脚本（本地 mock API，不联网、不花钱） |

## 安装

### Arch / Manjaro

```sh
git clone https://github.com/IrisDream-Cubic/pkgtrans
cd pkgtrans/packaging
makepkg -si
```

或者直接从 Release 里下 `.pkg.tar.zst`：

```sh
sudo pacman -U pkgtrans-1.3-1-any.pkg.tar.zst
```

（AUR 上架后 `yay -S pkgtrans` 即可。）

### macOS（Homebrew）

```sh
git clone https://github.com/IrisDream-Cubic/pkgtrans
cd pkgtrans
./install.sh --user          # 装到 ~/.local/bin，不需要 sudo
```

翻译 `brew info <包名>` 的描述行，以及 `brew search --desc <关键词>` 的描述。
`brew search` 本身只输出包名，没有可翻的东西，会原样透传。

### Windows

从 Release 下 `pkgtrans-windows-x64.exe`，放到任意目录（或者加进 `PATH`），
然后：

```powershell
.\pkgtrans-windows-x64.exe keyadd        # 加 API Key
.\pkgtrans-windows-x64.exe setup winget  # 接管 winget
winget show Neovim.Neovim                # 描述自动翻成中文
```

**机器上还没有 winget 怎么办**（Windows Server / LTSC 常见）：

```powershell
.\pkgtrans-windows-x64.exe install-winget
```

它会去 `microsoft/winget-cli` 的最新 release 下载官方 App Installer 和对应的
框架依赖（按 x64 / arm64 自动挑），再用 `Add-AppxPackage` 装上。装完重开一个
窗口就能用 `winget` 了。

> Windows 上的配置放在 `%APPDATA%\pkgtrans\`，缓存放在 `%LOCALAPPDATA%\pkgtrans\`，
> 不会在家目录里凭空多出一个 `.config`。

### openSUSE

用源码 tarball 里的 `install.sh`，或者直接用原始脚本；`zypper search` 的解析
已在支持列表里。

### Debian / Ubuntu

```sh
sudo apt install ./pkgtrans_1.3-1_all.deb
# 或
sudo dpkg -i pkgtrans_1.3-1_all.deb
```

### Fedora / RHEL / openSUSE

```sh
sudo rpm -ivh pkgtrans-1.3-1.noarch.rpm
# 或
sudo dnf install ./pkgtrans-1.3-1.noarch.rpm
```

### Nix / NixOS

**Nix 不通过下载包安装，而是直接用仓库里的 flake**（这也是为什么 Release 里没有
nix 的 `.tar.gz`——`nix build` 的产物里 shebang 指向 `/nix/store/...`，那个路径只
存在于构建它的机器上，打包发出来在别人机器上是跑不起来的）：

```sh
# 临时用一次
nix run github:IrisDream-Cubic/pkgtrans -- keylist

# 装进 profile
nix profile install github:IrisDream-Cubic/pkgtrans

# 或者在 configuration.nix 里
#   environment.systemPackages = [
#     (builtins.getFlake "github:IrisDream-Cubic/pkgtrans").packages.${system}.default
#   ];
```

### 其它发行版 / 不想用包管理器

```sh
./install.sh --user      # 装到 ~/.local，不需要 root
./install.sh             # 装到 /usr/local
./install.sh --uninstall # 卸载
```

### 其实一个文件就够了

`pkgtrans` 是**单文件、只用 Python 标准库**的脚本。把仓库里那个 `pkgtrans`
复制到任何有 Python 3.9+ 的地方、`chmod +x`，就能跑。包管理器提供的只是
补全、文档和 `/usr/bin` 里的软链。

### 打包产物对照

| 格式 | 文件 | 构建方式 |
| --- | --- | --- |
| Arch | `pkgtrans-1.3-1-any.pkg.tar.zst` | `makepkg`（`packaging/PKGBUILD`） |
| deb | `pkgtrans_1.3-1_all.deb` | `dpkg-deb -Zgzip`，没有 dpkg 时用 `packaging/build-deb.py` 手工组装 ar |
| rpm | `pkgtrans-1.3-1.fcNN.noarch.rpm` | `rpmbuild -bb packaging/pkgtrans.spec` |
| Windows | `pkgtrans-windows-x64.exe` | 在 **windows-latest** 上用 PyInstaller 打成单文件（不能在 Linux 上交叉编译） |
| winget 清单 | `pkgtrans-1.3-winget-manifests.tar.gz` | `packaging/make-winget-manifest.py`，用真实 exe 的 sha256 生成 |
| 源码 | `pkgtrans-1.3.tar.gz` | `sh packaging/build-source-tarball.sh`（`git archive`，可重复构建） |
| Nix | *不发布 tarball* | flake 就是交付方式，见上面「Nix / NixOS」 |

一次性全构建：

```sh
sh packaging/build-all.sh dist
```

优先用本机工具链，缺哪个就用 Docker 顶上（跑的是和 CI 完全相同的命令，所以
本机没有 `rpmbuild` / `nix` 也能把 rpm 构建出来并验证 flake）。国内拉不动
Docker Hub 时可以换镜像源：

```sh
PSTRANS_FEDORA_IMAGE=docker.m.daocloud.io/library/fedora:latest \
PSTRANS_NIX_IMAGE=dockerproxy.com/nixos/nix:latest \
sh packaging/build-all.sh dist
```

Windows 的 exe **必须**在 Windows 上打（PyInstaller 不支持交叉编译），所以本地
`build-all.sh` 不管它，由 CI 的 Windows 任务产出。

### 发布到 winget 源

Release 里附带的 `pkgtrans-<版本>-winget-manifests.tar.gz` 已经填好了真实的
exe sha256，解包后把 `manifests/` 整个目录提到
[microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs) 即可：

```sh
tar -xzf pkgtrans-1.3-winget-manifests.tar.gz
# fork winget-pkgs，把 manifests/ 下的四级目录原样拷进去，开 PR
```

合并之后 `winget install IrisDream.pkgtrans` 就能装。

版本号只有一个来源：主程序的 `__version__`，脚本都从那里读（有自测盯着，
改一处忘一处会直接挂）。完整构建 + 安装验证在 CI 里跑，见 `.github/workflows/release.yml`。

## 快速开始

```sh
pkgtrans                      # 打开配置页，按提示加 API Key
```

配置页里 `↑`/`↓` 移动光标、`Space` 勾选、`Enter` 进入下一层，加完 Key 就能直接用：

```sh
pacman -Ss neovim             # 和平时一模一样，描述会自动翻译
apt search neovim
dnf search neovim
brew info neovim
winget show Neovim.Neovim
```

## 命令一览

对外只保留三件事，其余全部收进配置页：

| 命令 | 作用 |
| --- | --- |
| `pkgtrans` | **打开配置页**（等价于 `pkgtrans menu` / `ui` / `config`）|
| `pkgtrans [选项] <命令> …` | 运行该命令并翻译其搜索结果；非搜索类调用原样透传 |
| `pkgtrans [选项]` | 从标准输入读取结果并翻译（`apt search x \| pkgtrans`）|
| `pkgtrans help` | 命令行帮助 |
| `pkgtrans --version` / `-v` / `info` | 版本与开发者信息 |

主界面只有 5 个入口，其余都在二级界面里：

- **包管理器**：接管开关 + 安装（没装的标灰不可选，平台不支持的标红并说明）
- **目标语言**：10 种预置或手填
- **API Key**：添加 / 设为优先 / 删除 / 锁定
- **帮助**：用法速查
- **关于**：版本信息 + 翻译总开关 / 自检 / 查看最终配置 / 清空缓存

> 以前那些 `keyadd` / `aim` / `setup` / `putes` / `on` / `off` / `check` /
> `clear-cache` / `show-config` / `install-winget` 等命令已经全部收进配置页，
> 不再作为独立命令提供。要恢复翻译功能，在配置页里把「翻译开关」勾上即可。

## 多密钥与自动回退

```
（在配置页的 API Key 界面里看）
 * 1 -> DeepSeek  |  sk-*****f105a8
   2 -> Claude    |  sk-ant-*****klmnop

     共 2 个 API key，当前优先：DeepSeek sk-*****f105a8
     优先密钥失败时会自动切换到其它 1 个
```

- `*` 标出当前优先的密钥。
- 默认**不锁定**：优先密钥遇到 401/403 或连续失败，会自动改用下一个备用密钥重试，
  并在 stderr 提示 `切换过 N 次备用密钥`。这样一把密钥欠费/过期不会让整个工具瘫掉。
- 在配置页里把 API Key **锁定**后只使用优先密钥（适合想严格控制成本、或不想把内容发给第二家服务商时）；解锁后优先 Key 失败会自动切换。
- 密钥一律打码显示，`keylist` 不会回显完整密钥；密钥库文件权限 600。
- 缓存按「协议 + 地址 + 模型 + 目标语言」做键，**与用哪个密钥无关**，换密钥不会让缓存失效。

## 目标语言

在配置页里按 `Enter` 打开「目标语言」，`↑`/`↓` 选、`Enter` 确认：

```
 目标语言
 ❯ (*) 简体中文
   ( ) 繁體中文
   ( ) 日本語
   ( ) 한국어
   ( ) 世界语（Esperanto）
   ( ) English
   ( ) Français
   ( ) Deutsch
   ( ) Español
   ( ) Русский
   + 手动输入其它
   返回
```

「手动输入其它」可以填任意语言名（比如 `文言文`）或代码（`zh-hant` / `ja-jpan`）。

## 配置页

```sh
pkgtrans            # 直接打开（等价于 pkgtrans menu / ui / config）
```

**光标操作**：`↑`/`↓` 移动、`Space` 勾选、`Enter` 进入二级界面、`q` 退出。
进菜单时会先清屏并切到备用屏幕缓冲区（和 `vim` / `less` 一样），退出后原来的
终端内容和滚动历史原样回来。

```
--------------------------------------------------------------
  _ __  | |__    __ _  _     _ __  __ _   _ __   ___
 | '_ \ | / /   / _` || |_  | '__|/ _` | | '_ \ / __|
 | |_) ||  \   | (_| ||  _| | |   | (_| || | | |\__ \
 | .__/ | |\ \  \__, | \__| |_|    \__,_||_| |_||___/
 |_|    |_| \_\ |___/

 v1.3 · Arch 系（Arch / Manjaro / EndeavourOS …）
 翻译已开启 · 目标语言 简体中文 · API Key 未配置

 ❯ 包管理器         4/5 个已接管
   目标语言         简体中文
   API Key          未配置
   帮助
   关于
   退出

--------------------------------------------------------------
 ↑/↓ 移动   Enter 打开   q 退出
```

主界面只放入口，**包管理器的开关在二级界面里**：

```
--------------------------------------------------------------
 包管理器

 勾选的会被接管；没装的要先把包装上

 ❯ [✓] pacman
   [✓] yay
   [✓] pamac
   [✓] flatpak
   [ ] paru         未安装
 本平台不支持
   [×] apt          apt仅在Debian 系上可用（当前系统：Arch 系）
   [×] apt-cache    apt-cache仅在Debian 系上可用（当前系统：Arch 系）
   [×] dnf          dnf仅在Fedora 系上可用（当前系统：Arch 系）
   [×] yum          yum仅在Fedora 系上可用（当前系统：Arch 系）
   [×] zypper       zypper仅在openSUSE上可用（当前系统：Arch 系）
   [×] brew         brew仅在macOS上可用（当前系统：Arch 系）
   [×] winget       winget仅在Windows上可用（当前系统：Arch 系）
--------------------------------------------------------------
 ↑/↓ 移动   Space 勾选   i 安装   q 返回
```

三种状态：

| 状态 | 长什么样 | 能不能勾 |
| --- | --- | --- |
| 已装、可接管 | `[✓]` / `[ ]` + 命令名 | 能 |
| **没装**（本平台能用但系统里没有）| 灰色 `[ ]` + `未安装` | **不能**，按 Space 会告诉你装它的命令 |
| **平台不支持** | 红色 `[×]` + `仅在 XXX 上可用（当前系统：YYY）` | **不能**，按 Space 只给原因 |

按 `i` 进入「安装包管理器」：Windows 一键装官方 App Installer、macOS 跑 Homebrew
官方脚本（都会先要一次确认），其它平台给出对应安装命令；AUR 才有的 `yay` /
`paru` 会单独说明。

### 二级界面

语言、API Key、帮助、关于都是独立的一屏，`↑`/`↓` 移动、`Enter` 确认、
`q` 返回（只回主界面，不会退出程序）。

```
 目标语言                          API Key
 ❯ (*) 简体中文                    ❯ + 添加 API Key
   ( ) 繁體中文                      * 设为优先
   ( ) 日本語                        - 删除
   ( ) 한국어                        [锁定] 只用优先 Key
   ...                               返回
   ( ) Русский
   + 手动输入其它                    共 1 个，优先：DeepSeek
   返回
 ↑/↓ 选择   Enter 确认   q 返回      ↑/↓ 移动   Enter 确认   q 返回
```

- **目标语言**：单选，`Enter` 确认后立刻写进配置。
- **API Key**：添加 / 设为优先 / 删除 / 锁定。
- **帮助**：命令行用法速查。
- **关于**：版本、开发者，以及翻译总开关、自检、查看最终配置、清空缓存。

### 没有终端时自动退回编号模式

`stdin` / `stdout` 不是终端（管道、重定向、CI）、或 `TERM=dumb` 时，会自动改用
「输入编号 + 回车」的纯文本模式，所以脚本里也能用：

```sh
printf '1\n1\nq\nq\n' | pkgtrans menu    # 主界面 → 包管理器 → 勾第 1 个 → 退出
PSTRANS_PLAIN=1 pkgtrans                    # 强制编号模式（屏幕阅读器 / 无障碍）
```

实现上不依赖 `curses`（Windows 的 stdlib 里没有），只用了 `termios`（POSIX）和
`msvcrt`（Windows）读单个按键，读完立刻恢复终端，所以中间夹着的文本输入
（比如粘贴 API Key）照常可用。

## 用法（包装命令）

```sh
pacman -Ss neovim                 # 透明拦截，推荐
yay -Ss neovim
pamac search neovim               # 子命令语法
pamac info neovim                 # Description 字段（值折行也能合并）
flatpak search neovim             # TSV，只动 description 列
pacman -Si neovim                 # -Si / -Qi 的 Description 也会翻译

apt search neovim                 # Debian / Ubuntu
apt-cache search neovim           # 单行格式
apt show neovim                   # Description 字段
dnf search neovim                 # Fedora / RHEL
dnf info neovim

brew info neovim                  # macOS（描述行紧跟在 ==> 包名: 版本 后面）
brew search --desc neovim         # 带描述的那版 search
winget show Neovim.Neovim         # Windows（Description 字段）
zypper search neovim              # openSUSE

pkgtrans pacman -Ss neovim        # 手动指定命令
pkgtrans --lang 繁體中文 yay -Ss neovim
apt search neovim | pkgtrans      # 管道过滤（自动识别 7 种方言）
pkgtrans --dialect pamac < out.txt

pkgtrans                          # 配置页里关掉「翻译开关」，一切原样透传
PSTRANS_DISABLE=1 pacman -Ss x    # 只关这一次
```

## 配置文件

`~/.config/pkgtrans/config`，`KEY = VALUE` 格式，带注释。优先级：

```
命令行选项  >  显式环境变量  >  keys.json  >  配置文件  >  自动探测
```

> keys.json 一旦有内容，就不会被环境里「顺带存在」的 `DEEPSEEK_API_KEY` 之类抢走；
> 但显式写 `PSTRANS_API_BASE` / `--api-key` 依然可以临时覆盖它（方便调试）。

常用项：

| 项 | 默认 | 说明 |
| --- | --- | --- |
| `target_lang` | 简体中文 | 目标语言（配置页里改）|
| `enabled` | 1 | 全局开关（配置页里改）|
| `shell_targets` | auto | 接管哪些命令（配置页里勾选）|
| `chunk_size` | 24 | 每次请求翻译多少条（批量更省 token） |
| `concurrency` | 4 | 并发请求数 |
| `max_items` | 300 | 单次最多翻译多少条，`0` = 不限 |
| `timeout` / `retries` | 30 / 2 | 单次请求超时、失败重试次数 |
| `translate_info` | 1 | 是否翻译 `-Si` / `-Qi` 的 Description |
| `skip_cjk` | 1 | 描述本来就是中文时不调 API，直接算成功 |
| `bilingual` | 0 | 1 = 译文后用灰色附上原文 |
| `color_ok` / `color_fail` | 31 / 33 | 成功红 / 失败黄，可换 32 绿、36 青等 |
| `cache` | 1 | 翻译缓存开关 |

也支持环境变量：`PSTRANS_API_KEY`、`PSTRANS_API_BASE`、`PSTRANS_MODEL`、`PSTRANS_LANG`、
`PSTRANS_ENABLED`、`PSTRANS_KEYS_FILE`、`PSTRANS_CONFIG`、`PSTRANS_TIMEOUT` 等。

## 支持的 API

`api_style` 两种协议，覆盖绝大多数服务商：

- **`openai`**：DeepSeek、OpenAI、OpenRouter、硅基流动、通义千问、Kimi、智谱、Groq、
  Gemini（OpenAI 兼容端点）、Ollama、LM Studio、vLLM、one-api 中转站……
- **`anthropic`**：Claude 官方接口

配置页「添加 API Key」里预置了 11 家常用的，选 `0` 可以手填任意地址和模型。
没建密钥库时会自动探测这些环境变量：`DEEPSEEK_API_KEY` → `OPENAI_API_KEY` →
`OPENROUTER_API_KEY` → `SILICONFLOW_API_KEY` → `DASHSCOPE_API_KEY` → `MOONSHOT_API_KEY` →
`ZHIPUAI_API_KEY` → `GEMINI_API_KEY` → `GROQ_API_KEY` → `ANTHROPIC_API_KEY` → `OLLAMA_HOST`。

## 安全性：为什么不会干扰 `pacman -Syu`

shell 里只把 `pacman` / `yay` / `paru` / `pamac` / `flatpak` / `apt` / `apt-cache` /
`dnf` / `yum` 包了一层函数，函数把参数交给 `pkgtrans` 判断：

| 调用 | 行为 |
| --- | --- |
| `pacman -Ss` `-Qs` `-Fs` `-Ssq` `--search`、`apt search`、`apt-cache search`、`dnf search`、`flatpak search` | 捕获输出 → 翻译描述 → 原样保留其他行 |
| `pacman -Si` `-Qi`、`pamac info`、`apt show`、`dnf info` | 只翻译 `Description` / `Summary` 字段（含折行与续行） |
| `pamac search` | 折行描述合并后翻译，再按原宽度折回 |
| `-Syu` `-S` `-R` `-Q` `-Sl` `-F`、`pamac install/update/…`、`flatpak run/install/list/…`、**`apt install/upgrade/…`、`dnf upgrade/install/…`** | **`exec` 完全透传**，不捕获输出、不改一个字节、退出码和信号完全一致 |
| `flatpak search --json` | 透传（机器可读格式不碰） |

判断逻辑对 `-R -s`（recursive，不是 search）、`-Rns`、`-Slq`、`-b<路径>` 这类容易误判的情况
都做了区分，25 条分类用例全部通过。

> 把 `apt` 也包一层会让人担心，但它和 pacman 那套一样走 **`os.execv` 完全替换进程**：
> `apt install` 的交互提示、进度条、退出码、信号全都原样，只是多花约 30ms 起一个 Python。
> 脚本里跑 `apt` 不受影响（非交互 shell 不读 `.zshrc`），`sudo apt` 也不受影响
> （sudo 看不到 shell 函数，直接跑真二进制）。

其它保障：

- 翻译失败 ≠ 命令失败。API 挂了照样输出完整包列表，退出码仍是原命令的退出码。
- `pacman -Ssq` 这类没有描述的搜索输出逐字节不变（已验证）。
- `flatpak list`、`flatpak --version`、`pamac list`、`pamac --version` 等透传输出逐字节一致（已验证）。
- 配置页的「翻译开关」、`--raw`、`PSTRANS_DISABLE=1` 三档绕过，粒度从全局到单次。
- 只增删 `.zshrc` 里 `# >>> pkgtrans >>>` … `# <<< pkgtrans <<<` 之间的一段，
  安装前自动备份，重复安装不会重复插入。
- 输出编码全程按 UTF-8 字节处理，不受系统 locale 影响（本机 `LC_ALL` 是坏的，实测无碍）。
- 译文按**显示宽度**折行（中文算 2 列），不会撑破 pamac 的对齐。

## 常见问题

**搜索出来还是英文？**
三步排查：`type pacman` 看拦截是否生效（不是 function 就 `exec zsh` 或新开终端）；
在配置页里点「自检」看密钥链路；把「翻译开关」关一次看看是不是被全局关了。

**输出全是黄色？**
没配好 API 或密钥失效。在配置页里点「自检」，它会直接告诉你是哪一环断了。

**终端里看不到红/黄？**
配置页「自检」输出的「颜色标记」一行会说明原因。常见的是环境里设了 `NO_COLOR=1`
（按规范它优先于一切配色设置），`unset NO_COLOR` 或配置里写 `force_color = 1` 即可。
输出被管道/重定向时不着色是正常行为。

**一把密钥欠费了怎么办？**
再 `keyadd` 一把别家的，默认就会自动回退。想强制只用某一把就 `keyprefer <编号>` + `keylock`。

**翻译慢？**
一批默认 24 条、并发 4。结果多时把 `concurrency` 调到 6~8；本地 Ollama 建议 1~2。

**怎么完全卸载？**
在配置页里把包管理器全部取消勾选，再删掉 `~/.local/bin/pkgtrans`、`~/.local/share/pkgtrans`、
`~/.config/pkgtrans`、`~/.cache/pkgtrans` 和 `.zshrc` 里的标记段即可。

## 自测

```sh
python3 ~/.local/share/pkgtrans/run_tests.py
```

不联网、不需要真实密钥，用本地 mock API 覆盖 **191 项**断言：

- 翻译链路：成功 / 500 / 401、批量与去重、缓存命中、熔断边界、部分返回补译
- 畸形返回：```` ```json ```` 围栏、包在对象里、前后带废话、只返回部分
- 协议：OpenAI 兼容 + Anthropic
- 方言：pacman 旗标、pamac 折行合并与折回、flatpak TSV 列完整性与 `--columns`、
  `--json` 透传、apt / apt-cache / dnf、**brew / winget**、管道模式自动识别 7 种方言
- 信息类：`Summary` / `Description` 字段值折行、**续行合并**（含 dnf 续行重复的冒号）、
  失败时逐字节还原
- 平台感知：六种平台各自该显示哪些命令、跨平台接管被拒绝、`PSTRANS_PLATFORM` 覆盖
- 设置面板：`menu` 编号模式渲染、切换接管、改目标语言、加 API Key、各平台的安装入口与「本平台不支持」警示、EOF 干净退出；
  **光标模式用 pty 模拟真实按键测**（↑/↓ 移动、Space 勾选、Enter 进二级界面、锁定行只提示不落盘、二级界面里 q 只返回、语言单选落盘、`PSTRANS_PLAIN` 退回）
- 子命令：`keyadd/keylist/keyprefer/keyremove/keylock/keyunlock`、
  `aim`（含 `zh-hant` `eo-latn` `default`）、`on/off`、`setup/putes/putesy`、
  `install-winget`、`info`、`help`
- 多密钥：优先密钥 401 时自动切换备用；`keylock` 后不切换
- 安全性：27 条调用分类矩阵、`-Ssq` / `flatpak list` 等透传逐字节一致
- logo：纯 ASCII、无歧义宽度字符、README 与程序输出逐字节一致

Windows 上另跑 `packaging/windows-smoke.py`（完整自测依赖 POSIX 的 `.zshrc`
和 `#!/bin/sh` 假二进制，跑不了），覆盖 exe 启动、平台判定、winget 解析、
`install-winget` 和 `%APPDATA%` 路径。

## 开发者

- 开发者：Toru Momose
- 开发：DeepSeek v4 Pro
- More about Developer: <https://iris-dream.top>
