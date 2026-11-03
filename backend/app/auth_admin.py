import argparse
import getpass
import hashlib
import secrets


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
        dklen=64,
        maxmem=64 * 1024 * 1024,
    )
    return f"scrypt:{salt.hex()}:{digest.hex()}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a LaunchScope password hash for local environment configuration.")
    parser.add_argument("--role", choices=("analyst", "reviewer"), required=True)
    parser.add_argument("--username", required=True)
    arguments = parser.parse_args()
    password = getpass.getpass("Password (hidden): ")
    confirmation = getpass.getpass("Confirm password (hidden): ")
    if not password or password != confirmation:
        parser.error("Passwords must be nonempty and match")
    prefix = arguments.role.upper()
    print(f"{prefix}_USERNAME={arguments.username}")
    print(f"{prefix}_PASSWORD_HASH={hash_password(password)}")


if __name__ == "__main__":
    main()