from __future__ import annotations

from database.connection import (
    database_health_check,
)


def main() -> None:
    result = database_health_check()

    print("Database connection: SUCCESS")
    print("User:", result["user"])
    print("Database:", result["database"])
    print("Server:", result["server"])
    print(
        "users table:",
        result["users_table"],
    )
    print(
        "user_settings table:",
        result["settings_table"],
    )


if __name__ == "__main__":
    main()
