#!/usr/bin/env python3
"""
DocOrchestrator - Content Generation Pipeline Orchestrator

Phase 1: File-based integration with existing programs
Orchestrates DocIdeaGenerator and PersonalizedDocGenerator with human-in-the-loop review.
"""

import os
import sys
import json
import yaml
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

try:
    from rich.console import Console
    from rich.prompt import Confirm, Prompt
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.panel import Panel
    from rich.markdown import Markdown
    import inquirer
except ImportError:
    print("Error: Required packages not installed.")
    print("Please run: pip install -r requirements.txt")
    sys.exit(1)


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator"""
    name: str
    global_mode: str

    # Stage 1: Idea Generation
    idea_source: str
    idea_start_date: Optional[str]
    idea_label: Optional[str]
    idea_focus: Optional[str]
    idea_folder_id: Optional[str]
    idea_combined_topics: bool

    # Stage 2: Document Generation
    doc_style: str
    doc_audience: str
    doc_type: str
    doc_size: str
    doc_customer_story: Optional[str]
    doc_output: str
    doc_mode_override: Optional[str]

    # Orchestration settings
    stage1_timeout: int
    stage2_timeout: int
    retry_on_failure: bool
    save_session: bool


class DocOrchestrator:
    """Main orchestrator class"""

    def __init__(self, config_path: str):
        """Initialize orchestrator with config file"""
        self.console = Console()
        self.config = self._load_config(config_path)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = Path("sessions") / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Paths to other programs
        self.scripts_dir = Path(__file__).parent.parent
        self.idea_generator_path = self.scripts_dir / "DocIdeaGenerator" / "cli.py"
        self.doc_generator_path = self.scripts_dir / "PersonalizedDocGenerator" / "document_generator.py"

        # Working directory for topic files
        self.topics_dir = self.session_dir / "topics"
        self.topics_dir.mkdir(exist_ok=True)

        # Validate paths
        if not self.idea_generator_path.exists():
            raise FileNotFoundError(f"DocIdeaGenerator not found at {self.idea_generator_path}")
        if not self.doc_generator_path.exists():
            raise FileNotFoundError(f"PersonalizedDocGenerator not found at {self.doc_generator_path}")

    def _load_config(self, config_path: str) -> OrchestratorConfig:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)

        global_settings = data.get('global', {})
        idea_gen = data.get('idea_generation', {})
        doc_gen = data.get('document_generation', {})
        orchestration = data.get('orchestration', {})

        return OrchestratorConfig(
            name=data.get('name', 'Content Pipeline'),
            global_mode=global_settings.get('mode', 'test'),

            # Stage 1
            idea_source=idea_gen.get('source', 'gmail'),
            idea_start_date=idea_gen.get('start_date'),
            idea_label=idea_gen.get('label'),
            idea_focus=idea_gen.get('focus'),
            idea_folder_id=idea_gen.get('folder_id'),
            idea_combined_topics=idea_gen.get('combined_topics', False),

            # Stage 2
            doc_style=doc_gen.get('style', ''),
            doc_audience=doc_gen.get('audience', ''),
            doc_type=doc_gen.get('type', 'blog post'),
            doc_size=doc_gen.get('size', '800 words'),
            doc_customer_story=doc_gen.get('customer_story'),
            doc_output=doc_gen.get('output', './output'),
            doc_mode_override=doc_gen.get('mode'),

            # Orchestration
            stage1_timeout=orchestration.get('stage1_timeout', 600),
            stage2_timeout=orchestration.get('stage2_timeout', 300),
            retry_on_failure=orchestration.get('retry_on_failure', True),
            save_session=orchestration.get('save_session', True),
        )

    def run(self):
        """Run the complete orchestration workflow"""
        self.console.print(Panel.fit(
            f"[bold cyan]{self.config.name}[/bold cyan]\n"
            f"Mode: [yellow]{self.config.global_mode}[/yellow]\n"
            f"Session: [dim]{self.session_id}[/dim]",
            title="🚀 Your Personalized Idea and Document Creator"
        ))

        try:
            # Stage 1: Generate ideas
            self.console.print("\n[bold]Stage 1: Generating Topic Ideas[/bold]")
            self.console.print("[dim]This will run DocIdeaGenerator interactively.[/dim]")
            self.console.print("[dim]Please follow the prompts to generate and save topics.[/dim]\n")

            if not Confirm.ask("[yellow]Ready to start idea generation?[/yellow]", default=True):
                self.console.print("[yellow]Cancelled.[/yellow]")
                return 0

            topic_files = self._run_stage1()

            if not topic_files:
                self.console.print("[yellow]No topic files found. Make sure to save topics when prompted by DocIdeaGenerator.[/yellow]")
                self.console.print("[dim]Hint: DocIdeaGenerator saves topics as 'topic_N_*.md' files in the current directory.[/dim]")

                # Ask if user wants to manually specify topic files
                if Confirm.ask("\n[yellow]Do you want to manually specify topic files to process?[/yellow]", default=False):
                    topic_files = self._manual_topic_selection()

                if not topic_files:
                    return 1

            # Human review checkpoint
            self.console.print(f"\n[bold]Stage 2: Review and Select Topics[/bold]")
            selected_topics = self._interactive_review(topic_files)

            if not selected_topics:
                self.console.print("[yellow]No topics selected. Exiting.[/yellow]")
                return 0

            # Confirm parameters
            if not self._confirm_parameters(selected_topics):
                self.console.print("[yellow]Cancelled by user.[/yellow]")
                return 0

            # Stage 3: Generate documents
            self.console.print(f"\n[bold]Stage 3: Generating Documents[/bold]")
            documents = self._run_stage2(selected_topics)

            # Summary
            self._print_summary(topic_files, selected_topics, documents)

            return 0

        except KeyboardInterrupt:
            self.console.print("\n[yellow]Interrupted by user.[/yellow]")
            return 130
        except Exception as e:
            self.console.print(f"\n[red]Error: {e}[/red]")
            if self.config.retry_on_failure:
                self.console.print("[dim]Session saved for potential recovery.[/dim]")
            raise

    def _run_stage1(self) -> List[Path]:
        """Run DocIdeaGenerator and return list of generated topic files"""
        # Change to topics directory so files are saved there
        original_cwd = Path.cwd()
        os.chdir(self.topics_dir)

        try:
            # Build command
            cmd = [
                "python3", str(self.idea_generator_path),
                "--mode", self.config.global_mode,
                "--source", self.config.idea_source,
                "--save-local",  # Always save as local markdown for orchestration
            ]

            # Add optional arguments
            if self.config.idea_start_date:
                cmd.extend(["--start-date", self.config.idea_start_date])
            if self.config.idea_label:
                cmd.extend(["--label", self.config.idea_label])
            if self.config.idea_focus:
                cmd.extend(["--focus", self.config.idea_focus])
            if self.config.idea_folder_id:
                cmd.extend(["--folder-id", self.config.idea_folder_id])
            if self.config.idea_combined_topics:
                cmd.append("--combined-topics")

            self.console.print(f"[dim]Running: {' '.join(cmd)}[/dim]\n")

            # Run interactively (user will see and interact with DocIdeaGenerator)
            result = subprocess.run(cmd, timeout=self.config.stage1_timeout)

            if result.returncode != 0:
                self.console.print(f"[red]Stage 1 exited with code {result.returncode}[/red]")
                return []

        finally:
            os.chdir(original_cwd)

        # Find generated topic files
        topic_files = list(self.topics_dir.glob("topic_*.md"))

        if not topic_files:
            # Try alternative patterns
            topic_files = list(self.topics_dir.glob("analysis_*.md"))

        self.console.print(f"\n[green]✓[/green] Found {len(topic_files)} topic file(s)")

        return sorted(topic_files)

    def _manual_topic_selection(self) -> List[Path]:
        """Allow user to manually specify topic files"""
        self.console.print("\n[bold]Manual Topic File Selection[/bold]")
        self.console.print("Enter paths to topic markdown files (one per line, empty line to finish):")

        files = []
        while True:
            path_str = Prompt.ask(f"Topic file #{len(files) + 1} (or press Enter to finish)", default="")
            if not path_str:
                break

            path = Path(path_str).expanduser()
            if path.exists() and path.is_file():
                files.append(path)
                self.console.print(f"[green]✓[/green] Added: {path.name}")
            else:
                self.console.print(f"[red]✗[/red] File not found: {path}")

        return files

    def _interactive_review(self, topic_files: List[Path]) -> List[Dict]:
        """Interactive UI for reviewing and selecting topics"""
        if not topic_files:
            return []

        # Parse topic files to extract metadata
        topics = []
        for file_path in topic_files:
            with open(file_path, 'r') as f:
                content = f.read()

            # Extract title (first heading)
            lines = content.split('\n')
            title = file_path.stem.replace('_', ' ').title()
            for line in lines:
                if line.startswith('#'):
                    title = line.lstrip('#').strip()
                    break

            # Count insights and quotes
            insights_count = content.count('- ') if '## Key Insights' in content or '## Insights' in content else 0
            quotes_count = content.count('> ') + content.count('- "')

            topics.append({
                'file_path': file_path,
                'title': title,
                'insights_count': min(insights_count, 10),  # Cap display at reasonable number
                'quotes_count': min(quotes_count, 10),
                'size': len(content.split())
            })

        # Display topics in a rich table
        table = Table(title=f"📋 Generated Topics ({len(topics)} found)", show_header=True)
        table.add_column("#", style="cyan", width=3)
        table.add_column("Title", style="bold")
        table.add_column("File", style="dim", width=30)
        table.add_column("Words", justify="right", width=7)

        for i, topic in enumerate(topics, 1):
            table.add_row(
                str(i),
                topic['title'][:50],
                topic['file_path'].name[:28],
                str(topic['size'])
            )

        self.console.print(table)

        # Show preview option
        if Confirm.ask("\n[yellow]Would you like to preview topics before selecting?[/yellow]", default=False):
            for i, topic in enumerate(topics, 1):
                self.console.print(f"\n[bold cyan]{i}. {topic['title']}[/bold cyan]")
                self.console.print(f"[dim]File: {topic['file_path'].name}[/dim]")
                with open(topic['file_path'], 'r') as f:
                    preview = f.read()[:500]
                self.console.print(Markdown(preview))
                if i < len(topics):
                    if not Confirm.ask("Continue to next topic?", default=True):
                        break

        # Interactive selection using inquirer
        self.console.print("\n")
        choices = [
            f"{i}. {topic['title'][:60]}"
            for i, topic in enumerate(topics, 1)
        ]

        questions = [
            inquirer.Checkbox(
                'selected',
                message="Select topics to generate documents for (Space=toggle, Enter=confirm)",
                choices=choices,
                default=choices[:min(3, len(choices))]  # Pre-select first 3
            ),
        ]

        answers = inquirer.prompt(questions)

        if not answers or not answers['selected']:
            return []

        # Extract selected indices
        selected_indices = []
        for selection in answers['selected']:
            idx = int(selection.split('.')[0]) - 1
            selected_indices.append(idx)

        selected = [topics[i] for i in selected_indices]

        self.console.print(f"\n[green]✓[/green] Selected {len(selected)} topics")

        return selected

    def _confirm_parameters(self, selected_topics: List[Dict]) -> bool:
        """Display parameters and get confirmation"""
        table = Table(title="📝 Document Generation Parameters", show_header=True)
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="green")

        # Determine mode for stage 2
        mode = self.config.doc_mode_override or self.config.global_mode

        table.add_row("Mode", mode)
        table.add_row("Writing Style", self.config.doc_style or "[dim]Default[/dim]")
        table.add_row("Audience", self.config.doc_audience or "[dim]General[/dim]")
        table.add_row("Document Type", self.config.doc_type)
        table.add_row("Size", self.config.doc_size)
        table.add_row("Customer Story", self.config.doc_customer_story or "[dim]None (AI will create fictional)[/dim]")
        table.add_row("Output Location", self.config.doc_output)
        table.add_row("Topics to Generate", str(len(selected_topics)))

        self.console.print(table)

        return Confirm.ask("\n[bold]Proceed with document generation?[/bold]", default=True)

    def _run_stage2(self, selected_topics: List[Dict]) -> List[Dict]:
        """Run PersonalizedDocGenerator for each selected topic"""
        documents = []
        mode = self.config.doc_mode_override or self.config.global_mode

        with Progress(console=self.console) as progress:
            task = progress.add_task(
                "[cyan]Generating documents...",
                total=len(selected_topics)
            )

            for i, topic in enumerate(selected_topics, 1):
                progress.update(task, description=f"[cyan]Generating document {i}/{len(selected_topics)}: {topic['title'][:40]}...")

                # Build command
                cmd = [
                    "python3", str(self.doc_generator_path),
                    "--mode", mode,
                    "--topic", str(topic['file_path']),
                    "--audience", self.config.doc_audience,
                    "--type", self.config.doc_type,
                    "--size", self.config.doc_size,
                    "--output", self.config.doc_output,
                ]

                if self.config.doc_style:
                    cmd.extend(["--style", self.config.doc_style])
                if self.config.doc_customer_story:
                    cmd.extend(["--customer-story", self.config.doc_customer_story])

                # Run document generator
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.config.stage2_timeout
                )

                if result.returncode != 0:
                    self.console.print(f"\n[red]✗ Failed to generate document for: {topic['title']}[/red]")
                    self.console.print(f"[dim]Error: {result.stderr[:200]}[/dim]")
                    if not self.config.retry_on_failure:
                        raise RuntimeError(f"Document generation failed: {result.stderr}")
                    documents.append({
                        'topic': topic['title'],
                        'status': 'failed',
                        'error': result.stderr[:200]
                    })
                else:
                    documents.append({
                        'topic': topic['title'],
                        'status': 'success',
                        'output': result.stdout
                    })

                progress.update(task, advance=1)

        successful = len([d for d in documents if d['status'] == 'success'])
        self.console.print(f"\n[green]✓[/green] Generated {successful}/{len(documents)} documents successfully")

        return documents

    def _print_summary(self, topic_files: List[Path], selected_topics: List[Dict], documents: List[Dict]):
        """Print final summary"""
        self.console.print("\n" + "="*60)
        self.console.print("[bold green]✅ Orchestration Complete![/bold green]")
        self.console.print("="*60)

        successful = len([d for d in documents if d['status'] == 'success'])
        failed = len([d for d in documents if d['status'] == 'failed'])

        table = Table(show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Topic Files Found", str(len(topic_files)))
        table.add_row("Topics Selected", str(len(selected_topics)))
        table.add_row("Documents Created", f"{successful} success, {failed} failed" if failed > 0 else str(successful))
        table.add_row("Session ID", self.session_id)

        self.console.print(table)

        if self.config.save_session:
            session_file = self.session_dir / "session_summary.json"
            with open(session_file, 'w') as f:
                json.dump({
                    'session_id': self.session_id,
                    'config': asdict(self.config),
                    'topic_files': [str(f) for f in topic_files],
                    'selected_topics': [
                        {'title': t['title'], 'file': str(t['file_path'])}
                        for t in selected_topics
                    ],
                    'documents': documents,
                    'timestamp': datetime.now().isoformat()
                }, f, indent=2)

            self.console.print(f"\n[dim]Session saved to: {session_file}[/dim]")


def main():
    parser = argparse.ArgumentParser(
        description="Your Personalized Idea and Document Creator - Content Generation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with config file
  python orchestrator.py --config my_pipeline.yaml

  # Use example config
  python orchestrator.py --config config.example.yaml

Note: This is Phase 1 implementation using file-based integration.
DocIdeaGenerator will run interactively - follow its prompts to generate topics.
        """
    )

    parser.add_argument(
        "-c", "--config",
        required=True,
        help="Path to YAML configuration file"
    )

    args = parser.parse_args()

    try:
        orchestrator = DocOrchestrator(args.config)
        return orchestrator.run()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
