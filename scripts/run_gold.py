#!/usr/bin/env python3
"""
CLI entrypoint for running the Gold loader.
Refreshes materialized view gold_estate_current and updates gold_estate_daily in Supabase.
"""

import logging
import os
from pipeline.gold import loader as gold_loader

def main():
    # гарантируем наличие директории logs/
    os.makedirs("logs", exist_ok=True)

    logging.basicConfig(
        filename="logs/run_gold.log",
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logging.info("Run_gold started")
    gold_loader.main()
    logging.info("Run_gold finished")

if __name__ == "__main__":
    main()