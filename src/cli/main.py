import argparse
from . import handlers


def main() -> None:
    """Main function for the devctl CLI."""
    parser = argparse.ArgumentParser(description="A CLI to manage DevServers.")
    subparsers = parser.add_subparsers(
        dest="command", required=True, help="Available commands"
    )

    # 'create' command
    parser_create = subparsers.add_parser("create", help="Create a new DevServer.")
    parser_create.add_argument("name", type=str, help="The name of the DevServer.")
    parser_create.add_argument(
        "--flavor", type=str, required=True, help="The flavor of the DevServer."
    )
    parser_create.add_argument("--image", type=str, help="The container image to use.")

    # 'list' command
    subparsers.add_parser("list", help="List all DevServers.")

    # 'delete' command
    parser_delete = subparsers.add_parser("delete", help="Delete a DevServer.")
    parser_delete.add_argument(
        "name", type=str, help="The name of the DevServer to delete."
    )

    args = parser.parse_args()

    # Dispatch to handler functions
    if args.command == "create":
        handlers.create_devserver(name=args.name, flavor=args.flavor, image=args.image)
    elif args.command == "list":
        handlers.list_devservers()
    elif args.command == "delete":
        handlers.delete_devserver(name=args.name)


if __name__ == "__main__":
    main()
