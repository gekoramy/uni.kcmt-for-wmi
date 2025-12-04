{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    crane.url = "github:ipetkov/crane";
  };

  outputs = {
    self,
    nixpkgs,
    crane,
  }: let
    system = "x86_64-linux";
    pkgs = nixpkgs.legacyPackages.${system};
    pkgs-self = self.packages.${system};
    i686 = pkgs.pkgsi686Linux;
    craneLib = crane.mkLib pkgs;
  in {
    packages.${system} = {
      c2d = i686.callPackage ./nix/c2d.nix {};
      d4 = pkgs.callPackage ./nix/d4.nix {};
      mathsat = pkgs.callPackage ./nix/mathsat.nix {};
      tabularAllSMT = pkgs.callPackage ./nix/tabularAllSMT.nix {};
      volesti-integrate = pkgs.callPackage ./nix/volesti.nix {};
      decdnnf_rs = pkgs.callPackage ./nix/decdnnf_rs.nix {inherit craneLib;};

      bundle = pkgs.buildEnv {
        name = "bundle";
        paths = [
          pkgs.gmp
          pkgs.graphviz
          pkgs.latte-integrale
          pkgs.z3
          pkgs-self.c2d
          pkgs-self.d4
          pkgs-self.mathsat
          pkgs-self.tabularAllSMT
          pkgs-self.volesti-integrate
          pkgs-self.decdnnf_rs
        ];
      };
    };
  };
}
