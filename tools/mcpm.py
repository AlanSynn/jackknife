#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Manages GitMCP server entries in the Cursor configuration file (~/.cursor/mcp.json).

Provides commands to add, remove, and list GitMCP server configurations using Typer.
Handles various URL formats and automatically generates names if not provided.
"""

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import typer

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Define the path to the MCP configuration file
MCP_CONFIG_PATH = Path.home() / ".cursor" / "mcp.json"

# Create a Typer application instance
app = typer.Typer(
    help="Manage GitMCP servers in ~/.cursor/mcp.json.",
    epilog=(
        "Example Usage:\n"
        "  python mcpm.py add github.com/owner/repo --name my-repo\n"
        "  python mcpm.py add gitmcp.io/docs\n"
        "  python mcpm.py list\n"
        "  python mcpm.py remove my-repo"
    )
)


def _load_mcp_config() -> Dict[str, Any]:
    """Loads the MCP configuration from the JSON file.

    Creates the directory and file with a default structure if they don't exist.

    Returns:
        The loaded configuration dictionary.

    Raises:
        typer.Exit: If there's an error reading or creating the file, or if JSON is invalid.
    """
    if not MCP_CONFIG_PATH.exists():
        logging.info(
            f"Configuration file not found at {MCP_CONFIG_PATH}. Creating it."
        )
        try:
            MCP_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            default_config = {"mcpServers": {}}
            with open(MCP_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=2)
            logging.info(f"Created default configuration file: {MCP_CONFIG_PATH}")
            return default_config
        except OSError as e:
            logging.error(f"Failed to create configuration file: {e}")
            raise typer.Exit(code=1)
    try:
        with open(MCP_CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
            # Ensure the basic structure exists
            if "mcpServers" not in config or not isinstance(
                config["mcpServers"], dict
            ):
                logging.warning(
                    "MCP configuration file is missing 'mcpServers' dictionary."
                    " Initializing it."
                )
                config["mcpServers"] = {}
            return config
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from {MCP_CONFIG_PATH}: {e}")
        raise typer.Exit(code=1)
    except OSError as e:
        logging.error(f"Error reading configuration file {MCP_CONFIG_PATH}: {e}")
        raise typer.Exit(code=1)


def _save_mcp_config(config: Dict[str, Any]) -> None:
    """Saves the MCP configuration to the JSON file.

    Args:
        config: The configuration dictionary to save.

    Raises:
        typer.Exit: If there's an error writing the file.
    """
    try:
        MCP_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(MCP_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        logging.debug(f"Configuration saved to {MCP_CONFIG_PATH}")
    except OSError as e:
        logging.error(f"Error writing configuration file {MCP_CONFIG_PATH}: {e}")
        raise typer.Exit(code=1)


def _normalize_gitmcp_url(input_url: str) -> Tuple[Optional[str], Optional[str]]:
    """Normalizes various GitHub/GitMCP URL formats to the GitMCP URL format.

    Also generates a default name based on the URL.

    Handles:
        - github.com/owner/repo
        - owner.github.io/repo
        - gitmcp.io/docs
        - gitmcp.io/owner/repo
        - owner.gitmcp.io/repo
        - Full URLs (http/https) for the above

    Args:
        input_url: The input URL string.

    Returns:
        A tuple containing (normalized_gitmcp_url, default_name) or (None, None)
        if the format is unrecognized.
    """
    # Remove http(s):// prefix if present
    input_url = re.sub(r"^https?://", "", input_url).strip("/")

    # Case 1: GitHub repo (github.com/owner/repo)
    match = re.match(r"^(?:www\.)?github\.com/([^/]+)/([^/]+)/?$", input_url)
    if match:
        owner, repo = match.groups()
        url = f"https://gitmcp.io/{owner}/{repo}"
        name = f"gitmcp-{repo}"
        return url, name

    # Case 2: GitHub Pages (owner.github.io/repo)
    match = re.match(r"^([^.]+)\.github\.io/([^/]+)/?$", input_url)
    if match:
        owner, repo = match.groups()
        url = f"https://{owner}.gitmcp.io/{repo}"
        name = f"gitmcp-{owner}-{repo}"
        return url, name

    # Case 3: GitMCP dynamic (gitmcp.io/docs)
    if input_url == "gitmcp.io/docs":
        url = "https://gitmcp.io/docs"
        name = "gitmcp-docs"
        return url, name

    # Case 4: GitMCP repo (gitmcp.io/owner/repo)
    match = re.match(r"^gitmcp\.io/([^/]+)/([^/]+)/?$", input_url)
    if match:
        owner, repo = match.groups()
        url = f"https://gitmcp.io/{owner}/{repo}"
        name = f"gitmcp-{repo}"
        return url, name

    # Case 5: GitMCP Pages (owner.gitmcp.io/repo)
    match = re.match(r"^([^.]+)\.gitmcp\.io/([^/]+)/?$", input_url)
    if match:
        owner, repo = match.groups()
        url = f"https://{owner}.gitmcp.io/{repo}"
        name = f"gitmcp-{owner}-{repo}"
        return url, name

    logging.warning(f"Unrecognized URL format: {input_url}")
    return None, None


@app.command("add")
def add_server(
    url_or_path: str = typer.Argument(
        ...,
        help=(
            "The GitMCP/GitHub URL (e.g., gitmcp.io/owner/repo, "
            "github.com/owner/repo, owner.github.io/repo)."
        ),
    ),
    name: Optional[str] = typer.Option(
        None, "--name", "-n", help="Optional custom name for the server entry."
    ),
) -> None:
    """Adds a GitMCP server entry to the configuration."""
    normalized_url, default_name = _normalize_gitmcp_url(url_or_path)
    if not normalized_url or not default_name:
        logging.error(f"Could not parse or normalize URL: {url_or_path}")
        raise typer.Exit(code=1)

    server_name = name if name else default_name
    server_entry = {"url": normalized_url}

    try:
        config = _load_mcp_config()
        servers = config.get("mcpServers", {}) # Use .get for safety
        if server_name in servers:
            logging.warning(
                f"Server name '{server_name}' already exists."
                " Overwriting is not supported by this script,"
                " but adding anyway (check mcp.json manually)."
            )
        # Ensure mcpServers exists
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        config["mcpServers"][server_name] = server_entry
        _save_mcp_config(config)
        logging.info(
            f"Successfully added server '{server_name}' with URL:"
            f" {normalized_url}"
        )
    except typer.Exit:
        # Propagate exit signals from load/save functions
        raise
    except Exception as e:
        logging.exception(f"Failed to add server: {e}", exc_info=True)
        raise typer.Exit(code=1)


@app.command("remove")
def remove_server(
    name: str = typer.Argument(..., help="The name of the server entry to remove.")
) -> None:
    """Removes a GitMCP server entry from the configuration by name."""
    try:
        config = _load_mcp_config()
        servers = config.get("mcpServers", {})
        if name in servers:
            del servers[name]
            config["mcpServers"] = servers  # Update the main config dict
            _save_mcp_config(config)
            logging.info(f"Successfully removed server '{name}'.")
        else:
            logging.warning(f"Server name '{name}' not found.")
            raise typer.Exit(code=1) # Exit if not found
    except typer.Exit:
        # Propagate exit signals from load/save functions or not found
        raise
    except Exception as e:
        logging.exception(f"Failed to remove server: {e}", exc_info=True)
        raise typer.Exit(code=1)


@app.command("list")
def list_servers() -> None:
    """Lists all configured GitMCP server entries."""
    try:
        config = _load_mcp_config()
        servers = config.get("mcpServers", {})
        if not servers:
            logging.info("No GitMCP servers configured.")
            typer.echo("No GitMCP servers configured.") # Use typer.echo for output
            return

        typer.echo("Configured GitMCP Servers:")
        typer.echo("-" * 30)
        for name, details in servers.items():
            url = details.get("url", "N/A")
            typer.echo(f"  Name: {name}")
            typer.echo(f"  URL:  {url}")
            typer.echo("-" * 30)
    except typer.Exit:
        # Propagate exit signals from load function
        raise
    except Exception as e:
        logging.exception(f"Failed to list servers: {e}", exc_info=True)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()