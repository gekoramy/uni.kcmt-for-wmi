{
  stdenv,
  fetchzip,
  fetchFromGitHub,
  cmake,
  ninja,
  boost,
  gmp,
  zlib,
}: let
  patoh = fetchzip {
    url = "https://faculty.cc.gatech.edu/~umit/PaToH/patoh-Linux-x86_64.tar.gz";
    sha256 = "sha256-vnO3PKNdKF9Bom4jJogV+VKacyaSc5JtMQHgda62D9g=";
  };
in
  stdenv.mkDerivation rec {
    pname = "d4";
    version = "2";

    nativeBuildInputs = [
      cmake
      ninja
    ];

    buildInputs = [
      boost
      gmp
      zlib
    ];

    src = fetchFromGitHub {
      owner = "ecivini";
      repo = "d4v2";
      rev = "dda4511f218dd250e5973d7c27271f7228edc210";
      sha256 = "sha256-KV9Ofu4oqBkmuKD/LxO+nza0wcXiaJYg2RpdNr+Lmu0=";
    };

    hardeningDisable = ["format"];

    dontConfigure = true;

    patchPhase = ''
      patchShebangs .
      ln -s ${patoh}/*/libpatoh.a 3rdParty/patoh/libpatoh.a
      find . -type f -name "CMakeLists.txt" -exec sed -i 's/cmake_minimum_required(VERSION.*)/cmake_minimum_required(VERSION 3.10)/' {} +
    '';

    buildPhase = ''
      cd demo/compiler
      ./build.sh
    '';

    installPhase = ''
      install -m755 -D build/compiler $out/bin/${pname}
    '';

    meta = {
      homepage = "https://github.com/ecivini/d4v2";
      description = "D4";
      platforms = ["x86_64-linux"];
    };
  }
