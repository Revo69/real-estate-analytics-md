"""Send a failure notification for the Estate MD pipeline."""

import argparse
import os
import sys

import requests


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, help="Failed pipeline stage")
    parser.add_argument("--run-url", required=True, help="GitHub Actions run URL")
    args = parser.parse_args()

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print(
            "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be configured.",
            file=sys.stderr,
        )
        return 1

    message = (
        "🔴 Estate MD pipeline failed\n\n"
        f"Stage: {args.stage}\n"
        f"Run: {args.run_url}\n\n"
        "Check the GitHub Actions run and pipeline_runs before using new data."
    )

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": message,
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
        response.raise_for_status()

    except requests.RequestException as error:
        print(f"Could not send Telegram alert: {error}", file=sys.stderr)
        return 1

    print("Telegram failure alert sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
