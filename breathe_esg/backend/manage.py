#!/usr/bin/env python
"""
Django's command-line utility for administrative tasks.
"""
import os
import sys
from pathlib import Path


def get_paths():
    """Get project paths."""
    BASE_DIR = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(BASE_DIR))
    return BASE_DIR


if __name__ == '__main__':
    get_paths()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', os.environ.get('DJANGO_SETTINGS_MODULE', 'config.settings.local'))
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
