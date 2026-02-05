#!/usr/bin/env python3
"""
Nix Fine-tuning Data Generator with Built-in Scraping

Copyright (c) 2024-2025 DeMoD LLC
Licensed under the MIT License - see LICENSE file for details

Generates high-quality training data for Nix-oriented LLM fine-tuning
by scraping from multiple sources:
- nixpkgs repository (GitHub API)
- NixOS wiki
- Discourse forums
- Official search.nixos.org API
"""

import json
import csv
import re
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime
import time

try:
    import requests
    from bs4 import BeautifulSoup
    from github import Github
    from tqdm import tqdm
except ImportError as e:
    print(f"Error: Missing required dependency: {e}")
    print("Run this inside the Nix flake environment: nix develop")
    sys.exit(1)


@dataclass
class FineTuningExample:
    """Structure for a single training example"""
    prompt: str
    completion: str
    metadata: Dict = field(default_factory=dict)
    source: str = "manual"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class NixSearchAPIScraper:
    """Scrapes official NixOS search API for packages, options, and flakes"""
    
    def __init__(self):
        self.base_url = "https://search.nixos.org/backend"
        self.session = requests.Session()
        
        # Curated queries for comprehensive coverage
        self.package_queries = [
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
        
        self.option_queries = [
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
        
        self.flake_queries = [
            "flake-utils", "home-manager", "nixvim", "devos",
            "impermanence", "disko", "lanzaboote", "sops-nix",
            "nix-colors", "nur", "agenix", "nixos-hardware",
            "flake-parts", "nixpkgs", "crane", "fenix"
        ]
    
    def fetch_search(self, search_type: str, query: str, channel: str = "unstable") -> Optional[Dict]:
        """Fetch results from the NixOS search API"""
        params = {"channel": channel, "query": query}
        url = f"{self.base_url}/{search_type}"
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching {search_type} '{query}': {e}")
            return None
    
    def scrape_packages(self, max_per_query: int = 5) -> List[Dict]:
        """Scrape package information from search API"""
        results = []
        
        print("Scraping packages from search.nixos.org API...")
        for query in tqdm(self.package_queries, desc="Package queries"):
            data = self.fetch_search("packages", query)
            
            if data and "results" in data:
                for item in data["results"][:max_per_query]:
                    results.append({
                        "type": "package",
                        "attr_name": item.get("attr_name", "unknown"),
                        "pname": item.get("pname", "unknown"),
                        "version": item.get("version", "unknown"),
                        "description": item.get("description", ""),
                        "longDescription": item.get("longDescription"),
                        "licenses": item.get("licenses", []),
                        "platforms": item.get("platforms", [])
                    })
            
            time.sleep(0.2)  # Rate limiting
        
        return results
    
    def scrape_options(self, max_per_query: int = 5) -> List[Dict]:
        """Scrape NixOS options from search API"""
        results = []
        
        print("Scraping options from search.nixos.org API...")
        for query in tqdm(self.option_queries, desc="Option queries"):
            data = self.fetch_search("options", query)
            
            if data and "results" in data:
                for item in data["results"][:max_per_query]:
                    results.append({
                        "type": "option",
                        "name": item.get("name", "unknown"),
                        "description": item.get("description", ""),
                        "option_type": item.get("type", "unknown"),
                        "default": item.get("default"),
                        "example": item.get("example"),
                        "declarations": item.get("declarations", [])
                    })
            
            time.sleep(0.2)
        
        return results
    
    def scrape_flakes(self, max_per_query: int = 3) -> List[Dict]:
        """Scrape flake information from search API"""
        results = []
        
        print("Scraping flakes from search.nixos.org API...")
        for query in tqdm(self.flake_queries, desc="Flake queries"):
            data = self.fetch_search("flakes", query)
            
            if data and "results" in data:
                for item in data["results"][:max_per_query]:
                    results.append({
                        "type": "flake",
                        "name": item.get("name", "unknown"),
                        "description": item.get("description", ""),
                        "repo": item.get("repo", "unknown"),
                        "resolved": item.get("resolved")
                    })
            
            time.sleep(0.2)
        
        return results


class NixPackageScraper:
    """Scrapes Nix package definitions from nixpkgs"""
    
    def __init__(self, github_token: Optional[str] = None):
        self.session = requests.Session()
        self.github = Github(github_token) if github_token else None
        
    def scrape_package_files(self, max_packages: int = 100) -> List[Tuple[str, str, str]]:
        """Scrape package definitions from nixpkgs GitHub"""
        results = []
        
        if not self.github:
            print("Warning: No GitHub token provided. Using unauthenticated requests (limited).")
            return self._scrape_without_api(max_packages)
        
        try:
            repo = self.github.get_repo("NixOS/nixpkgs")
            
            # Search for default.nix files in pkgs directory
            query = "repo:NixOS/nixpkgs path:pkgs/ filename:default.nix"
            results_iter = self.github.search_code(query)
            
            print(f"Scraping package definitions from nixpkgs...")
            for i, result in enumerate(tqdm(results_iter[:max_packages])):
                if i >= max_packages:
                    break
                    
                try:
                    content = result.decoded_content.decode('utf-8')
                    pkg_name = Path(result.path).parent.name
                    
                    results.append((pkg_name, result.path, content))
                    time.sleep(0.1)  # Rate limiting
                    
                except Exception as e:
                    print(f"Error processing {result.path}: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error accessing GitHub API: {e}")
            
        return results
    
    def _scrape_without_api(self, max_packages: int) -> List[Tuple[str, str, str]]:
        """Fallback scraping method without GitHub API"""
        results = []
        
        # Popular packages to scrape as examples
        popular_pkgs = [
            "hello", "vim", "git", "python3", "nodejs", "gcc", 
            "postgresql", "redis", "nginx", "docker"
        ]
        
        base_url = "https://raw.githubusercontent.com/NixOS/nixpkgs/master/pkgs"
        
        for pkg in popular_pkgs[:max_packages]:
            try:
                # Try common locations
                for category in ["applications/misc", "tools/misc", "development/tools/misc"]:
                    url = f"{base_url}/{category}/{pkg}/default.nix"
                    response = self.session.get(url)
                    
                    if response.status_code == 200:
                        results.append((pkg, f"{category}/{pkg}/default.nix", response.text))
                        break
                        
                time.sleep(0.5)
                
            except Exception as e:
                continue
                
        return results


class NixWikiScraper:
    """Scrapes NixOS wiki for documentation and examples"""
    
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://nixos.wiki"
        
    def scrape_wiki_pages(self, topics: List[str]) -> List[Dict]:
        """Scrape specific wiki pages"""
        results = []
        
        for topic in tqdm(topics, desc="Scraping wiki pages"):
            try:
                url = f"{self.base_url}/wiki/{topic}"
                response = self.session.get(url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'lxml')
                content_div = soup.find('div', {'id': 'mw-content-text'})
                
                if not content_div:
                    continue
                
                # Extract code blocks
                code_blocks = content_div.find_all('pre')
                sections = content_div.find_all(['h2', 'h3'])
                
                for i, section in enumerate(sections):
                    section_title = section.get_text().strip()
                    
                    # Get content until next section
                    content_parts = []
                    for sibling in section.find_next_siblings():
                        if sibling.name in ['h2', 'h3']:
                            break
                        if sibling.name == 'pre':
                            content_parts.append(('code', sibling.get_text()))
                        elif sibling.name == 'p':
                            content_parts.append(('text', sibling.get_text()))
                    
                    if content_parts:
                        results.append({
                            'topic': topic,
                            'section': section_title,
                            'content': content_parts,
                            'url': url
                        })
                
                time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                print(f"Error scraping {topic}: {e}")
                continue
                
        return results


class NixDiscourseScraperr:
    """Scrapes Discourse forum for Q&A examples"""
    
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://discourse.nixos.org"
        
    def scrape_topics(self, category: str = "all", max_topics: int = 50) -> List[Dict]:
        """Scrape topics from Discourse"""
        results = []
        
        try:
            # Get latest topics
            url = f"{self.base_url}/latest.json"
            response = self.session.get(url)
            response.raise_for_status()
            
            topics_data = response.json()
            topics = topics_data.get('topic_list', {}).get('topics', [])
            
            for topic in tqdm(topics[:max_topics], desc="Scraping Discourse topics"):
                topic_id = topic.get('id')
                
                # Get full topic with posts
                topic_url = f"{self.base_url}/t/{topic_id}.json"
                topic_response = self.session.get(topic_url)
                
                if topic_response.status_code != 200:
                    continue
                
                topic_full = topic_response.json()
                posts = topic_full.get('post_stream', {}).get('posts', [])
                
                if len(posts) >= 2:  # Need question and answer
                    question = posts[0].get('cooked', '')
                    answer = posts[1].get('cooked', '') if len(posts) > 1 else ''
                    
                    # Clean HTML
                    question_text = BeautifulSoup(question, 'lxml').get_text()
                    answer_text = BeautifulSoup(answer, 'lxml').get_text()
                    
                    results.append({
                        'title': topic.get('title'),
                        'question': question_text,
                        'answer': answer_text,
                        'tags': topic.get('tags', []),
                        'url': f"{self.base_url}/t/{topic_id}"
                    })
                
                time.sleep(0.3)
                
        except Exception as e:
            print(f"Error scraping Discourse: {e}")
            
        return results


class NixFineTuningGenerator:
    """Main generator class with integrated scraping"""
    
    def __init__(self, github_token: Optional[str] = None):
        self.examples = []
        self.pkg_scraper = NixPackageScraper(github_token)
        self.wiki_scraper = NixWikiScraper()
        self.discourse_scraper = NixDiscourseScraperr()
        self.search_api_scraper = NixSearchAPIScraper()  # NEW: Official API scraper
        
    def add_example(self, prompt: str, completion: str, 
                   metadata: Dict = None, source: str = "manual"):
        """Add a training example"""
        self.examples.append(FineTuningExample(
            prompt=prompt,
            completion=completion,
            metadata=metadata or {},
            source=source
        ))
    
    def generate_from_packages(self, max_packages: int = 100):
        """Generate examples from scraped packages"""
        packages = self.pkg_scraper.scrape_package_files(max_packages)
        
        print(f"\nGenerating examples from {len(packages)} packages...")
        
        for pkg_name, path, content in tqdm(packages):
            # Extract key information
            lines = content.split('\n')
            
            # Basic package definition example
            self.add_example(
                prompt=f"Write a Nix derivation for the package '{pkg_name}'",
                completion=f"Here's the Nix derivation:\n\n```nix\n{content}\n```",
                metadata={
                    "type": "package_definition",
                    "package": pkg_name,
                    "path": path
                },
                source="nixpkgs"
            )
            
            # If contains version, create version-specific example
            version_match = re.search(r'version\s*=\s*"([^"]+)"', content)
            if version_match:
                version = version_match.group(1)
                self.add_example(
                    prompt=f"How do I specify the version for {pkg_name} in Nix?",
                    completion=f"You can specify the version using the `version` attribute:\n\n```nix\nversion = \"{version}\";\n```",
                    metadata={
                        "type": "package_version",
                        "package": pkg_name,
                        "version": version
                    },
                    source="nixpkgs"
                )
            
            # Extract fetchurl/fetchFromGitHub patterns
            if 'fetchurl' in content:
                fetch_section = re.search(r'fetchurl\s*{([^}]+)}', content, re.DOTALL)
                if fetch_section:
                    self.add_example(
                        prompt=f"How do I fetch a source tarball in Nix for {pkg_name}?",
                        completion=f"Use `fetchurl` with the URL and hash:\n\n```nix\nfetchurl {fetch_section.group(0)}\n```",
                        metadata={"type": "fetcher", "fetcher": "fetchurl"},
                        source="nixpkgs"
                    )
    
    def generate_from_wiki(self, topics: List[str] = None):
        """Generate examples from wiki pages"""
        if topics is None:
            topics = [
                "NixOS", "Flakes", "Overlays", "Home_Manager",
                "Docker", "Kubernetes", "Development_environment"
            ]
        
        wiki_data = self.wiki_scraper.scrape_wiki_pages(topics)
        
        print(f"\nGenerating examples from {len(wiki_data)} wiki sections...")
        
        for item in tqdm(wiki_data):
            topic = item['topic']
            section = item['section']
            content_parts = item['content']
            
            # Combine text and code
            text_parts = [c[1] for c in content_parts if c[0] == 'text']
            code_parts = [c[1] for c in content_parts if c[0] == 'code']
            
            if text_parts and code_parts:
                self.add_example(
                    prompt=f"How do I {section.lower()} in NixOS?",
                    completion=f"{' '.join(text_parts[:2])}\n\n```nix\n{code_parts[0]}\n```",
                    metadata={
                        "type": "wiki_guide",
                        "topic": topic,
                        "section": section
                    },
                    source="nixos_wiki"
                )
    
    def generate_from_discourse(self, max_topics: int = 50):
        """Generate examples from Discourse Q&A"""
        topics = self.discourse_scraper.scrape_topics(max_topics=max_topics)
        
        print(f"\nGenerating examples from {len(topics)} Discourse topics...")
        
        for topic in tqdm(topics):
            # Extract code blocks from answers
            code_blocks = re.findall(r'```(?:nix)?\n(.*?)```', topic['answer'], re.DOTALL)
            
            if code_blocks:
                self.add_example(
                    prompt=topic['title'],
                    completion=topic['answer'][:1000],  # Limit length
                    metadata={
                        "type": "qa",
                        "tags": topic.get('tags', []),
                        "has_code": len(code_blocks) > 0
                    },
                    source="discourse"
                )
    
    def generate_from_search_api(self, max_per_query: int = 5):
        """Generate examples from official NixOS search API"""
        
        # Scrape packages
        packages = self.search_api_scraper.scrape_packages(max_per_query=max_per_query)
        print(f"\nGenerating examples from {len(packages)} packages (search API)...")
        
        for pkg in tqdm(packages):
            attr = pkg.get("attr_name", "unknown")
            pname = pkg.get("pname", "unknown")
            version = pkg.get("version", "unknown")
            desc = pkg.get("description", "").rstrip(".")
            
            # Installation example
            self.add_example(
                prompt=f"How do I install {pname} on NixOS?",
                completion=f"To install {pname} ({desc}) system-wide:\n\n```nix\nenvironment.systemPackages = with pkgs; [ {attr} ];\n```\n\nCurrent version: {version}",
                metadata={
                    "type": "package_installation",
                    "package": pname,
                    "attr_name": attr,
                    "version": version
                },
                source="search_api"
            )
            
            # Attribute lookup example
            self.add_example(
                prompt=f"What is the NixOS package attribute for {pname.lower()}?",
                completion=f"The attribute is `{attr}` (pname: {pname}, version: {version}).\n\nDescription: {desc}",
                metadata={
                    "type": "package_attribute",
                    "package": pname
                },
                source="search_api"
            )
            
            # Quick config example
            if len(pname) > 2:  # Avoid very short names
                self.add_example(
                    prompt=f"Add {pname} to my NixOS config",
                    completion=f"Add `{attr}` to your `environment.systemPackages`:\n\n```nix\nenvironment.systemPackages = with pkgs; [\n  {attr}\n];\n```",
                    metadata={
                        "type": "quick_config",
                        "package": pname
                    },
                    source="search_api"
                )
        
        # Scrape options
        options = self.search_api_scraper.scrape_options(max_per_query=max_per_query)
        print(f"\nGenerating examples from {len(options)} options (search API)...")
        
        for opt in tqdm(options):
            name = opt.get("name", "unknown")
            desc = opt.get("description", "").rstrip(".")
            typ = opt.get("option_type", "unknown")
            default = opt.get("default", "none")
            example = opt.get("example")
            
            # How-to example
            lower_desc = desc[0].lower() + desc[1:] if desc else "configure this option"
            self.add_example(
                prompt=f"How do I {lower_desc} in NixOS?",
                completion=f"Set the option `{name}`:\n\n```nix\n{name} = true;  # or appropriate value\n```\n\nDescription: {desc}\nType: {typ}\nDefault: {default}" + 
                    (f"\n\nExample:\n```nix\n{name} = {json.dumps(example, indent=2)};\n```" if example else ""),
                metadata={
                    "type": "option_howto",
                    "option": name,
                    "option_type": typ
                },
                source="search_api"
            )
            
            # Option explanation
            self.add_example(
                prompt=f"What is the NixOS option {name} for?",
                completion=f"The `{name}` option {lower_desc}.\n\nType: {typ}\nDefault: {default}" +
                    (f"\n\nExample value: `{json.dumps(example)}`" if example else ""),
                metadata={
                    "type": "option_explanation",
                    "option": name
                },
                source="search_api"
            )
        
        # Scrape flakes
        flakes = self.search_api_scraper.scrape_flakes(max_per_query=3)
        print(f"\nGenerating examples from {len(flakes)} flakes (search API)...")
        
        for flake in tqdm(flakes):
            name = flake.get("name", "unknown")
            desc = flake.get("description", "").rstrip(".")
            repo = flake.get("repo", "unknown")
            
            # Flake usage example
            self.add_example(
                prompt=f"How do I use the {name} flake in NixOS?",
                completion=f"{name} provides: {desc}\n\nRepository: {repo}\n\nAdd as input in your `flake.nix`:\n\n```nix\ninputs.{name}.url = \"github:{repo}\";\n```\n\nThen use its outputs in your configuration (e.g., overlays, NixOS modules, packages).",
                metadata={
                    "type": "flake_usage",
                    "flake": name,
                    "repo": repo
                },
                source="search_api"
            )
            
            # Flake description
            self.add_example(
                prompt=f"What is the {name} flake?",
                completion=f"{desc}\n\nSource: github:{repo}\n\nThis is a Nix flake that can be used as an input in your flake-based NixOS configuration or development environment.",
                metadata={
                    "type": "flake_description",
                    "flake": name
                },
                source="search_api"
            )
    
    def add_manual_examples(self):
        """Add curated manual examples for common patterns"""
        
        # Flake template
        self.add_example(
            prompt="Create a basic Nix flake template",
            completion="""Here's a basic Nix flake template:

```nix
{
  description = "A basic flake";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        packages.default = pkgs.hello;
        
        devShells.default = pkgs.mkShell {
          buildInputs = [ pkgs.hello ];
        };
      }
    );
}
```""",
            metadata={"type": "template", "category": "flake"},
            source="manual"
        )
        
        # Overlay example
        self.add_example(
            prompt="How do I create a Nix overlay to modify a package?",
            completion="""Overlays allow you to customize packages. Here's an example:

```nix
final: prev: {
  # Override an existing package
  mypackage = prev.mypackage.overrideAttrs (oldAttrs: {
    version = "1.2.3";
    src = prev.fetchurl {
      url = "https://example.com/mypackage-1.2.3.tar.gz";
      sha256 = "...";
    };
  });
  
  # Add a new package
  newpackage = prev.callPackage ./newpackage.nix { };
}
```

Use it in your configuration:

```nix
nixpkgs.overlays = [ (import ./overlay.nix) ];
```""",
            metadata={"type": "guide", "category": "overlay"},
            source="manual"
        )
    
    def export_jsonl(self, filename: str, format: str = "openai"):
        """Export to JSONL format"""
        output_path = Path(filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for example in self.examples:
                if format == "openai":
                    entry = {
                        "messages": [
                            {"role": "user", "content": example.prompt},
                            {"role": "assistant", "content": example.completion}
                        ]
                    }
                elif format == "anthropic":
                    entry = {
                        "prompt": example.prompt,
                        "completion": example.completion
                    }
                else:
                    entry = asdict(example)
                
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        
        print(f"\nExported {len(self.examples)} examples to {output_path}")
    
    def export_csv(self, filename: str):
        """Export to CSV format"""
        output_path = Path(filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['prompt', 'completion', 'source', 'metadata', 'timestamp'])
            
            for example in self.examples:
                writer.writerow([
                    example.prompt,
                    example.completion,
                    example.source,
                    json.dumps(example.metadata),
                    example.timestamp
                ])
        
        print(f"Exported {len(self.examples)} examples to {output_path}")
    
    def generate_statistics(self) -> Dict:
        """Generate statistics about the dataset"""
        stats = {
            "total_examples": len(self.examples),
            "by_source": {},
            "by_type": {},
            "avg_prompt_length": 0,
            "avg_completion_length": 0
        }
        
        for example in self.examples:
            # Count by source
            stats["by_source"][example.source] = stats["by_source"].get(example.source, 0) + 1
            
            # Count by type
            ex_type = example.metadata.get("type", "unknown")
            stats["by_type"][ex_type] = stats["by_type"].get(ex_type, 0) + 1
            
            # Length statistics
            stats["avg_prompt_length"] += len(example.prompt)
            stats["avg_completion_length"] += len(example.completion)
        
        if len(self.examples) > 0:
            stats["avg_prompt_length"] //= len(self.examples)
            stats["avg_completion_length"] //= len(self.examples)
        
        return stats


def main():
    parser = argparse.ArgumentParser(
        description="Generate fine-tuning data for Nix-oriented LLMs"
    )
    parser.add_argument(
        "--output", "-o",
        default="nix_training_data.jsonl",
        help="Output file path (default: nix_training_data.jsonl)"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["openai", "anthropic", "generic"],
        default="openai",
        help="Output format (default: openai)"
    )
    parser.add_argument(
        "--github-token", "-g",
        help="GitHub personal access token for API access"
    )
    parser.add_argument(
        "--max-packages", "-p",
        type=int,
        default=50,
        help="Maximum number of packages to scrape (default: 50)"
    )
    parser.add_argument(
        "--max-discourse", "-d",
        type=int,
        default=30,
        help="Maximum Discourse topics to scrape (default: 30)"
    )
    parser.add_argument(
        "--skip-packages",
        action="store_true",
        help="Skip package scraping"
    )
    parser.add_argument(
        "--skip-wiki",
        action="store_true",
        help="Skip wiki scraping"
    )
    parser.add_argument(
        "--skip-discourse",
        action="store_true",
        help="Skip Discourse scraping"
    )
    parser.add_argument(
        "--skip-search-api",
        action="store_true",
        help="Skip search.nixos.org API scraping"
    )
    parser.add_argument(
        "--search-api-only",
        action="store_true",
        help="Only use search.nixos.org API (fastest, most reliable)"
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help="Also export as CSV"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print statistics about generated data"
    )
    
    args = parser.parse_args()
    
    print("=== Nix Fine-tuning Data Generator ===\n")
    
    generator = NixFineTuningGenerator(github_token=args.github_token)
    
    # Add manual examples
    print("Adding manual examples...")
    generator.add_manual_examples()
    
    # Search API only mode (fastest and most reliable)
    if args.search_api_only:
        print("\n🚀 Using search.nixos.org API only (fast mode)")
        generator.generate_from_search_api(max_per_query=args.max_packages // 10)
    else:
        # Scrape and generate from different sources
        if not args.skip_search_api:
            generator.generate_from_search_api(max_per_query=5)
        
        if not args.skip_packages:
            generator.generate_from_packages(max_packages=args.max_packages)
        
        if not args.skip_wiki:
            generator.generate_from_wiki()
        
        if not args.skip_discourse:
            generator.generate_from_discourse(max_topics=args.max_discourse)
    
    # Export data
    print("\nExporting data...")
    generator.export_jsonl(args.output, format=args.format)
    
    if args.csv:
        csv_path = Path(args.output).with_suffix('.csv')
        generator.export_csv(str(csv_path))
    
    # Print statistics
    if args.stats:
        stats = generator.generate_statistics()
        print("\n=== Dataset Statistics ===")
        print(f"Total examples: {stats['total_examples']}")
        print(f"\nBy source:")
        for source, count in stats['by_source'].items():
            print(f"  {source}: {count}")
        print(f"\nBy type:")
        for ex_type, count in stats['by_type'].items():
            print(f"  {ex_type}: {count}")
        print(f"\nAverage prompt length: {stats['avg_prompt_length']} chars")
        print(f"Average completion length: {stats['avg_completion_length']} chars")
    
    print("\n✓ Done!")


if __name__ == "__main__":
    main()
