from pathlib import Path
import subprocess
import sys


# ==========================================================
# Configuration
# ==========================================================

EXPECTED_WITNESSES = 18


# ==========================================================
# Main program
# ==========================================================

def main():

    base_dir = Path(__file__).resolve().parent

    results_dir = base_dir / "results"

    verifier = base_dir / "verify_witness.py"

    # ------------------------------------------------------
    # Check required paths
    # ------------------------------------------------------

    if not results_dir.is_dir():

        print(
            f"Results directory not found: "
            f"{results_dir}"
        )

        sys.exit(1)

    if not verifier.is_file():

        print(
            f"Witness verifier not found: "
            f"{verifier}"
        )

        sys.exit(1)

    # ------------------------------------------------------
    # Locate all SAT witness files
    # ------------------------------------------------------

    sat_files = sorted(
        results_dir.glob("*_SAT.txt")
    )

    if not sat_files:

        print(
            "No SAT witness files found."
        )

        sys.exit(1)

    # ------------------------------------------------------
    # For n=3,...,20 there should be exactly 18 boundary
    # SAT witnesses, one on K_{R-1} for each n.
    # ------------------------------------------------------

    if len(sat_files) != EXPECTED_WITNESSES:

        print(
            "Incorrect number of SAT witness files."
        )

        print(
            f"Expected: {EXPECTED_WITNESSES}"
        )

        print(
            f"Found:    {len(sat_files)}"
        )

        print()

        print(
            "Files found:"
        )

        for file_path in sat_files:

            print(
                f"  {file_path.name}"
            )

        sys.exit(1)

    # ------------------------------------------------------
    # Output summary file
    # ------------------------------------------------------

    output_file = (
        results_dir
        / "witness_verification.txt"
    )

    passed = 0
    failed = 0

    lines = []

    lines.append(
        "=" * 70
    )

    lines.append(
        "Batch verification of SAT witnesses"
    )

    lines.append(
        "=" * 70
    )

    lines.append(
        f"Expected witness files = "
        f"{EXPECTED_WITNESSES}"
    )

    lines.append(
        f"Found witness files    = "
        f"{len(sat_files)}"
    )

    lines.append("")

    # ======================================================
    # Verify every witness independently
    # ======================================================

    for file_path in sat_files:

        print()

        print(
            f"Checking: {file_path.name}"
        )

        # Run the independent verifier using the same
        # Python interpreter that runs this script.
        result = subprocess.run(
            [
                sys.executable,
                str(verifier),
                str(file_path),
            ],
            capture_output=True,
            text=True,
        )

        verified = (
            result.returncode == 0
            and
            "VERIFIED WITNESS"
            in result.stdout
        )

        if verified:

            print(
                "VERIFIED"
            )

            lines.append(
                f"{file_path.name}: VERIFIED"
            )

            passed += 1

        else:

            print(
                "FAILED"
            )

            lines.append(
                f"{file_path.name}: FAILED"
            )

            failed += 1

            # Preserve diagnostic information on screen.
            if result.stdout:

                print()

                print(
                    "[Verifier stdout]"
                )

                print(
                    result.stdout
                )

            if result.stderr:

                print()

                print(
                    "[Verifier stderr]"
                )

                print(
                    result.stderr
                )

    # ======================================================
    # Final summary
    # ======================================================

    summary = [
        "",
        "=" * 70,
        "Finished",
        "=" * 70,
        f"VERIFIED = {passed}",
        f"FAILED   = {failed}",
        "=" * 70,
    ]

    lines.extend(
        summary
    )

    print()

    for line in summary:

        print(line)

    # ------------------------------------------------------
    # Save batch summary
    # ------------------------------------------------------

    output_file.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    print()

    print(
        f"Saved summary to: "
        f"{output_file}"
    )

    # ------------------------------------------------------
    # Nonzero exit status if any witness failed.
    # ------------------------------------------------------

    if failed > 0:

        sys.exit(1)

    # Also require all 18 expected witnesses to pass.
    if passed != EXPECTED_WITNESSES:

        print(
            "Not all expected witnesses were verified."
        )

        sys.exit(1)

    print()

    print(
        "All expected SAT witnesses were "
        "independently verified."
    )


if __name__ == "__main__":

    main()
