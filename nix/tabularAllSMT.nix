{
  stdenv,
  fetchFromGitHub,
}:
stdenv.mkDerivation rec {
  pname = "tabularAllSMT";
  version = "9a799caebd100d189e8d4a8c269b9dadf4869cbe";

  src = fetchFromGitHub {
    owner = "giuspek";
    repo = pname;
    rev = version;
    sha256 = "sha256-bsMdHeYUvxggIYkjnXNRkmbD0hLHXHbqlBVU8ys8yfs=";
  };

  installPhase = ''
    install -m755 -D ${pname} $out/bin/${pname}
  '';

  meta = {
    homepage = "https://github.com/giuspek/tabularAllSMT";
    description = "Disjoint SMT enumeration without introducing blocking clauses";
    platforms = [ "x86_64-linux" ];
  };
}
