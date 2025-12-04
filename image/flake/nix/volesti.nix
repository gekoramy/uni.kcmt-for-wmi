{
  stdenv,
  fetchFromGitHub,
  fetchFromGitLab,
  fetchzip,
  cmake,
  lp_solve,
}:
stdenv.mkDerivation {
  pname = "volesti_integrate";
  version = "0.1";

  nativeBuildInputs = [
    cmake
    lp_solve
  ];

  src = fetchFromGitHub {
    owner = "masinag";
    repo = "approximate-integration";
    rev = "ab3ba410296c7720c999572d40810f3f86023895";
    sha256 = "sha256-8Gng/7t6F43lQybpClxBNwzrvJ2+JDxxEoq999w8pDc=";
  };

  cmakeFlags = let
    exprtk = fetchFromGitHub {
      owner = "ArashPartow";
      repo = "exprtk";
      rev = "806c519c91fd08ba4fa19380dbf3f6e42de9e2d1";
      sha256 = "sha256-5/k+y3gNJeggfwXmtAVqmaiV+BXX+WKtWwZWcQSrQDM=";
    };
    volesti = fetchFromGitHub {
      owner = "GeomScale";
      repo = "volesti";
      rev = "ba0e697a414bda101c8010676cc929131da2f064";
      sha256 = "sha256-Y5RJE4mi7yM/+gdC0NN90gq9RCtng5ES7addIFODd0s=";
    };
    argparse = fetchFromGitHub {
      owner = "p-ranav";
      repo = "argparse";
      rev = "v3.2";
      sha256 = "sha256-w4IU8Yr+zPFOo7xR4YMHlqNJcEov4KU/ppDYrgsGlxM=";
    };
    eigen = fetchFromGitLab {
      owner = "libeigen";
      repo = "eigen";
      rev = "3.4.0";
      sha256 = "sha256-1/4xMetKMDOgZgzz3WMxfHUEpmdAm52RqZvz6i0mLEw=";
    };
    boost = fetchzip {
      url = "https://archives.boost.io/release/1.84.0/source/boost_1_84_0.tar.bz2";
      sha256 = "sha256-wtNL5NfnoUYJtW70eIYpEh+FkuuZWY+Pn0OGvIF65ic=";
    };
    lpsolve = fetchzip {
      url = "https://downloads.sourceforge.net/project/lpsolve/lpsolve/5.5.2.11/lp_solve_5.5.2.11_source.tar.gz";
      sha256 = "sha256-yXX9ZnWSFiLaFdVdmgM/Wbbi+sMA700nWqzM4g+O9VU=";
    };
  in [
    "-DFETCHCONTENT_SOURCE_DIR_EXPRTK=${exprtk}"
    "-DFETCHCONTENT_SOURCE_DIR_VOLESTI=${volesti}"
    "-DFETCHCONTENT_SOURCE_DIR_ARGPARSE=${argparse}"
    "-DFETCHCONTENT_SOURCE_DIR_ARGPARSE=${argparse}"
    "-DFETCHCONTENT_SOURCE_DIR_EIGEN=${eigen}"
    "-DFETCHCONTENT_SOURCE_DIR_BOOST=${boost}"
    "-DFETCHCONTENT_SOURCE_DIR_LPSOLVE=${lpsolve}"
  ];

  installPhase = ''
    cd ..
    install -m755 -D bin/volesti_integrate $out/bin/volesti_integrate
  '';

  meta = {
    homepage = "https://github.com/masinag/approximate-integration";
    platforms = ["x86_64-linux"];
  };
}
