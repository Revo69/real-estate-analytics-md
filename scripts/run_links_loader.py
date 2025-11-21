#!/usr/bin/env python3
"""
CLI entrypoint for running the links loader.
Collects new real estate listing links and saves them into raw_links table.
"""

import logging
from pipeline.acquisition import links_loader

def main():
    logging.info("Starting links loader...")
    links_loader.main()
    logging.info("Links loader finished.")

if __name__ == "__main__":
    main()
