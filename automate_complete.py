"""Glidly Pro AI Automator - Main Entry Point.

This is the main entry point for the Glidly Pro AI Automator application.
It launches the wxPython UI for video generation automation.
"""
import wx
from ui.main_window import MainWindow


def main():
    """Main entry point for the application."""
    app = wx.App(False)
    frame = MainWindow()
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
