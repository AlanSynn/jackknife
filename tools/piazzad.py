#!/usr/bin/env python3

"""
Jackknife tool to download resources (files and links) from a Piazza course page.
Requires manual login via Selenium browser interaction.
"""

import functools  # For caching
import json
import re
import string
import time
import unicodedata
from pathlib import Path
from typing import Optional

# --- Standard Library Imports --- DONE
# --- Dependency Imports (Moved inside functions/getters) ---
# try:
#     import requests
#     import typer
#     from rich.console import Console
#     from selenium import webdriver
#     from selenium.common.exceptions import WebDriverException
#     from selenium.webdriver.chrome.service import Service as ChromeService
# except ImportError as e:
#     missing_module = getattr(e, "name", "dependency")
#     print(
#         f"Error: Missing dependency '{missing_module}'. Please ensure dependencies from piazzad.requirements.txt are installed.",
#         file=sys.stderr,
#     )
#     sys.exit(1)
# --- Typer App Setup (Typer needed at top level) ---
import typer


app = typer.Typer(
    name="piazzad",
    help="Download resources from a Piazza course page after manual login.",
    add_completion=False,
)


# --- Lazy Loaded Console Getters ---
@functools.lru_cache(maxsize=1)
def _get_console():
    from rich.console import Console

    return Console()


@functools.lru_cache(maxsize=1)
def _get_console_stderr():
    from rich.console import Console

    return Console(stderr=True)


# --- Helper Function ---
def sanitize_filename(filename: str) -> str:
    """Sanitizes a string to be used as a filename."""
    valid_filename_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    # Normalize unicode characters
    cleaned_filename = (
        unicodedata.normalize("NFKD", filename).encode("ASCII", "ignore").decode()
    )
    # Replace whitespace with underscore and keep only valid chars
    cleaned_filename = "_".join(cleaned_filename.split())
    cleaned_filename = "".join(c for c in cleaned_filename if c in valid_filename_chars)
    if not cleaned_filename:
        cleaned_filename = "_unnamed_file_"
    # Prevent excessively long filenames (common on cloud storage)
    return cleaned_filename[:150]


# --- Main Command ---
@app.command()
def main(
    url: str = typer.Argument(
        ..., help="The URL of the Piazza course *Resources* page."
    ),
    network_id: str = typer.Argument(
        ...,
        help="The Network ID (e.g., 'm3icaapxwwz1f5') found in Piazza URLs or network data.",
    ),
    output_dir: Path = typer.Option(
        Path("./piazza_downloads"),
        "--output-dir",
        "-o",
        help="Directory to save downloaded files and links.",
        writable=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    webdriver_path: Optional[Path] = typer.Option(
        None,
        "--webdriver-path",
        help="Optional path to the ChromeDriver executable.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    login_url: str = typer.Option(
        "https://piazza.com/account/login",
        help="URL of the Piazza login page.",
    ),
) -> None:
    """Downloads files and links from a Piazza resources page using Selenium and Requests."""
    # --- Import Dependencies Needed for Main Function ---
    import requests
    from selenium import webdriver
    from selenium.common.exceptions import WebDriverException
    from selenium.webdriver.chrome.service import Service as ChromeService

    try:
        # Questionary is optional for the prompt, handle if missing
        import questionary

        HAS_QUESTIONARY = True
    except ImportError:
        HAS_QUESTIONARY = False

    # --- Get Console Instances ---
    console = _get_console()
    console_stderr = _get_console_stderr()

    # --- Print Initial Info (Uses console) ---
    console.print("[bold cyan]Piazza Downloader (piazzad)[/]")
    console.print(f"Target Resources URL: [link={url}]{url}[/link]")
    console.print(f"Network ID: [bold magenta]{network_id}[/bold magenta]")
    console.print(f"Download Directory: [dim]{output_dir}[/]")
    if webdriver_path:
        console.print(f"WebDriver Path: [dim]{webdriver_path}[/]")
    console.print("---")

    # --- Initialization ---
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"Ensured download directory exists: {output_dir}")
    except OSError as e:
        console_stderr.print(
            f"[bold red]Error:[/] Could not create output directory {output_dir}: {e}"
        )
        raise typer.Exit(code=1) from e

    # Setup WebDriver options
    options = webdriver.ChromeOptions()
    # Add options if needed (e.g., headless)
    # options.add_argument("--headless")

    # Initialize WebDriver
    driver = None
    try:
        if webdriver_path:
            service = ChromeService(executable_path=str(webdriver_path))
        else:
            # Assume Selenium Manager handles it
            service = ChromeService()
        driver = webdriver.Chrome(service=service, options=options)
        console.print("[green]WebDriver initialized successfully.[/]")
    except WebDriverException as e:
        console_stderr.print(f"[bold red]Error initializing WebDriver:[/] {e.message}")
        console_stderr.print(
            "[info]Ensure ChromeDriver is installed and accessible.[/]"
        )
        console_stderr.print(
            "[info]Try `pip install --upgrade selenium` or specify --webdriver-path.[/]"
        )
        raise typer.Exit(code=1) from e
    except Exception as e:
        console_stderr.print(
            f"[bold red]Unexpected error initializing WebDriver:[/] {e}"
        )
        raise typer.Exit(code=1) from e

    # --- Main Logic --- #
    session = None  # Initialize session
    try:
        # --- Login --- #
        console.print(f"Navigating to login page: {login_url}")
        driver.get(login_url)
        console.print(
            "[bold yellow]>>> Please log in to Piazza in the browser window now. <<<[/]"
        )
        try:
            # Use questionary for a slightly nicer prompt
            questionary.confirm(
                "Press Enter here after you have successfully logged in...",
                default=True,
            ).ask()
        except NameError:
            # Fallback if questionary somehow failed to import earlier
            input(">>> Press Enter here after you have successfully logged in... <<<")

        console.print("Assuming login successful. Continuing...")

        # --- Navigate to Resources --- #
        console.print(f"Navigating to resources page: {url}")
        driver.get(url)
        console.print("Waiting briefly for page elements to load...")
        time.sleep(5)  # Simple wait

        # --- Extract Data --- #
        console.print("Fetching page source to extract resource data...")
        page_source = driver.page_source
        resources_pattern = r"var\s+RESOURCES\s*=\s*(\[.*?\])\s*;?"
        resources_match = re.search(resources_pattern, page_source, re.DOTALL)

        if not resources_match:
            console_stderr.print(
                "[bold red]Error:[/] Could not find 'var RESOURCES = [...]' in page source."
            )
            console_stderr.print(
                "[info]Maybe the page didn't load correctly or Piazza structure changed?[/]"
            )
            raise typer.Exit(code=1)

        resources_json_str = resources_match.group(1)
        try:
            resources_data = json.loads(resources_json_str)
            console.print(
                f"Successfully parsed [bold green]{len(resources_data)}[/] resource entries."
            )
        except json.JSONDecodeError as e:
            console_stderr.print(
                f"[bold red]Error:[/] Failed to parse RESOURCES JSON data: {e}"
            )
            raise typer.Exit(code=1) from e

        # --- Setup Requests Session --- #
        session = requests.Session()
        for cookie in driver.get_cookies():
            session.cookies.set(cookie["name"], cookie["value"])
        console.print("Copied browser cookies to requests session.")

        # --- Process Resources --- #
        console.print("Processing resources...")
        processed_count = 0
        skipped_count = 0
        error_count = 0

        for resource in resources_data:
            try:
                resource_id = resource.get("id")
                subject = resource.get("subject", "_no_subject_")
                config = resource.get("config", {})
                section = config.get("section", "general")
                resource_type = config.get("resource_type")
                content = resource.get("content", "")

                if not resource_id or not resource_type:
                    console.print(
                        f"[yellow]WARN:[/] Skipping resource due to missing id or type: {subject}"
                    )
                    skipped_count += 1
                    continue

                section_dir = output_dir / sanitize_filename(section)
                section_dir.mkdir(parents=True, exist_ok=True)

                if resource_type == "file":
                    download_url = f"https://piazza.com/class_profile/get_resource/{network_id}/{resource_id}"
                    filename = sanitize_filename(subject)
                    if not Path(filename).suffix:
                        if (
                            content
                            and "." in content
                            and len(content.split(".")[-1]) <= 5
                        ):
                            ext = content.split(".")[-1]
                            filename = f"{filename}.{ext}"
                        else:
                            console.print(
                                f"[yellow]WARN:[/] No extension for '{subject}', assuming '.bin'. URL: {download_url}"
                            )
                            filename = f"{filename}.bin"

                    local_filepath = section_dir / filename

                    if local_filepath.exists():
                        console.print(
                            f"  [dim]SKIP:[/] File exists: {local_filepath.relative_to(output_dir.parent)}"
                        )
                        skipped_count += 1
                        continue

                    console.print(
                        f"  [cyan]FILE:[/] '{subject}' -> [dim]{local_filepath.relative_to(output_dir.parent)}[/]..."
                    )
                    try:
                        response = session.get(download_url, stream=True, timeout=60)
                        response.raise_for_status()
                        with open(local_filepath, "wb") as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        processed_count += 1
                    except requests.exceptions.RequestException as req_err:
                        console_stderr.print(
                            f"    [red]ERROR downloading {filename}: {req_err}[/]"
                        )
                        error_count += 1
                    except Exception as dl_err:
                        console_stderr.print(
                            f"    [red]ERROR (unexpected) downloading {filename}: {dl_err}[/]"
                        )
                        error_count += 1

                elif resource_type == "link":
                    link_url = content
                    if not link_url:
                        console.print(
                            f"[yellow]WARN:[/] Skipping LINK with empty URL: {subject}"
                        )
                        skipped_count += 1
                        continue

                    console.print(
                        f"  [blue]LINK:[/] '{subject}' -> [dim]_links.txt[/] in section '{section}'"
                    )
                    links_filepath = section_dir / "_links.txt"
                    mode = "a" if links_filepath.exists() else "w"
                    try:
                        with open(links_filepath, mode, encoding="utf-8") as f:
                            if mode == "w":
                                f.write(f"# Links for Section: {section}\n{'-' * 30}\n")
                            f.write(
                                f"Subject: {subject}\nURL: {link_url}\n{'-' * 30}\n"
                            )
                        processed_count += 1
                    except OSError as io_err:
                        console_stderr.print(
                            f"    [red]ERROR writing link to {links_filepath.name}: {io_err}[/]"
                        )
                        error_count += 1
                else:
                    console.print(
                        f"[yellow]WARN:[/] Unknown type '{resource_type}' for: {subject}"
                    )
                    skipped_count += 1

            except Exception as proc_err:
                subj = resource.get("subject", "[unknown subject]")
                console_stderr.print(
                    f"[red]ERROR processing entry '{subj}': {proc_err}[/]"
                )
                error_count += 1

        console.print("---")
        console.print("[bold green]Finished processing resources.[/]")
        console.print(f"  Processed: {processed_count}")
        console.print(f"  Skipped:   {skipped_count}")
        console.print(f"  Errors:    [red]{error_count}[/]")

    except Exception as e:
        console_stderr.print(
            f"[bold red]An unexpected error occurred during the main process:[/] {e}"
        )
        # Attempt screenshot for debugging
        if driver:
            try:
                screenshot_path = Path("piazza_error_screenshot.png").resolve()
                driver.save_screenshot(str(screenshot_path))
                console_stderr.print(
                    f"[yellow]Screenshot saved to: {screenshot_path}[/]"
                )
            except Exception as screen_err:
                console_stderr.print(
                    f"[yellow]Could not save screenshot: {screen_err}[/]"
                )
        raise typer.Exit(code=1) from e

    finally:
        # --- Cleanup --- #
        console.print("Closing browser...")
        if driver:
            driver.quit()
        console.print("Script finished.")

    # Exit with error if any errors occurred during processing
    if error_count > 0:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
