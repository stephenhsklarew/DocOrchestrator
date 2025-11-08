# Quick Start Guide

## 5-Minute Setup

### 1. Create Your Config File

```bash
cd /Users/stephensklarew/Development/Scripts/DocOrchestrator
cp config.example.yaml my_pipeline.yaml
```

### 2. Edit Your Config

Edit `my_pipeline.yaml` with your preferences:

```yaml
name: "My Weekly Content Pipeline"

global:
  mode: "test"  # Start with test mode (free)

idea_generation:
  source: "gmail"
  start_date: "01012025"  # Adjust to your needs
  label: "AIQ"  # Your Gmail label
  focus: "AI and business strategy"

document_generation:
  audience: "business leaders and CTOs"
  type: "blog post"
  size: "800 words"
  output: "./output"  # or Google Drive URL
```

### 3. Run the Orchestrator

```bash
python3 orchestrator.py --config my_pipeline.yaml
```

## What Happens

### Stage 1: Idea Generation (Interactive)
1. DocIdeaGenerator starts
2. You'll see the Qwilo interface
3. Select transcripts to analyze
4. Save topics when prompted (files saved to `sessions/[timestamp]/topics/`)

### Stage 2: Review (Human Checkpoint)
1. Orchestrator shows table of generated topics
2. Optional preview of each topic
3. Select topics using checkbox UI (Space=toggle, Enter=confirm)
4. Review generation parameters
5. Confirm to proceed

### Stage 3: Document Generation (Batch)
1. PersonalizedDocGenerator runs for each selected topic
2. Progress bar shows status
3. Documents created at your specified output location
4. Summary displays results

## Example Session

```
🚀 DocOrchestrator
─────────────────────────────────────
  My Weekly Content Pipeline
  Mode: test
  Session: 20250108_143022
─────────────────────────────────────

Stage 1: Generating Topic Ideas
This will run DocIdeaGenerator interactively.
Please follow the prompts to generate and save topics.

Ready to start idea generation? [Y/n]: y

Running: python3 ../DocIdeaGenerator/cli.py --mode test --source gmail --save-local

[DocIdeaGenerator starts, you interact with it...]

✓ Found 5 topic file(s)

Stage 2: Review and Select Topics

┏━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━┓
┃ # ┃ Title                   ┃ File        ┃ Words ┃
┡━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━┩
│ 1 │ AI in Healthcare        │ topic_1_... │  342  │
│ 2 │ Remote Work Trends      │ topic_2_... │  298  │
│ 3 │ Data Integration        │ topic_3_... │  415  │
│ 4 │ DevOps Best Practices   │ topic_4_... │  267  │
│ 5 │ Cloud Security          │ topic_5_... │  389  │
└───┴─────────────────────────┴─────────────┴───────┘

Would you like to preview topics before selecting? [y/N]: n

Select topics to generate documents for (Space=toggle, Enter=confirm)
❯ ◉ 1. AI in Healthcare
  ◯ 2. Remote Work Trends
  ◉ 3. Data Integration
  ◯ 4. DevOps Best Practices
  ◯ 5. Cloud Security

✓ Selected 2 topics

📝 Document Generation Parameters
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Parameter       ┃ Value                          ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Mode            │ test                           │
│ Writing Style   │ Default                        │
│ Audience        │ business leaders and CTOs      │
│ Document Type   │ blog post                      │
│ Size            │ 800 words                      │
│ Customer Story  │ None (AI will create fictional)│
│ Output Location │ ./output                       │
│ Topics          │ 2                              │
└─────────────────┴────────────────────────────────┘

Proceed with document generation? [Y/n]: y

Stage 3: Generating Documents
Generating documents... ━━━━━━━━━━━━━━━━ 100% 2/2

✓ Generated 2/2 documents successfully

════════════════════════════════════════════════════════════
✅ Orchestration Complete!
════════════════════════════════════════════════════════════
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓
┃ Topic Files Found ┃ 5                 ┃
┃ Topics Selected   ┃ 2                 ┃
┃ Documents Created ┃ 2                 ┃
┃ Session ID        ┃ 20250108_143022   ┃
└───────────────────┴───────────────────┘

Session saved to: sessions/20250108_143022/session_summary.json
```

## Tips

### Cost Management
- Use `mode: "test"` (free Gemini) while testing
- Switch to `mode: "production"` (GPT-4o) for final documents
- Or use mixed mode:
  ```yaml
  global:
    mode: "test"
  document_generation:
    mode: "production"  # Only pay for final docs
  ```

### Topic Selection Strategy
- Preview topics first if unsure about quality
- Start by selecting 1-2 topics to test the flow
- Scale up to more topics once comfortable

### Troubleshooting
- **No topics found**: Make sure to save topics in DocIdeaGenerator when prompted
- **DocIdeaGenerator fails**: Check that API keys are configured in its `.env`
- **Document generation fails**: Verify PersonalizedDocGenerator works standalone

## Next Steps

1. **First run**: Use test mode, select 1 topic, verify end-to-end flow
2. **Iterate**: Adjust config parameters based on results
3. **Scale**: Increase to multiple topics per run
4. **Production**: Switch to production mode for final content

## Session Management

Each run creates a session directory:
```
sessions/
└── 20250108_143022/
    ├── topics/                    # Topic files from Stage 1
    │   ├── topic_1_*.md
    │   ├── topic_2_*.md
    │   └── ...
    └── session_summary.json       # Complete workflow data
```

Session summary includes:
- Configuration used
- Topics found and selected
- Document generation results
- Timestamps

Useful for debugging, recovery, or analysis.
