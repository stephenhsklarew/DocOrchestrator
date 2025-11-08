# DocOrchestrator

A content generation pipeline orchestrator that coordinates **DocIdeaGenerator** and **PersonalizedDocGenerator** with human-in-the-loop review.

## Overview

DocOrchestrator automates the workflow of:
1. **Stage 1:** Analyzing conversation transcripts to generate article topic ideas
2. **Human Review:** Interactive selection of which topics to pursue
3. **Stage 2:** Generating full documents for selected topics

All configuration is done upfront via YAML, and the orchestrator runs both stages in batch mode with a single human checkpoint in between.

## Features

- ✅ **Config-driven workflow** - All parameters set upfront in YAML
- ✅ **Interactive topic selection** - Rich CLI with checkbox interface
- ✅ **Parameter review** - Human confirms settings before document generation
- ✅ **Test/Production modes** - Control AI model costs
- ✅ **Batch processing** - Both stages run unattended until review checkpoint
- ✅ **Session persistence** - Save workflow state for debugging
- ✅ **Error handling** - Configurable retry behavior

## Installation

### Prerequisites

- Python 3.8+
- DocIdeaGenerator installed at `../DocIdeaGenerator`
- PersonalizedDocGenerator installed at `../PersonalizedDocGenerator`

### Install Dependencies

```bash
cd /Users/stephensklarew/Development/Scripts/DocOrchestrator
pip install -r requirements.txt
```

This installs:
- `pyyaml` - Config file parsing
- `rich` - Beautiful terminal UI
- `inquirer` - Interactive prompts

## Quick Start

### 1. Create Your Configuration

```bash
cp config.example.yaml my_pipeline.yaml
# Edit my_pipeline.yaml with your settings
```

### 2. Run the Orchestrator

```bash
python orchestrator.py --config my_pipeline.yaml
```

### 3. Workflow

The orchestrator will:
1. **Stage 1:** Run DocIdeaGenerator to analyze transcripts and generate topic ideas
2. **Display topics** in a rich table with preview
3. **Prompt you to select** which topics to generate documents for (checkbox UI)
4. **Show parameters** and ask for confirmation
5. **Stage 2:** Generate documents for selected topics
6. **Display summary** with statistics

## Configuration

### Config File Structure

```yaml
name: "My Pipeline Name"

global:
  mode: "test"  # or "production"

idea_generation:
  source: "gmail"  # or "drive"
  start_date: "01012025"
  label: "AIQ"
  focus: "AI transformation"
  save_local: true

document_generation:
  style: "~/my_writing_style.txt"
  audience: "business leaders"
  type: "blog post"
  size: "800 words"
  customer_story: "~/stories/acme.txt"
  output: "./output"  # or Google Drive URL

orchestration:
  stage1_timeout: 600
  stage2_timeout: 300
  retry_on_failure: true
  save_session: true
```

### Key Configuration Options

#### Global Settings

- **`mode`**: `"test"` (Gemini 1.5 Flash - free) or `"production"` (GPT-4o)

#### Idea Generation (Stage 1)

- **`source`**: `"gmail"` or `"drive"`
- **`start_date`**: Filter emails from date (MMDDYYYY)
- **`label`**: Gmail label to filter
- **`focus`**: Content analysis perspective
- **`save_local`**: `true` for markdown files, `false` for Google Docs

#### Document Generation (Stage 2)

- **`style`**: Path to writing style guide file
- **`audience`**: Target audience description
- **`type`**: Document type (`"blog post"`, `"whitepaper"`, `"article"`, etc.)
- **`size`**: Document length (`"800 words"`, `"3 pages"`, etc.)
- **`customer_story`**: Optional customer story/case study file
- **`output`**: Output location (local path or Google Drive URL)
- **`mode`**: Optional override (use production for stage 2 even if stage 1 was test)

#### Orchestration Settings

- **`stage1_timeout`**: Max seconds for idea generation (default: 600)
- **`stage2_timeout`**: Max seconds per document (default: 300)
- **`retry_on_failure`**: Continue if a document fails (default: true)
- **`save_session`**: Save workflow data (default: true)

## Interactive Review

After Stage 1 completes, you'll see:

1. **Topics Table** - Overview of all generated topics
2. **Detailed Preview** - Title, description, and key insights for each topic
3. **Checkbox Selection** - Use Space to toggle, Enter to confirm
4. **Parameters Table** - Review all settings before proceeding
5. **Confirmation Prompt** - Final approval before document generation

### Selection Tips

- **Space bar**: Toggle topic selection
- **Arrow keys**: Navigate topics
- **Enter**: Confirm selection
- **Ctrl+C**: Cancel workflow

## Cost Management

### Test Mode (Default)
- Uses **Gemini 1.5 Flash** (Google)
- **FREE** up to 1,500 requests/day
- Ideal for testing workflows

### Production Mode
- Uses **GPT-4o** (OpenAI)
- ~$0.10 per analysis/document
- Higher quality output

### Mixed Mode
Set `global.mode: "test"` but override for stage 2:

```yaml
global:
  mode: "test"  # Free idea generation

document_generation:
  mode: "production"  # High-quality final documents
```

## Session Management

Each orchestration run creates a session:

```
sessions/
└── 20250108_143022/
    ├── ideas_manifest.json     # All generated topics
    ├── topic_1.txt             # Extracted topic files
    ├── topic_2.txt
    └── session_summary.json    # Complete workflow data
```

Sessions are useful for:
- Debugging failures
- Recovering from interruptions
- Analyzing topic selection patterns

## Examples

### Example 1: Test Run with Local Output

```yaml
name: "Test Pipeline"
global:
  mode: "test"

idea_generation:
  source: "gmail"
  start_date: "01012025"
  focus: "AI and automation"
  save_local: true

document_generation:
  audience: "developers"
  type: "technical article"
  size: "600 words"
  output: "./output"
```

### Example 2: Production Run with Google Drive

```yaml
name: "Weekly Blog Pipeline"
global:
  mode: "production"

idea_generation:
  source: "gmail"
  label: "blog-worthy"
  save_local: false

document_generation:
  style: "~/Documents/brand_voice.txt"
  audience: "business executives"
  type: "blog post"
  size: "800-1000 words"
  customer_story: "~/case_studies/latest.txt"
  output: "https://drive.google.com/drive/folders/1ABC..."
```

### Example 3: Mixed Mode (Cost Optimization)

```yaml
name: "Cost-Optimized Pipeline"
global:
  mode: "test"  # Free idea generation

idea_generation:
  source: "gmail"
  start_date: "12012024"

document_generation:
  mode: "production"  # High-quality final docs only
  style: "~/writing_style.txt"
  audience: "CTOs and tech leaders"
  type: "thought leadership article"
  size: "1200 words"
  output: "https://drive.google.com/drive/folders/..."
```

## Troubleshooting

### Error: "DocIdeaGenerator not found"

Ensure DocIdeaGenerator is installed at `../DocIdeaGenerator/cli.py` relative to the orchestrator.

### Error: "Stage 1 failed"

1. Check DocIdeaGenerator works standalone:
   ```bash
   cd ../DocIdeaGenerator
   python cli.py --help
   ```
2. Verify API keys are configured in DocIdeaGenerator's `.env`

### Error: "No topics generated"

- Check `start_date` isn't too restrictive
- Verify Gmail label exists
- Ensure transcripts match expected format

### Timeout Errors

Increase timeouts in config:
```yaml
orchestration:
  stage1_timeout: 1200  # 20 minutes
  stage2_timeout: 600   # 10 minutes per doc
```

## Architecture

```
DocOrchestrator
│
├── orchestrator.py          # Main orchestration logic
├── config.yaml              # User configuration
├── requirements.txt         # Python dependencies
│
└── Orchestrates:
    ├── DocIdeaGenerator     # Stage 1: Generate topic ideas
    │   └── cli.py --output-manifest
    │
    └── PersonalizedDocGenerator  # Stage 2: Generate documents
        └── document_generator.py --mode --topic ...
```

## Future Enhancements

- [ ] Resume capability (continue from saved session)
- [ ] Web dashboard for remote review
- [ ] Webhook notifications (Slack, email)
- [ ] Advanced filtering/ranking of topics
- [ ] Parallel document generation
- [ ] A/B testing support (generate multiple versions)

## License

Same as parent projects.

## Support

For issues:
1. Check session logs in `sessions/[session_id]/`
2. Run programs standalone to isolate issues
3. Verify config file syntax (YAML validators)

## Credits

Orchestrates:
- **DocIdeaGenerator** - AI-powered topic idea extraction
- **PersonalizedDocGenerator** - AI-powered document generation
