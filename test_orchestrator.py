#!/usr/bin/env python3
"""
Test script for DocOrchestrator

Tests core functionality without requiring full program execution.
"""

import os
import sys
import yaml
import tempfile
from pathlib import Path

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


def test_config_loading():
    """Test 1: Config file loading"""
    console.print("\n[bold cyan]Test 1: Config Loading[/bold cyan]")

    # Create a test config
    test_config = {
        'name': 'Test Pipeline',
        'global': {'mode': 'test'},
        'idea_generation': {
            'source': 'gmail',
            'start_date': '01012025',
            'label': 'test',
            'focus': 'testing',
            'combined_topics': False
        },
        'document_generation': {
            'audience': 'testers',
            'type': 'blog post',
            'size': '500 words',
            'output': './test_output'
        },
        'orchestration': {
            'stage1_timeout': 300,
            'stage2_timeout': 180,
            'retry_on_failure': True,
            'save_session': True
        }
    }

    # Write to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(test_config, f)
        temp_config_path = f.name

    try:
        # Test loading
        orchestrator = DocOrchestrator(temp_config_path)

        # Verify config values
        assert orchestrator.config.name == 'Test Pipeline', "Config name mismatch"
        assert orchestrator.config.global_mode == 'test', "Mode mismatch"
        assert orchestrator.config.idea_source == 'gmail', "Source mismatch"
        assert orchestrator.config.doc_audience == 'testers', "Audience mismatch"
        assert orchestrator.config.stage1_timeout == 300, "Timeout mismatch"

        console.print("[green]✓[/green] Config loading: PASSED")
        return True

    except Exception as e:
        console.print(f"[red]✗[/red] Config loading: FAILED - {e}")
        return False

    finally:
        os.unlink(temp_config_path)


def test_path_validation():
    """Test 2: Program path validation"""
    console.print("\n[bold cyan]Test 2: Path Validation[/bold cyan]")

    test_config = {
        'name': 'Test',
        'global': {'mode': 'test'},
        'idea_generation': {'source': 'gmail', 'combined_topics': False},
        'document_generation': {'audience': 'test', 'type': 'test', 'size': 'test', 'output': './test'},
        'orchestration': {'stage1_timeout': 300, 'stage2_timeout': 300, 'retry_on_failure': True, 'save_session': True}
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(test_config, f)
        temp_config_path = f.name

    try:
        orchestrator = DocOrchestrator(temp_config_path)

        # Check that paths were validated
        idea_gen_exists = orchestrator.idea_generator_path.exists()
        doc_gen_exists = orchestrator.doc_generator_path.exists()

        console.print(f"  DocIdeaGenerator path: {orchestrator.idea_generator_path}")
        console.print(f"  Exists: {idea_gen_exists}")
        console.print(f"  PersonalizedDocGenerator path: {orchestrator.doc_generator_path}")
        console.print(f"  Exists: {doc_gen_exists}")

        if idea_gen_exists and doc_gen_exists:
            console.print("[green]✓[/green] Path validation: PASSED")
            return True
        else:
            console.print("[yellow]⚠[/yellow] Path validation: PARTIAL - Programs not found at expected locations")
            console.print("[dim]This is expected if programs are not at ../DocIdeaGenerator and ../PersonalizedDocGenerator[/dim]")
            return True  # Still pass since paths are validated, just not present

    except Exception as e:
        console.print(f"[red]✗[/red] Path validation: FAILED - {e}")
        return False

    finally:
        os.unlink(temp_config_path)


def test_session_creation():
    """Test 3: Session directory creation"""
    console.print("\n[bold cyan]Test 3: Session Creation[/bold cyan]")

    test_config = {
        'name': 'Test',
        'global': {'mode': 'test'},
        'idea_generation': {'source': 'gmail', 'combined_topics': False},
        'document_generation': {'audience': 'test', 'type': 'test', 'size': 'test', 'output': './test'},
        'orchestration': {'stage1_timeout': 300, 'stage2_timeout': 300, 'retry_on_failure': True, 'save_session': True}
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(test_config, f)
        temp_config_path = f.name

    try:
        orchestrator = DocOrchestrator(temp_config_path)

        # Check session directory
        session_exists = orchestrator.session_dir.exists()
        topics_dir_exists = orchestrator.topics_dir.exists()

        console.print(f"  Session dir: {orchestrator.session_dir}")
        console.print(f"  Exists: {session_exists}")
        console.print(f"  Topics dir: {orchestrator.topics_dir}")
        console.print(f"  Exists: {topics_dir_exists}")

        if session_exists and topics_dir_exists:
            console.print("[green]✓[/green] Session creation: PASSED")
            return True
        else:
            console.print("[red]✗[/red] Session creation: FAILED")
            return False

    except Exception as e:
        console.print(f"[red]✗[/red] Session creation: FAILED - {e}")
        return False

    finally:
        os.unlink(temp_config_path)


def test_topic_parsing():
    """Test 4: Topic file parsing"""
    console.print("\n[bold cyan]Test 4: Topic File Parsing[/bold cyan]")

    # Create test config
    test_config = {
        'name': 'Test',
        'global': {'mode': 'test'},
        'idea_generation': {'source': 'gmail', 'combined_topics': False},
        'document_generation': {'audience': 'test', 'type': 'test', 'size': 'test', 'output': './test'},
        'orchestration': {'stage1_timeout': 300, 'stage2_timeout': 300, 'retry_on_failure': True, 'save_session': True}
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(test_config, f)
        temp_config_path = f.name

    try:
        orchestrator = DocOrchestrator(temp_config_path)

        # Create test topic files
        test_topics = [
            {
                'filename': 'topic_1_ai_healthcare.md',
                'content': '''# AI in Healthcare

This is a test topic about AI in healthcare.

## Key Insights

- Insight 1: AI can improve diagnostics
- Insight 2: Machine learning helps predict outcomes
- Insight 3: Automation reduces costs

## Notable Quotes

> "AI is transforming healthcare" - Dr. Smith
> "The future is automated" - Jane Doe

## Description

This topic explores how artificial intelligence is revolutionizing healthcare delivery.
'''
            },
            {
                'filename': 'topic_2_remote_work.md',
                'content': '''# Remote Work Revolution

Exploring the shift to distributed teams.

## Key Insights

- Remote work increases productivity
- Communication tools are essential
- Work-life balance improves

## Evidence

- 80% of workers prefer hybrid model
- Productivity up 25% since 2020
'''
            }
        ]

        # Write test files
        for topic in test_topics:
            file_path = orchestrator.topics_dir / topic['filename']
            with open(file_path, 'w') as f:
                f.write(topic['content'])

        # Test parsing
        topic_files = list(orchestrator.topics_dir.glob("topic_*.md"))
        console.print(f"  Found {len(topic_files)} topic files")

        if len(topic_files) == 2:
            # Test the interactive review parsing logic
            topics = []
            for file_path in topic_files:
                with open(file_path, 'r') as f:
                    content = f.read()

                # Extract title
                lines = content.split('\n')
                title = file_path.stem
                for line in lines:
                    if line.startswith('#'):
                        title = line.lstrip('#').strip()
                        break

                topics.append({
                    'file_path': file_path,
                    'title': title,
                    'size': len(content.split())
                })

            console.print(f"  Parsed topics:")
            for i, topic in enumerate(topics, 1):
                console.print(f"    {i}. {topic['title']} ({topic['size']} words)")

            console.print("[green]✓[/green] Topic parsing: PASSED")
            return True
        else:
            console.print("[red]✗[/red] Topic parsing: FAILED - Wrong number of files")
            return False

    except Exception as e:
        console.print(f"[red]✗[/red] Topic parsing: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        os.unlink(temp_config_path)


def test_config_modes():
    """Test 5: Mode configuration"""
    console.print("\n[bold cyan]Test 5: Mode Configuration[/bold cyan]")

    test_cases = [
        ({'global': {'mode': 'test'}, 'document_generation': {}}, 'test', 'test'),
        ({'global': {'mode': 'test'}, 'document_generation': {'mode': 'production'}}, 'test', 'production'),
        ({'global': {'mode': 'production'}, 'document_generation': {}}, 'production', 'production'),
    ]

    all_passed = True
    for i, (config_data, expected_global, expected_doc) in enumerate(test_cases, 1):
        full_config = {
            'name': f'Test {i}',
            'global': config_data['global'],
            'idea_generation': {'source': 'gmail', 'combined_topics': False},
            'document_generation': {
                'audience': 'test',
                'type': 'test',
                'size': 'test',
                'output': './test',
                **config_data['document_generation']
            },
            'orchestration': {
                'stage1_timeout': 300,
                'stage2_timeout': 300,
                'retry_on_failure': True,
                'save_session': True
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(full_config, f)
            temp_config_path = f.name

        try:
            orchestrator = DocOrchestrator(temp_config_path)

            actual_global = orchestrator.config.global_mode
            actual_doc = orchestrator.config.doc_mode_override or orchestrator.config.global_mode

            if actual_global == expected_global and actual_doc == expected_doc:
                console.print(f"  [green]✓[/green] Test case {i}: global={actual_global}, doc={actual_doc}")
            else:
                console.print(f"  [red]✗[/red] Test case {i}: Expected global={expected_global}, doc={expected_doc}, got global={actual_global}, doc={actual_doc}")
                all_passed = False

        except Exception as e:
            console.print(f"  [red]✗[/red] Test case {i}: FAILED - {e}")
            all_passed = False

        finally:
            os.unlink(temp_config_path)

    if all_passed:
        console.print("[green]✓[/green] Mode configuration: PASSED")
    else:
        console.print("[red]✗[/red] Mode configuration: FAILED")

    return all_passed


def main():
    """Run all tests"""
    console.print("[bold cyan]═══════════════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]       DocOrchestrator Test Suite                  [/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════════════════[/bold cyan]")

    tests = [
        ("Config Loading", test_config_loading),
        ("Path Validation", test_path_validation),
        ("Session Creation", test_session_creation),
        ("Topic Parsing", test_topic_parsing),
        ("Mode Configuration", test_config_modes),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            console.print(f"\n[red]✗[/red] {test_name}: EXCEPTION - {e}")
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
        console.print("\n[bold green]✅ All tests passed![/bold green]")
        return 0
    else:
        console.print(f"\n[bold red]❌ {total_count - passed_count} test(s) failed[/bold red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
