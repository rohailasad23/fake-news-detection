"""Admin CLI for the on-chain registry.

    python -m blockchain.manage deploy              # (re)deploy NewsRegistry
    python -m blockchain.manage status
    python -m blockchain.manage sources             # list verified sources
    python -m blockchain.manage add-source bbc.com
    python -m blockchain.manage remove-source bbc.com
"""
import argparse
import json

from blockchain.ledger import Ledger


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["deploy", "status", "sources", "add-source", "remove-source"])
    parser.add_argument("source", nargs="?")
    args = parser.parse_args()
    ledger = Ledger()

    if args.command == "deploy":
        if not ledger.w3.is_connected():
            ledger.connect()  # raises a helpful error
        ledger.deploy()
    elif args.command == "status":
        print(json.dumps(ledger.status(), indent=2))
    elif args.command == "sources":
        print("\n".join(ledger.connect().trusted_sources()))
    elif not args.source:
        parser.error(f"{args.command} needs a source")
    elif args.command == "add-source":
        print(f"Added verified source: {ledger.connect().add_trusted_source(args.source)}")
    else:
        print(f"Removed verified source: {ledger.connect().remove_trusted_source(args.source)}")


if __name__ == "__main__":
    main()
