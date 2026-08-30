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

    output_file = results_dir / "witness_verification.txt"

    passed = 0
    failed = 0

    lines = []

    lines.append("=" * 70)
    lines.append("Batch verification of SAT witnesses")
    lines.append("=" * 70)

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
            lines.append(f"{file_path.name}: VERIFIED")
            passed += 1
        else:
            print("FAILED")
            lines.append(f"{file_path.name}: FAILED")
            failed += 1

            print(result.stdout)

            if result.stderr:
                print(result.stderr)

    summary = [
        "",
        "=" * 70,
        "Finished",
        "=" * 70,
        f"VERIFIED = {passed}",
        f"FAILED   = {failed}",
        "=" * 70,
    ]

    lines.extend(summary)

    print()
    for line in summary:
        print(line)

    output_file.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8"
    )

    print()
    print(f"Saved summary to: {output_file}")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()