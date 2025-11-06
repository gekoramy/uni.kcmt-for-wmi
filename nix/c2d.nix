{
  lib,
  stdenv,
  fetchurl,
  unzip,
}:
stdenv.mkDerivation rec {
  pname = "c2d";
  version = "2.20";

  nativeBuildInputs = [unzip];

  src = fetchurl {
    url = "http://reasoning.cs.ucla.edu/c2d/fetchme.php?${
      lib.pipe {
        n = "test";
        e = "noreply@test.com";
        o = "test";
        os = "Linux i386";
      }
      [
        (lib.mapAttrsToList (k: v: "${k}=${lib.escapeURL v}"))
        (lib.concatStringsSep "&")
      ]
    }";
    sha256 = "sha256-DqlZSkkjRTPNLqKojUx4jv+6TQ1gs/vXJMInrQR5g4Q=";
  };

  unpackPhase = ''
    unzip ${src}
  '';

  installPhase = ''
    install -m755 -D ${pname}_linux $out/bin/${pname}
  '';

  meta = {
    homepage = "http://reasoning.cs.ucla.edu/c2d";
    description = "TODO";
    platforms = ["x86_64-linux"];
  };
}
