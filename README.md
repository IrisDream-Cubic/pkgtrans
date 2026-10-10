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

支持 `pacman` / `yay` / `paru` / `pamac` / `flatpak` 五家——它们的语法和输出格式各不相同
（旗标式 vs 子命令式、单行 vs 折行 vs TSV），工具会各自解析。

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
sudo pacman -U pkgtrans-1.0-1-any.pkg.tar.zst
```

（AUR 上架后 `yay -S pkgtrans` 即可。）

### Debian / Ubuntu

```sh
sudo apt install ./pkgtrans_1.0-1_all.deb
# 或
sudo dpkg -i pkgtrans_1.0-1_all.deb
```

### Fedora / RHEL / openSUSE

```sh
sudo rpm -ivh pkgtrans-1.0-1.noarch.rpm
# 或
sudo dnf install ./pkgtrans-1.0-1.noarch.rpm
```

### Nix / NixOS

```sh
# 临时用一次
nix run github:IrisDream-Cubic/pkgtrans -- keylist

# 装进 profile
nix profile install github:IrisDream-Cubic/pkgtrans

# 或者在 configuration.nix 里
#   environment.systemPackages = [ (pkgs.callPackage (fetchTarball "...") { }) ];
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
| Arch | `pkgtrans-1.0-1-any.pkg.tar.zst` | `makepkg`（`packaging/PKGBUILD`） |
| deb | `pkgtrans_1.0-1_all.deb` | `dpkg-deb`，没有则用 `packaging/build-deb.py` 手工组装 |
| rpm | `pkgtrans-1.0-1.noarch.rpm` | `rpmbuild -ba packaging/pkgtrans.spec` |
| Nix | flake 输出 | `nix build .#`（`flake.nix` + `default.nix`） |
| 源码 | `pkgtrans-1.0.tar.gz` | `sh packaging/build-source-tarball.sh` |

一次性全构建：`sh packaging/build-all.sh`（本机缺的工具链会明确跳过）。
四个格式的完整构建与安装验证在 CI 里跑：见 `.github/workflows/release.yml`。

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

## 包管理器 setup / putes

```sh
pkgtrans setup                 # 看状态表
pkgtrans setup pamac flatpak   # 接管这两个
pkgtrans setup all             # 接管所有已安装的
pkgtrans putes pamac           # 取消 pamac（setup 反过来写）
pkgtrans putes all             # 全部取消
```

```
  包管理器    已安装  已接管
  pacman      ✓       ✓
  yay         ✓       ✓
  paru        -       -
  pamac       ✓       ✓
  flatpak     ✓       ✓
```

配置里 `shell_targets` 的含义：留空 / `auto` = 所有已安装的；`none` = 一个都不接管；
否则就是显式列表。**注意 `putes all` 会写成 `none` 而不是留空**，否则会被当成「未配置」而自动反弹回全接管。

## 用法（包装命令）

```sh
pacman -Ss neovim                 # 透明拦截，推荐
yay -Ss neovim
pamac search neovim               # 子命令语法
pamac info neovim                 # Description 字段（值折行也能合并）
flatpak search neovim             # TSV，只动 description 列
pacman -Si neovim                 # -Si / -Qi 的 Description 也会翻译

pkgtrans pacman -Ss neovim        # 手动指定命令
pkgtrans --lang 繁體中文 yay -Ss neovim
pamac search neovim | pkgtrans    # 管道过滤（自动识别 pacman/pamac/flatpak 格式）
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

shell 里只把 `pacman` / `yay` / `paru` / `pamac` / `flatpak` 包了一层函数，
函数把参数交给 `pkgtrans` 判断：

| 调用 | 行为 |
| --- | --- |
| `pacman -Ss` `-Qs` `-Fs` `-Ssq` `--search` | 捕获输出 → 翻译描述 → 原样保留其他行 |
| `pacman -Si` `-Qi` `pamac info` | 只翻译 `Description` 字段（含折行的值） |
| `pamac search` / `flatpak search` | 翻译描述；pamac 折行合并后重排，flatpak 只改 description 列 |
| `-Syu` `-S` `-R` `-Q` `-Sl` `-F`、`pamac install/update/…`、`flatpak run/install/list/…` | **`exec` 完全透传**，不捕获输出、不改一个字节、退出码和信号完全一致 |
| `flatpak search --json` | 透传（机器可读格式不碰） |

判断逻辑对 `-R -s`（recursive，不是 search）、`-Rns`、`-Slq`、`-b<路径>` 这类容易误判的情况
都做了区分，16 条分类用例全部通过。

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

不联网、不需要真实密钥，用本地 mock API 覆盖 **103 项**断言：

- 翻译链路：成功 / 500 / 401、批量与去重、缓存命中、熔断边界、部分返回补译
- 畸形返回：```` ```json ```` 围栏、包在对象里、前后带废话、只返回部分
- 协议：OpenAI 兼容 + Anthropic
- 方言：pacman 旗标、pamac 折行合并与折回、pamac info 字段续行、flatpak TSV 列完整性与 `--columns`、
  `--json` 透传、管道模式自动识别
- 子命令：`keyadd/keylist/keyprefer/keyremove/keylock/keyunlock`、
  `aim`（含 `zh-hant` `eo-latn` `default`）、`on/off`、`setup/putes/putesy`、`info`、`help`
- 多密钥：优先密钥 401 时自动切换备用；`keylock` 后不切换
- 安全性：16 条调用分类矩阵、`-Ssq` / `flatpak list` 等透传逐字节一致

## 开发者

- 开发者：Toru Momose
- 开发：DeepSeek v4 Pro
- More about Developer: <https://iris-dream.top>
