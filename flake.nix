{
  inputs = {
    nixpkgs = {
      type = "github";
      owner = "NixOS";
      repo = "nixpkgs";
      ref = "nixos-unstable";
    };

    treefmt-nix = {
      type = "github";
      owner = "numtide";
      repo = "treefmt-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    systems = {
      type = "github";
      owner = "nix-systems";
      repo = "default-linux";
    };

    libgencomics = {
      type = "github";
      owner = "matt1432";
      repo = "LibgenComics";

      inputs = {
        nixpkgs.follows = "nixpkgs";
        treefmt-nix.follows = "treefmt-nix";
        systems.follows = "systems";
      };
    };
  };

  outputs = {
    self,
    systems,
    nixpkgs,
    treefmt-nix,
    libgencomics,
    ...
  }: let
    perSystem = attrs:
      nixpkgs.lib.genAttrs (import systems) (system:
        attrs (import nixpkgs {
          inherit system;
          overlays = [
            libgencomics.overlays.default
            self.overlays.default
          ];
          config.allowUnfreePredicate = pkg: builtins.elem pkg.pname ["rar"];
        }));
  in {
    overlays.default = final: _prev: let
      pyPkgs = final.python3Packages.override {
        overrides = pyFinal: _pyPrev: {
          inherit (final.python3Packages) libgencomics beautifulsoup4 requests idna;

          bencoding = pyFinal.callPackage ({
            # nix build inputs
            buildPythonPackage,
            fetchPypi,
            ...
          }: let
            pname = "bencoding";
            version = "0.2.6";
          in
            buildPythonPackage {
              inherit pname version;

              src = fetchPypi {
                inherit pname version;
                hash = "sha256-Q8zjHUhj4p1rxhFVHU6fJlK+KZXp1eFbRtg4PxgNREA=";
              };
            }) {};
        };
      };
    in {
      kapowarr = pyPkgs.callPackage ({
        # nix build inputs
        lib,
        buildPythonApplication,
        # deps
        rar,
        # python deps
        aiohttp,
        beautifulsoup4,
        bencoding, # from overrides
        cryptography,
        flask,
        flask-socketio,
        libgencomics,
        requests,
        setuptools,
        waitress,
        websocket-client,
        qbittorrent-api,
        ...
      }: let
        inherit (lib) getExe;
        inherit (builtins) fromTOML readFile;

        pyproject = fromTOML (readFile ./pyproject.toml);

        pname = "kapowarr";
        version = "${pyproject.project.version}+${self.shortRev or "dirty"}";
      in
        buildPythonApplication {
          format = "pyproject";
          inherit pname version;

          src = ./.;

          build-system = [setuptools];

          dependencies = [
            requests
            beautifulsoup4
            flask
            waitress
            cryptography
            bencoding
            aiohttp
            flask-socketio
            websocket-client
            libgencomics
            qbittorrent-api
          ];

          postPatch = ''
            # Disable PWA for now
            substituteInPlace ./src/backend/internals/settings.py \
                --replace-fail 'with open(filename, "w") as f:' "" \
                --replace-fail 'dump(manifest, f, indent=4)' ""

            substituteInPlace ./src/backend/implementations/converters.py \
                --replace-fail \
                    'exe = folder_path("backend", "lib", Constants.RAR_EXECUTABLES[platform])' \
                    'exe = "${getExe rar}"'
          '';

          meta = {
            inherit (rar.meta) platforms;
            mainProgram = pname;
            license = lib.licenses.gpl3Only;
            homepage = "https://casvt.github.io/Kapowarr";
            description = ''
              Kapowarr is a software to build and manage a comic book library,
              fitting in the *arr suite of software.
            '';
          };
        }) {};
    };

    packages = perSystem (pkgs: {
      kapowarr = pkgs.kapowarr;
      default = self.packages.${pkgs.system}.kapowarr;
    });

    formatter = perSystem (pkgs: let
      treefmtEval = treefmt-nix.lib.evalModule pkgs ./treefmt.nix;
    in
      treefmtEval.config.build.wrapper);

    devShells = perSystem (pkgs: {
      default = pkgs.mkShell {
        packages = with pkgs; [
          alejandra
          (python3.withPackages (_ps: pkgs.kapowarr.dependencies ++ [pkgs.kapowarr]))
        ];
      };
    });
  };
}
