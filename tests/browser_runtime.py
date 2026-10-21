"""Shared Chromium launcher for local and CI browser checks."""
import os
from pathlib import Path


def launch_chromium(playwright, **options):
    """Prefer an installed browser, then use Playwright's managed browser."""
    if not options.get('executable_path'):
        candidates = [
            Path(os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE'])
            if os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE') else None,
            Path('/usr/bin/chromium'),
            Path(os.environ.get('PROGRAMFILES', 'C:/Program Files')) / 'Google/Chrome/Application/chrome.exe',
            Path(os.environ.get('PROGRAMFILES(X86)', 'C:/Program Files (x86)')) / 'Microsoft/Edge/Application/msedge.exe',
            Path(os.environ.get('PROGRAMFILES', 'C:/Program Files')) / 'Microsoft/Edge/Application/msedge.exe',
        ]
        binary = next((path for path in candidates if path and path.is_file()), None)
        if binary:
            options['executable_path'] = str(binary)
    args = list(options.get('args', []))
    if os.name != 'nt' and '--no-sandbox' not in args:
        args.append('--no-sandbox')
    if args:
        options['args'] = args
    return playwright.chromium.launch(**options)
