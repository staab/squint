import os, re
from raddoo import slurp, first
from squint.db import db

root = os.path.dirname(__file__)


def get_filenames():
    for filename in os.listdir(root):
        if re.match('^[0-9]+\.(py|sql)', filename):
            yield filename


create_version_t = """
CREATE TABLE IF NOT EXISTS version (
  number int NOT NULL,
  applied timestamp NOT NULL
)"""


if __name__ == '__main__':
    with db.transaction():
        db.execute(create_version_t)

        current = db.val("select max(number) from version") or 0

        print(f"Current database version: {current}")

        for filename in sorted(get_filenames()):
            number = int(first(filename.split('.')))

            if number <= current:
                continue

            print(f"Running migration {filename}")

            db.execute(slurp(os.path.join(root, filename)))
            db.execute(
                "INSERT INTO version (number, applied) VALUES (%s, now())",
                args=[number]
            )

    print("Done running migrations")
