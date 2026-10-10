{ lib
, stdenv
, python3
, src ? lib.cleanSource ./.
}:

stdenv.mkDerivation (finalAttrs: {
  pname = "pkgtrans";
  version = "1.0";

  inherit src;

  # 单文件 Python 脚本，没有构建步骤。
  #
  # python3 放 nativeBuildInputs 是为了让 fixupPhase 的 patchShebangs 能改写
  # `#!/usr/bin/env python3`。但实测在沙箱里 patchShebangs 并不会动这个 shebang
  # （构建期 PATH 里有 python3，所以 installCheck 还能过，等于骗过了自检），
  # 装到 NixOS 上运行时 PATH 里没有 python3，直接 `env: 'python3': No such file`。
  # 所以 installPhase 里显式把 shebang 写死成 store 路径，不依赖那个机制。
  nativeBuildInputs = [ python3 ];

  dontConfigure = true;
  dontBuild = true;

  strictDeps = true;

  installPhase = ''
    runHook preInstall

    install -Dm755 pkgtrans $out/bin/pkgtrans

    substituteInPlace $out/bin/pkgtrans \
      --replace-fail '#!/usr/bin/env python3' '#!${python3}/bin/python3'

    install -Dm644 README.md $out/share/doc/pkgtrans/README.md
    install -Dm644 LICENSE   $out/share/licenses/pkgtrans/LICENSE

    install -Dm644 packaging/pkgtrans.bash-completion \
      $out/share/bash-completion/completions/pkgtrans
    install -Dm644 packaging/_pkgtrans \
      $out/share/zsh/site-functions/_pkgtrans

    runHook postInstall
  '';

  # 自检在**清空 PATH** 的情况下跑，才能真正验出 shebang 有没有写对。
  # 正常情况下构建期 PATH 里带着 python3，会让坏掉的 shebang 蒙混过关。
  doInstallCheck = true;
  installCheckPhase = ''
    runHook preInstallCheck
    env -i "$out/bin/pkgtrans" --version > /dev/null
    env -i "$out/bin/pkgtrans" help > /dev/null
    env -i "$out/bin/pkgtrans" aim > /dev/null
    runHook postInstallCheck
  '';

  meta = with lib; {
    description = "AI translation for package manager search results";
    longDescription = ''
      pkgtrans translates the description lines of pacman / yay / paru /
      pamac / flatpak search results with an LLM API. Successful
      translations are shown in red, failed ones fall back to the original
      text in yellow. Non-search invocations are passed through untouched.
    '';
    homepage = "https://github.com/IrisDream-Cubic/pkgtrans";
    license = licenses.mit;
    mainProgram = "pkgtrans";
    platforms = platforms.unix;
  };
})
