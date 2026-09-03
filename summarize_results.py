from pathlib import Path
import csv
import re
import sys


# ==========================================================
# Claimed exact values for n = 3,...,20
#
# For each n and claimed value r, the boundary computations
# should contain:
#
#     N = r - 1 : SAT
#     N = r     : UNSAT
#
# Together, these two boundary results establish the claimed
# exact value once the SAT witness and UNSAT certificate are
# independently verified.
# ==========================================================

CLAIMED_VALUES = {
    3: 5,
    4: 6,
    5: 7,
    6: 8,
    7: 10,
    8: 11,
    9: 12,
    10: 13,
    11: 14,
    12: 15,
    13: 17,
    14: 18,
    15: 19,
    16: 20,
    17: 21,
    18: 22,
    19: 23,
    20: 24,
}


# ==========================================================
# Expected number of boundary result files
#
# There are 18 values of n and two boundary instances for
# each value:
#
#     18 x 2 = 36.
# ==========================================================

EXPECTED_RESULT_COUNT = 2 * len(CLAIMED_VALUES)


# ==========================================================
# Standard result-file naming convention
#
# Examples:
#
#     n16_N19_SAT.txt
#     n16_N20_UNSAT.txt
# ==========================================================

RESULT_FILE_PATTERN = re.compile(
    r"^n(\d+)_N(\d+)_(SAT|UNSAT|UNKNOWN)\.txt$"
)


# ==========================================================
# Construct the expected boundary cases
# ==========================================================

def build_expected_cases():
    """
    Return a dictionary mapping every expected pair (n,N)
    to its required status.

    For each claimed value r:

        (n, r-1) -> SAT
        (n, r)   -> UNSAT
    """

    expected_cases = {}

    for n, claimed_value in CLAIMED_VALUES.items():

        expected_cases[
            (n, claimed_value - 1)
        ] = "SAT"

        expected_cases[
            (n, claimed_value)
        ] = "UNSAT"

    return expected_cases


# ==========================================================
# Extract one value from file text
# ==========================================================

def extract_value(
    pattern,
    text,
    default="",
):
    """
    Extract the first captured value matching a regular
    expression.

    If no match is found, return default.
    """

    match = re.search(
        pattern,
        text,
        flags=re.MULTILINE,
    )

    if match:
        return match.group(1).strip()

    return default


# ==========================================================
# Parse information encoded in a result filename
# ==========================================================

def parse_result_filename(file_path):
    """
    Parse a standard result filename.

    Example:

        n16_N19_SAT.txt

    returns:

        n      = 16
        N      = 19
        status = SAT
    """

    match = RESULT_FILE_PATTERN.fullmatch(
        file_path.name
    )

    if match is None:

        raise ValueError(
            "Filename does not follow the standard "
            f"result-file format: {file_path.name}"
        )

    n_value = int(
        match.group(1)
    )

    N_value = int(
        match.group(2)
    )

    status = (
        match.group(3)
        .upper()
    )

    return (
        n_value,
        N_value,
        status,
    )


# ==========================================================
# Read one computation result file
# ==========================================================

def read_result_file(file_path):
    """
    Read one result file produced by
    ramsey_z3_batch_autosave.py.

    The information extracted includes:

        n
        N
        Status
        Total rounds
        Number of lazy blocking constraints
        Running time

    The filename metadata is independently compared with
    the metadata stored inside the file.
    """

    file_path = Path(file_path)

    if not file_path.is_file():

        raise FileNotFoundError(
            f"Result file does not exist: {file_path}"
        )

    # ------------------------------------------------------
    # Parse filename first
    # ------------------------------------------------------

    (
        filename_n,
        filename_N,
        filename_status,
    ) = parse_result_filename(
        file_path
    )

    # ------------------------------------------------------
    # Read file contents
    # ------------------------------------------------------

    text = file_path.read_text(
        encoding="utf-8"
    )

    # ------------------------------------------------------
    # Required metadata
    # ------------------------------------------------------

    n_value = extract_value(
        r"^n\s*=\s*(\d+)\s*$",
        text,
    )

    N_value = extract_value(
        r"^N\s*=\s*(\d+)\s*$",
        text,
    )

    status = extract_value(
        r"^Status\s*=\s*"
        r"(SAT|UNSAT|UNKNOWN)\s*$",
        text,
    )

    # ------------------------------------------------------
    # Optional computational metadata
    #
    # Both the old Chinese labels and the newer English
    # labels are accepted.
    # ------------------------------------------------------

    rounds = extract_value(
        r"^(?:Total rounds|总轮数)"
        r"\s*=\s*(\d+)\s*$",
        text,
    )

    blocking_constraints = extract_value(
        r"^(?:"
        r"Added blue alternating-path blocking constraints"
        r"|按需补入的蓝色交替路阻断约束数"
        r")\s*=\s*(\d+)\s*$",
        text,
    )

    running_time = extract_value(
        r"^(?:Running time|运行时间)"
        r"\s*=\s*"
        r"([0-9]+(?:\.[0-9]+)?)",
        text,
    )

    # ------------------------------------------------------
    # Required fields must be present
    # ------------------------------------------------------

    if not n_value:

        raise ValueError(
            f"Could not read n from {file_path.name}."
        )

    if not N_value:

        raise ValueError(
            f"Could not read N from {file_path.name}."
        )

    if not status:

        raise ValueError(
            f"Could not read Status from {file_path.name}."
        )

    n_value = int(
        n_value
    )

    N_value = int(
        N_value
    )

    status = status.upper()

    # ======================================================
    # Cross-check filename and file contents
    # ======================================================

    if n_value != filename_n:

        raise ValueError(
            f"n mismatch in {file_path.name}: "
            f"filename says n={filename_n}, "
            f"file contents say n={n_value}."
        )

    if N_value != filename_N:

        raise ValueError(
            f"N mismatch in {file_path.name}: "
            f"filename says N={filename_N}, "
            f"file contents say N={N_value}."
        )

    if status != filename_status:

        raise ValueError(
            f"Status mismatch in {file_path.name}: "
            f"filename says {filename_status}, "
            f"file contents say {status}."
        )

    # ======================================================
    # Determine the expected boundary status
    # ======================================================

    claimed_value = CLAIMED_VALUES.get(
        n_value
    )

    if claimed_value is None:

        expected = "N/A"

    elif N_value == claimed_value - 1:

        expected = "SAT"

    elif N_value == claimed_value:

        expected = "UNSAT"

    else:

        expected = "N/A"

    # ======================================================
    # Compare actual and expected status
    # ======================================================

    if expected == "N/A":

        check = "N/A"

    elif status == expected:

        check = "PASSED"

    else:

        check = "FAILED"

    return {
        "n": n_value,
        "claimed_value": claimed_value,
        "N": N_value,
        "expected": expected,
        "result": status,
        "rounds": rounds,
        "blocking_constraints":
            blocking_constraints,
        "time_seconds":
            running_time,
        "check":
            check,
        "source_file":
            file_path.name,
    }


# ==========================================================
# Find standard result files
# ==========================================================

def find_result_files(results_dir):
    """
    Find only files following the standard result naming
    convention.

    Other text files such as

        witness_verification.txt

    are intentionally ignored.
    """

    result_files = []

    for file_path in results_dir.iterdir():

        if not file_path.is_file():
            continue

        if RESULT_FILE_PATTERN.fullmatch(
            file_path.name
        ):

            result_files.append(
                file_path
            )

    result_files.sort(
        key=lambda path: path.name
    )

    return result_files


# ==========================================================
# Save CSV summary
# ==========================================================

def save_csv(
    rows,
    output_file,
):
    """
    Save the computational summary as CSV.
    """

    fieldnames = [
        "n",
        "claimed_value",
        "N",
        "expected",
        "result",
        "rounds",
        "blocking_constraints",
        "time_seconds",
        "check",
        "source_file",
    ]

    with output_file.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as csv_file:

        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


# ==========================================================
# Main program
# ==========================================================

def main():

    # ------------------------------------------------------
    # Repository-relative paths
    #
    # No machine-specific absolute path is used.
    # ------------------------------------------------------

    base_dir = (
        Path(__file__)
        .resolve()
        .parent
    )

    results_dir = (
        base_dir
        / "results"
    )

    # ------------------------------------------------------
    # Check results directory
    # ------------------------------------------------------

    if not results_dir.is_dir():

        print(
            "ERROR: results directory not found:"
        )

        print(
            results_dir
        )

        sys.exit(1)

    # ------------------------------------------------------
    # Find standard result files
    # ------------------------------------------------------

    result_files = find_result_files(
        results_dir
    )

    if not result_files:

        print(
            "ERROR: no standard computation result "
            "files were found in:"
        )

        print(
            results_dir
        )

        sys.exit(1)

    # ======================================================
    # Expected boundary cases
    # ======================================================

    expected_cases = build_expected_cases()

    expected_pairs = set(
        expected_cases.keys()
    )

    # ======================================================
    # Read result files
    # ======================================================

    rows = []

    parse_errors = []

    duplicate_cases = []

    seen_cases = {}

    for file_path in result_files:

        try:

            row = read_result_file(
                file_path
            )

        except Exception as error:

            parse_errors.append(
                (
                    file_path.name,
                    str(error),
                )
            )

            continue

        pair = (
            row["n"],
            row["N"],
        )

        # --------------------------------------------------
        # Detect duplicate (n,N) instances
        # --------------------------------------------------

        if pair in seen_cases:

            duplicate_cases.append(
                (
                    pair,
                    seen_cases[pair],
                    file_path.name,
                )
            )

            continue

        seen_cases[pair] = (
            file_path.name
        )

        # --------------------------------------------------
        # Only target n=3,...,20 is included in the summary.
        # --------------------------------------------------

        if row["n"] in CLAIMED_VALUES:

            rows.append(
                row
            )

    # ------------------------------------------------------
    # Sort by n and N
    # ------------------------------------------------------

    rows.sort(
        key=lambda row: (
            row["n"],
            row["N"],
        )
    )

    # ======================================================
    # Compare actual and expected instance sets
    # ======================================================

    actual_pairs = {
        (
            row["n"],
            row["N"],
        )
        for row in rows
    }

    missing_cases = sorted(
        expected_pairs
        - actual_pairs
    )

    unexpected_cases = sorted(
        actual_pairs
        - expected_pairs
    )

    failed_rows = [
        row
        for row in rows
        if row["check"] == "FAILED"
    ]

    # ======================================================
    # Write CSV even if errors are found.
    #
    # This makes diagnosis easier.
    # ======================================================

    output_file = (
        results_dir
        / "computational_results.csv"
    )

    save_csv(
        rows,
        output_file,
    )

    # ======================================================
    # Console summary
    # ======================================================

    print(
        "=" * 72
    )

    print(
        "Computational results summary"
    )

    print(
        "=" * 72
    )

    print(
        "Expected boundary instances = "
        f"{EXPECTED_RESULT_COUNT}"
    )

    print(
        "Successfully parsed instances = "
        f"{len(rows)}"
    )

    print(
        "Parsing errors = "
        f"{len(parse_errors)}"
    )

    print(
        "Duplicate instances = "
        f"{len(duplicate_cases)}"
    )

    print(
        "Missing expected instances = "
        f"{len(missing_cases)}"
    )

    print(
        "Unexpected instances = "
        f"{len(unexpected_cases)}"
    )

    print(
        "Status mismatches = "
        f"{len(failed_rows)}"
    )

    # ======================================================
    # Parsing errors
    # ======================================================

    if parse_errors:

        print()
        print(
            "[Parsing errors]"
        )

        for filename, error in parse_errors:

            print(
                f"{filename}: {error}"
            )

    # ======================================================
    # Duplicate cases
    # ======================================================

    if duplicate_cases:

        print()
        print(
            "[Duplicate instances]"
        )

        for (
            pair,
            first_file,
            second_file,
        ) in duplicate_cases:

            n, N = pair

            print(
                f"n={n}, N={N}: "
                f"{first_file} and {second_file}"
            )

    # ======================================================
    # Missing expected cases
    # ======================================================

    if missing_cases:

        print()
        print(
            "[Missing expected instances]"
        )

        for n, N in missing_cases:

            expected_status = (
                expected_cases[
                    (n, N)
                ]
            )

            print(
                f"n={n}, N={N}, "
                f"expected {expected_status}"
            )

    # ======================================================
    # Unexpected cases
    # ======================================================

    if unexpected_cases:

        print()
        print(
            "[Unexpected instances]"
        )

        for n, N in unexpected_cases:

            print(
                f"n={n}, N={N}"
            )

    # ======================================================
    # Wrong boundary status
    # ======================================================

    if failed_rows:

        print()
        print(
            "[Boundary status mismatches]"
        )

        for row in failed_rows:

            print(
                f"n={row['n']}, "
                f"N={row['N']}, "
                f"expected={row['expected']}, "
                f"result={row['result']}"
            )

    # ======================================================
    # Final status
    # ======================================================

    all_ok = (
        len(rows) == EXPECTED_RESULT_COUNT
        and
        not parse_errors
        and
        not duplicate_cases
        and
        not missing_cases
        and
        not unexpected_cases
        and
        not failed_rows
    )

    print()
    print(
        "-" * 72
    )

    if all_ok:

        print(
            "All 36 expected boundary computation "
            "results are present and consistent."
        )

        print()

        print(
            "For every n=3,...,20:"
        )

        print(
            "    N = r-1 : SAT"
        )

        print(
            "    N = r   : UNSAT"
        )

    else:

        print(
            "ERROR: the computational result set is "
            "incomplete or inconsistent."
        )

    print()
    print(
        "CSV summary saved to:"
    )

    print(
        output_file
    )

    print(
        "=" * 72
    )

    # ------------------------------------------------------
    # Exit code
    # ------------------------------------------------------

    if all_ok:
        sys.exit(0)

    sys.exit(1)


# ==========================================================
# Main
# ==========================================================

if __name__ == "__main__":

    main()
