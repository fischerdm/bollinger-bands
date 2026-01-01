# examples/app.py

"""
Development launcher for Bollinger Bands Dashboard

This is a convenience script for development. In production, use:
    python -m bollinger_bands

Or after installation:
    pip install .
    python -m bollinger_bands
"""

if __name__ == '__main__':
    try:
        # Try to import from installed package
        from bollinger_bands.__main__ import main
        main()
    except ImportError:
        # Fallback for development (not installed)
        import sys
        from pathlib import Path
        
        # Add src to path
        src_dir = Path(__file__).parent.parent / 'src'
        sys.path.insert(0, str(src_dir))
        
        from bollinger_bands.__main__ import main
        main()
