Name:           pkgtrans
Version:        1.3
Release:        1%{?dist}
Summary:        AI translation for package manager search results
Summary(zh_CN): 用 AI 翻译包管理器搜索结果的描述文字

License:        MIT
URL:            https://github.com/IrisDream-Cubic/pkgtrans
Source0:        %{url}/releases/download/v%{version}/%{name}-%{version}.tar.gz

BuildArch:      noarch

Requires:       python3 >= 3.9
# 只列 Fedora 上真实存在的命令。把 pacman / pamac 写成 Suggests 只会在
# 用户 `dnf install` 时得到「找不到这个包」的提示。
Recommends:     flatpak

%description
pkgtrans translates the description lines of dnf / yum search and
flatpak search results with an LLM API. Successful translations are shown
in red, failed ones fall back to the original text in yellow. Non-search
invocations (dnf upgrade, flatpak run, ...) are passed through untouched.
On Arch and Debian it also handles pacman / pamac and apt / apt-cache.

%description -l zh_CN
pkgtrans 给 dnf / yum search、flatpak search 的搜索结果描述接上 AI 翻译：
翻译成功显示红色，失败原样回退显示黄色。非搜索类调用（dnf upgrade、
flatpak run 等）完全原样透传，不改变任何行为。在 Arch 和 Debian 上还支持
pacman / pamac 与 apt / apt-cache。

%prep
%autosetup -n %{name}-%{version}

%build
# 纯 Python 单文件脚本，无需构建步骤。

%check
python3 run_tests.py

%install
install -Dpm0755 pkgtrans %{buildroot}%{_bindir}/pkgtrans
install -Dpm0644 packaging/pkgtrans.bash-completion \
    %{buildroot}%{_datadir}/bash-completion/completions/pkgtrans
install -Dpm0644 packaging/_pkgtrans \
    %{buildroot}%{_datadir}/zsh/site-functions/_pkgtrans

%files
%{_bindir}/pkgtrans
%{_datadir}/bash-completion/completions/pkgtrans
%{_datadir}/zsh/site-functions/_pkgtrans
%doc README.md
%license LICENSE

%changelog
* Wed Oct 21 2026 Toru Momose <iris@iris-dream.top> - 1.3-1
- 新增交互式设置面板 `pkgtrans menu`（别名 ui / config）：包管理器开关、
  安装包管理器、目标语言、API Key 都在一个界面里改
- 安装屏按平台给路径：Windows 一键装官方 App Installer，macOS 跑 Homebrew
  官方脚本，其它平台给对应安装命令；本平台不支持的命令单独警示
- 修复：Windows 上输出被管道接走时中文会抛 UnicodeEncodeError
- 修复：rpmbuild 的 %check 在缺 git 的环境里会崩
- 修复：源码包不带参数构建时版本号为空（pkgtrans-.tar.gz）
- 交互式配置页成为唯一的设置入口：keyadd / aim / setup / putes / on / off /
  check / clear-cache / show-config / install-winget 等子命令全部收进配置页，
  对外只保留 help / --version / 包装调用
- 修复：`pkgtrans setup | head` 的退出码是 120

* Tue Oct 20 2026 Toru Momose <iris@iris-dream.top> - 1.2-1
- 按平台过滤包管理器：dnf 系上不再显示 pacman / yay / apt 等不相干的命令
- 新增 Homebrew（macOS）：brew info 的描述行、brew search --desc 的描述
- 新增 winget（Windows）：winget show 的 Description
- 新增 install-winget 子命令：没装 winget 的 Windows 机器自动装官方 App Installer
- Windows 上配置改放 %APPDATA%\pkgtrans，并打开控制台的 ANSI 支持
- shell 集成支持 PowerShell（写 $PROFILE）

* Sun Oct 11 2026 Toru Momose <iris@iris-dream.top> - 1.1-1
- 支持 9 个命令 / 5 种输出方言：pacman、yay、paru、pamac、flatpak、
  apt、apt-cache、dnf、yum；信息类命令 -Si / -Qi / show / info 也支持
- 多 API Key 管理与失败自动回退，可锁定为只用其中一个
- 目标语言可切换（简体 / 繁體 / 日本語 / 한국어 / 世界语 / …）
- setup / putes 按包管理器维护 shell 集成，on / off 全局开关
- 翻译成功的描述显示红色，失败原样回退并显示黄色
