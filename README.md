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

$ pkgtrans aim zh-hant && pacman -Ss neovide         ← 目标语言随时可换
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
# 1) 添加 API Key（交互式选服务商，密钥不回显）
pkgtrans keyadd

# 2) 自检：打印生效配置并真实调一次 API
pkgtrans check

# 3) 直接用，和平时一模一样
pacman -Ss neovim
pamac search neovim
flatpak search neovim
```

`setup` 已经把 shell 集成写进 `~/.zshrc`，**新开一个终端**或 `source ~/.zshrc` 后生效。
在终端里跑 `type pacman`，显示 `pacman is a shell function` 就说明拦截已生效。

## 子命令一览

| 命令 | 作用 |
| --- | --- |
| `pkgtrans help` | 显示完整帮助 |
| `pkgtrans info` / `-v` / `--version` | 大字 `PKGTRANS` 图案 + 开发者信息 |
| `pkgtrans check` / `status` | 自检：配置、密钥链路、颜色、shell 集成、真实调一次 API |
| `pkgtrans aim [语言]` | 设置 / 查看目标语言 |
| `pkgtrans keyadd` | 添加 API Key |
| `pkgtrans keylist` | 列出所有 Key 及当前优先项 |
| `pkgtrans keyprefer [编号]` | 设置 / 查看优先使用的 Key |
| `pkgtrans keyremove <编号>` | 删除某个 Key |
| `pkgtrans keylock` | 锁定：只用优先 Key，不自动切换 |
| `pkgtrans keyunlock` | 解锁：优先 Key 失败时自动切换备用 |
| `pkgtrans setup [包管理器…]` | 为包管理器启用翻译（不带参数=查看状态，`all`=全部） |
| `pkgtrans putes [包管理器…]` | 取消（setup 反过来写；`unsetup` 同义） |
| `pkgtrans on` / `off` | 全局开启 / 关闭 |
| `pkgtrans clear-cache` | 清空翻译缓存 |
| `pkgtrans show-config` | 显示最终生效的配置 |

每个设置类命令都会给出明确回执，例如：

```
$ pkgtrans keyadd
请选择服务商：
   1) DeepSeek     deepseek-chat
   2) Claude       claude-3-5-haiku-latest
   ...
   0) 其它（自己填地址和模型）
选择 [1]: 1
API Key（输入不回显）:
  ✓ 已添加 DeepSeek 密钥 sk-*****f105a8（编号 1）
    地址：https://api.deepseek.com/v1
    模型：deepseek-chat
    密钥库：~/.config/pkgtrans/keys.json（权限 600）
```

## 多密钥与自动回退

```
$ pkgtrans keylist
 * 1 -> DeepSeek  |  sk-*****f105a8
   2 -> Claude    |  sk-ant-*****klmnop

     共 2 个 API key，当前优先：DeepSeek sk-*****f105a8
     优先密钥失败时会自动切换到其它 1 个
```

- `*` 标出当前优先的密钥。
- 默认**不锁定**：优先密钥遇到 401/403 或连续失败，会自动改用下一个备用密钥重试，
  并在 stderr 提示 `切换过 N 次备用密钥`。这样一把密钥欠费/过期不会让整个工具瘫掉。
- `pkgtrans keylock` 后只使用优先密钥（适合想严格控制成本、或不想把内容发给第二家服务商时）。
- 密钥一律打码显示，`keylist` 不会回显完整密钥；密钥库文件权限 600。
- 缓存按「协议 + 地址 + 模型 + 目标语言」做键，**与用哪个密钥无关**，换密钥不会让缓存失效。

## 目标语言

```sh
pkgtrans aim                 # 查询当前
pkgtrans aim zh-hant         # 繁體中文
pkgtrans aim zh-hans         # 简体中文
pkgtrans aim ja-jpan         # 日本語
pkgtrans aim ko-kore         # 한국어
pkgtrans aim eo-latn         # 世界语（Esperanto）
pkgtrans aim en-latn         # English
pkgtrans aim default         # 恢复汉语（简体中文）
pkgtrans aim 文言文           # 不认识的直接当语言名用
```

`zh-hans` `zh-cn` `zh` 都映射到简体中文，`zh-hant` `zh-tw` `zh-hk` 都映射到繁體中文。
缓存按语言分开存，来回切换不会串味，也不会重复花 token。

## 交互式设置面板

不想记子命令的话，直接开面板，一个界面把常用设置都改完：

```sh
pkgtrans menu        # 别名：pkgtrans ui / pkgtrans config
```

```
--------------------------------------------------------------
 pkgtrans 1.2 · 设置                    Arch 系（Arch / Manjaro / EndeavourOS …）
--------------------------------------------------------------
 翻译已开启 · 目标语言 简体中文 · API Key 1 个（优先 DeepSeek，未锁定）

 包管理器（输入编号切换接管）
   1  pacman       已安装  ✓ 已接管
   2  yay          已安装  ✓ 已接管
   3  paru         未安装    未接管
   4  pamac        已安装  ✓ 已接管
   5  flatpak      已安装  ✓ 已接管

 其它
   6  目标语言           简体中文
   7  API Key        1 个（DeepSeek）
   8  安装包管理器
   9  查看最终配置
   q  退出

 本平台不支持：apt、apt-cache、dnf、yum、zypper、brew、winget
   （属于 Debian 系、Fedora 系、macOS、openSUSE、Windows）
--------------------------------------------------------------
 输入编号或 q 退出 >
```

- **输编号即切换接管**，改完直接生效（重开窗口后加载）。
- **本平台不支持的命令单独列在末尾并标注归属**，不会被当成可选项误导你。
- **安装包管理器**：Windows 上能一键装 winget（下官方 App Installer），macOS 上能
  跑 Homebrew 官方脚本；其它平台给出对应的安装命令（`sudo apt install flatpak` 之类），
  AUR 才有的 `yay` / `paru` 会单独提示。
- **目标语言**和 **API Key** 各有一层子菜单：语言可选 10 种预置或手填，密钥可以
  添加 / 设为优先 / 删除 / 锁定。

只用「编号 + 回车」的纯文本交互——不依赖 `curses`（Windows 的 stdlib 里没有），
也不用 raw mode，所以管道喂输入也能跑：

```sh
printf '3\nq\n' | pkgtrans menu     # 脚本里切换第 3 项再退出
```

## 包管理器 setup / putes

```sh
pkgtrans setup                 # 看状态表
pkgtrans setup pamac flatpak   # 接管这两个
pkgtrans setup apt flatpak     # Debian / Ubuntu
pkgtrans setup dnf             # Fedora / RHEL
pkgtrans setup brew            # macOS
pkgtrans setup winget          # Windows
pkgtrans setup all             # 接管所有已安装的
pkgtrans putes pamac           # 取消 pamac（setup 反过来写）
pkgtrans putes all             # 全部取消
```

表格**只列当前系统适用的命令**。在 Arch 上长这样：

```
  包管理器    已安装  已接管
  pacman      ✓       ✓
  yay         ✓       ✓
  paru        -       -
  pamac       ✓       ✓
  flatpak     ✓       ✓
```

换到 Debian 上，`pacman` / `yay` / `paru` / `pamac` 就不会出现了：

```
  包管理器    已安装  已接管
  apt         ✓       ✓
  apt-cache   ✓       ✓
  flatpak     -       -
```

规则是「本平台适用的 + 虽不适用但确实装了的」。所以：
- Debian 上把 `pacman` 藏起来，不会误导人；
- 但如果你真在 WSL 里装了个 `pacman`，它照样会出现在表里、也能被接管；
- 反过来，`pkgtrans setup yay` 在 Debian 上会被明确拒绝，并告诉你本平台有哪些：

```
  ✗ yay 属于 Arch 系（Arch / Manjaro / EndeavourOS …），当前系统是 Debian 系（…）
    本平台可用：apt, apt-cache, flatpak
```

配置里 `shell_targets` 的含义：留空 / `auto` = 所有已安装的；`none` = 一个都不接管；
否则就是显式列表。**注意 `putes all` 会写成 `none` 而不是留空**，否则会被当成「未配置」而自动反弹回全接管。

> 想覆盖自动判定（比如 WSL 里想按 arch 看），设 `PSTRANS_PLATFORM=arch` 即可。

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

pkgtrans off                      # 全局关闭，一切原样透传
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
| `target_lang` | 简体中文 | 目标语言（用 `pkgtrans aim` 改） |
| `enabled` | 1 | 全局开关（用 `pkgtrans on/off` 改） |
| `shell_targets` | auto | 接管哪些命令（用 `pkgtrans setup/putes` 改） |
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

`pkgtrans keyadd` 的菜单里预置了 11 家常用的，选 `0` 可以手填任意地址和模型。
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
- `pkgtrans off`、`--raw`、`PSTRANS_DISABLE=1` 三档绕过，粒度从全局到单次。
- 只增删 `.zshrc` 里 `# >>> pkgtrans >>>` … `# <<< pkgtrans <<<` 之间的一段，
  安装前自动备份，重复安装不会重复插入。
- 输出编码全程按 UTF-8 字节处理，不受系统 locale 影响（本机 `LC_ALL` 是坏的，实测无碍）。
- 译文按**显示宽度**折行（中文算 2 列），不会撑破 pamac 的对齐。

## 常见问题

**搜索出来还是英文？**
三步排查：`type pacman` 看拦截是否生效（不是 function 就 `exec zsh` 或新开终端）；
`pkgtrans check` 看密钥链路；`pkgtrans off` 过一次看是不是被全局关了。

**输出全是黄色？**
没配好 API 或密钥失效。跑 `pkgtrans check`，它会直接告诉你是哪一环断了。

**终端里看不到红/黄？**
`pkgtrans check` 的「颜色标记」一行会说明原因。常见的是环境里设了 `NO_COLOR=1`
（按规范它优先于一切配色设置），`unset NO_COLOR` 或配置里写 `force_color = 1` 即可。
输出被管道/重定向时不着色是正常行为。

**一把密钥欠费了怎么办？**
再 `keyadd` 一把别家的，默认就会自动回退。想强制只用某一把就 `keyprefer <编号>` + `keylock`。

**翻译慢？**
一批默认 24 条、并发 4。结果多时把 `concurrency` 调到 6~8；本地 Ollama 建议 1~2。

**怎么完全卸载？**
`pkgtrans putes all` 取消接管，再删掉 `~/.local/bin/pkgtrans`、`~/.local/share/pkgtrans`、
`~/.config/pkgtrans`、`~/.cache/pkgtrans` 和 `.zshrc` 里的标记段即可。

## 自测

```sh
python3 ~/.local/share/pkgtrans/run_tests.py
```

不联网、不需要真实密钥，用本地 mock API 覆盖 **171 项**断言：

- 翻译链路：成功 / 500 / 401、批量与去重、缓存命中、熔断边界、部分返回补译
- 畸形返回：```` ```json ```` 围栏、包在对象里、前后带废话、只返回部分
- 协议：OpenAI 兼容 + Anthropic
- 方言：pacman 旗标、pamac 折行合并与折回、flatpak TSV 列完整性与 `--columns`、
  `--json` 透传、apt / apt-cache / dnf、**brew / winget**、管道模式自动识别 7 种方言
- 信息类：`Summary` / `Description` 字段值折行、**续行合并**（含 dnf 续行重复的冒号）、
  失败时逐字节还原
- 平台感知：六种平台各自该显示哪些命令、跨平台接管被拒绝、`PSTRANS_PLATFORM` 覆盖
- 设置面板：`menu` 渲染、切换接管、改目标语言、加 API Key、各平台的安装入口与「本平台不支持」警示、EOF 干净退出
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
