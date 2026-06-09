{
  description = "Daktari - assist in setting up and maintaining developer environments";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    { self, nixpkgs, flake-utils }:
    let
      # Single source of truth: read the version from the same file the
      # automated release (bumpversion) rewrites. There is no second place to
      # update, so the flake's version always matches the source it builds.
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

          # Use the flake's own source tree. No fetchFromGitHub and no src hash
          # to maintain - the consumer's flake.lock pins the revision for us.
          src = self;

          build-system = [ py.setuptools ];

          # requirements.txt pins exact versions (==); use nixpkgs' versions
          # instead of trying to match those pins.
          pythonRelaxDeps = true;

          dependencies =
            with py;
            [
              ansicolors
              distro
              pyfiglet
              importlib-resources
              packaging
              setuptools
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

          # Tests are colocated with the source and expect to run with the
          # daktari/ working directory (see CLAUDE.md); they are not part of
          # the packaged build. Validate the install via an import instead.
          doCheck = false;
          pythonImportsCheck = [ "daktari" ];

          meta = {
            description = "Assist in setting up and maintaining developer environments";
            homepage = "https://github.com/genio-learn/daktari";
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
      # System-independent overlay so the genio flake can pull daktari in as
      # `pkgs.daktari` after adding this flake as an input.
      overlays.default = final: _prev: {
        daktari = mkDaktari final;
      };
    };
}
