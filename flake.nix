{
  description = "Production-ready Nix fine-tuning data generator with multi-arch Docker support";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        
        # Python environment with all required dependencies
        pythonEnv = pkgs.python311.withPackages (ps: with ps; [
          requests
          beautifulsoup4
          lxml
          pygithub
          tqdm
          pandas
        ]);

        # Wrapper script with proper environment setup
        generatorScript = pkgs.writeScriptBin "nix-finetune-generator" ''
          #!${pkgs.bash}/bin/bash
          set -euo pipefail
          
          # SSL certificates for HTTPS requests
          export SSL_CERT_FILE="${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt"
          export REQUESTS_CA_BUNDLE="${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt"
          
          # Ensure UTF-8 encoding
          export PYTHONIOENCODING="utf-8"
          export LANG="en_US.UTF-8"
          
          # Add tools to PATH
          export PATH="${pythonEnv}/bin:${pkgs.git}/bin:${pkgs.cacert}/bin:$PATH"
          
          # Run generator
          exec ${pythonEnv}/bin/python ${./generator.py} "$@"
        '';

        # Standalone API-only script (zero dependencies)
        simpleScript = pkgs.writeScriptBin "nix-finetune-simple" ''
          #!${pkgs.bash}/bin/bash
          set -euo pipefail
          
          export SSL_CERT_FILE="${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt"
          export PYTHONIOENCODING="utf-8"
          
          exec ${pkgs.python311}/bin/python ${./search_api_simple.py} "$@"
        '';

        # Docker image configuration
        dockerImage = pkgs.dockerTools.buildLayeredImage {
          name = "nix-finetune-generator";
          tag = "latest";
          
          contents = [
            pkgs.bash
            pkgs.coreutils
            pkgs.cacert
            pkgs.git
            pythonEnv
            generatorScript
            simpleScript
          ];
          
          config = {
            Cmd = [ "${generatorScript}/bin/nix-finetune-generator" "--help" ];
            WorkingDir = "/workspace";
            Env = [
              "SSL_CERT_FILE=${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt"
              "REQUESTS_CA_BUNDLE=${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt"
              "PYTHONIOENCODING=utf-8"
              "LANG=en_US.UTF-8"
              "PATH=/bin:${pythonEnv}/bin:${pkgs.git}/bin"
            ];
            Labels = {
              "org.opencontainers.image.title" = "Nix Fine-tuning Data Generator";
              "org.opencontainers.image.description" = "Generate training data for Nix-oriented LLMs";
              "org.opencontainers.image.licenses" = "MIT";
              "org.opencontainers.image.vendor" = "DeMoD LLC";
              "org.opencontainers.image.source" = "https://github.com/yourusername/nix-finetune-generator";
            };
          };
        };

      in
      {
        packages = {
          default = generatorScript;
          generator = generatorScript;
          simple = simpleScript;
          docker = dockerImage;
        };

        apps = {
          default = {
            type = "app";
            program = "${generatorScript}/bin/nix-finetune-generator";
          };
          
          simple = {
            type = "app";
            program = "${simpleScript}/bin/nix-finetune-simple";
          };
        };

        devShells.default = pkgs.mkShell {
          buildInputs = [
            pythonEnv
            pkgs.git
            pkgs.gh
            pkgs.cacert
            pkgs.ruff  # Modern Python linter/formatter
            pkgs.jq    # JSON processing
            pkgs.docker  # For building multi-arch images
          ];

          shellHook = ''
            export SSL_CERT_FILE="${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt"
            export REQUESTS_CA_BUNDLE="${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt"
            export PYTHONIOENCODING="utf-8"
            
            echo "╔═══════════════════════════════════════════════════════════════╗"
            echo "║  Nix Fine-tuning Data Generator - Development Environment    ║"
            echo "╚═══════════════════════════════════════════════════════════════╝"
            echo ""
            echo "Available commands:"
            echo "  python generator.py --help          # Full-featured generator"
            echo "  python search_api_simple.py --help  # API-only (fast)"
            echo "  ruff check .                        # Lint Python code"
            echo "  ruff format .                       # Format Python code"
            echo ""
            echo "Build Docker images:"
            echo "  nix build .#docker                  # Build Docker image"
            echo "  ./build-multiarch.sh                # Build multi-arch (x86_64/arm64)"
            echo ""
          '';
        };
      }
    );
}

