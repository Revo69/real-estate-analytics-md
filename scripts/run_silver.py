#!/usr/bin/env python3
"""
CLI entrypoint for running the Silver loader.
Transforms bronze_estate data, normalizes values and uploads into silver_estate table (Supabase).
"""

import logging
from pipeline.silver import loader as silver_loader

def main():
    logging.info("Starting Silver loader...")
    silver_loader.main()
    logging.info("Silver loader finished.")

if __name__ == "__main__":
    main()
