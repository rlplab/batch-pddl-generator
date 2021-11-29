#! /usr/bin/env python3

"""Find duplicate PDDL instances."""

import argparse
from collections import defaultdict
import hashlib
from pathlib import Path
import shlex
from subprocess import check_output
import sys


DIR = Path(__file__).resolve().parent


def hash_unparsed_task(task):
    m = hashlib.md5()
    for path in [task.domain_file, task.problem_file]:
        with path.open() as f:
            m.update(f.read().encode("utf-8"))
    return m.hexdigest()


def parse_pddl_and_hash_task(task):
    return check_output(
        [sys.executable, DIR / "hash-instance.py", str(task.domain_file), str(task.problem_file)],
        encoding="utf-8")


def find_tasks(paths):
    for path in paths:
        path = Path(path)
        if path.is_file() and path.suffix == ".pddl" and not "domain" in path.name:
            yield Task(path)
        elif path.is_dir():
            yield from find_tasks(list(path.iterdir()))


def find_file(filenames, dir: Path):
    for filename in filenames:
        path = dir / filename
        if path.is_file():
            return path
    raise OSError(f"none found in {dir!r}: {filenames!r}")


def find_domain_file(task_path: Path):
    domain_basenames = [
        "domain.pddl",
        task_path.stem + "-domain" + task_path.suffix,
        task_path.stem[:3] + "-domain.pddl",  # for airport and psr-small
        "domain_" + task_path.name,
        "domain-" + task_path.name,
    ]
    return find_file(domain_basenames, task_path.parent)


class Task:
    def __init__(self, path):
        self.problem_file = path
        self.domain_file = find_domain_file(path)

    def __lt__(self, other):
        return self.problem_file < other.problem_file

    def __le__(self, other):
        return self.problem_file <= other.problem_file

    def __repr__(self):
        return str(self)

    def __str__(self):
        return f"<Task {self.problem_file}>"


def get_equivalent_problems(tasks, hash_unparsed_files):
    equivalent_tasks = defaultdict(list)
    for task in tasks:
        if hash_unparsed_files:
            hash = hash_unparsed_task(task)
        else:
            hash = parse_pddl_and_hash_task(task)
        equivalent_tasks[hash].append(task)
    return equivalent_tasks.values()


def print_duplicates(equivalence_partition):
    print("Duplicates:\n")
    to_delete = []
    for partition in equivalence_partition:
        if len(partition) > 1:
            to_delete.extend(sorted(partition)[1:])
            for task in sorted(partition):
                try:
                    relpath = task.problem_file.relative_to(Path.cwd())
                except ValueError:
                    relpath = task.problem_file
                print(f"{relpath}")
            print()

    if to_delete:
        print("Delete the following files to only keep the first task of each class:")
        cmd = []
        for task in to_delete:
            cmd.append(f"{task.problem_file}")
            if task.domain_file.name != "domain.pddl":
                cmd.append(f"{task.domain_file.name}")
        print(shlex.join(cmd))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="+",
        help="one or more paths to PDDL files or directories containing PDDL files",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="compare tasks based on the MD5 hash of the unparsed file contents",
    )
    args = parser.parse_args()

    tasks = list(find_tasks(args.paths))
    print(f"Found {len(tasks)} tasks")
    equivalence_partition = get_equivalent_problems(tasks, args.raw)
    print_duplicates(equivalence_partition)


main()
