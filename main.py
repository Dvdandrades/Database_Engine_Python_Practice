import sys

from tabulate import tabulate

from db.engine import QueryEngine
from db.storage import StorageEngine


def print_formatted(result):
    if isinstance(result, list):
        if not result:
            print("Empty set (0 rows)")
            return

        keys = list(result[0].keys())
        table_data = [[row.get(k, "") for k in keys] for row in result]

        print(tabulate(table_data, headers=keys, tablefmt="psql"))
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
    print("Type '.exit', '.tables', or '.compact' for CLI commands.\n")

    buffer = ""

    while True:
        try:
            prompt = "db> " if not buffer else "   -> "
            line = input(prompt).strip()

            if not line:
                continue

            if line.startswith("."):
                cmd = line.lower()
                if cmd == ".exit":
                    print("Goodbye!")
                    break
                elif cmd == ".compact":
                    storage.compact()
                    print("Storage compacted successfully")
                elif cmd == ".tables":
                    tables = [
                        [t[1:-6]]
                        for t in engine.schema
                        if t.startswith("$") and t.endswith("_table")
                    ]
                    if not tables:
                        print("No tables found.")
                    else:
                        print(tabulate(tables, headers=["Table Name"], tablefmt="psql"))
                else:
                    print(f"Unknown command: {cmd}")

                buffer = ""
                continue

            if not buffer and line.lower() in "exit":
                print("Goodbye!")
                break

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
