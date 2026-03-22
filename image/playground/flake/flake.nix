{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    crane.url = "github:ipetkov/crane";
    ddnnife.url = "github:gekoramy/uni.kcmt-for-wmi/ddnnife";
  };

  outputs = {
    self,
    nixpkgs,
    crane,
    ddnnife,
  }: let
    system = "x86_64-linux";
    pkgs = nixpkgs.legacyPackages.${system};
    pkgs-self = self.packages.${system};
    craneLib = crane.mkLib pkgs;
  in {
    packages.${system} = {
      d4 = pkgs.callPackage ./nix/d4 {};
      mathsat = pkgs.callPackage ./nix/mathsat {};
      decdnnf_rs = pkgs.callPackage ./nix/decdnnf_rs {inherit craneLib;};
      ddnnife = ddnnife.packages.${system}.python;

      bundle = pkgs.buildEnv {
        name = "bundle";
        paths = [
          pkgs.gmp
          pkgs.graphviz
          pkgs.latte-integrale
          pkgs.z3
          pkgs-self.d4
          pkgs-self.mathsat
          pkgs-self.decdnnf_rs
        ];
      };
    };
  };
}
