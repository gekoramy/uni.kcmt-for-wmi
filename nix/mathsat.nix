{
  stdenv,
  fetchurl,
}:
stdenv.mkDerivation rec {
  pname = "mathsat";
  version = "5.6.12";

  src = fetchurl {
    url = "https://mathsat.fbk.eu/release/${pname}-${version}-linux-x86_64.tar.gz";
    sha256 = "sha256-HemE7YUAzgiVlwEW1X9zs4GSn6ZgDU4ptr6zBC8rchs=";
  };

  installPhase = ''
    install -m755 -D bin/${pname} $out/bin/${pname}
  '';

  meta = {
    homepage = "https://mathsat.fbk.eu/";
    description = "An SMT Solver for Formal Verification & More";
    platforms = ["x86_64-linux"];
  };
}
