from tabulate import tabulate


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
