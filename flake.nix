{
  description = "Nix fine-tuning data generator with built-in scraping";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        
        pythonEnv = pkgs.python311.withPackages (ps: with ps; [
          requests
          beautifulsoup4
          lxml
          pygithub
          tqdm
          pandas
        ]);

        generatorScript = pkgs.writeScriptBin "nix-finetune-generator" ''
          #!${pkgs.bash}/bin/bash
          export PATH="${pythonEnv}/bin:${pkgs.git}/bin:$PATH"
          exec ${pythonEnv}/bin/python ${./generator.py} "$@"
        '';

      in
      {
        packages = {
          default = generatorScript;
          generator = generatorScript;
        };

        apps = {
          default = {
            type = "app";
            program = "${generatorScript}/bin/nix-finetune-generator";
          };
        };

        devShells.default = pkgs.mkShell {
          buildInputs = [
            pythonEnv
            pkgs.git
            pkgs.gh
          ];

          shellHook = ''
            echo "Nix Fine-tuning Data Generator Development Shell"
            echo "Run: python generator.py --help"
          '';
        };
      }
    );
}
