{
  lib,
  stdenv,
  fetchurl,
  autoreconfHook,
}:
stdenv.mkDerivation {
  pname = "cudd";
  version = "3.0.0";

  src = fetchurl {
    url = "https://github.com/davidkebo/cudd/raw/c8d587ef3fbcc115977fed48a867aa6664ca11d0/cudd_versions/cudd-3.0.0.tar.gz";
    sha256 = "sha256-uOlmtFYslqA+f76iOXKVh9ezldU8rcw5pyA7Sc9+62k=";
  };

  configureFlags = [
    "--enable-dddmp"
    "--enable-obj"
  ];

  nativeBuildInputs = [autoreconfHook];

  meta = with lib; {
    homepage = "https://davidkebo.com/cudd";
    description = "Binary Decision Diagram (BDD) library";
    license = licenses.bsd3;
    platforms = platforms.all;
  };
}
