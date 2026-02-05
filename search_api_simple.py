#!/usr/bin/env python3
"""
Standalone NixOS Search API Fine-tuning Data Generator

Copyright (c) 2024-2025 DeMoD LLC
Licensed under the MIT License - see LICENSE file for details

Simple, dependency-free script that uses only the Python standard library
to generate fine-tuning data from the official search.nixos.org API.

Usage:
    python search_api_simple.py [--output FILE] [--channel unstable|24.05|23.11]
"""

import json
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
import argparse

# Base URL for search.nixos.org backend
BASE_URL = "https://search.nixos.org/backend"

# System prompt for all examples (OpenAI format)
SYSTEM_PROMPT = "You are a knowledgeable assistant specialized in NixOS and the Nix package manager. Provide accurate, concise configuration snippets and explanations using valid Nix syntax."

# Curated queries for comprehensive coverage
PACKAGE_QUERIES = [
    "firefox", "chromium", "google-chrome", "brave", "librewolf",
    "vim", "neovim", "emacs", "helix", "vscode", "zed",
    "tmux", "zellij", "htop", "btop", "starship",
    "git", "curl", "ripgrep", "fd", "jq", "fzf",
    "python3", "nodejs", "go", "rustc", "zig", "gcc",
    "nginx", "caddy", "apache-httpd", "traefik",
    "steam", "wine", "lutris", "gamescope", "heroic",
    "tailscale", "wireguard", "zerotierone", "openvpn",
    "podman", "docker", "libvirt", "virt-manager", "kubernetes"
]

OPTION_QUERIES = [
    "services.openssh", "sshd", "ssh",
    "services.nginx", "services.caddy", "services.httpd",
    "services.postgresql", "services.mysql", "services.redis",
    "fonts", "fontconfig",
    "i18n", "time.timeZone", "locale",
    "boot.loader", "grub", "systemd-boot",
    "users.users", "users.mutableUsers", "security.sudo",
    "networking.networkmanager", "networking.firewall",
    "sound", "hardware.pulseaudio", "services.pipewire",
    "services.xserver", "desktopManager", "displayManager", "wayland",
    "virtualisation.podman", "virtualisation.docker", "virtualisation.libvirtd",
    "services.tailscale", "networking.wireguard", "nix.settings"
]

FLAKE_QUERIES = [
    "flake-utils", "home-manager", "nixvim", "devos",
    "impermanence", "disko", "lanzaboote", "sops-nix",
    "nix-colors", "nur", "agenix", "nixos-hardware",
    "flake-parts", "nixpkgs", "crane", "fenix"
]


def fetch_search(search_type: str, query: str, channel: str = "unstable"):
    """Fetch JSON results from search.nixos.org API using stdlib urllib"""
    params = {"channel": channel, "query": query}
    url = f"{BASE_URL}/{search_type}?{urllib.parse.urlencode(params)}"
    
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = response.read()
            return json.loads(data)
    except urllib.error.HTTPError as e:
        print(f"HTTP ERROR fetching {search_type} '{query}': {e.code} {e.reason}")
    except urllib.error.URLError as e:
        print(f"URL ERROR fetching {search_type} '{query}': {e.reason}")
    except json.JSONDecodeError as e:
        print(f"JSON decode error for {search_type} '{query}': {e}")
    except Exception as e:
        print(f"Unexpected error fetching {search_type} '{query}': {e}")
    
    return None


def generate_package_examples(pkg: dict):
    """Generate training examples for a package"""
    attr = pkg.get("attr_name", "unknown")
    pname = pkg.get("pname", "unknown")
    version = pkg.get("version", "unknown")
    desc = pkg.get("description", "").rstrip(".")
    
    examples = []
    
    # Installation example
    q = f"How do I install {pname} on NixOS?"
    a = f"To install {pname} ({desc}) system-wide:\n\n```nix\nenvironment.systemPackages = with pkgs; [ {attr} ];\n```\n\nCurrent version: {version}"
    examples.append({
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": q},
            {"role": "assistant", "content": a}
        ]
    })
    
    # Attribute lookup
    q = f"What is the NixOS package attribute for {pname.lower()}?"
    a = f"The attribute is `{attr}` (pname: {pname}, version: {version}).\n\nDescription: {desc}"
    examples.append({
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": q},
            {"role": "assistant", "content": a}
        ]
    })
    
    # Quick config
    q = f"Add {pname} to my NixOS config"
    a = f"Add `{attr}` to your `environment.systemPackages`:\n\n```nix\nenvironment.systemPackages = with pkgs; [\n  {attr}\n];\n```"
    examples.append({
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": q},
            {"role": "assistant", "content": a}
        ]
    })
    
    return examples


def generate_option_examples(opt: dict):
    """Generate training examples for a NixOS option"""
    name = opt.get("name", "unknown")
    desc = opt.get("description", "").rstrip(".")
    typ = opt.get("type", "unknown")
    default = opt.get("default", "none")
    example = opt.get("example")
    
    examples = []
    
    # How-to example
    lower_desc = desc[0].lower() + desc[1:] if desc else "configure this option"
    q = f"How do I {lower_desc} in NixOS?"
    a = f"Set the option `{name}`:\n\n```nix\n{name} = true;  # or appropriate value\n```\n\nDescription: {desc}\nType: {typ}\nDefault: {default}"
    if example is not None:
        a += f"\n\nExample:\n```nix\n{name} = {json.dumps(example, indent=2)};\n```"
    examples.append({
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": q},
            {"role": "assistant", "content": a}
        ]
    })
    
    # Option explanation
    q = f"What is the NixOS option {name} for?"
    a = f"The `{name}` option {lower_desc}.\n\nType: {typ}\nDefault: {default}"
    if example is not None:
        a += f"\n\nExample value: `{json.dumps(example)}`"
    examples.append({
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": q},
            {"role": "assistant", "content": a}
        ]
    })
    
    return examples


def generate_flake_examples(flake: dict):
    """Generate training examples for a flake"""
    name = flake.get("name", "unknown")
    desc = flake.get("description", "").rstrip(".")
    repo = flake.get("repo", "unknown")
    
    examples = []
    
    # Flake usage
    q = f"How do I use the {name} flake in NixOS?"
    a = f"{name} provides: {desc}\n\nRepository: {repo}\n\nAdd as input in your `flake.nix`:\n\n```nix\ninputs.{name}.url = \"github:{repo}\";\n```\n\nThen use its outputs in your configuration (e.g., overlays, NixOS modules, packages)."
    examples.append({
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": q},
            {"role": "assistant", "content": a}
        ]
    })
    
    # Flake description
    q = f"What is the {name} flake?"
    a = f"{desc}\n\nSource: github:{repo}\n\nThis is a Nix flake that can be used as an input in your flake-based NixOS configuration or development environment."
    examples.append({
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": q},
            {"role": "assistant", "content": a}
        ]
    })
    
    return examples


def generate_dataset(output_file: str, channel: str = "unstable", max_per_query: int = 5):
    """Generate complete dataset from search API"""
    all_examples = []
    
    # Process packages
    print(f"Fetching packages (channel: {channel})...")
    for query in PACKAGE_QUERIES:
        print(f"  - {query}")
        data = fetch_search("packages", query, channel)
        
        if data and "results" in data:
            for item in data["results"][:max_per_query]:
                all_examples.extend(generate_package_examples(item))
    
    # Process options
    print(f"\nFetching options (channel: {channel})...")
    for query in OPTION_QUERIES:
        print(f"  - {query}")
        data = fetch_search("options", query, channel)
        
        if data and "results" in data:
            for item in data["results"][:max_per_query]:
                all_examples.extend(generate_option_examples(item))
    
    # Process flakes
    print(f"\nFetching flakes...")
    for query in FLAKE_QUERIES:
        print(f"  - {query}")
        data = fetch_search("flakes", query, channel)
        
        if data and "results" in data:
            for item in data["results"][:3]:  # Fewer per flake query
                all_examples.extend(generate_flake_examples(item))
    
    # Write to file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        for ex in all_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    
    print(f"\n✓ Generated {len(all_examples)} training examples → {output_path.absolute()}")
    
    # Print statistics
    print("\nDataset Statistics:")
    print(f"  Total examples: {len(all_examples)}")
    print(f"  Estimated packages: {len(PACKAGE_QUERIES)} queries × {max_per_query} × 3 examples")
    print(f"  Estimated options: {len(OPTION_QUERIES)} queries × {max_per_query} × 2 examples")
    print(f"  Estimated flakes: {len(FLAKE_QUERIES)} queries × 3 × 2 examples")


def main():
    parser = argparse.ArgumentParser(
        description="Generate NixOS fine-tuning data from search.nixos.org API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
  %(prog)s --output my_dataset.jsonl
  %(prog)s --channel 24.05
  %(prog)s --output datasets/stable.jsonl --channel 24.05
        """
    )
    
    parser.add_argument(
        "--output", "-o",
        default="nixos_search_api_data.jsonl",
        help="Output JSONL file (default: nixos_search_api_data.jsonl)"
    )
    
    parser.add_argument(
        "--channel", "-c",
        default="unstable",
        choices=["unstable", "24.05", "23.11", "24.11"],
        help="NixOS channel (default: unstable)"
    )
    
    parser.add_argument(
        "--max-per-query", "-m",
        type=int,
        default=5,
        help="Maximum results per query (default: 5)"
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("NixOS Search API Fine-tuning Data Generator")
    print("Copyright (c) 2024-2025 DeMoD LLC - MIT License")
    print("=" * 70)
    print()
    
    generate_dataset(args.output, args.channel, args.max_per_query)


if __name__ == "__main__":
    main()
