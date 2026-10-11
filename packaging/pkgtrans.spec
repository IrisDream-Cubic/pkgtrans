Name:           pkgtrans
Version:        1.0
Release:        1%{?dist}
Summary:        AI translation for package manager search results
Summary(zh_CN): 用 AI 翻译包管理器搜索结果的描述文字

License:        MIT
URL:            https://github.com/IrisDream-Cubic/pkgtrans
Source0:        %{url}/releases/download/v%{version}/%{name}-%{version}.tar.gz

BuildArch:      noarch

Requires:       python3 >= 3.9
Recommends:     flatpak
Suggests:       pacman
Suggests:       pamac

%description
pkgtrans translates the description lines of dnf / yum search and
flatpak search results (and pacman / yay / paru / pamac on Arch) with an
LLM API. Successful translations are shown in red, failed ones fall back to
the original text in yellow. Non-search invocations (dnf upgrade,
apt install, flatpak run, ...) are passed through untouched.

%description -l zh_CN
pkgtrans 给 dnf / yum search、flatpak search（以及在 Arch 上的 pacman /
yay / paru / pamac）的搜索结果描述接上 AI 翻译：翻译成功显示红色，
失败原样回退显示黄色。非搜索类调用（dnf upgrade、apt install、
flatpak run 等）完全原样透传，不改变任何行为。

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
* Sat Oct 10 2026 Toru Momose <iris@iris-dream.top> - 1.0-1
- 首个版本：三种方言解析、多 API Key、目标语言、shell 集成
