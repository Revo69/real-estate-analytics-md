#!/usr/bin/env python3
"""
CLI entrypoint for running the Gold loader.
Refreshes materialized view gold_estate_current and updates gold_estate_daily in Supabase.
"""

import logging
from pipeline.gold import loader as gold_loader

def main():
    logging.info("Starting Gold loader...")
    gold_loader.main()
    logging.info("Gold loader finished.")

if __name__ == "__main__":
    main()
