#!/usr/bin/env python3
"""
Integration tests for DocOrchestrator with mock programs

Tests the full orchestration workflow using mock versions of
DocIdeaGenerator and PersonalizedDocGenerator.
"""

import os
import sys
import json
import yaml
import tempfile
import subprocess
from pathlib import Path
from textwrap import dedent

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from orchestrator import DocOrchestrator, OrchestratorConfig
    from rich.console import Console
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure to run: pip3 install -r requirements.txt")
    sys.exit(1)

console = Console()


def create_mock_idea_generator(script_path: Path):
    """Create a mock DocIdeaGenerator script"""
    script_content = '''#!/usr/bin/env python3
"""Mock DocIdeaGenerator for testing"""
import sys
import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--mode', required=True)
parser.add_argument('--source', required=True)
parser.add_argument('--save-local', action='store_true')
parser.add_argument('--start-date', default=None)
parser.add_argument('--label', default=None)
parser.add_argument('--focus', default=None)
parser.add_argument('--folder-id', default=None)
parser.add_argument('--combined-topics', action='store_true')

args = parser.parse_args()

# Create mock topic files
topic1 = Path("topic_1_ai_healthcare.md")
topic1.write_text("""# AI in Healthcare

This is a test topic about AI in healthcare.

## Key Insights

- AI can improve diagnostics
- Machine learning helps predict outcomes
- Automation reduces costs

## Notable Quotes

> "AI is transforming healthcare" - Dr. Smith

## Description

This topic explores how artificial intelligence is revolutionizing healthcare delivery.
""")

topic2 = Path("topic_2_remote_work.md")
topic2.write_text("""# Remote Work Revolution

Exploring the shift to distributed teams.

## Key Insights

- Remote work increases productivity
- Communication tools are essential
- Work-life balance improves
""")

topic3 = Path("topic_3_cloud_computing.md")
topic3.write_text("""# Cloud Computing Trends

The future of infrastructure.

## Key Insights

- Serverless is gaining traction
- Multi-cloud strategies are common
- Cost optimization is critical
""")

print(f"Mock DocIdeaGenerator: Created 3 topic files")
print(f"Mode: {args.mode}, Source: {args.source}")
sys.exit(0)
'''

    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(script_content)
    script_path.chmod(0o755)


def create_mock_doc_generator(script_path: Path):
    """Create a mock PersonalizedDocGenerator script"""
    script_content = '''#!/usr/bin/env python3
"""Mock PersonalizedDocGenerator for testing"""
import sys
import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--mode', required=True)
parser.add_argument('--topic', required=True)
parser.add_argument('--audience', required=True)
parser.add_argument('--type', required=True)
parser.add_argument('--size', required=True)
parser.add_argument('--output', required=True)
parser.add_argument('--style', default=None)
parser.add_argument('--customer-story', default=None)

args = parser.parse_args()

# Read topic file
topic_path = Path(args.topic)
if not topic_path.exists():
    print(f"Error: Topic file not found: {topic_path}", file=sys.stderr)
    sys.exit(1)

topic_title = topic_path.stem

# Create mock output
output_dir = Path(args.output)
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / f"{topic_title}_document.md"

output_file.write_text(f"""# {topic_title}

Generated document for {args.audience}

Type: {args.type}
Size: {args.size}
Mode: {args.mode}

This is a mock document generated for testing purposes.
""")

print(f"Generated document: {output_file}")
sys.exit(0)
'''

    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(script_content)
    script_path.chmod(0o755)


def test_full_orchestration():
    """Test 1: Full orchestration workflow with mocks"""
    console.print("\n[bold cyan]Test 1: Full Orchestration Workflow[/bold cyan]")

    # Create temporary directory structure
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create mock programs
        mock_idea_gen = temp_path / "MockIdeaGen" / "cli.py"
        mock_doc_gen = temp_path / "MockDocGen" / "document_generator.py"
        create_mock_idea_generator(mock_idea_gen)
        create_mock_doc_generator(mock_doc_gen)

        # Create output directory
        output_dir = temp_path / "output"
        output_dir.mkdir(parents=True)

        # Create test config
        test_config = {
            'name': 'Integration Test Pipeline',
            'global': {'mode': 'test'},
            'idea_generation': {
                'source': 'gmail',
                'focus': 'testing',
                'combined_topics': False
            },
            'document_generation': {
                'audience': 'testers',
                'type': 'blog post',
                'size': '500 words',
                'output': str(output_dir)
            },
            'orchestration': {
                'stage1_timeout': 30,
                'stage2_timeout': 30,
                'retry_on_failure': True,
                'save_session': True,
                'idea_generator_path': str(mock_idea_gen),
                'doc_generator_path': str(mock_doc_gen),
                'log_level': 'DEBUG'
            }
        }

        # Write config file
        config_path = temp_path / "test_config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(test_config, f)

        try:
            # Initialize orchestrator
            orchestrator = DocOrchestrator(str(config_path))

            # Verify paths
            assert orchestrator.idea_generator_path == mock_idea_gen
            assert orchestrator.doc_generator_path == mock_doc_gen

            # Verify session directory was created
            assert orchestrator.session_dir.exists()
            assert orchestrator.topics_dir.exists()

            # Verify log file exists
            log_file = orchestrator.session_dir / "orchestrator.log"
            assert log_file.exists(), "Log file should be created"

            # Check log file has content
            log_content = log_file.read_text()
            assert len(log_content) > 0, "Log file should have content"
            assert "Initializing DocOrchestrator" in log_content

            console.print("[green]✓[/green] Full orchestration setup: PASSED")
            console.print(f"[dim]  - Mock programs created")
            console.print(f"[dim]  - Session directory: {orchestrator.session_dir}")
            console.print(f"[dim]  - Log file created: {log_file}")
            console.print(f"[dim]  - Log entries: {len(log_content.split(chr(10)))}")

            return True

        except Exception as e:
            console.print(f"[red]✗[/red] Full orchestration: FAILED - {e}")
            import traceback
            traceback.print_exc()
            return False


def test_mock_stage1_execution():
    """Test 2: Stage 1 execution with mock"""
    console.print("\n[bold cyan]Test 2: Stage 1 Mock Execution[/bold cyan]")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create mock idea generator
        mock_idea_gen = temp_path / "MockIdeaGen" / "cli.py"
        create_mock_idea_generator(mock_idea_gen)

        # Create output directory
        output_dir = temp_path / "output"
        output_dir.mkdir(parents=True)

        # Create minimal config
        test_config = {
            'name': 'Stage 1 Test',
            'global': {'mode': 'test'},
            'idea_generation': {'source': 'gmail', 'combined_topics': False},
            'document_generation': {
                'audience': 'test',
                'type': 'test',
                'size': 'test',
                'output': str(output_dir)
            },
            'orchestration': {
                'stage1_timeout': 30,
                'stage2_timeout': 30,
                'retry_on_failure': True,
                'save_session': True,
                'idea_generator_path': str(mock_idea_gen),
                'doc_generator_path': str(temp_path / "MockDocGen" / "document_generator.py"),
                'log_level': 'DEBUG'
            }
        }

        # Create mock doc generator (required for initialization)
        mock_doc_gen_path = Path(test_config['orchestration']['doc_generator_path'])
        create_mock_doc_generator(mock_doc_gen_path)

        config_path = temp_path / "test_config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(test_config, f)

        try:
            orchestrator = DocOrchestrator(str(config_path))

            # Run Stage 1
            topic_files = orchestrator._run_stage1()

            # Verify results
            assert len(topic_files) == 3, f"Expected 3 topics, got {len(topic_files)}"
            assert all(f.exists() for f in topic_files), "All topic files should exist"
            assert all(f.parent == orchestrator.topics_dir for f in topic_files), "Topics should be in session directory"

            # Verify topics were moved to session directory
            for topic_file in topic_files:
                assert topic_file.exists()
                content = topic_file.read_text()
                assert len(content) > 0

            console.print(f"[green]✓[/green] Stage 1 execution: PASSED")
            console.print(f"[dim]  - Found {len(topic_files)} topics")
            console.print(f"[dim]  - Topics in session dir: {orchestrator.topics_dir}")

            return True

        except Exception as e:
            console.print(f"[red]✗[/red] Stage 1 execution: FAILED - {e}")
            import traceback
            traceback.print_exc()
            return False


def test_topic_parsing():
    """Test 3: Topic file parsing"""
    console.print("\n[bold cyan]Test 3: Topic File Parsing[/bold cyan]")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create mock programs
        mock_idea_gen = temp_path / "MockIdeaGen" / "cli.py"
        mock_doc_gen = temp_path / "MockDocGen" / "document_generator.py"
        create_mock_idea_generator(mock_idea_gen)
        create_mock_doc_generator(mock_doc_gen)

        output_dir = temp_path / "output"
        output_dir.mkdir(parents=True)

        test_config = {
            'name': 'Parsing Test',
            'global': {'mode': 'test'},
            'idea_generation': {'source': 'gmail', 'combined_topics': False},
            'document_generation': {
                'audience': 'test',
                'type': 'test',
                'size': 'test',
                'output': str(output_dir)
            },
            'orchestration': {
                'stage1_timeout': 30,
                'stage2_timeout': 30,
                'retry_on_failure': True,
                'save_session': True,
                'idea_generator_path': str(mock_idea_gen),
                'doc_generator_path': str(mock_doc_gen),
                'log_level': 'DEBUG'
            }
        }

        config_path = temp_path / "test_config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(test_config, f)

        try:
            orchestrator = DocOrchestrator(str(config_path))

            # Create test topic files manually
            topic1 = orchestrator.topics_dir / "topic_1_test.md"
            topic1.write_text("# Test Topic\n\n## Key Insights\n\n- Insight 1\n- Insight 2\n")

            topic2 = orchestrator.topics_dir / "topic_2_another.md"
            topic2.write_text("# Another Topic\n\nSome content here.")

            # Parse topics
            topics = orchestrator._parse_topic_files([topic1, topic2])

            # Verify parsing
            assert len(topics) == 2
            assert topics[0]['title'] == 'Test Topic'
            assert topics[1]['title'] == 'Another Topic'
            assert topics[0]['size'] > 0
            assert topics[0]['file_path'] == topic1

            console.print(f"[green]✓[/green] Topic parsing: PASSED")
            console.print(f"[dim]  - Parsed {len(topics)} topics")
            console.print(f"[dim]  - Titles: {[t['title'] for t in topics]}")

            return True

        except Exception as e:
            console.print(f"[red]✗[/red] Topic parsing: FAILED - {e}")
            import traceback
            traceback.print_exc()
            return False


def test_error_handling():
    """Test 4: Error handling with failing mock"""
    console.print("\n[bold cyan]Test 4: Error Handling[/bold cyan]")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create failing mock idea generator
        mock_idea_gen = temp_path / "MockIdeaGen" / "cli.py"
        mock_idea_gen.parent.mkdir(parents=True, exist_ok=True)
        mock_idea_gen.write_text('''#!/usr/bin/env python3
import sys
print("Error: Mock failure", file=sys.stderr)
sys.exit(1)
''')
        mock_idea_gen.chmod(0o755)

        # Create normal mock doc generator
        mock_doc_gen = temp_path / "MockDocGen" / "document_generator.py"
        create_mock_doc_generator(mock_doc_gen)

        output_dir = temp_path / "output"
        output_dir.mkdir(parents=True)

        test_config = {
            'name': 'Error Test',
            'global': {'mode': 'test'},
            'idea_generation': {'source': 'gmail', 'combined_topics': False},
            'document_generation': {
                'audience': 'test',
                'type': 'test',
                'size': 'test',
                'output': str(output_dir)
            },
            'orchestration': {
                'stage1_timeout': 30,
                'stage2_timeout': 30,
                'retry_on_failure': True,
                'save_session': True,
                'idea_generator_path': str(mock_idea_gen),
                'doc_generator_path': str(mock_doc_gen),
                'log_level': 'DEBUG'
            }
        }

        config_path = temp_path / "test_config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(test_config, f)

        try:
            orchestrator = DocOrchestrator(str(config_path))

            # Run Stage 1 (should handle error gracefully)
            topic_files = orchestrator._run_stage1()

            # Should return empty list on failure
            assert len(topic_files) == 0, "Should return empty list on failure"

            # Check that error was logged
            log_file = orchestrator.session_dir / "orchestrator.log"
            log_content = log_file.read_text()
            assert "exited with non-zero code" in log_content or "ERROR" in log_content

            console.print(f"[green]✓[/green] Error handling: PASSED")
            console.print(f"[dim]  - Handled Stage 1 failure gracefully")
            console.print(f"[dim]  - Error logged properly")

            return True

        except Exception as e:
            console.print(f"[red]✗[/red] Error handling: FAILED - {e}")
            import traceback
            traceback.print_exc()
            return False


def test_logging_levels():
    """Test 5: Logging configuration"""
    console.print("\n[bold cyan]Test 5: Logging Levels[/bold cyan]")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create mock programs
        mock_idea_gen = temp_path / "MockIdeaGen" / "cli.py"
        mock_doc_gen = temp_path / "MockDocGen" / "document_generator.py"
        create_mock_idea_generator(mock_idea_gen)
        create_mock_doc_generator(mock_doc_gen)

        output_dir = temp_path / "output"
        output_dir.mkdir(parents=True)

        # Test with DEBUG level
        test_config = {
            'name': 'Logging Test',
            'global': {'mode': 'test'},
            'idea_generation': {'source': 'gmail', 'combined_topics': False},
            'document_generation': {
                'audience': 'test',
                'type': 'test',
                'size': 'test',
                'output': str(output_dir)
            },
            'orchestration': {
                'stage1_timeout': 30,
                'stage2_timeout': 30,
                'retry_on_failure': True,
                'save_session': True,
                'idea_generator_path': str(mock_idea_gen),
                'doc_generator_path': str(mock_doc_gen),
                'log_level': 'DEBUG'
            }
        }

        config_path = temp_path / "test_config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(test_config, f)

        try:
            orchestrator = DocOrchestrator(str(config_path))

            # Verify log file exists
            log_file = orchestrator.session_dir / "orchestrator.log"
            assert log_file.exists()

            # Check that DEBUG messages are in the log
            log_content = log_file.read_text()
            assert "DEBUG" in log_content, "Should have DEBUG level messages"
            assert "INFO" in log_content, "Should have INFO level messages"

            console.print(f"[green]✓[/green] Logging configuration: PASSED")
            console.print(f"[dim]  - Log file created: {log_file}")
            console.print(f"[dim]  - DEBUG level active")
            console.print(f"[dim]  - Log size: {len(log_content)} bytes")

            return True

        except Exception as e:
            console.print(f"[red]✗[/red] Logging configuration: FAILED - {e}")
            import traceback
            traceback.print_exc()
            return False


def test_phase2_manifest():
    """Test 6: Phase 2 manifest-based integration"""
    console.print("\n[bold cyan]Test 6: Phase 2 Manifest Integration[/bold cyan]")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create mock programs that support manifest
        mock_idea_gen = temp_path / "MockIdeaGen" / "cli.py"
        mock_doc_gen = temp_path / "MockDocGen" / "document_generator.py"

        # Create a Phase 2 compatible mock idea generator
        mock_idea_gen.parent.mkdir(parents=True, exist_ok=True)
        mock_idea_gen.write_text('''#!/usr/bin/env python3
import sys
import json
import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--mode', required=True)
parser.add_argument('--source', required=True)
parser.add_argument('--save-local', action='store_true')
parser.add_argument('--batch', action='store_true')
parser.add_argument('--output-manifest', default=None)
args = parser.parse_args()

# Create mock topic files
topic1 = Path("topic_1_ai_healthcare.md")
topic1.write_text("# AI in Healthcare\\n\\nTest content")

topic2 = Path("topic_2_remote_work.md")
topic2.write_text("# Remote Work Revolution\\n\\nTest content")

# Create manifest
if args.output_manifest:
    manifest = {
        'status': 'success',
        'timestamp': '2025-01-01T00:00:00',
        'mode': args.mode,
        'model': 'gemini-1.5-flash',
        'topics': [
            {
                'id': 'topic_1',
                'title': 'AI in Healthcare',
                'description': 'How AI is transforming healthcare',
                'file': str(topic1.absolute()),
                'key_insights': ['Insight 1', 'Insight 2', 'Insight 3'],
                'notable_quotes': ['Quote 1', 'Quote 2'],
                'word_count': 100
            },
            {
                'id': 'topic_2',
                'title': 'Remote Work Revolution',
                'description': 'The shift to distributed teams',
                'file': str(topic2.absolute()),
                'key_insights': ['Insight A', 'Insight B'],
                'notable_quotes': ['Quote A'],
                'word_count': 80
            }
        ]
    }
    with open(args.output_manifest, 'w') as f:
        json.dump(manifest, f, indent=2)
    print(f"Created manifest: {args.output_manifest}")

sys.exit(0)
''')
        mock_idea_gen.chmod(0o755)
        create_mock_doc_generator(mock_doc_gen)

        output_dir = temp_path / "output"
        output_dir.mkdir(parents=True)

        # Test config with Phase 2 enabled
        test_config = {
            'name': 'Phase 2 Test',
            'global': {'mode': 'test'},
            'idea_generation': {'source': 'gmail', 'combined_topics': False},
            'document_generation': {
                'audience': 'test',
                'type': 'test',
                'size': 'test',
                'output': str(output_dir)
            },
            'orchestration': {
                'stage1_timeout': 30,
                'stage2_timeout': 30,
                'retry_on_failure': True,
                'save_session': True,
                'idea_generator_path': str(mock_idea_gen),
                'doc_generator_path': str(mock_doc_gen),
                'log_level': 'DEBUG',
                'use_manifest': True,
                'batch_mode': True
            }
        }

        config_path = temp_path / "test_config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(test_config, f)

        try:
            orchestrator = DocOrchestrator(str(config_path))

            # Run Stage 1 with manifest
            topic_files = orchestrator._run_stage1()

            # Verify manifest was created and used
            manifest_file = orchestrator.session_dir / "ideas_manifest.json"
            assert manifest_file.exists(), "Manifest file should be created"

            with open(manifest_file) as f:
                manifest = json.load(f)

            assert manifest['status'] == 'success'
            assert len(manifest['topics']) == 2

            # Verify topics were loaded
            assert len(topic_files) == 2

            # Verify manifest attribute was set
            assert hasattr(orchestrator, 'manifest')
            assert orchestrator.manifest == manifest

            # Test parsing with manifest
            topics = orchestrator._parse_topic_files(topic_files)
            assert len(topics) == 2
            assert topics[0]['insights_count'] == 3  # From manifest metadata
            assert topics[0]['quotes_count'] == 2

            console.print(f"[green]✓[/green] Phase 2 manifest integration: PASSED")
            console.print(f"[dim]  - Manifest created and loaded")
            console.print(f"[dim]  - Topics: {[t['title'] for t in topics]}")
            console.print(f"[dim]  - Using rich metadata from manifest")

            return True

        except Exception as e:
            console.print(f"[red]✗[/red] Phase 2 manifest integration: FAILED - {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Run all integration tests"""
    console.print("[bold cyan]═══════════════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]    DocOrchestrator Integration Test Suite        [/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════════════════[/bold cyan]")

    tests = [
        ("Full Orchestration", test_full_orchestration),
        ("Stage 1 Execution", test_mock_stage1_execution),
        ("Topic Parsing", test_topic_parsing),
        ("Error Handling", test_error_handling),
        ("Logging Levels", test_logging_levels),
        ("Phase 2 Manifest", test_phase2_manifest),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            console.print(f"\n[red]✗[/red] {test_name}: EXCEPTION - {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    console.print("\n[bold cyan]═══════════════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]                  Test Summary                     [/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════════════════[/bold cyan]")

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for test_name, passed in results:
        status = "[green]PASSED[/green]" if passed else "[red]FAILED[/red]"
        console.print(f"  {test_name:.<40} {status}")

    console.print(f"\n[bold]Results: {passed_count}/{total_count} tests passed[/bold]")

    if passed_count == total_count:
        console.print("\n[bold green]✅ All integration tests passed![/bold green]")
        return 0
    else:
        console.print(f"\n[bold red]❌ {total_count - passed_count} test(s) failed[/bold red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
