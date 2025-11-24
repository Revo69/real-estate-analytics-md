#!/usr/bin/env python3
"""
CLI entrypoint for running the Bronze loader.
Collects raw estate data and saves it into bronze_estate table.
"""

import logging
from pipeline.bronze import loader as bronze_loader

def main():
    logging.info("Starting Bronze loader...")
    bronze_loader.main()
    logging.info("Bronze loader finished.")

if __name__ == "__main__":
    main()
