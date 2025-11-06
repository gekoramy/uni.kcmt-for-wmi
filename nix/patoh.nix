{
  stdenv,
  fetchurl,
}:
stdenv.mkDerivation {
  pname = "PaToH";
  version = "3.3";

  src = fetchurl {
    url = "https://faculty.cc.gatech.edu/~umit/PaToH/patoh-Darwin-x86_64.tar.gz";
    sha256 = "sha256-Ih0m//utw9cxPvbndw/vUjuqPbPehY5R4Y84Mj+fdxo=";
  };

  installPhase = ''
    cd *

    mkdir -p $out/include
    mkdir -p $out/lib

    cp patoh.h $out/include/
    cp libpatoh.a $out/lib/
  '';

  meta = {
    homepage = "https://faculty.cc.gatech.edu/~umit/software.html";
    description = "Partitioning Tools for Hypergraph";
    platforms = ["x86_64-linux"];
  };
}
