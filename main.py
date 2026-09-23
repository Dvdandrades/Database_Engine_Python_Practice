import sys

from db.engine import QueryEngine
from db.storage import StorageEngine


def print_formatted(result):
    if isinstance(result, list):
        if not result:
            print("Empty set (0 rows)")
            return
        keys = list(result[0].keys())
        header = " | ".join(f"{k:12}" for k in keys)
        print("-" * len(header))
        print(header)
        print("-" * len(header))
        for row in result:
            print(" | ".join(f"{row.get(k, '')!s:12}" for k in keys))
        print("-" * len(header))
        print(f"({len(result)} rows)")
    elif isinstance(result, dict):
        formatted = ", ".join(f"{k}: {v}" for k, v in result.items())
        print(f"OK: [{formatted}]")
    else:
        print(result)


def main():
    storage = StorageEngine(db_path="./db_data")
    engine = QueryEngine(storage)

    print("--- SQL DB Terminal CLI ---")
    print("Type your SQL commands. End commands with ';' or press Enter.")
    print("Type 'exit' or 'quit' to close.\n")

    buffer = ""

    while True:
        try:
            prompt = "db> " if not buffer else "   -> "
            line = input(prompt).strip()

            if line.lower() in ("exit", "quit"):
                print("Goodbye!")
                break

            if not line:
                continue

            buffer += " " + line if buffer else line

            if buffer.endswith(";") or buffer.upper() in (
                "BEGIN",
                "COMMIT",
                "ROLLBACK",
            ):
                query_to_run = buffer.rstrip(";").strip()
                buffer = ""

                try:
                    result = engine.execute(query_to_run)
                    print_formatted(result)
                except ValueError as e:
                    print(f"Error: {e}")

        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            sys.exit(0)


if __name__ == "__main__":
    main()
