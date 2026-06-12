# PDF KNOWLEDGE EXTRACTOR - Native Desktop App Launcher
# Run this to open the app in a native window

import subprocess
import sys
import os
import webview
import threading
import time


def start_streamlit():
    """Start streamlit server"""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "app.py",
            "--server.port=8501",
            "--server.headless=true",
            "--browser.gatherUsageStats=false",
        ]
    )


def open_app():
    """Open the webview window"""
    time.sleep(3)  # Wait for streamlit to start
    webview.create_window(
        "PDF Knowledge Extractor - 100 Books RAG System",
        "http://localhost:8501",
        width=1400,
        height=900,
        background_color="#0E1117",
    )
    webview.start()


if __name__ == "__main__":
    # Start streamlit in background
    t = threading.Thread(target=start_streamlit)
    t.daemon = True
    t.start()

    # Open native window
    open_app()
