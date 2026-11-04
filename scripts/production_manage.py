"""Deliberate Rumi-only administration; credentials stay in ignored local files."""

import argparse
import os
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import certifi
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent
TARGET_HOSTS = {
    "production": "ep-shiny-hall-azw0c7pa.c-3.ap-southeast-1.aws.neon.tech",
    "verification": "ep-wild-cloud-az9fnh9q.c-3.ap-southeast-1.aws.neon.tech",
}
COMMANDS = {
    "check",
    "migrate",
    "showmigrations",
    "makemigrations",
    "collectstatic",
    "createsuperuser",
    "changepassword",
    "audit_catalog",
    "sqlsequencereset",
    "test",
}


def configure(target):
    values = dotenv_values(ROOT / f".env.phase6.{target}.local")
    if not values.get("DATABASE_URL") or not values.get("SECRET_KEY"):
        raise RuntimeError("Missing private Rumi environment file; see docs/LIVE_OPERATIONS.md.")
    destination = urlsplit(values["DATABASE_URL"])
    if destination.hostname != TARGET_HOSTS[target] or destination.path != "/rumi_library":
        raise RuntimeError("Refusing an unexpected database target.")
    for name, value in values.items():
        if value is not None:
            os.environ[name] = value
    parameters = dict(parse_qsl(destination.query))
    parameters.update(sslmode="verify-full", sslrootcert=certifi.where())
    os.environ["DATABASE_URL"] = urlunsplit(destination._replace(query=urlencode(parameters)))
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
    os.environ.pop("VERCEL", None)
    sys.path.insert(0, str(ROOT))
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=TARGET_HOSTS, default="production")
    parser.add_argument("command", choices=sorted(COMMANDS))
    arguments, rest = parser.parse_known_args()
    values = configure(arguments.target)
    if arguments.command == "test":
        if arguments.target != "verification":
            raise RuntimeError("Tests require --target verification; production is never a test target.")
        # The suite's HTTP test clients use development transport; the database still uses TLS.
        os.environ["DJANGO_ENV"] = "development"
    print(
        f"Rumi Library target: {arguments.target}, database: rumi_library, host: {TARGET_HOSTS[arguments.target]}"
    )
    from django.core.management import execute_from_command_line

    try:
        execute_from_command_line(["manage.py", arguments.command, *rest])
    except Exception as error:
        message = str(error)
        for secret in [
            values.get("DATABASE_URL"),
            values.get("SECRET_KEY"),
            urlsplit(values["DATABASE_URL"]).password,
        ]:
            if secret:
                message = message.replace(secret, "[redacted]")
        print(f"{type(error).__name__}: {message}", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
