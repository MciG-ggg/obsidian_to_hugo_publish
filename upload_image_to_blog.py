#!/usr/bin/env python3
"""
Blog Image Uploader
This script demonstrates how to upload images to your Hugo blog following the same
process as the main blog publishing tool.
This is a compatibility wrapper that calls the function in src.utils.image_uploader
"""

import sys
from pathlib import Path

# Add src directory to Python path
current_dir = Path(__file__).resolve().parent
src_dir = current_dir / 'src'
sys.path.insert(0, str(src_dir))

from src.utils.image_uploader import main

if __name__ == "__main__":
    sys.exit(main())