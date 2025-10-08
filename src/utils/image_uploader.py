#!/usr/bin/env python3
"""
Blog Image Uploader Module
This module provides functions to upload images to your Hugo blog following the same
process as the main blog publishing tool.
"""

import argparse
from pathlib import Path
import shutil
import sys
from typing import Optional
from .cli_utils import print_success, print_error, print_warning


def copy_image_to_blog(image_path: Path, hugo_post_dir: Path) -> Optional[str]:
    """
    Copy an image to a Hugo blog post directory
    :param image_path: Path to the source image file
    :param hugo_post_dir: Path to the Hugo post directory
    :return: Path to the copied image relative to the post directory
    """
    try:
        # Create a safe filename (replace spaces with hyphens)
        original_name = Path(image_path).name
        safe_name = original_name.replace(' ', '-')
        destination_path = Path(hugo_post_dir) / safe_name

        # Copy the image to the post directory
        shutil.copy2(image_path, destination_path)

        print_success(f"Image copied from {image_path} to {destination_path}")
        return f"{safe_name}"
    except Exception as e:
        print_error(f"Error copying image: {e}")
        return None


def update_markdown_with_image(markdown_file: Path, image_path: str, alt_text: str = "") -> bool:
    """
    Update a markdown file with an image reference
    :param markdown_file: Path to the markdown file to update
    :param image_path: Path to the image file (relative to the markdown file)
    :param alt_text: Alt text for the image
    :return: True if successful
    """
    try:
        with open(markdown_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Add image to the content (at the beginning for demonstration)
        image_markdown = f"![{alt_text}]({image_path})\n\n"
        new_content = image_markdown + content

        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(new_content)

        print_success(f"Updated {markdown_file} with image reference")
        return True
    except Exception as e:
        print_error(f"Error updating markdown file: {e}")
        return False


def upload_image_to_blog(image_path: Path, hugo_post_dir: Path, 
                        markdown_file: Optional[Path] = None, 
                        alt_text: str = "") -> bool:
    """
    Main function to upload an image to a Hugo blog and optionally update a markdown file
    :param image_path: Path to the image file to upload
    :param hugo_post_dir: Path to the Hugo post directory where images should be copied
    :param markdown_file: Optional: Path to the markdown file to update with the image reference
    :param alt_text: Alt text for the image (optional)
    :return: True if successful
    """
    # Validate image path
    if not Path(image_path).exists():
        print_error(f"Error: Image file does not exist: {image_path}")
        return False

    # Validate hugo post directory
    if not Path(hugo_post_dir).exists():
        print_error(f"Error: Hugo post directory does not exist: {hugo_post_dir}")
        return False

    # Copy image to blog
    relative_image_path = copy_image_to_blog(image_path, hugo_post_dir)
    if not relative_image_path:
        return False

    # Optionally update the markdown file
    if markdown_file:
        if not Path(markdown_file).exists():
            print_warning(f"Warning: Markdown file does not exist: {markdown_file}")
        else:
            update_markdown_with_image(markdown_file, relative_image_path, alt_text)

    print_success(f"\nSuccessfully added image to your Hugo blog!")
    print_success(f"Image is available at: {hugo_post_dir}/{relative_image_path}")
    print_success(f"The image can now be referenced in your markdown as:")
    print_success(f"![{alt_text}]({relative_image_path})")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Upload images to your Hugo blog and update markdown files",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "image_path",
        help="Path to the image file to upload"
    )

    parser.add_argument(
        "hugo_post_dir",
        help="Path to the Hugo post directory where images should be copied"
    )

    parser.add_argument(
        "--markdown-file",
        help="Optional: Path to the markdown file to update with the image reference"
    )

    parser.add_argument(
        "--alt-text",
        default="",
        help="Alt text for the image (optional)"
    )

    args = parser.parse_args()

    # Convert string paths to Path objects
    image_path = Path(args.image_path)
    hugo_post_dir = Path(args.hugo_post_dir)
    markdown_file = Path(args.markdown_file) if args.markdown_file else None

    # Call the main upload function
    success = upload_image_to_blog(
        image_path=image_path,
        hugo_post_dir=hugo_post_dir,
        markdown_file=markdown_file,
        alt_text=args.alt_text
    )

    return 0 if success else 1