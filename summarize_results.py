from pathlib import Path
import csv
import re


EXACT_VALUES = {
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


def extract_value(pattern, text, default=""):
    match = re.search(
        pattern,
        text,
        flags=re.MULTILINE,
    )

    if match:
        return match.group(1).strip()

    return default


def read_result_file(file_path):
    text = file_path.read_text(
        encoding="utf-8"
    )

    n_value = extract_value(
        r"^n\s*=\s*(\d+)",
        text,
    )

    N_value = extract_value(
        r"^N\s*=\s*(\d+)",
        text,
    )

    status = extract_value(
        r"^Status\s*=\s*(SAT|UNSAT|UNKNOWN)",
        text,
    )

    rounds = extract_value(
        r"^(?:Total rounds|总轮数)\s*=\s*(\d+)",
        text,
    )

    blocking_constraints = extract_value(
        r"^(?:Added blue alternating-path blocking constraints|"
        r"按需补入的蓝色交替路阻断约束数)\s*=\s*(\d+)",
        text,
    )

    running_time = extract_value(
        r"^(?:Running time|运行时间)\s*=\s*([0-9.]+)",
        text,
    )

    if not n_value or not N_value or not status:
        raise ValueError(
            f"无法正确读取文件：{file_path.name}"
        )

    n_value = int(n_value)
    N_value = int(N_value)

    exact_value = EXACT_VALUES.get(n_value)

    if exact_value is None:
        expected = "N/A"
    elif N_value == exact_value - 1:
        expected = "SAT"
    elif N_value == exact_value:
        expected = "UNSAT"
    else:
        expected = "N/A"

    if expected == "N/A":
        check = "N/A"
    elif status == expected:
        check = "PASSED"
    else:
        check = "FAILED"

    return {
        "n": n_value,
        "exact_value": exact_value,
        "N": N_value,
        "expected": expected,
        "result": status,
        "rounds": rounds,
        "blocking_constraints": blocking_constraints,
        "time_seconds": running_time,
        "check": check,
        "source_file": file_path.name,
    }


def main():
    results_dir = Path(r"E:\results")

    if not results_dir.exists():
        raise FileNotFoundError(
            f"没有找到 results 文件夹：{results_dir}"
        )

    result_files = sorted(
        results_dir.glob("*.txt")
    )

    if not result_files:
        raise FileNotFoundError(
            "results 文件夹中没有找到 txt 文件。"
        )

    rows = []

    for file_path in result_files:
        try:
            row = read_result_file(
                file_path
            )

            if row["n"] in EXACT_VALUES:
                rows.append(row)

        except Exception as error:
            print(
                f"读取失败：{file_path.name}"
            )
            print(
                f"原因：{error}"
            )

    rows.sort(
        key=lambda row: (
            row["n"],
            row["N"]
        )
    )

    output_file = results_dir / "computational_results.csv"

    fieldnames = [
        "n",
        "exact_value",
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
        writer.writerows(rows)

    print("=" * 70)
    print("Computational results summary")
    print("=" * 70)

    print(
        f"成功汇总实例数：{len(rows)}"
    )

    failed_rows = [
        row
        for row in rows
        if row["check"] == "FAILED"
    ]

    if failed_rows:
        print()
        print("发现与预期不一致的实例：")

        for row in failed_rows:
            print(
                f"n={row['n']}, "
                f"N={row['N']}, "
                f"Expected={row['expected']}, "
                f"Result={row['result']}"
            )
    else:
        print(
            "所有读取到的实例均与预期一致。"
        )

    if len(rows) == 36:
        print(
            "36 个目标实例全部存在。"
        )
    else:
        print(
            f"注意：目标应有 36 个实例，"
            f"目前只读取到 {len(rows)} 个。"
        )

    print()
    print(
        f"汇总表已经保存到：{output_file}"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()