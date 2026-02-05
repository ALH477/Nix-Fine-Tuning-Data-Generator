# Architecture Overview

## System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    Nix Flake Environment                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Python 3.11 + Dependencies                               │  │
│  │  - requests, beautifulsoup4, pygithub, tqdm, pandas      │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    generator.py (Main Script)                   │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐ │
│  │ NixPackage      │  │ NixWiki         │  │ NixDiscourse   │ │
│  │ Scraper         │  │ Scraper         │  │ Scraper        │ │
│  │                 │  │                 │  │                │ │
│  │ • GitHub API    │  │ • BeautifulSoup │  │ • REST API     │ │
│  │ • Parse .nix    │  │ • Extract code  │  │ • Q&A pairs    │ │
│  │ • Rate limiting │  │ • Sections      │  │ • Tags         │ │
│  └────────┬────────┘  └────────┬────────┘  └────────┬───────┘ │
│           │                    │                      │         │
│           └────────────────────┼──────────────────────┘         │
│                                ↓                                │
│                   ┌─────────────────────────┐                  │
│                   │ NixFineTuningGenerator  │                  │
│                   │                         │                  │
│                   │ • Collect examples      │                  │
│                   │ • Format data           │                  │
│                   │ • Add metadata          │                  │
│                   │ • Deduplicate           │                  │
│                   └────────────┬────────────┘                  │
│                                ↓                                │
└────────────────────────────────┼────────────────────────────────┘
                                 ↓
                    ┌────────────────────────┐
                    │   Export Formats       │
                    ├────────────────────────┤
                    │ • JSONL (OpenAI)       │
                    │ • JSONL (Anthropic)    │
                    │ • JSONL (Generic)      │
                    │ • CSV                  │
                    └────────────────────────┘
```

## Data Flow

### 1. Input Sources

```
┌──────────────────┐
│   nixpkgs Repo   │  → Package definitions (.nix files)
└──────────────────┘  → Fetchers, versions, dependencies
                      → Build instructions

┌──────────────────┐
│   NixOS Wiki     │  → Documentation pages
└──────────────────┘  → Code examples
                      → Configuration guides

┌──────────────────┐
│   Discourse      │  → Community questions
└──────────────────┘  → Expert answers
                      → Real-world problems
```

### 2. Processing Pipeline

```
Raw Data → Scraping → Parsing → Structuring → Formatting → Export
   │          │          │           │            │           │
   │          │          │           │            │           └→ .jsonl
   │          │          │           │            │              .csv
   │          │          │           │            │
   │          │          │           │            └→ Add metadata
   │          │          │           │               timestamps
   │          │          │           │               sources
   │          │          │           │
   │          │          │           └→ Create prompt/completion
   │          │          │              pairs
   │          │          │
   │          │          └→ Extract code blocks
   │          │             Extract explanations
   │          │
   │          └→ HTTP requests
   │             API calls
   │             Rate limiting
   │
   └→ GitHub API
      Wiki pages
      Discourse API
```

### 3. Example Structure

```
┌─────────────────────────────────────────────────────────┐
│ FineTuningExample                                       │
├─────────────────────────────────────────────────────────┤
│ prompt: "How do I create a package in Nix?"             │
│                                                         │
│ completion: "Here's how to create a package:            │
│              ```nix                                     │
│              { stdenv, fetchurl }:                      │
│              stdenv.mkDerivation { ... }                │
│              ```"                                       │
│                                                         │
│ metadata: {                                             │
│   type: "package_definition",                          │
│   package: "hello",                                    │
│   path: "pkgs/applications/misc/hello"                 │
│ }                                                       │
│                                                         │
│ source: "nixpkgs"                                       │
│ timestamp: "2024-02-04T..."                            │
└─────────────────────────────────────────────────────────┘
```

## Scraper Details

### NixPackageScraper

**Purpose**: Extract package definitions from nixpkgs repository

**Methods**:
- `scrape_package_files()`: Main scraping function
  - Uses GitHub API when token provided
  - Falls back to raw HTTP requests without token
  - Searches for `default.nix` files in `pkgs/` directory
  - Rate limits requests to avoid blocking

**Output**: List of (package_name, path, content) tuples

**Example Generation**:
1. Full package definition
2. Version specification patterns
3. Source fetcher usage
4. Dependency declarations

### NixWikiScraper

**Purpose**: Extract documentation and examples from wiki

**Methods**:
- `scrape_wiki_pages()`: Scrapes specified topics
  - Parses HTML with BeautifulSoup
  - Extracts headers and sections
  - Separates text from code blocks
  - Preserves structure

**Output**: List of dicts with topic, section, content

**Example Generation**:
1. Configuration guides
2. How-to articles
3. Best practices
4. Common patterns

### NixDiscourseScraper

**Purpose**: Extract community Q&A from Discourse forum

**Methods**:
- `scrape_topics()`: Fetches recent topics
  - Uses Discourse JSON API
  - Gets questions from first post
  - Gets answers from subsequent posts
  - Extracts tags for categorization

**Output**: List of dicts with title, question, answer, tags

**Example Generation**:
1. Troubleshooting scenarios
2. Real-world solutions
3. Common pitfalls
4. Best practices

## Export Formats Explained

### OpenAI Format
```json
{
  "messages": [
    {"role": "user", "content": "prompt"},
    {"role": "assistant", "content": "completion"}
  ]
}
```
- Used for GPT-3.5/GPT-4 fine-tuning
- Each line is a complete conversation
- Multiple messages can be included

### Anthropic Format
```json
{
  "prompt": "Human: prompt\n\nAssistant:",
  "completion": " completion"
}
```
- Used for Claude fine-tuning
- Simple prompt/completion pairs
- Space before completion is important

### Generic Format
```json
{
  "prompt": "prompt",
  "completion": "completion",
  "metadata": {"type": "...", "source": "..."},
  "source": "nixpkgs",
  "timestamp": "2024-..."
}
```
- Retains all information
- Useful for analysis and filtering
- Can be converted to other formats

## Performance Considerations

### Rate Limiting

1. **GitHub API**:
   - Authenticated: 5,000 requests/hour
   - Unauthenticated: 60 requests/hour
   - Built-in delays between requests

2. **Wiki Scraping**:
   - 0.5 second delay between pages
   - Respectful crawling

3. **Discourse API**:
   - 0.3 second delay between topics
   - Uses pagination

### Memory Usage

- Examples stored in memory until export
- For large datasets (1000+ examples):
  - ~10-50 MB RAM depending on completion length
  - Export streams to disk (no memory spike)

### Execution Time

Approximate times for different configurations:

| Configuration | Packages | Discourse | Wiki | Time |
|--------------|----------|-----------|------|------|
| Quick demo   | 10       | 0         | 0    | 30s  |
| Small        | 50       | 20        | 5    | 5m   |
| Medium       | 100      | 50        | 10   | 10m  |
| Large        | 300      | 100       | 20   | 30m  |

## Extensibility Points

### Adding New Scrapers

1. Create scraper class:
```python
class MyCustomScraper:
    def scrape_data(self) -> List[Dict]:
        # Your logic
        pass
```

2. Add to generator:
```python
self.custom_scraper = MyCustomScraper()
```

3. Add processing method:
```python
def generate_from_custom(self):
    data = self.custom_scraper.scrape_data()
    for item in data:
        self.add_example(...)
```

### Custom Example Templates

Modify `add_manual_examples()` to include your patterns:
- Flake templates
- Module patterns
- Common configurations
- Your organization's conventions

### Metadata Enrichment

Add custom metadata fields:
```python
metadata = {
    "type": "custom",
    "category": "internal",
    "difficulty": "advanced",
    "tags": ["flakes", "overlays"]
}
```

## Quality Assurance

### Automatic Filtering

Currently implemented:
- Minimum content length
- Valid Nix syntax (basic check)
- Deduplication by content hash

### Manual Review

Recommended before fine-tuning:
1. Sample random examples
2. Check for errors
3. Verify diversity
4. Ensure proper formatting

### Statistics for Quality

The `--stats` flag provides:
- Total example count
- Source distribution
- Type distribution
- Average lengths
- Helps identify imbalances

## Security Considerations

1. **API Tokens**: Never commit tokens to git
2. **Rate Limiting**: Respects service limits
3. **Error Handling**: Graceful failures
4. **User-Agent**: Identifies as scraper
5. **Robots.txt**: Should be respected (future enhancement)

## Future Enhancements

Potential additions:
- [ ] GitHub Issues scraping
- [ ] Reddit r/NixOS scraping
- [ ] Deduplication improvements
- [ ] Quality scoring
- [ ] Content validation
- [ ] Parallel scraping
- [ ] Resume capability
- [ ] Incremental updates
- [ ] Dataset versioning
