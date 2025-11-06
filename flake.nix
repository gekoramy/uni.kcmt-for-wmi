{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    d4.url = "github:SoftVarE-Group/d4v2/2.3.2";
  };

  outputs = {
    self,
    nixpkgs,
    d4,
  }: let
    system = "x86_64-linux";
    pkgs = nixpkgs.legacyPackages.${system};
  in {
    packages.${system} = {
      patoh = pkgs.pkgsStatic.callPackage ./nix/patoh.nix {};

      c2d = pkgs.pkgsStatic.callPackage ./nix/c2d.nix {};

      mathsat = pkgs.pkgsStatic.callPackage ./nix/mathsat.nix {};

      tabularAllSMT = pkgs.pkgsStatic.callPackage ./nix/tabularAllSMT.nix {};

      image = pkgs.dockerTools.buildLayeredImage {
        name = "playground";
        tag = "latest";
        contents = [
          pkgs.python310
          pkgs.gcc
          pkgs.bashInteractive
          self.packages.${system}.c2d
          self.packages.${system}.mathsat
          self.packages.${system}.tabularAllSMT
          self.packages.${system}.patoh
          d4.packages.${system}.d4
        ];
        config = {
          Entrypoint = ["/bin/sh"];
        };
      };
    };

    devShells.${system}.default = pkgs.mkShell {
      buildInputs = [
        pkgs.python313
        pkgs.gcc
        pkgs.gmp
        self.packages.${system}.c2d
        self.packages.${system}.mathsat
        self.packages.${system}.tabularAllSMT
        self.packages.${system}.patoh
        d4.packages.${system}.d4
      ];
    };
  };
}
