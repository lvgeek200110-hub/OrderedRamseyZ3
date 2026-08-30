from pathlib import Path
import subprocess
import sys


def main():
    base_dir = Path(__file__).resolve().parent
    results_dir = base_dir / "results"
    verifier = base_dir / "verify_witness.py"

    sat_files = sorted(results_dir.glob("*_SAT.txt"))

    if not sat_files:
        print("No SAT witness files found.")
        sys.exit(1)

    passed = 0
    failed = 0

    print("=" * 70)
    print("Batch verification of SAT witnesses")
    print("=" * 70)

    for file_path in sat_files:
        print()
        print(f"Checking: {file_path.name}")

        result = subprocess.run(
            [sys.executable, str(verifier), str(file_path)],
            capture_output=True,
            text=True
        )

        if result.returncode == 0 and "VERIFIED WITNESS" in result.stdout:
            print("VERIFIED")
            passed += 1
        else:
            print("FAILED")
            failed += 1

            print(result.stdout)

            if result.stderr:
                print(result.stderr)

    print()
    print("=" * 70)
    print("Finished")
    print("=" * 70)
    print(f"VERIFIED = {passed}")
    print(f"FAILED   = {failed}")
    print("=" * 70)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()