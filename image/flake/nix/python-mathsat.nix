{
  fetchurl,
  python,
  python-pkgs,
  gmp,
  swig,
}:
python-pkgs.buildPythonPackage rec {
  pname = "mathsat";
  version = "5.6.12";

  pyproject = false;

  src = fetchurl {
    url = "https://mathsat.fbk.eu/release/${pname}-${version}-linux-x86_64.tar.gz";
    sha256 = "sha256-HemE7YUAzgiVlwEW1X9zs4GSn6ZgDU4ptr6zBC8rchs=";
  };

  nativeBuildInputs = [
    python
    python-pkgs.setuptools
    python-pkgs.wheel
    swig
  ];

  buildInputs = [
    gmp
  ];

  buildPhase = ''
    cd python
    ${python.executable} setup.py build_ext -R \$ORIGIN
  '';

  installPhase = ''
    mkdir -p $out/${python.sitePackages}
    cp build/lib*/_mathsat*.so $out/${python.sitePackages}
    cp mathsat.py $out/${python.sitePackages}

    mkdir -p $out/lib
    cp ../lib/libmathsat.* $out/lib/
  '';

  meta = {
    description = "MathSAT SMT solver with Python bindings";
    homepage = "https://mathsat.fbk.eu";
    platforms = ["x86_64-linux"];
  };
}
