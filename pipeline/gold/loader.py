"""
Loader entrypoint for Gold layer.
Delegates to aggregator logic.
"""

import logging
from pipeline.gold import aggregator

def main():
    logging.info("Starting Gold loader...")
    aggregator.refresh()
    logging.info("Gold loader finished.")
