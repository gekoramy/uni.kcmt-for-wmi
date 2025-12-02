{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    d4.url = "github:SoftVarE-Group/d4v2/2.3.2";
    crane.url = "github:ipetkov/crane";
  };

  outputs = {
    self,
    nixpkgs,
    d4,
    crane,
  }: let
    system = "x86_64-linux";
    pkgs = nixpkgs.legacyPackages.${system};
    pkgs-self = self.packages.${system};
    pkgs-d4 = d4.packages.${system};
    i686 = pkgs.pkgsi686Linux;
    craneLib = crane.mkLib pkgs;
  in {
    packages.${system} = {
      patoh = pkgs.callPackage ./nix/patoh.nix {};
      c2d = i686.callPackage ./nix/c2d.nix {};
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
          pkgs-d4.d4
          pkgs-self.c2d
          pkgs-self.mathsat
          pkgs-self.tabularAllSMT
          pkgs-self.patoh
          pkgs-self.volesti-integrate
          pkgs-self.decdnnf_rs
        ];
      };
    };
  };
}
