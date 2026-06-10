{
  description = "Daktari - assist in setting up and maintaining developer environments";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    { self, nixpkgs, flake-utils }:
    let
      version = (builtins.fromTOML (builtins.readFile ./pyproject.toml)).project.version;

      mkDaktari =
        pkgs:
        let
          inherit (pkgs) lib stdenv;
          py = pkgs.python3.pkgs;
        in
        py.buildPythonApplication {
          pname = "daktari";
          inherit version;
          pyproject = true;

          src = self;

          build-system = [ py.setuptools ];

          # Use nixpkgs' versions rather than the == pins in requirements.txt.
          pythonRelaxDeps = true;

          dependencies =
            with py;
            [
              ansicolors
              distro
              pyfiglet
              importlib-resources
              packaging
              requests
              responses
              semver
              python-hosts
              pyyaml
              types-pyyaml
              requests-unixsocket
              dpath
              pyopenssl
              types-pyopenssl
              pyclip
              urllib3
            ]
            ++ lib.optionals stdenv.hostPlatform.isDarwin [
              pyobjc-core
              pyobjc-framework-Cocoa
            ];

          # Tests need the daktari/ working directory; not run as part of packaging.
          doCheck = false;
          pythonImportsCheck = [ "daktari" ];

          meta = {
            description = "Assist in setting up and maintaining developer environments";
            homepage = "https://github.com/genio-learn/daktari";
            changelog = "https://github.com/genio-learn/daktari/releases/tag/v${version}";
            license = lib.licenses.mit;
            mainProgram = "daktari";
          };
        };
    in
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        daktari = mkDaktari pkgs;
      in
      {
        packages.default = daktari;
        packages.daktari = daktari;
        apps.default = flake-utils.lib.mkApp { drv = daktari; };
      }
    )
    // {
      overlays.default = final: _prev: {
        daktari = mkDaktari final;
      };
    };
}
