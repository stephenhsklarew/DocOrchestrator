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
import logging
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
    idea_email_subject: Optional[str]
    idea_focus: Optional[str]
    idea_folder_id: Optional[str]
    idea_combined_topics: bool
    idea_fast_mode: bool

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

    # Dependency paths (optional, defaults to ../DocIdeaGenerator and ../PersonalizedDocGenerator)
    idea_generator_path: Optional[str] = None
    doc_generator_path: Optional[str] = None

    # Logging settings
    log_level: str = "INFO"

    # Phase 2: Manifest-based integration
    use_manifest: bool = True  # Use manifest if available, fall back to file discovery
    batch_mode: bool = False  # Run Stage 1 in batch mode (requires external program support)
    idea_select_all: bool = True  # Auto-select all transcripts (for scheduled/automated runs)


class DocOrchestrator:
    """Main orchestrator class"""

    def __init__(self, config_path: str = None, auto_confirm: bool = False, session_id: str = None, config: OrchestratorConfig = None):
        """Initialize orchestrator with config file or existing session"""
        self.console = Console()

        # Support loading from existing session or new config
        if config:
            self.config = config
        elif config_path:
            self.config = self._load_config(config_path)
            self.config_path = config_path
        else:
            raise ValueError("Must provide either config_path or config object")

        self.auto_confirm = auto_confirm
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        # Use absolute path for session directory to avoid issues when changing working directory
        self.session_dir = (Path.cwd() / "sessions" / self.session_id).absolute()
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Set up logging
        self._setup_logging()

        self.logger.info(f"Initializing DocOrchestrator - Session ID: {self.session_id}")
        self.logger.info(f"Config loaded from: {config_path}")

        # Paths to other programs (use config paths if provided, otherwise default)
        self.scripts_dir = Path(__file__).parent.parent
        if self.config.idea_generator_path:
            self.idea_generator_path = Path(self.config.idea_generator_path).expanduser()
            self.logger.info(f"Using custom DocIdeaGenerator path from config: {self.idea_generator_path}")
        else:
            self.idea_generator_path = self.scripts_dir / "DocIdeaGenerator" / "cli.py"
            self.logger.debug(f"Using default DocIdeaGenerator path: {self.idea_generator_path}")

        if self.config.doc_generator_path:
            self.doc_generator_path = Path(self.config.doc_generator_path).expanduser()
            self.logger.info(f"Using custom PersonalizedDocGenerator path from config: {self.doc_generator_path}")
        else:
            self.doc_generator_path = self.scripts_dir / "PersonalizedDocGenerator" / "document_generator.py"
            self.logger.debug(f"Using default PersonalizedDocGenerator path: {self.doc_generator_path}")

        # Working directory for topic files
        self.topics_dir = self.session_dir / "topics"
        self.topics_dir.mkdir(exist_ok=True)
        self.logger.debug(f"Session directory: {self.session_dir}")
        self.logger.debug(f"Topics directory: {self.topics_dir}")

        # Validate paths
        if not self.idea_generator_path.exists():
            self.logger.error(f"DocIdeaGenerator not found at {self.idea_generator_path}")
            raise FileNotFoundError(f"DocIdeaGenerator not found at {self.idea_generator_path}")
        if not self.doc_generator_path.exists():
            self.logger.error(f"PersonalizedDocGenerator not found at {self.doc_generator_path}")
            raise FileNotFoundError(f"PersonalizedDocGenerator not found at {self.doc_generator_path}")

        self.logger.info("Initialization complete - all dependencies validated")

    def _setup_logging(self):
        """Configure logging to both file and console"""
        # Create logger
        self.logger = logging.getLogger('DocOrchestrator')
        self.logger.setLevel(getattr(logging, self.config.log_level.upper(), logging.INFO))

        # Clear any existing handlers
        self.logger.handlers.clear()

        # File handler - detailed logs
        log_file = self.session_dir / "orchestrator.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # Always log DEBUG to file
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # Console handler - less verbose
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, self.config.log_level.upper(), logging.INFO))
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # Prevent propagation to root logger
        self.logger.propagate = False

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
            idea_email_subject=idea_gen.get('email_subject'),
            idea_focus=idea_gen.get('focus'),
            idea_folder_id=idea_gen.get('folder_id'),
            idea_combined_topics=idea_gen.get('combined_topics', False),
            idea_fast_mode=idea_gen.get('fast_mode', False),
            idea_select_all=idea_gen.get('select_all', True),

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

            # Dependency paths (optional)
            idea_generator_path=orchestration.get('idea_generator_path'),
            doc_generator_path=orchestration.get('doc_generator_path'),

            # Logging
            log_level=orchestration.get('log_level', 'INFO'),

            # Phase 2: Manifest-based integration
            use_manifest=orchestration.get('use_manifest', True),
            batch_mode=orchestration.get('batch_mode', False),
        )

    def run(self):
        """Run the complete orchestration workflow"""
        self.logger.info(f"Starting orchestration workflow: {self.config.name}")
        self.logger.info(f"Mode: {self.config.global_mode}")

        self.console.print(Panel.fit(
            f"[bold cyan]{self.config.name}[/bold cyan]\n"
            f"Mode: [yellow]{self.config.global_mode}[/yellow]\n"
            f"Session: [dim]{self.session_id}[/dim]",
            title="🚀 Your Personalized Idea and Document Creator"
        ))

        try:
            # Stage 1: Generate ideas
            self.logger.info("Starting Stage 1: Idea Generation")
            self.console.print("\n[bold]Stage 1: Generating Topic Ideas[/bold]")
            self.console.print("[dim]This will run DocIdeaGenerator interactively.[/dim]")
            self.console.print("[dim]Please follow the prompts to generate and save topics.[/dim]\n")

            if not self.auto_confirm:
                if not Confirm.ask("[yellow]Ready to start idea generation?[/yellow]", default=True):
                    self.logger.info("User cancelled at Stage 1 prompt")
                    self.console.print("[yellow]Cancelled.[/yellow]")
                    return 0
            else:
                self.logger.info("Auto-confirming Stage 1 start (--yes flag)")
                self.console.print("[green]Auto-confirmed: Starting idea generation[/green]")

            topic_files = self._run_stage1()
            self.logger.info(f"Stage 1 complete. Found {len(topic_files)} topic files")

            if not topic_files:
                self.logger.warning("No topic files found after Stage 1")
                self.console.print("[yellow]No topic files found. Make sure to save topics when prompted by DocIdeaGenerator.[/yellow]")
                self.console.print("[dim]Hint: DocIdeaGenerator saves topics as 'topic_N_*.md' files in the current directory.[/dim]")

                # Ask if user wants to manually specify topic files
                if not self.auto_confirm and Confirm.ask("\n[yellow]Do you want to manually specify topic files to process?[/yellow]", default=False):
                    self.logger.info("User opted for manual topic file selection")
                    topic_files = self._manual_topic_selection()

                if not topic_files:
                    self.logger.warning("No topic files available. Exiting.")
                    return 1

            # Human review checkpoint
            self.logger.info("Starting Stage 2: Human Review and Topic Selection")
            self.console.print(f"\n[bold]Stage 2: Review and Select Topics[/bold]")
            selected_topics = self._interactive_review(topic_files)

            if not selected_topics:
                self.logger.info("No topics selected by user. Exiting.")
                self.console.print("[yellow]No topics selected. Exiting.[/yellow]")
                return 0

            self.logger.info(f"User selected {len(selected_topics)} topics for document generation")

            # Confirm parameters
            if not self.auto_confirm:
                if not self._confirm_parameters(selected_topics):
                    self.logger.info("User cancelled at parameter confirmation")
                    self.console.print("[yellow]Cancelled by user.[/yellow]")
                    return 0
            else:
                self.logger.info("Auto-confirming parameters (--yes flag)")
                self._display_parameters(selected_topics)
                self.console.print("[green]Auto-confirmed: Proceeding with document generation[/green]")

            # Stage 3: Generate documents
            self.logger.info("Starting Stage 3: Document Generation")
            self.console.print(f"\n[bold]Stage 3: Generating Documents[/bold]")
            documents = self._run_stage2(selected_topics)

            # Summary
            self.logger.info("Orchestration workflow complete")
            self._print_summary(topic_files, selected_topics, documents)

            return 0

        except KeyboardInterrupt:
            self.logger.warning("Workflow interrupted by user (KeyboardInterrupt)")
            self.console.print("\n[yellow]Interrupted by user.[/yellow]")
            return 130
        except Exception as e:
            self.logger.error(f"Fatal error in orchestration workflow: {e}", exc_info=True)
            self.console.print(f"\n[red]Error: {e}[/red]")
            if self.config.retry_on_failure:
                self.console.print("[dim]Session saved for potential recovery.[/dim]")
            raise

    def _run_stage1(self) -> List[Path]:
        """Run DocIdeaGenerator and return list of generated topic files

        Supports both Phase 1 (file discovery) and Phase 2 (manifest-based) integration.
        """
        self.logger.debug("Entering _run_stage1")
        # Run from DocIdeaGenerator directory to access credentials.json
        idea_gen_dir = self.idea_generator_path.parent
        original_cwd = Path.cwd()
        self.logger.debug(f"Changing directory from {original_cwd} to {idea_gen_dir}")
        os.chdir(idea_gen_dir)

        # Manifest file path (absolute)
        manifest_file = self.session_dir / "ideas_manifest.json"

        try:
            # Build command
            cmd = [
                "python3", str(self.idea_generator_path),
                "--mode", self.config.global_mode,
                "--source", self.config.idea_source,
                "--save-local",  # Always save as local markdown for orchestration
            ]

            # Phase 2: Add manifest and batch mode flags if enabled
            if self.config.use_manifest and self.config.batch_mode:
                cmd.extend(["--batch", "--output-manifest", str(manifest_file)])
                self.logger.info("Phase 2 mode: Using batch mode with manifest output")
            else:
                self.logger.info("Phase 1 mode: Using interactive file discovery")

            # Add --yes flag for auto-confirmation if enabled
            if self.auto_confirm:
                cmd.append("--yes")
                self.logger.info("Adding --yes flag to DocIdeaGenerator for auto-confirmation")

            # Add --select-all flag to auto-select all transcripts (for scheduled/automated runs)
            if self.config.idea_select_all:
                cmd.append("--select-all")
                self.logger.info("Adding --select-all flag to auto-select all transcripts")

            # Add --fast flag if fast mode is enabled
            if self.config.idea_fast_mode:
                cmd.append("--fast")
                self.logger.info("Fast mode enabled - using Gemini 2.5 Flash (300+ tok/s)")

            # Add optional arguments
            if self.config.idea_start_date:
                cmd.extend(["--start-date", self.config.idea_start_date])
            if self.config.idea_label:
                cmd.extend(["--label", self.config.idea_label])
            if self.config.idea_email_subject:
                cmd.extend(["--email", self.config.idea_email_subject])
            if self.config.idea_focus:
                cmd.extend(["--focus", self.config.idea_focus])
            if self.config.idea_folder_id:
                cmd.extend(["--folder-id", self.config.idea_folder_id])
            if self.config.idea_combined_topics:
                cmd.append("--combined-topics")

            self.logger.info(f"Executing DocIdeaGenerator: {' '.join(cmd)}")
            self.console.print(f"[dim]Running: {' '.join(cmd)}[/dim]\n")

            # Run (interactive or batch depending on config)
            # Only capture output in batch mode; let it flow through in interactive mode
            if self.config.batch_mode:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.config.stage1_timeout
                )
            else:
                # Interactive mode - don't capture output so errors are visible
                result = subprocess.run(
                    cmd,
                    timeout=self.config.stage1_timeout
                )
                # Create a fake result object with empty stdout/stderr for compatibility
                result.stdout = ""
                result.stderr = ""

            if result.returncode != 0:
                # Parse output for error messages
                error_details = []

                # Look for error messages in stdout
                if result.stdout:
                    for line in result.stdout.split('\n'):
                        if 'error' in line.lower() or 'failed' in line.lower() or 'blocked' in line.lower():
                            error_details.append(line.strip())

                # Look for error messages in stderr
                if result.stderr:
                    for line in result.stderr.split('\n'):
                        if 'error' in line.lower() or 'failed' in line.lower() or 'blocked' in line.lower():
                            error_details.append(line.strip())

                # Build detailed error message
                if error_details:
                    error_summary = "\n".join(error_details[:5])  # Show first 5 error lines
                    self.logger.error(f"DocIdeaGenerator exited with code {result.returncode}. Errors:\n{error_summary}")
                    self.console.print(f"[red]Stage 1 failed with errors:[/red]\n{error_summary[:200]}")
                else:
                    self.logger.error(f"DocIdeaGenerator exited with non-zero code: {result.returncode}")
                    self.console.print(f"[red]Stage 1 exited with code {result.returncode}[/red]")
                    # Include last 10 lines of output for debugging
                    if result.stdout:
                        last_lines = result.stdout.strip().split('\n')[-10:]
                        self.logger.debug(f"Last output:\n" + "\n".join(last_lines))

                return []

            self.logger.debug("DocIdeaGenerator completed successfully")

            # Phase 2: Try to load manifest if enabled
            if self.config.use_manifest and manifest_file.exists():
                self.logger.info("Phase 2: Manifest file found, loading topics from manifest")
                return self._load_topics_from_manifest(manifest_file)

            # Phase 1: Fall back to file discovery
            self.logger.info("Phase 1: Using file discovery for topics")
            return self._discover_topic_files(idea_gen_dir)

        finally:
            self.logger.debug(f"Restoring directory to {original_cwd}")
            os.chdir(original_cwd)

    def _load_topics_from_manifest(self, manifest_file: Path) -> List[Path]:
        """Load topic files from manifest (Phase 2)"""
        self.logger.debug(f"Loading manifest from {manifest_file}")

        try:
            with open(manifest_file, 'r') as f:
                manifest = json.load(f)

            self.logger.info(f"Manifest loaded successfully: {manifest.get('status', 'unknown')} status")

            # Store manifest for later use
            self.manifest = manifest

            # Extract topic file paths
            topic_files = []
            for topic in manifest.get('topics', []):
                file_path = Path(topic.get('file'))
                if file_path.exists():
                    # Move to session directory if not already there
                    if file_path.parent != self.topics_dir:
                        import shutil
                        dest_path = self.topics_dir / file_path.name
                        self.logger.debug(f"Moving {file_path} to {dest_path}")
                        shutil.move(str(file_path.absolute()), str(dest_path))
                        topic_files.append(dest_path)
                    else:
                        topic_files.append(file_path)
                else:
                    self.logger.warning(f"Topic file not found: {file_path}")

            self.logger.info(f"Loaded {len(topic_files)} topics from manifest")
            self.console.print(f"\n[green]✓[/green] Loaded {len(topic_files)} topics from manifest")

            return sorted(topic_files)

        except Exception as e:
            self.logger.error(f"Failed to load manifest: {e}")
            self.logger.info("Falling back to file discovery")
            # Fall back to file discovery
            return self._discover_topic_files(self.idea_generator_path.parent)

    def _discover_topic_files(self, idea_gen_dir: Path) -> List[Path]:
        """Discover topic files by pattern matching (Phase 1)"""
        self.logger.debug("Discovering topic files by pattern matching")

        # Find generated topic files in DocIdeaGenerator directory
        topic_files = list(idea_gen_dir.glob("topic_*.md"))
        self.logger.debug(f"Found {len(topic_files)} files matching 'topic_*.md'")

        if not topic_files:
            # Try alternative patterns
            self.logger.debug("No files matching 'topic_*.md', trying 'analysis_*.md'")
            topic_files = list(idea_gen_dir.glob("analysis_*.md"))
            self.logger.debug(f"Found {len(topic_files)} files matching 'analysis_*.md'")

        # Move files to topics directory
        moved_files = []
        for file_path in topic_files:
            dest_path = self.topics_dir.absolute() / file_path.name
            import shutil
            self.logger.debug(f"Moving {file_path.absolute()} to {dest_path}")
            shutil.move(str(file_path.absolute()), str(dest_path))
            moved_files.append(dest_path)

        self.logger.info(f"Successfully moved {len(moved_files)} topic files to session directory")
        self.console.print(f"\n[green]✓[/green] Found {len(moved_files)} topic file(s)")

        return sorted(moved_files)

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

    def _interactive_review(self, topic_files_or_topics: List) -> List[Dict]:
        """Interactive UI for reviewing and selecting topics

        Args:
            topic_files_or_topics: Either a list of Path objects (for full run) or
                                  a list of topic dictionaries (for review stage)
        """
        if not topic_files_or_topics:
            return []

        # Check if we received Path objects or already-parsed topics
        if isinstance(topic_files_or_topics[0], Path):
            # Parse topic files to extract metadata
            topics = self._parse_topic_files(topic_files_or_topics)
        else:
            # Already have parsed topics (from review stage)
            topics = topic_files_or_topics

        # Display topics in a rich table
        self._display_topics_table(topics)

        # Auto-confirm mode: select all topics
        if self.auto_confirm:
            self.logger.info("Auto-confirming: Selecting all topics (--yes flag)")
            self.console.print(f"\n[green]✓[/green] Auto-selected all {len(topics)} topics")
            return topics

        # Show preview option
        self._preview_topics(topics)

        # Interactive selection
        selected = self._select_topics(topics)

        self.console.print(f"\n[green]✓[/green] Selected {len(selected)} topics")
        return selected

    def _parse_topic_files(self, topic_files: List[Path]) -> List[Dict]:
        """Parse topic files to extract metadata

        Phase 2: Uses manifest data if available for richer metadata
        Phase 1: Falls back to parsing markdown files
        """
        self.logger.debug(f"Parsing {len(topic_files)} topic files")

        # Phase 2: If we have manifest data, use it
        if hasattr(self, 'manifest') and self.manifest:
            self.logger.info("Phase 2: Using manifest metadata for topic parsing")
            return self._parse_topics_from_manifest(topic_files)

        # Phase 1: Parse from files
        self.logger.info("Phase 1: Parsing topics from files")
        topics = []
        for file_path in topic_files:
            with open(file_path, 'r') as f:
                content = f.read()

            # Extract title - look for "## TOPIC N:" pattern first, then fall back to first heading
            lines = content.split('\n')
            title = file_path.stem.replace('_', ' ').title()

            # First try to find "## TOPIC N:" heading
            for line in lines:
                if line.strip().startswith('## TOPIC'):
                    # Extract everything after "## TOPIC N:"
                    title = line.split(':', 1)[-1].strip()
                    break
            else:
                # Fall back to first heading if no TOPIC heading found
                for line in lines:
                    if line.startswith('#'):
                        title = line.lstrip('#').strip()
                        break

            # Extract description (look for "**Description:**" line)
            description = ""
            for i, line in enumerate(lines):
                if line.strip().startswith('**Description:**'):
                    # Get the description text after the label
                    desc_text = line.split('**Description:**', 1)[-1].strip()
                    # If description continues on next lines, include them too
                    if not desc_text and i + 1 < len(lines):
                        desc_text = lines[i + 1].strip()
                    description = desc_text
                    break

            # Count insights and quotes
            insights_count = content.count('- ') if '## Key Insights' in content or '## Insights' in content else 0
            quotes_count = content.count('> ') + content.count('- "')

            topics.append({
                'file_path': file_path,
                'title': title,
                'description': description,
                'insights_count': min(insights_count, 10),  # Cap display at reasonable number
                'quotes_count': min(quotes_count, 10),
                'size': len(content.split())
            })
            self.logger.debug(f"Parsed topic: {title} ({len(content.split())} words)")

        return topics

    def _parse_topics_from_manifest(self, topic_files: List[Path]) -> List[Dict]:
        """Parse topics using manifest metadata (Phase 2)"""
        self.logger.debug("Parsing topics from manifest")
        topics = []

        # Create a mapping of file names to topic data
        topic_map = {}
        for topic_data in self.manifest.get('topics', []):
            file_path = Path(topic_data.get('file'))
            topic_map[file_path.name] = topic_data

        for file_path in topic_files:
            # Try to get data from manifest
            manifest_data = topic_map.get(file_path.name, {})

            topics.append({
                'file_path': file_path,
                'title': manifest_data.get('title', file_path.stem.replace('_', ' ').title()),
                'insights_count': len(manifest_data.get('key_insights', [])),
                'quotes_count': len(manifest_data.get('notable_quotes', [])),
                'size': manifest_data.get('word_count', 0),
                'description': manifest_data.get('description', ''),
                'manifest_data': manifest_data  # Store full manifest data for later use
            })
            self.logger.debug(f"Parsed topic from manifest: {topics[-1]['title']} ({topics[-1]['size']} words)")

        return topics

    def _display_topics_table(self, topics: List[Dict]):
        """Display topics in a rich table"""
        table = Table(title=f"📋 Generated Topics ({len(topics)} found)", show_header=True, show_lines=True)
        table.add_column("#", style="cyan", width=3)
        table.add_column("Title", style="bold", width=35)
        table.add_column("Description", style="dim", width=110)
        table.add_column("Words", justify="right", width=7)

        for i, topic in enumerate(topics, 1):
            desc = topic.get('description', '')
            desc_preview = desc[:160] + '...' if len(desc) > 160 else desc

            table.add_row(
                str(i),
                topic['title'][:33],
                desc_preview,
                str(topic['size'])
            )

        self.console.print(table)

    def _preview_topics(self, topics: List[Dict]):
        """Show preview of topics if user requests it"""
        if Confirm.ask("\n[yellow]Would you like to preview topics before selecting?[/yellow]", default=False):
            self.logger.info("User requested topic preview")
            for i, topic in enumerate(topics, 1):
                self.console.print(f"\n[bold cyan]{i}. {topic['title']}[/bold cyan]")
                self.console.print(f"[dim]File: {topic['file_path'].name}[/dim]")
                with open(topic['file_path'], 'r') as f:
                    preview = f.read()[:500]
                self.console.print(Markdown(preview))
                if i < len(topics):
                    if not Confirm.ask("Continue to next topic?", default=True):
                        break

    def _select_topics(self, topics: List[Dict]) -> List[Dict]:
        """Interactive selection of topics using checkbox interface"""
        self.console.print("\n")
        choices = []
        for i, topic in enumerate(topics, 1):
            # Build choice text with title and description preview
            title = topic['title'][:70]
            desc = topic.get('description', '')

            if desc:
                # Show first 160 chars of description
                desc_preview = desc[:160] + '...' if len(desc) > 160 else desc
                choice_text = f"{i}. {title}\n   → {desc_preview}"
            else:
                choice_text = f"{i}. {title}"

            choices.append(choice_text)

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
            self.logger.info("No topics selected by user")
            return []

        # Extract selected indices
        selected_indices = []
        for selection in answers['selected']:
            idx = int(selection.split('.')[0]) - 1
            selected_indices.append(idx)

        selected = [topics[i] for i in selected_indices]
        self.logger.info(f"User selected {len(selected)} topics: {[t['title'] for t in selected]}")

        return selected

    def _display_parameters(self, selected_topics: List[Dict]):
        """Display document generation parameters"""
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

    def _confirm_parameters(self, selected_topics: List[Dict]) -> bool:
        """Display parameters and get confirmation"""
        self._display_parameters(selected_topics)
        return Confirm.ask("\n[bold]Proceed with document generation?[/bold]", default=True)

    def _run_stage2(self, selected_topics: List[Dict]) -> List[Dict]:
        """Run PersonalizedDocGenerator for each selected topic"""
        self.logger.debug("Entering _run_stage2")
        documents = []
        mode = self.config.doc_mode_override or self.config.global_mode
        self.logger.info(f"Stage 2 will generate {len(selected_topics)} documents using mode: {mode}")

        with Progress(console=self.console) as progress:
            task = progress.add_task(
                "[cyan]Generating documents...",
                total=len(selected_topics)
            )

            for i, topic in enumerate(selected_topics, 1):
                self.logger.info(f"Generating document {i}/{len(selected_topics)}: {topic['title']}")
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

                self.logger.debug(f"Executing: {' '.join(cmd)}")

                # Run document generator
                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=self.config.stage2_timeout
                    )

                    if result.returncode != 0:
                        self.logger.error(f"Document generation failed for '{topic['title']}' with return code {result.returncode}")
                        self.logger.error(f"stderr: {result.stderr[:500]}")
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
                        self.logger.info(f"Successfully generated document for '{topic['title']}'")
                        self.logger.debug(f"stdout: {result.stdout[:200]}")
                        documents.append({
                            'topic': topic['title'],
                            'status': 'success',
                            'output': result.stdout
                        })
                except subprocess.TimeoutExpired:
                    self.logger.error(f"Document generation timed out for '{topic['title']}' after {self.config.stage2_timeout} seconds")
                    self.console.print(f"\n[red]✗ Timeout generating document for: {topic['title']}[/red]")
                    documents.append({
                        'topic': topic['title'],
                        'status': 'failed',
                        'error': f'Timeout after {self.config.stage2_timeout} seconds'
                    })

                progress.update(task, advance=1)

        successful = len([d for d in documents if d['status'] == 'success'])
        self.logger.info(f"Stage 2 complete: {successful}/{len(documents)} documents generated successfully")
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

        # Send notification
        if successful > 0:
            output_dir = Path(self.config.doc_output)
            if not output_dir.is_absolute():
                output_dir = Path.cwd() / output_dir
            self._send_document_notification(self.session_id, successful, output_dir)

    # ===== SESSION STATE MANAGEMENT =====

    def _get_session_state_file(self, session_id: str = None) -> Path:
        """Get path to session state file"""
        sid = session_id or self.session_id
        return Path.cwd() / "sessions" / sid / "session_state.json"

    def _get_pending_index_file(self) -> Path:
        """Get path to pending sessions index"""
        return Path.cwd() / "sessions" / "pending_reviews.json"

    def _save_session_state(self, stage: str, topics: List[Dict] = None, selected_topics: List[Dict] = None, documents: List[Dict] = None):
        """Save current session state"""
        state_file = self._get_session_state_file()

        state = {
            'session_id': self.session_id,
            'config_file': getattr(self, 'config_path', None),
            'config_snapshot': asdict(self.config),
            'stage': stage,
            'created_at': state_file.exists() and json.loads(state_file.read_text()).get('created_at') or datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'topics': topics or [],
            'selected_topics': selected_topics,
            'generated_documents': documents or []
        }

        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2, default=str)

        self.logger.info(f"Session state saved: stage={stage}, session={self.session_id}")

    def _load_session_state(self, session_id: str) -> Dict:
        """Load session state from file"""
        state_file = self._get_session_state_file(session_id)

        if not state_file.exists():
            raise FileNotFoundError(f"Session {session_id} not found at {state_file}")

        with open(state_file, 'r') as f:
            state = json.load(f)

        self.logger.info(f"Loaded session state: stage={state['stage']}, session={session_id}")
        return state

    def _add_to_pending_reviews(self):
        """Add session to pending reviews index"""
        index_file = self._get_pending_index_file()

        # Load existing index
        if index_file.exists():
            with open(index_file, 'r') as f:
                index = json.load(f)
        else:
            index = {'pending_reviews': [], 'reviewed_awaiting_generation': []}

        # Add to pending reviews
        index['pending_reviews'].append({
            'session_id': self.session_id,
            'created_at': datetime.now().isoformat(),
            'topic_count': len(self._parse_topic_files(list(self.topics_dir.glob("topic_*.md")))),
            'config_name': self.config.name
        })

        # Write index
        index_file.parent.mkdir(parents=True, exist_ok=True)
        with open(index_file, 'w') as f:
            json.dump(index, f, indent=2)

        self.logger.info(f"Added session {self.session_id} to pending reviews")

    def _move_to_awaiting_generation(self, session_id: str, selected_count: int):
        """Move session from pending reviews to awaiting generation"""
        index_file = self._get_pending_index_file()

        if not index_file.exists():
            return

        with open(index_file, 'r') as f:
            index = json.load(f)

        # Remove from pending reviews
        index['pending_reviews'] = [s for s in index['pending_reviews'] if s['session_id'] != session_id]

        # Add to awaiting generation
        index['reviewed_awaiting_generation'].append({
            'session_id': session_id,
            'reviewed_at': datetime.now().isoformat(),
            'selected_count': selected_count
        })

        with open(index_file, 'w') as f:
            json.dump(index, f, indent=2)

        self.logger.info(f"Moved session {session_id} to awaiting generation")

    def _remove_from_awaiting_generation(self, session_id: str):
        """Remove session from awaiting generation after docs are created"""
        index_file = self._get_pending_index_file()

        if not index_file.exists():
            return

        with open(index_file, 'r') as f:
            index = json.load(f)

        # Remove from awaiting generation
        index['reviewed_awaiting_generation'] = [s for s in index['reviewed_awaiting_generation'] if s['session_id'] != session_id]

        with open(index_file, 'w') as f:
            json.dump(index, f, indent=2)

        self.logger.info(f"Removed session {session_id} from awaiting generation (completed)")

    def _send_document_notification(self, session_id: str, document_count: int, output_dir: Path):
        """Send notification (Slack or desktop) when documents are generated"""
        # Load notification settings from scheduler config if available
        scheduler_config_path = Path.cwd().parent / 'DocOrchestrationScheduler' / 'schedules.yaml'
        notification_type = 'desktop'  # Default fallback
        slack_webhook = None

        if scheduler_config_path.exists():
            try:
                with open(scheduler_config_path, 'r') as f:
                    scheduler_config = yaml.safe_load(f)
                    notifications = scheduler_config.get('notifications', {})
                    if notifications.get('enabled', False):
                        notification_type = notifications.get('type', 'slack')
                        slack_webhook = notifications.get('slack', {}).get('webhook_url')
            except Exception as e:
                self.logger.warning(f"Failed to load scheduler config for notifications: {e}")

        # Send appropriate notification
        if notification_type == 'slack' and slack_webhook:
            self._send_slack_document_notification(session_id, document_count, output_dir, slack_webhook)
        else:
            self._send_desktop_document_notification(session_id, document_count, output_dir)

    def _send_slack_document_notification(self, session_id: str, document_count: int, output_dir: Path, webhook_url: str):
        """Send Slack notification for document completion"""
        try:
            import requests
        except ImportError:
            self.logger.warning("requests module not installed. Skipping Slack notification.")
            return

        # Build Slack message with action button
        view_docs_url = f"qwilo://view-documents?session={session_id}"

        message = {
            "text": f"📄 *Blog Posts Generated!*",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "📄 Blog Posts Generated!",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Documents Created:*\n{document_count}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Session ID:*\n`{session_id}`"
                        }
                    ]
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "📁 Open Documents Folder",
                                "emoji": True
                            },
                            "url": view_docs_url,
                            "style": "primary"
                        }
                    ]
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"_Output Location: `{output_dir}`_"
                        }
                    ]
                }
            ]
        }

        try:
            response = requests.post(webhook_url, json=message, timeout=10)
            if response.status_code == 200:
                self.logger.info(f"Slack document notification sent for session {session_id}")
            else:
                self.logger.warning(f"Slack document notification failed: HTTP {response.status_code}")
        except Exception as e:
            self.logger.warning(f"Failed to send Slack document notification: {e}")

    def _send_desktop_document_notification(self, session_id: str, document_count: int, output_dir: Path):
        """Send desktop notification for document completion"""
        try:
            # Find Qwilo logo
            logo_path = Path(__file__).parent.parent / 'DocIdeaGenerator' / 'qwilo_logo.png'

            # Build notification command
            cmd = [
                'terminal-notifier',
                '-title', '📄 Blog Posts Generated!',
                '-message', f'Generated {document_count} blog post(s)! 👆 Click to open folder.\n\nSession: {session_id}',
                '-sound', 'default',
                '-timeout', '30',
                '-execute', f'open "{output_dir.absolute()}"'
            ]

            # Add logo if it exists
            if logo_path.exists():
                cmd.extend(['-contentImage', str(logo_path)])

            # Send notification
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                self.logger.info(f"Desktop document notification sent for session {session_id}")
            else:
                self.logger.warning(f"Failed to send desktop document notification: {result.stderr}")

        except FileNotFoundError:
            self.logger.warning("terminal-notifier not found. Skipping notification.")
        except Exception as e:
            self.logger.warning(f"Error sending desktop document notification: {e}")

    # ===== STAGED EXECUTION METHODS =====

    def run_generate_ideas(self):
        """Stage 1: Generate ideas only"""
        self.logger.info(f"Starting staged execution - Stage 1: Idea Generation")
        self.console.print(Panel.fit(
            f"[bold cyan]{self.config.name}[/bold cyan]\n"
            f"Mode: [yellow]{self.config.global_mode}[/yellow]\n"
            f"Session: [dim]{self.session_id}[/dim]\n"
            f"Stage: [green]1 - Generate Ideas[/green]",
            title="🚀 DocOrchestrator - Staged Execution"
        ))

        try:
            # Run Stage 1
            self.console.print("\n[bold]Stage 1: Generating Topic Ideas[/bold]")
            topic_files = self._run_stage1()

            if not topic_files:
                self.logger.warning("No topic files generated")
                self.console.print("[yellow]No topic files generated. Exiting.[/yellow]")
                return 1

            # Parse topics for state
            topics = self._parse_topic_files(topic_files)

            # Save session state
            self._save_session_state(stage="ideas_generated", topics=topics)
            self._add_to_pending_reviews()

            # Summary
            self.console.print(f"\n[green]✓[/green] Generated {len(topics)} topic(s)")
            self.console.print(f"[cyan]Session ID:[/cyan] {self.session_id}")
            self.console.print(f"[dim]Use this command to review: python orchestrator.py --review --session {self.session_id}[/dim]")

            return 0

        except Exception as e:
            self.logger.error(f"Error in idea generation: {e}", exc_info=True)
            self.console.print(f"\n[red]Error: {e}[/red]")
            return 1

    def run_review_session(self, session_id: str):
        """Stage 2: Review a single session"""
        self.logger.info(f"Starting staged execution - Stage 2: Review Session {session_id}")

        try:
            # Load session state
            state = self._load_session_state(session_id)

            if state['stage'] != 'ideas_generated':
                self.console.print(f"[yellow]Warning: Session {session_id} is in stage '{state['stage']}', not 'ideas_generated'[/yellow]")
                if state['stage'] == 'reviewed':
                    self.console.print(f"[dim]Session already reviewed. Use --generate-docs to create documents.[/dim]")
                    return 0
                elif state['stage'] == 'completed':
                    self.console.print(f"[dim]Session already completed.[/dim]")
                    return 0

            # Load config from state
            self.config = OrchestratorConfig(**state['config_snapshot'])
            self.session_id = session_id
            self.session_dir = Path.cwd() / "sessions" / session_id

            # Display session info
            self.console.print(Panel.fit(
                f"[bold cyan]{self.config.name}[/bold cyan]\n"
                f"Session: [dim]{session_id}[/dim]\n"
                f"Created: [dim]{state['created_at']}[/dim]\n"
                f"Topics: [yellow]{len(state['topics'])}[/yellow]\n"
                f"Stage: [green]2 - Review & Select[/green]",
                title="🚀 DocOrchestrator - Review Session"
            ))

            # Reconstruct topic objects with file paths
            topics = []
            for topic_data in state['topics']:
                topics.append({
                    'file_path': Path(topic_data['file_path']),
                    'title': topic_data['title'],
                    'size': topic_data['size'],
                    'insights_count': topic_data.get('insights_count', 0),
                    'quotes_count': topic_data.get('quotes_count', 0)
                })

            # Interactive review
            self.console.print(f"\n[bold]Stage 2: Review and Select Topics[/bold]")
            selected_topics = self._interactive_review(topics)

            if not selected_topics:
                self.logger.info("No topics selected by user")
                self.console.print("[yellow]No topics selected. Session remains in 'ideas_generated' stage.[/yellow]")
                return 0

            # Save updated state
            self._save_session_state(
                stage="reviewed",
                topics=state['topics'],
                selected_topics=[{'title': t['title'], 'file_path': str(t['file_path'])} for t in selected_topics]
            )
            self._move_to_awaiting_generation(session_id, len(selected_topics))

            # Summary
            self.console.print(f"\n[green]✓[/green] Selected {len(selected_topics)} topic(s) for document generation")
            self.console.print(f"[dim]Use this command to generate documents: python orchestrator.py --generate-docs --session {session_id}[/dim]")

            return 0

        except Exception as e:
            self.logger.error(f"Error in review: {e}", exc_info=True)
            self.console.print(f"\n[red]Error: {e}[/red]")
            return 1

    def run_generate_documents(self, session_id: str):
        """Stage 3: Generate documents from reviewed session"""
        self.logger.info(f"Starting staged execution - Stage 3: Generate Documents for Session {session_id}")

        try:
            # Load session state
            state = self._load_session_state(session_id)

            if state['stage'] != 'reviewed':
                self.console.print(f"[red]Error: Session {session_id} is in stage '{state['stage']}', expected 'reviewed'[/red]")
                if state['stage'] == 'ideas_generated':
                    self.console.print(f"[dim]Session not yet reviewed. Use --review to select topics first.[/dim]")
                elif state['stage'] == 'completed':
                    self.console.print(f"[dim]Session already completed.[/dim]")
                return 1

            # Load config from state
            self.config = OrchestratorConfig(**state['config_snapshot'])
            self.session_id = session_id
            self.session_dir = Path.cwd() / "sessions" / session_id

            # Display session info
            self.console.print(Panel.fit(
                f"[bold cyan]{self.config.name}[/bold cyan]\n"
                f"Session: [dim]{session_id}[/dim]\n"
                f"Selected Topics: [yellow]{len(state['selected_topics'])}[/yellow]\n"
                f"Stage: [green]3 - Generate Documents[/green]",
                title="🚀 DocOrchestrator - Generate Documents"
            ))

            # Reconstruct selected topics with file paths
            selected_topics = []
            for topic_data in state['selected_topics']:
                selected_topics.append({
                    'title': topic_data['title'],
                    'file_path': Path(topic_data['file_path'])
                })

            # Generate documents
            self.console.print(f"\n[bold]Stage 3: Generating Documents[/bold]")
            documents = self._run_stage2(selected_topics)

            # Save updated state
            self._save_session_state(
                stage="completed",
                topics=state['topics'],
                selected_topics=state['selected_topics'],
                documents=documents
            )
            self._remove_from_awaiting_generation(session_id)

            # Summary
            successful = len([d for d in documents if d['status'] == 'success'])
            self.console.print(f"\n[green]✓[/green] Generated {successful}/{len(documents)} document(s) successfully")
            self.console.print(f"[cyan]Session completed:[/cyan] {session_id}")

            # Send notification
            if successful > 0:
                output_dir = Path(self.config.doc_output)
                if not output_dir.is_absolute():
                    output_dir = Path.cwd() / output_dir
                self._send_document_notification(session_id, successful, output_dir)

            return 0

        except Exception as e:
            self.logger.error(f"Error in document generation: {e}", exc_info=True)
            self.console.print(f"\n[red]Error: {e}[/red]")
            return 1

    # ===== CLASS METHODS FOR SESSION MANAGEMENT =====

    @classmethod
    def from_session(cls, session_id: str, auto_confirm: bool = False):
        """Create orchestrator from existing session"""
        state_file = Path.cwd() / "sessions" / session_id / "session_state.json"

        if not state_file.exists():
            raise FileNotFoundError(f"Session {session_id} not found")

        with open(state_file, 'r') as f:
            state = json.load(f)

        # Reconstruct config
        config = OrchestratorConfig(**state['config_snapshot'])

        return cls(config=config, auto_confirm=auto_confirm, session_id=session_id)

    @classmethod
    def list_pending_sessions(cls):
        """List all sessions pending review"""
        console = Console()
        index_file = Path.cwd() / "sessions" / "pending_reviews.json"

        if not index_file.exists():
            console.print("[yellow]No pending sessions found.[/yellow]")
            return

        with open(index_file, 'r') as f:
            index = json.load(f)

        pending = index.get('pending_reviews', [])

        if not pending:
            console.print("[yellow]No sessions pending review.[/yellow]")
            return

        table = Table(title=f"📋 Pending Reviews ({len(pending)} sessions)")
        table.add_column("Session ID", style="cyan")
        table.add_column("Created", style="dim")
        table.add_column("Topics", justify="right")
        table.add_column("Config Name", style="green")

        for session in pending:
            created = datetime.fromisoformat(session['created_at']).strftime("%Y-%m-%d %H:%M")
            table.add_row(
                session['session_id'],
                created,
                str(session['topic_count']),
                session['config_name']
            )

        console.print(table)
        console.print(f"\n[dim]Review a session: python orchestrator.py --review --session <SESSION_ID>[/dim]")

    @classmethod
    def list_all_sessions(cls):
        """List all sessions with their status"""
        console = Console()
        sessions_dir = Path.cwd() / "sessions"

        if not sessions_dir.exists():
            console.print("[yellow]No sessions found.[/yellow]")
            return

        # Collect all sessions
        sessions = []
        for session_dir in sorted(sessions_dir.iterdir()):
            if not session_dir.is_dir() or session_dir.name == '__pycache__':
                continue

            state_file = session_dir / "session_state.json"
            if state_file.exists():
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    sessions.append(state)

        if not sessions:
            console.print("[yellow]No sessions with state found.[/yellow]")
            return

        table = Table(title=f"📊 All Sessions ({len(sessions)} total)")
        table.add_column("Session ID", style="cyan")
        table.add_column("Stage", style="yellow")
        table.add_column("Topics", justify="right")
        table.add_column("Selected", justify="right")
        table.add_column("Updated", style="dim")

        for state in sessions:
            updated = datetime.fromisoformat(state['updated_at']).strftime("%Y-%m-%d %H:%M")
            stage_display = {
                'ideas_generated': '1️⃣  Ideas',
                'reviewed': '2️⃣  Reviewed',
                'completed': '✅ Complete'
            }.get(state['stage'], state['stage'])

            table.add_row(
                state['session_id'],
                stage_display,
                str(len(state.get('topics', []))),
                str(len(state.get('selected_topics', []))) if state.get('selected_topics') else '-',
                updated
            )

        console.print(table)

    @classmethod
    def generate_all_pending_documents(cls):
        """Generate documents for all sessions awaiting generation (automated mode)"""
        console = Console()
        index_file = Path.cwd() / "sessions" / "pending_reviews.json"

        if not index_file.exists():
            console.print("[yellow]No pending reviews index found.[/yellow]")
            return 0

        with open(index_file, 'r') as f:
            index = json.load(f)

        awaiting = index.get('reviewed_awaiting_generation', [])

        if not awaiting:
            console.print("[dim]No sessions awaiting document generation.[/dim]")
            return 0

        console.print(f"\n[bold cyan]Found {len(awaiting)} session(s) awaiting document generation[/bold cyan]\n")

        success_count = 0
        failed_count = 0

        for session_info in awaiting:
            session_id = session_info['session_id']
            topic_count = session_info.get('selected_count', 0)

            console.print(f"[cyan]Processing session {session_id}[/cyan] ({topic_count} topics)")

            try:
                # Create orchestrator from session
                orchestrator = cls.from_session(session_id, auto_confirm=True)
                result = orchestrator.run_generate_documents(session_id)

                if result == 0:
                    success_count += 1
                    console.print(f"[green]✓ Session {session_id} completed[/green]\n")
                else:
                    failed_count += 1
                    console.print(f"[red]✗ Session {session_id} failed[/red]\n")

            except Exception as e:
                failed_count += 1
                console.print(f"[red]✗ Error processing session {session_id}: {e}[/red]\n")
                import traceback
                traceback.print_exc()

        # Summary
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  Successful: [green]{success_count}[/green]")
        console.print(f"  Failed: [red]{failed_count}[/red]")

        return 0 if failed_count == 0 else 1


def main():
    parser = argparse.ArgumentParser(
        description="Your Personalized Idea and Document Creator - Content Generation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # FULL SEQUENTIAL MODE (default - unchanged behavior)
  python orchestrator.py --config my_pipeline.yaml

  # STAGED EXECUTION MODE

  # Stage 1: Generate ideas only
  python orchestrator.py --config my_pipeline.yaml --generate-ideas

  # Stage 2: Review pending ideas
  python orchestrator.py --review --session 20251111_120000

  # Stage 3: Generate documents from reviewed session
  python orchestrator.py --generate-docs --session 20251111_120000

  # UTILITY COMMANDS

  # List sessions pending review
  python orchestrator.py --list-pending

  # List all sessions with status
  python orchestrator.py --list-sessions
        """
    )

    parser.add_argument(
        "-c", "--config",
        help="Path to YAML configuration file (required for full/generate-ideas mode)"
    )

    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Auto-confirm all prompts (non-interactive mode)"
    )

    # Execution modes (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--generate-ideas",
        action="store_true",
        help="Stage 1: Generate ideas only (creates session)"
    )
    mode_group.add_argument(
        "--review",
        action="store_true",
        help="Stage 2: Review pending ideas"
    )
    mode_group.add_argument(
        "--generate-docs",
        action="store_true",
        help="Stage 3: Generate documents from reviewed session"
    )
    mode_group.add_argument(
        "--list-pending",
        action="store_true",
        help="List sessions pending review"
    )
    mode_group.add_argument(
        "--list-sessions",
        action="store_true",
        help="List all sessions with status"
    )
    mode_group.add_argument(
        "--generate-all-pending",
        action="store_true",
        help="Generate documents for all sessions awaiting generation (automated mode)"
    )

    # Session selection
    parser.add_argument(
        "--session",
        help="Specific session ID (required for --review and --generate-docs)"
    )

    args = parser.parse_args()

    try:
        # Utility commands (no config needed)
        if args.list_pending:
            DocOrchestrator.list_pending_sessions()
            return 0

        if args.list_sessions:
            DocOrchestrator.list_all_sessions()
            return 0

        if args.generate_all_pending:
            return DocOrchestrator.generate_all_pending_documents()

        # Staged execution modes
        if args.generate_ideas:
            if not args.config:
                parser.error("--generate-ideas requires --config")
            orchestrator = DocOrchestrator(args.config, auto_confirm=args.yes)
            return orchestrator.run_generate_ideas()

        if args.review:
            if not args.session:
                parser.error("--review requires --session")
            # Create minimal orchestrator for review
            orchestrator = DocOrchestrator.from_session(args.session, auto_confirm=args.yes)
            return orchestrator.run_review_session(args.session)

        if args.generate_docs:
            if not args.session:
                parser.error("--generate-docs requires --session")
            orchestrator = DocOrchestrator.from_session(args.session, auto_confirm=args.yes)
            return orchestrator.run_generate_documents(args.session)

        # Default: full sequential mode
        if not args.config:
            parser.error("--config is required for full sequential mode")
        orchestrator = DocOrchestrator(args.config, auto_confirm=args.yes)
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
