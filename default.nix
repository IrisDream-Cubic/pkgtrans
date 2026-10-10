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
  # python3 放 nativeBuildInputs 是为了让 fixupPhase 的 patchShebangs 把
  # `#!/usr/bin/env python3` 改写成 nix store 里的路径——NixOS 上 PATH 里
  # 默认没有 python3，不改写脚本根本跑不起来。改写后 shebang 本身就成了
  # 运行时依赖，闭包里会带上解释器。
  nativeBuildInputs = [ python3 ];

  dontConfigure = true;
  dontBuild = true;

  strictDeps = true;

  installPhase = ''
    runHook preInstall

    install -Dm755 pkgtrans $out/bin/pkgtrans

    install -Dm644 README.md $out/share/doc/pkgtrans/README.md
    install -Dm644 LICENSE   $out/share/licenses/pkgtrans/LICENSE

    install -Dm644 packaging/pkgtrans.bash-completion \
      $out/share/bash-completion/completions/pkgtrans
    install -Dm644 packaging/_pkgtrans \
      $out/share/zsh/site-functions/_pkgtrans

    runHook postInstall
  '';

  doInstallCheck = true;
  installCheckPhase = ''
    runHook preInstallCheck
    $out/bin/pkgtrans help > /dev/null
    $out/bin/pkgtrans --version > /dev/null
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
