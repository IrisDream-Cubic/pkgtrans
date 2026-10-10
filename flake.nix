{
  description = "pkgtrans — 用 AI 翻译 pacman / yay / pamac / flatpak 搜索结果的描述文字";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forAllSystems = f:
        nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in
    {
      packages = forAllSystems (pkgs:
        let
          pkgtrans = pkgs.callPackage ./default.nix { src = self; };
        in
        {
          inherit pkgtrans;
          default = pkgtrans;
        });

      apps = forAllSystems (pkgs: {
        default = {
          type = "app";
          program = "${self.packages.${pkgs.system}.pkgtrans}/bin/pkgtrans";
          meta.description = "pkgtrans";
        };
      });

      devShells = forAllSystems (pkgs: {
        default = pkgs.mkShell {
          packages = [ pkgs.python3 ];
        };
      });

      formatter = forAllSystems (pkgs: pkgs.nixpkgs-fmt);
    };
}
