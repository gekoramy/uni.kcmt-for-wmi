{
  stdenv,
  fetchurl,
  gmp,
  unzip,
}:
stdenv.mkDerivation rec {
  pname = "query-dnnf";
  version = "0.4.180625";

  nativeBuildInputs = [
    unzip
  ];

  buildInputs = [
    gmp
  ];

  src = fetchurl {
    url = "https://www.cril.univ-artois.fr/KC/ressources/${pname}-${version}.zip";
    sha256 = "sha256-mui23VZ4SBeQmk/+VsumuF+GARkjoHUG9iro5UBaG7s=";
  };

  installPhase = ''
    install -m755 -D query-dnnf $out/bin/${pname}
  '';

  meta = {
    homepage = "https://www.cril.univ-artois.fr/KC/d-DNNF-reasoner.html";
    description = ''
      d-DNNF-reasoner is a tool for reasoning on d-DNNF representations.
      This tool implements some useful queries and transformations on compiled forms, including conditioning, satisfiability checking and model counting.
    '';
  };
}
