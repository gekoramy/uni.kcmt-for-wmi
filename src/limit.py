import argparse
import subprocess
import sys
from datetime import timedelta
from subprocess import CompletedProcess

import resource


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--minutes', type=int, required=True)
    parser.add_argument('--MBs', type=int, required=True)
    parser.add_argument('command', nargs=argparse.ONE_OR_MORE)
    args = parser.parse_args()

    Bs: int = args.MBs * 10 ** 6

    try:
        cmd: CompletedProcess[str] = subprocess.run(
            args.command,
            capture_output=True,
            check=True,
            preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_AS, (Bs, (3 * Bs) >> 1)),
            text=True,
            timeout=timedelta(minutes=args.minutes).total_seconds(),
        )

        print(cmd.stdout, file=sys.stdout)
        print(cmd.stderr, file=sys.stderr)

    except subprocess.TimeoutExpired as e:
        print(f"{e.timeout}s timeout expired", file=sys.stderr)

    except subprocess.CalledProcessError as e:
        if e.returncode in [polarity for errorcode in (137, 139, 11) for polarity in [+errorcode, -errorcode]]:
            print(f"memory limit exceeded", file=sys.stderr)
        else:
            print(e.stderr, file=sys.stderr)
            print(f"return code: {e.returncode}", file=sys.stderr)
            sys.exit(e.returncode)


if __name__ == '__main__':
    main()
