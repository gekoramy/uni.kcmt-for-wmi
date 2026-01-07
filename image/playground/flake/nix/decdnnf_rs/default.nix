{
  applyPatches,
  craneLib,
  fetchFromGitHub,
  m4,
}:
craneLib.buildPackage {
  nativeBuildInputs = [
    m4
  ];

  src = applyPatches {
    name = "patched-decdnnf_rs";
    src = fetchFromGitHub {
      owner = "crillab";
      repo = "decdnnf_rs";
      rev = "v1.0.0";
      sha256 = "sha256-4IRt4BgupQ2gdaZCIu18O/XSBrLAt22XkrtmglPvg1I=";
    };
    patches = [
      ./logging.patch
    ];
  };

  cargoLock = ./Cargo.lock;
}
