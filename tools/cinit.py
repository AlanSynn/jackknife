#!/usr/bin/env python3

"""
Jackknife tool to manage Cursor rules.

- `link`: Interactively creates symbolic links for rules from ~/.cursor/rules/
          to the current directory.
- `add`: Copies a local rule script to ~/.cursor/rules/ and optionally links it.
"""

import functools
import os
import shutil
import subprocess
from pathlib import Path

import typer


# --- Configuration ---
RULES_SOURCE_DIR = Path.home() / ".cursor" / "rules"
TARGET_DIR = Path.cwd()  # Link rules into the current working directory


app = typer.Typer(
    name="cinit",
    help="Manage Cursor rules: link, add, or edit rules.",
    add_completion=False,
)

# --- Lazy Loaded Console Getters ---


@functools.lru_cache(maxsize=1)
def _get_console():  # --> Console # noqa: F821 ANN202
    """Lazy load rich console."""
    from rich.console import Console

    console = Console()
    return console


@functools.lru_cache(maxsize=1)
def _get_console_stderr():  # --> Console # noqa: F821 ANN202
    """Lazy load rich stderr console."""
    from rich.console import Console

    console_stderr = Console(stderr=True)
    return console_stderr


# --- Helper Function for Symlinking ---


def _create_symlink(rule_name: str, source_dir: Path, dest_dir: Path) -> bool:
    console = _get_console()
    console_stderr = _get_console_stderr()
    source_path = source_dir / rule_name
    dest_path = dest_dir / rule_name

    if not source_path.exists():
        console_stderr.print(
            f"  [bold red]Error:[/] Source does not exist: {source_path}"
        )
        return False

    if dest_path.exists() or dest_path.is_symlink():
        console.print(
            f"  [yellow]Skipping:[/] '{rule_name}' - Destination already exists at [dim]{dest_path}[/]"
        )
        return False  # Indicate skipped, not error

    try:
        is_dir = source_path.is_dir()
        os.symlink(source_path, dest_path, target_is_directory=is_dir)
    except OSError as e:
        console_stderr.print(
            f"  [bold red]Error:[/]    Failed to link '{rule_name}': {e}"
        )
        return False
    except Exception as e:
        console_stderr.print(
            f"  [bold red]Error:[/]    Unexpected error linking '{rule_name}': {e}"
        )
        return False
    else:
        console.print(f"  [green]Linked:[/]   '{rule_name}' -> [dim]{source_path}[/]")
        return True


# --- Typer Commands ---


@app.command("link")
def link_rules() -> None:  # noqa: C901 PLR0912
    """Interactively select and symlink rules from ~/.cursor/rules/ to the current directory."""
    # Import required libraries here
    import questionary

    console = _get_console()
    console_stderr = _get_console_stderr()

    target_link_dir = TARGET_DIR / ".cursor" / "rules"  # Define specific target subdir

    console.print("[bold cyan]Link Cursor Rules[/]")
    console.print(f"Source directory: [dim]{RULES_SOURCE_DIR}[/]")
    console.print(f"Target link directory: [dim]{target_link_dir}[/]")

    # Ensure source directory exists, create if not
    if not RULES_SOURCE_DIR.is_dir():
        console.print(
            f"[info]Source directory {RULES_SOURCE_DIR} not found. Creating it...[/]"
        )
        try:
            RULES_SOURCE_DIR.mkdir(parents=True, exist_ok=True)
            console.print(f"[success]Created directory: {RULES_SOURCE_DIR}[/]")
        except OSError as e:
            console_stderr.print(
                f"[bold red]Error:[/] Could not create source directory {RULES_SOURCE_DIR}: {e}"
            )
            raise typer.Exit(code=1) from e

    # Ensure target link directory exists, create if not
    try:
        target_link_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        console_stderr.print(
            f"[bold red]Error:[/] Could not create target link directory {target_link_dir}: {e}"
        )
        raise typer.Exit(code=1) from e

    # List available rules (logic remains the same)
    try:
        available_rules = sorted([item.name for item in RULES_SOURCE_DIR.iterdir()])
    except OSError as e:
        console_stderr.print(
            f"[bold red]Error:[/] Failed to list rules in {RULES_SOURCE_DIR}: {e}"
        )
        raise typer.Exit(code=1) from e

    if not available_rules:
        console.print(
            f"[yellow]No rules found in {RULES_SOURCE_DIR}. Nothing to link.[/]"
        )
        raise typer.Exit()

    # Select rules (logic remains the same)
    try:
        selected_rules = questionary.checkbox(
            "Select rules to link to the current directory:",
            choices=available_rules,
            qmark="?",  # Changed back to string
        ).ask()
    except UnicodeDecodeError:
        # Fallback should also use string
        selected_rules = questionary.checkbox(
            "Select rules to link to the current directory:",
            choices=available_rules,
            qmark="?",
        ).ask()
    except Exception as e:
        console_stderr.print(f"[bold red]Error displaying selection prompt:[/] {e}")
        raise typer.Exit(code=1) from e
    except KeyboardInterrupt:
        console_stderr.print("\n[yellow]Operation cancelled by user.[/]")
        raise typer.Exit(code=130) from None

    if not selected_rules:
        console.print("[yellow]No rules selected. Exiting.[/]")
        raise typer.Exit()

    console.print(
        f"\nAttempting to link {len(selected_rules)} selected rules to {target_link_dir}:"
    )
    success_count = 0
    error_count = 0

    # Link selected rules to the target subdir
    for rule_name in selected_rules:
        if _create_symlink(rule_name, RULES_SOURCE_DIR, target_link_dir):
            success_count += 1
        else:
            dest_path = target_link_dir / rule_name  # Check against correct target
            if not (dest_path.exists() or dest_path.is_symlink()):
                error_count += 1

    # Summary (remains the same conceptually)
    console.print("\n[bold cyan]Link Summary:[/]")
    console.print(f"  Successfully linked: [green]{success_count}[/]")
    # Skipped count is implicitly len(selected_rules) - success_count - error_count
    skipped_count = len(selected_rules) - success_count - error_count
    console.print(f"  Skipped (exists):  [yellow]{skipped_count}[/]")
    console.print(f"  Errors:            [red]{error_count}[/]")

    if error_count > 0:
        raise typer.Exit(code=1)


@app.command("add")
def add_rule(  # noqa: C901 PLR0912
    script_path: Path = typer.Argument(  # noqa: B008
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Path to the rule script file (e.g., my_rule.mdc) to add.",
    ),
) -> None:
    """Copies a rule script to ~/.cursor/rules/ and optionally creates a symlink here."""
    # Import required libraries here
    import questionary

    console = _get_console()
    console_stderr = _get_console_stderr()

    rule_name = script_path.name
    dest_rule_path = RULES_SOURCE_DIR / rule_name

    console.print("[bold cyan]Add Cursor Rule[/]")
    console.print(f"Source script: [dim]{script_path}[/]")
    console.print(f"Target directory: [dim]{RULES_SOURCE_DIR}[/]")
    console.print(f"Target rule name: [dim]{rule_name}[/]")

    # 1. Ensure target directory exists
    try:
        RULES_SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        console_stderr.print(
            f"[bold red]Error:[/] Could not create target directory {RULES_SOURCE_DIR}: {e}"
        )
        raise typer.Exit(code=1) from e

    # 2. Check if rule already exists in target dir and ask to overwrite
    should_copy = True
    if dest_rule_path.exists():
        console.print(
            f"[yellow]Warning:[/] Rule '{rule_name}' already exists in {RULES_SOURCE_DIR}."
        )
        try:
            overwrite = questionary.confirm(
                f"Overwrite existing rule '{rule_name}'?", default=False
            ).ask()
            if not overwrite:
                console.print("[yellow]Skipping copy operation.[/]")
                should_copy = False
        except KeyboardInterrupt:
            console_stderr.print("\n[yellow]Operation cancelled by user.[/]")
            raise typer.Exit(code=130) from None
        except Exception as e:
            console_stderr.print(f"[bold red]Error during confirmation:[/] {e}")
            raise typer.Exit(code=1) from e

    # 3. Copy the file if needed
    copy_success = False
    if should_copy:
        console.print(f"Copying '{script_path.name}' to {RULES_SOURCE_DIR}...")
        try:
            shutil.copy2(script_path, dest_rule_path)
            console.print(f"[green]Successfully copied '{rule_name}'.[/]")
            copy_success = True
        except Exception as e:
            console_stderr.print(f"[bold red]Error:[/] Failed to copy script: {e}")
            raise typer.Exit(code=1) from e

    # 4. Ask to create symlink in current directory
    if copy_success or not should_copy:  # Ask even if copy was skipped but file exists
        if dest_rule_path.exists():  # Ensure source rule exists before asking to link
            console.print("")  # Spacer
            target_link_dir = (
                TARGET_DIR / ".cursor" / "rules"
            )  # Define specific target subdir
            try:
                # Updated confirmation message
                create_link = questionary.confirm(
                    f"Create a symlink for '{rule_name}' in ./.cursor/rules/ ({target_link_dir})?",
                    default=True,
                ).ask()
            except KeyboardInterrupt:
                console_stderr.print("\n[yellow]Operation cancelled by user.[/]")
                raise typer.Exit(code=130) from None
            except Exception as e:
                console_stderr.print(f"[bold red]Error during confirmation:[/] {e}")
                raise typer.Exit(code=1) from e

            if create_link:
                # Ensure target link directory exists, create if not
                try:
                    target_link_dir.mkdir(parents=True, exist_ok=True)
                except OSError as e:
                    console_stderr.print(
                        f"[bold red]Error:[/] Could not create target link directory {target_link_dir}: {e}"
                    )
                    # Don't exit, just report error and skip linking
                    console.print(
                        "[yellow]Symlink creation skipped due to directory error.[/]"
                    )
                else:
                    # Attempt to link to the target subdir
                    console.print(
                        f"Attempting to link '{rule_name}' to {target_link_dir}..."
                    )
                    if not _create_symlink(
                        rule_name, RULES_SOURCE_DIR, target_link_dir
                    ):
                        # Error/skip message printed by helper
                        console.print("[yellow]Symlink creation skipped or failed.[/]")
                        # Don't exit with error if only linking failed after successful add/confirmation
            else:
                console.print("[info]Skipping symlink creation.[/]")
        else:
            # Should not happen if copy_success is True, but defensive check
            console.print(
                f"[warning]Cannot link '{rule_name}' as it wasn't found in {RULES_SOURCE_DIR} after copy attempt.[/]"
            )


@app.command("edit")
def edit_rule() -> None:  # noqa: C901 PLR0912
    """Select a rule from ~/.cursor/rules/ and open it for editing."""
    # Import required libraries here
    import questionary

    console = _get_console()
    console_stderr = _get_console_stderr()

    console.print("[bold cyan]Edit Cursor Rule[/]")
    console.print(f"Rule directory: [dim]{RULES_SOURCE_DIR}[/]")

    # Ensure source directory exists, create if not
    if not RULES_SOURCE_DIR.is_dir():
        console.print(
            f"[info]Source directory {RULES_SOURCE_DIR} not found. Creating it...[/]"
        )
        try:
            RULES_SOURCE_DIR.mkdir(parents=True, exist_ok=True)
            console.print(f"[success]Created directory: {RULES_SOURCE_DIR}[/]")
        except OSError as e:
            console_stderr.print(
                f"[bold red]Error:[/] Could not create source directory {RULES_SOURCE_DIR}: {e}"
            )
            raise typer.Exit(code=1) from e
    # Proceed even if directory was just created (it will be empty)

    try:
        available_rules = sorted(
            [item.name for item in RULES_SOURCE_DIR.iterdir() if item.is_file()]
        )  # Only list files for editing
    except OSError as e:
        console_stderr.print(
            f"[bold red]Error:[/] Failed to list rules in {RULES_SOURCE_DIR}: {e}"
        )
        raise typer.Exit(code=1) from e

    if not available_rules:
        console.print(
            f"[yellow]No rule files found in {RULES_SOURCE_DIR}. Nothing to edit.[/]"
        )
        raise typer.Exit()

    try:
        rule_to_edit = questionary.select(
            "Select a rule file to edit:",
            choices=available_rules,
            qmark="?",  # Changed back to string
        ).ask()
    except UnicodeDecodeError:
        # Fallback should also use string
        rule_to_edit = questionary.select(
            "Select a rule file to edit:",
            choices=available_rules,
            qmark="?",
        ).ask()
    except Exception as e:
        console_stderr.print(f"[bold red]Error displaying selection prompt:[/] {e}")
        raise typer.Exit(code=1) from e
    except KeyboardInterrupt:
        console_stderr.print("\n[yellow]Operation cancelled by user.[/]")
        raise typer.Exit(code=130) from None

    if rule_to_edit is None:
        console.print("[yellow]No rule selected. Exiting.[/]")
        raise typer.Exit()

    rule_file_path = RULES_SOURCE_DIR / rule_to_edit

    # Determine the editor
    editor = os.environ.get("EDITOR")
    if not editor:
        if shutil.which("nano"):
            editor = "nano"
        elif shutil.which("vim"):
            editor = "vim"
        # Add more fallbacks like 'vi', 'emacs' if needed
        else:
            console_stderr.print(
                "[bold red]Error:[/] Could not determine editor. Set the $EDITOR environment variable."
            )
            raise typer.Exit(code=1)

    console.print(
        f"Opening [info]'{rule_file_path}'[/] with editor [info]'{editor}'[/]..."
    )

    try:
        # Run the editor. We don't check the return code, as closing the editor might return non-zero.
        subprocess.run([editor, str(rule_file_path)], check=False)  # noqa: S603
    except Exception as e:
        console_stderr.print(
            f"[bold red]Error:[/] Failed to launch editor '{editor}': {e}"
        )
        raise typer.Exit(code=1) from e

    console.print(f"Finished editing '{rule_to_edit}'.")


@app.callback()
def main_callback(ctx: typer.Context) -> None:
    """Main callback to handle cases where no command is given."""
    if ctx.invoked_subcommand is None:
        # Default to the link command if no subcommand is specified
        console = _get_console()
        console.print("[info]No command specified, defaulting to 'link'.[/]")
        ctx.invoke(link_rules)


if __name__ == "__main__":
    app()
