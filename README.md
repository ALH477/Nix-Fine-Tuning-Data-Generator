# Nix Fine-Tuning Data Generator

A comprehensive tool for generating high-quality fine-tuning datasets for Nix-oriented language models. Includes built-in scraping from nixpkgs, NixOS wiki, Discourse forums, and the official search.nixos.org API.

**License**: MIT (Copyright © 2024-2025 DeMoD LLC)

## Overview

This tool automates the creation of training datasets for fine-tuning large language models on Nix and NixOS. It aggregates examples from multiple authoritative sources and formats them for use with popular fine-tuning platforms.

## Features

**Data Sources**
- Official search.nixos.org API for packages, options, and flakes
- nixpkgs repository for package definitions and build instructions
- NixOS wiki for configuration guides and documentation
- Discourse forums for community questions and solutions
- Curated manual examples for common patterns

**Export Capabilities**
- OpenAI fine-tuning format (messages array)
- Anthropic fine-tuning format (prompt/completion pairs)
- Generic format with full metadata
- CSV export for analysis and filtering

**Performance**
- Fast mode generates 400+ examples in approximately 30 seconds
- Comprehensive mode generates 2000+ examples from all sources
- Respectful rate limiting to avoid overloading services
- Progress tracking and detailed statistics

## Quick Start

### Prerequisites

- Nix package manager with flakes enabled
- Python 3.6+ (for standalone script)
- Optional: GitHub personal access token for enhanced package scraping

### Installation and Basic Usage

Using Nix flakes (recommended):

```bash
# Clone or navigate to the project directory
cd nix-finetune-generator

# Run with default settings
nix run

# Fast mode using only the official API
nix run -- --search-api-only

# Specify output file and format
nix run -- --output my_dataset.jsonl --format openai
```

Using the standalone script (no Nix required):

```bash
# Basic usage
python search_api_simple.py

# Custom output and channel
python search_api_simple.py --output data.jsonl --channel 24.05
```

### Interactive Setup

For a guided setup experience, run the quickstart wizard:

```bash
./quickstart.sh
```

## Usage

### Command Line Options

```
--output, -o FILE          Output file path (default: nix_training_data.jsonl)
--format, -f FORMAT        Export format: openai, anthropic, or generic
--github-token TOKEN       GitHub API token for enhanced package scraping
--max-packages N           Maximum number of packages to scrape (default: 50)
--max-discourse N          Maximum Discourse topics to scrape (default: 30)
--skip-packages            Exclude nixpkgs scraping
--skip-wiki                Exclude wiki scraping
--skip-discourse           Exclude Discourse scraping
--skip-search-api          Exclude search.nixos.org API
--search-api-only          Use only search API (fastest mode)
--csv                      Also export data as CSV
--stats                    Display generation statistics
```

### Common Usage Patterns

Fast API-only generation (recommended for quick iteration):

```bash
nix run -- --search-api-only --stats
```

Balanced dataset with multiple sources:

```bash
nix run -- \
  --output datasets/balanced.jsonl \
  --max-packages 50 \
  --max-discourse 30 \
  --csv --stats
```

Large production dataset with GitHub authentication:

```bash
export GITHUB_TOKEN=ghp_your_token_here

nix run -- \
  --github-token $GITHUB_TOKEN \
  --output datasets/production.jsonl \
  --max-packages 300 \
  --max-discourse 100 \
  --format openai \
  --csv --stats
```

Selective source usage:

```bash
# API only, exclude other sources
nix run -- --skip-packages --skip-wiki --skip-discourse

# Packages and wiki only
nix run -- --skip-discourse --max-packages 100
```

## Data Sources

### 1. Official Search API (Recommended)

The search.nixos.org API provides fast, reliable access to official NixOS data:

- **Packages**: 40+ popular packages including browsers, editors, development tools, and servers
- **Options**: 30+ NixOS configuration options covering services, boot, networking, and more
- **Flakes**: 15+ essential flakes for home-manager, development environments, and system configuration

**Advantages**: Official data source, fast execution (~30 seconds), no GitHub token required, structured and consistent format.

### 2. nixpkgs Repository

Direct scraping from the nixpkgs GitHub repository provides:
- Complete package derivations with build instructions
- Version specifications and update patterns
- Source fetchers (fetchurl, fetchFromGitHub, fetchgit)
- Dependency declarations and build phases
- Package metadata and licensing information

### 3. NixOS Wiki

Community-maintained documentation covering:
- System configuration guides and best practices
- Flake templates and usage patterns
- Overlay creation and package customization
- Home Manager integration
- Service configuration examples
- Development environment setup

### 4. Discourse Forums

Community question-and-answer content including:
- Troubleshooting common issues
- Real-world configuration examples
- Best practices from experienced users
- Solutions to edge cases
- Package-specific guidance

### 5. Manual Curated Examples

Hand-crafted high-quality examples:
- Standard flake templates for common use cases
- Overlay patterns and techniques
- Frequently used configuration snippets
- Validated best practices

## Output Formats

### OpenAI Format

Structured as message arrays suitable for GPT-3.5 and GPT-4 fine-tuning:

```json
{
  "messages": [
    {"role": "user", "content": "prompt"},
    {"role": "assistant", "content": "completion"}
  ]
}
```

### Anthropic Format

Simple prompt-completion pairs for Claude fine-tuning:

```json
{
  "prompt": "prompt text",
  "completion": "completion text"
}
```

### Generic Format

Comprehensive format with full metadata for custom processing:

```json
{
  "prompt": "prompt",
  "completion": "completion",
  "metadata": {...},
  "source": "nixpkgs",
  "timestamp": "2024-..."
}
```

## GitHub Authentication

A GitHub personal access token enables higher rate limits for nixpkgs scraping (5,000 requests/hour vs 60 unauthenticated).

### Creating a Token

1. Navigate to GitHub Settings → Developer settings → Personal access tokens
2. Select "Generate new token (classic)"
3. Enable the `public_repo` scope
4. Copy the generated token

### Using the Token

```bash
export GITHUB_TOKEN=ghp_your_token_here
nix run -- --github-token $GITHUB_TOKEN
```

## Workflow Examples

### Development Iteration

```bash
# Enter development environment
nix develop

# Generate test dataset
python generator.py --max-packages 10 --stats

# Review output and adjust parameters
# Repeat until satisfied

# Generate final dataset
python generator.py --max-packages 100 --csv --stats
```

### Production Dataset Creation

```bash
# Set environment variables
export GITHUB_TOKEN=ghp_your_token_here

# Generate comprehensive dataset
nix run -- \
  --github-token $GITHUB_TOKEN \
  --output production.jsonl \
  --max-packages 200 \
  --max-discourse 100 \
  --csv \
  --stats

# Verify output
cat production.jsonl | wc -l
```

## Development

### Project Structure

```
.
├── flake.nix              Nix flake definition with dependencies
├── generator.py           Main generation script (full-featured)
├── search_api_simple.py   Standalone script (zero dependencies)
├── README.md              Primary documentation
├── ARCHITECTURE.md        Technical architecture details
├── LICENSE                MIT License
└── datasets/              Generated output (created on first run)
```

### Adding Custom Data Sources

Implement a new scraper class following the established pattern:

```python
class CustomScraper:
    def scrape_data(self) -> List[Dict]:
        # Implementation here
        pass
```

Add the scraper to the generator:

```python
def generate_from_custom(self):
    data = self.custom_scraper.scrape_data()
    # Process and generate examples
```

Include a CLI option in the main() function.

### Adding Manual Examples

Edit the `add_manual_examples()` method to include custom curated content:

```python
def add_manual_examples(self):
    self.add_example(
        prompt="Your question",
        completion="Your answer with code",
        metadata={"type": "custom"},
        source="manual"
    )
```

## Best Practices

**Dataset Balance**
- Include examples from multiple sources for diversity
- Start with small datasets (50-100 examples) for initial testing
- Scale to larger datasets (500-2000+ examples) for production

**Source Configuration**
- Use GitHub authentication token for optimal package scraping performance
- Begin with search API for rapid iteration
- Add additional sources incrementally as needed

**Quality Assurance**
- Review sample outputs before large-scale generation
- Use metadata fields to filter specific example types
- Validate examples match your intended use case
- Monitor statistics to ensure balanced representation

**Performance Optimization**
- Use `--search-api-only` for fastest results
- Reduce `--max-packages` and `--max-discourse` during development
- Implement delays between requests to avoid rate limiting
- Consider caching for repeated runs

## Troubleshooting

### Rate Limiting Issues

If encountering GitHub API rate limits:
```bash
# Use search API exclusively (no GitHub token required)
nix run -- --search-api-only

# Or obtain a GitHub personal access token
# Visit: https://github.com/settings/tokens
# Required scope: public_repo
export GITHUB_TOKEN=ghp_your_token
```

### Memory Constraints

For large dataset generation:
- Process in smaller batches using `--max-packages` and `--max-discourse`
- Use `--skip-*` flags to disable resource-intensive sources
- Ensure adequate system memory (4GB+ recommended for large runs)

### Dependency Issues

If imports fail within the Nix environment:
```bash
# Ensure proper environment activation
nix develop

# Verify all dependencies are available
python -c "import requests, bs4, github, tqdm"
```

For standalone script dependency issues:
```bash
# Verify Python version (3.6+ required)
python --version

# Standalone script uses only stdlib
python search_api_simple.py
```

## License

This project is licensed under the MIT License.

**Copyright © 2024-2025 DeMoD LLC**

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

See the LICENSE file for complete terms.

## Attribution and Compliance

When using datasets generated by this tool:

**Source Attribution**
- Attribution to this project is appreciated but not required
- Ensure compliance with upstream data source terms:
  - GitHub Terms of Service (nixpkgs repository access)
  - NixOS Wiki licensing terms
  - Discourse forum terms of service
  - search.nixos.org API terms of use

**Fine-Tuning Platforms**
- Review and comply with your LLM provider's acceptable use policies
- Verify dataset licensing compatibility with your intended use case

## Contributing

Contributions are welcome. Areas for development:

**Data Sources**
- Additional scraping targets (GitHub Issues, Reddit, etc.)
- Enhanced existing scrapers
- New curated example categories

**Quality Improvements**
- Advanced filtering algorithms
- Deduplication enhancements
- Example validation logic
- Quality scoring systems

**Features**
- Additional export format support
- Improved progress tracking
- Enhanced statistics and reporting
- Performance optimizations

**Documentation**
- Usage examples and tutorials
- Architecture documentation
- Integration guides
- Best practices documentation

## Resources

**NixOS Ecosystem**
- [nixpkgs Repository](https://github.com/NixOS/nixpkgs)
- [NixOS Wiki](https://nixos.wiki)
- [NixOS Discourse](https://discourse.nixos.org)
- [NixOS Search](https://search.nixos.org)
- [Nix Manual](https://nixos.org/manual/nix/stable/)

**Fine-Tuning Platforms**
- [OpenAI Fine-Tuning](https://platform.openai.com/docs/guides/fine-tuning)
- [Anthropic Claude](https://console.anthropic.com)

## Support

For assistance:

1. Review this README and supplementary documentation
2. Check ARCHITECTURE.md for technical details
3. Examine example scripts in examples.sh
4. Consult QUICK_REFERENCE.md for command syntax

For issues and feature requests, please refer to the project repository.
