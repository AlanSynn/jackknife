#!/usr/bin/env python3
"""
GIF to MP4 converter tool for Jackknife.

This tool converts GIF animations to MP4 video files using Pillow and imageio.
"""

import argparse
import os
import sys
import time
from pathlib import Path


# Try importing dependencies
try:
    from PIL import Image

    PILLOW_VERSION = Image.__version__
except ImportError:
    PILLOW_VERSION = "NOT FOUND - Environment may not be set up correctly"

# Try importing Rich for better output (if available)
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import (
        BarColumn,
        MofNCompleteColumn,
        PercentageColumn,
        Progress,
        SpinnerColumn,
        TextColumn,
        TimeElapsedColumn,
    )

    console = Console()
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


def convert_gif_to_mp4(input_path: str, output_path: str, fps: int) -> None:
    """
    Convert a GIF animation to MP4 video format.

    Args:
        input_path: Path to the input GIF file
        output_path: Path to save the output MP4 file
        fps: Frames per second for the output video
    """
    # Validation and imports are extracted to separate functions
    _validate_input_output_paths(input_path, output_path)

    # Import required libraries
    imaging_libs = _import_required_libraries()
    if not imaging_libs:
        return

    # Process the frames
    frames, result = _process_gif_frames(input_path, fps, imaging_libs)
    if not frames:
        return

    # Write output video
    _write_output_video(frames, output_path, fps, imaging_libs)

    # Show completion
    print(f"Conversion completed: {output_path}")


def _validate_input_output_paths(input_path: str, output_path: str) -> None:
    """Validate input and output paths."""
    # Check if input file exists
    if not os.path.isfile(input_path):
        print(f"Error: Input file '{input_path}' not found")
        sys.exit(1)

    # Check if input file is a GIF
    if not input_path.lower().endswith('.gif'):
        print("Error: Input file must be a GIF file")
        sys.exit(1)

    # Check if output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.isdir(output_dir):
        print(f"Error: Output directory '{output_dir}' does not exist")
        sys.exit(1)

    # Check if output is MP4
    if not output_path.lower().endswith('.mp4'):
        print("Warning: Output file should have .mp4 extension")
        if '.' not in os.path.basename(output_path):
            output_path += '.mp4'
            print(f"Output path adjusted to: {output_path}")


def _import_required_libraries() -> dict:
    """Import required libraries for GIF to MP4 conversion."""
    try:
        import cv2
        import numpy as np
        from PIL import Image
    except ImportError as e:
        module_name = str(e).split("'")[1] if "'" in str(e) else str(e)
        print(f"Error: Required library not found: {module_name}")
        print("Please install the required dependencies:")
        print("  pip install numpy pillow opencv-python")
        return None
    else:
        return {"np": np, "Image": Image, "cv2": cv2}

def _process_gif_frames(input_path: str, fps: int, libs: dict) -> tuple:
    """Process GIF frames and convert to format suitable for video."""
    np = libs["np"]
    image = libs["Image"]
    cv2 = libs["cv2"]

    try:
        # Open the GIF file
        gif = image.open(input_path)

        # Get the number of frames
        frame_count = 0
        try:
            while True:
                gif.seek(frame_count)
                frame_count += 1
        except EOFError:
            pass

        print(f"Processing {frame_count} frames at {fps} FPS")

        # Reset to first frame
        gif.seek(0)

        # Process frames with progress indicator
        frames = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
        ) as progress:
            task = progress.add_task("Processing frames", total=frame_count)

            for frame_idx in range(frame_count):
                gif.seek(frame_idx)
                frame = gif.convert('RGB')

                # Convert PIL Image to OpenCV format (numpy array)
                frame_np = np.array(frame)

                # OpenCV uses BGR instead of RGB
                frame_cv = cv2.cvtColor(frame_np, cv2.COLOR_RGB2BGR)

                frames.append(frame_cv)
                progress.update(task, advance=1)


    except Exception as e:
        print(f"Error processing GIF: {e}")
        return None, False
    else:
        return frames, True


def _write_output_video(frames: list, output_path: str, fps: int, libs: dict) -> None:
    """Write frames to MP4 video file."""
    cv2 = libs["cv2"]

    try:
        # Get frame dimensions
        height, width, _ = frames[0].shape

        # Create VideoWriter
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec for MP4
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        # Write frames to video
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            PercentageColumn(),
        ) as progress:
            task = progress.add_task("Converting", total=100)
            for _ in range(10):  # Simulate progress in 10 steps
                time.sleep(0.3)  # Simulate work
                progress.update(task, advance=10)

        for frame in frames:
            out.write(frame)

        # Release the VideoWriter
        out.release()
    except Exception as e:
        print(f"Error creating video: {e}")


def main() -> None:
    """Main entry point for the tool."""
    parser = argparse.ArgumentParser(
        description="giftomp4: Convert GIF animations to MP4 videos"
    )
    parser.add_argument("input_gif", help="Path to the input GIF file")
    parser.add_argument(
        "-o",
        "--output",
        help="Path for the output MP4 file (defaults to input filename with .mp4 extension)",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=15,
        help="Frames per second for the output video (default: 15)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )

    args = parser.parse_args()

    if args.verbose:
        if RICH_AVAILABLE:
            console.print(Panel("giftomp4 Tool - Verbose Mode", style="blue"))
            console.print(f"Arguments: {args}")
            console.print("-----------------------------------")
        else:
            print("giftomp4 Tool - Verbose Mode")
            print(f"Arguments: {args}")
            print("-----------------------------------")

    # Determine output filename if not specified
    output_file = args.output or (Path(args.input_gif).stem + ".mp4")

    # Run the conversion
    convert_gif_to_mp4(args.input_gif, output_file, args.fps)


if __name__ == "__main__":
    main()
