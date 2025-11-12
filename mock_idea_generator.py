#!/usr/bin/env python3
"""
Mock DocIdeaGenerator for testing staged execution
Creates sample topic files for testing
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime

def create_topic_file(num: int, content_type: str = "test"):
    """Create a mock topic file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"topic_{num}_{content_type}_{timestamp}.md"

    content = f"""# Topic {num}: {content_type.title()} Topic

## Summary
This is a test topic about {content_type} generated for testing purposes.

## Key Insights
- Insight 1: Important finding about {content_type}
- Insight 2: Another key observation
- Insight 3: Critical consideration

## Notable Quotes
> "This is a quote about {content_type}"
> "Another insightful quote"

## Context
This topic was generated from test data to validate the staged execution
workflow in DocOrchestrator.
"""

    with open(filename, 'w') as f:
        f.write(content)

    print(f"Created topic file: {filename}")
    return filename

def main():
    parser = argparse.ArgumentParser(description="Mock DocIdeaGenerator")
    parser.add_argument('--mode', default='test')
    parser.add_argument('--source', default='gmail')
    parser.add_argument('--save-local', action='store_true')
    parser.add_argument('--yes', action='store_true')
    parser.add_argument('--fast', action='store_true')
    parser.add_argument('--start-date', help='Start date')
    parser.add_argument('--label', help='Gmail label')
    parser.add_argument('--email', help='Email filter')
    parser.add_argument('--focus', help='Focus area')
    parser.add_argument('--folder-id', help='Folder ID')
    parser.add_argument('--combined-topics', action='store_true')
    parser.add_argument('--batch', action='store_true')
    parser.add_argument('--output-manifest', help='Output manifest file')
    parser.add_argument('--select-all', action='store_true', help='Auto-select all transcripts without prompting')

    args = parser.parse_args()

    print("=== Mock DocIdeaGenerator ===")
    print(f"Mode: {args.mode}")
    print(f"Source: {args.source}")
    print(f"Generating test topics...")
    print()

    # Create 3 test topic files
    topics = ["AI_Healthcare", "Remote_Work", "Cloud_Computing"]
    created_files = []

    for i, topic in enumerate(topics, 1):
        filename = create_topic_file(i, topic)
        created_files.append(filename)

    print(f"\n✓ Generated {len(created_files)} topic files")

    return 0

if __name__ == "__main__":
    sys.exit(main())
