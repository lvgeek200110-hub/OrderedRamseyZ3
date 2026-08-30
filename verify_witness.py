from itertools import combinations
from pathlib import Path
import sys


def read_witness(file_path):
    """
    Read one SAT witness file.

    Expected information:
        n = ...
        N = ...
        Status = SAT

    followed by

        [Red edges, 1-based indexing]
        u v
        ...
    """

    file_path = Path(file_path)

    text = file_path.read_text(
        encoding="utf-8"
    ).splitlines()

    n = None
    N = None
    status = None
    red_edges = set()

    reading_red_edges = False

    for raw_line in text:
        line = raw_line.strip()

        if line.startswith("n ="):
            n = int(
                line.split("=", 1)[1].strip()
            )

        elif line.startswith("N ="):
            N = int(
                line.split("=", 1)[1].strip()
            )

        elif line.startswith("Status ="):
            status = (
                line.split("=", 1)[1]
                .strip()
                .upper()
            )

        elif line == "[Red edges, 1-based indexing]":
            reading_red_edges = True

        elif (
            reading_red_edges
            and line.startswith("[")
        ):
            # Start of the next section.
            reading_red_edges = False

        elif reading_red_edges and line:
            parts = line.split()

            if len(parts) == 2:
                u = int(parts[0])
                v = int(parts[1])

                if u > v:
                    u, v = v, u

                red_edges.add((u, v))

    if n is None:
        raise ValueError(
            "Could not find n in witness file."
        )

    if N is None:
        raise ValueError(
            "Could not find N in witness file."
        )

    if status != "SAT":
        raise ValueError(
            f"Witness file is not SAT: "
            f"Status = {status}"
        )

    return n, N, red_edges


def verify_no_red_star(N, red_edges):
    """
    Verify that there is no red ordered S_{1,3}.

    Since the center is the leftmost vertex,
    every vertex may have at most one red edge
    to its right.
    """

    for i in range(1, N + 1):

        red_right_neighbors = [
            j
            for j in range(i + 1, N + 1)
            if (i, j) in red_edges
        ]

        if len(red_right_neighbors) >= 2:

            return False, (
                f"Red S_(1,3) found with center {i}: "
                f"{red_right_neighbors}"
            )

    return True, None


def alternating_path_edges(vertices):
    """
    Return the edges of the alternating ordered P_n
    induced by

        vertices[0] < ... < vertices[n-1].

    The required position pairs satisfy

        a + b in {n+1, n+2}

    using 1-based positions.
    """

    n = len(vertices)

    edges = []

    for a in range(1, n + 1):
        for b in range(a + 1, n + 1):

            if a + b in {n + 1, n + 2}:

                u = vertices[a - 1]
                v = vertices[b - 1]

                if u > v:
                    u, v = v, u

                edges.append((u, v))

    if len(edges) != n - 1:
        raise RuntimeError(
            f"Alternating P_{n} should have "
            f"{n - 1} edges, but got {len(edges)}."
        )

    return edges


def verify_no_blue_alternating_path(
    n,
    N,
    red_edges
):
    """
    Enumerate every increasing n-subset of [N].

    All edges not listed as red are blue.

    A candidate is a forbidden blue alternating
    P_n precisely when every required path edge
    is blue.
    """

    checked = 0

    for vertices in combinations(
        range(1, N + 1),
        n
    ):
        checked += 1

        path_edges = alternating_path_edges(
            vertices
        )

        all_blue = all(
            edge not in red_edges
            for edge in path_edges
        )

        if all_blue:
            return False, (
                vertices,
                path_edges,
                checked
            )

    return True, checked


def verify_witness(file_path):

    n, N, red_edges = read_witness(
        file_path
    )

    print("=" * 70)
    print("Independent SAT witness verification")
    print("=" * 70)

    print(f"File = {file_path}")
    print(f"n = {n}")
    print(f"N = {N}")
    print(
        f"Number of red edges = "
        f"{len(red_edges)}"
    )

    print()
    print("[1] Checking red S_(1,3)...")

    ok_star, star_error = (
        verify_no_red_star(
            N,
            red_edges
        )
    )

    if not ok_star:
        print("FAILED")
        print(star_error)
        return False

    print("PASSED")

    print()
    print(
        f"[2] Checking blue alternating P_{n}..."
    )

    result = verify_no_blue_alternating_path(
        n,
        N,
        red_edges
    )

    if not result[0]:

        _, vertices, path_edges, checked = result

        print("FAILED")
        print(
            "Blue alternating path found on:"
        )
        print(vertices)
        print("Path edges:")
        print(path_edges)
        print(
            f"Candidate subsets checked = "
            f"{checked}"
        )

        return False

    _, checked = result

    print("PASSED")
    print(
        f"Candidate n-subsets checked = "
        f"{checked}"
    )

    print()
    print("=" * 70)
    print("VERIFIED WITNESS")
    print("=" * 70)

    return True


def main():

    if len(sys.argv) != 2:
        print(
            "Usage:"
        )
        print(
            "  python verify_witness.py "
            "results/n4_N5_SAT.txt"
        )
        sys.exit(2)

    file_path = sys.argv[1]

    try:
        valid = verify_witness(
            file_path
        )

    except Exception as error:
        print(
            f"ERROR: {error}"
        )
        sys.exit(2)

    if valid:
        sys.exit(0)

    sys.exit(1)


if __name__ == "__main__":
    main()