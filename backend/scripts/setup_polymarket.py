"""
One-time script to generate Polymarket L2 API credentials from your private key.

Usage:
    cd comradeinfidel
    POLYMARKET_PRIVATE_KEY=0x... python -m backend.scripts.setup_polymarket

Copy the printed values into your .env file.
"""

import os
import sys

from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

HOST = "https://clob.polymarket.com"


def main():
    private_key = os.environ.get("POLYMARKET_PRIVATE_KEY", "").strip()
    if not private_key:
        print("ERROR: Set POLYMARKET_PRIVATE_KEY in your environment first.")
        sys.exit(1)

    print("Connecting to Polymarket CLOB…")
    client = ClobClient(host=HOST, chain_id=POLYGON, key=private_key)

    print("Deriving API credentials…")
    creds = client.create_or_derive_api_key()

    print("\n=== Add these to your .env file ===")
    print(f"POLYMARKET_API_KEY={creds.api_key}")
    print(f"POLYMARKET_API_SECRET={creds.api_secret}")
    print(f"POLYMARKET_API_PASSPHRASE={creds.api_passphrase}")
    print("\nDone.")


if __name__ == "__main__":
    main()
