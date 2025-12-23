{
  buildNpmPackage,
  kapowarr-react,
  ...
}:
buildNpmPackage {
  pname = "kapowarr-web";
  version = kapowarr-react.version;

  src = ./.;

  npmDepsHash = "sha256-CXXMoMLEpzkAlxSILD7xeWqV2vFD8S9Klxg7sir6QcM=";

  installPhase = ''
    runHook preInstall

    mkdir -p $out/share
    cp -a dist/static $out/share/kapowarr-web

    runHook postInstall
  '';
}
