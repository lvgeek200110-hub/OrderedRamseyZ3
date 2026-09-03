from itertools import combinations
from pathlib import Path
import sys


# ==========================================================
# Read one SAT witness file
# ==========================================================

def read_witness(file_path):
    """
    Read one SAT witness file.

    Expected information
    --------------------
    n = ...
    N = ...
    Status = SAT

    followed by

    [Red edges, 1-based indexing]
    u v
    u v
    ...

    Every edge not listed as red is interpreted as blue.

    Returns
    -------
    n:
        number of vertices of the forbidden alternating path;

    N:
        number of vertices of the ordered complete graph;

    red_edges:
        set of red edges using 1-based vertex labels.
    """

    file_path = Path(file_path)

    if not file_path.is_file():
        raise FileNotFoundError(
            f"Witness file does not exist: {file_path}"
        )

    lines = file_path.read_text(
        encoding="utf-8"
    ).splitlines()

    n = None
    N = None
    status = None

    red_edges = set()

    reading_red_edges = False

    for line_number, raw_line in enumerate(
        lines,
        start=1,
    ):

        line = raw_line.strip()

        # --------------------------------------------------
        # Parameters
        # --------------------------------------------------

        if line.startswith("n ="):

            try:
                n = int(
                    line.split(
                        "=",
                        1,
                    )[1].strip()
                )

            except ValueError as exc:

                raise ValueError(
                    f"Invalid n value on line "
                    f"{line_number}: {line}"
                ) from exc

        elif line.startswith("N ="):

            try:
                N = int(
                    line.split(
                        "=",
                        1,
                    )[1].strip()
                )

            except ValueError as exc:

                raise ValueError(
                    f"Invalid N value on line "
                    f"{line_number}: {line}"
                ) from exc

        elif line.startswith("Status ="):

            status = (
                line.split(
                    "=",
                    1,
                )[1]
                .strip()
                .upper()
            )

        # --------------------------------------------------
        # Start of red-edge section
        # --------------------------------------------------

        elif line == "[Red edges, 1-based indexing]":

            reading_red_edges = True

        # --------------------------------------------------
        # Start of the next section
        # --------------------------------------------------

        elif (
            reading_red_edges
            and line.startswith("[")
        ):

            reading_red_edges = False

        # --------------------------------------------------
        # Red-edge line
        # --------------------------------------------------

        elif reading_red_edges and line:

            parts = line.split()

            if len(parts) != 2:

                raise ValueError(
                    "Malformed red-edge line "
                    f"{line_number}: {line}"
                )

            try:

                u = int(parts[0])
                v = int(parts[1])

            except ValueError as exc:

                raise ValueError(
                    "Red-edge endpoints must be integers "
                    f"on line {line_number}: {line}"
                ) from exc

            if u == v:

                raise ValueError(
                    f"Loop edge ({u},{v}) found on "
                    f"line {line_number}."
                )

            if u > v:
                u, v = v, u

            edge = (u, v)

            if edge in red_edges:

                raise ValueError(
                    f"Duplicate red edge {edge} "
                    f"on line {line_number}."
                )

            red_edges.add(edge)

    # ======================================================
    # Required metadata
    # ======================================================

    if n is None:

        raise ValueError(
            "Could not find n in witness file."
        )

    if N is None:

        raise ValueError(
            "Could not find N in witness file."
        )

    if status is None:

        raise ValueError(
            "Could not find Status in witness file."
        )

    if status != "SAT":

        raise ValueError(
            f"Witness file is not SAT: "
            f"Status = {status}"
        )

    # ======================================================
    # Parameter sanity checks
    # ======================================================

    if n < 2:

        raise ValueError(
            f"Invalid parameter n={n}; "
            "n must be at least 2."
        )

    if N < n:

        raise ValueError(
            f"Invalid parameters: "
            f"N={N} < n={n}."
        )

    # ======================================================
    # Validate all red-edge endpoints
    # ======================================================

    for u, v in red_edges:

        if not (
            1 <= u < v <= N
        ):

            raise ValueError(
                f"Invalid red edge ({u},{v}); "
                f"expected 1 <= u < v <= {N}."
            )

    return n, N, red_edges


# ==========================================================
# Verify absence of a red S_{1,3}
# ==========================================================

def verify_no_red_star(
    N,
    red_edges,
):
    """
    Verify that the coloring contains no red ordered
    S_{1,3}.

    The center is the leftmost vertex.

    Hence, for every vertex i, there may be at most one
    red edge from i to a vertex on its right.
    """

    for i in range(
        1,
        N + 1,
    ):

        red_right_neighbors = [
            j
            for j in range(
                i + 1,
                N + 1,
            )
            if (i, j) in red_edges
        ]

        if len(
            red_right_neighbors
        ) >= 2:

            return False, (
                f"Red S_(1,3) found with center {i}. "
                f"Red right-neighbors: "
                f"{red_right_neighbors}"
            )

    return True, None


# ==========================================================
# Alternating ordered path edges
# ==========================================================

def alternating_path_edges(vertices):
    """
    Return the edges of the alternating ordered P_n
    induced by

        vertices[0] < ... < vertices[n-1].

    Using 1-based positions a<b, the required edges are
    exactly those satisfying

        a + b in {n+1, n+2}.
    """

    n = len(vertices)

    edges = []

    for a in range(
        1,
        n + 1,
    ):

        for b in range(
            a + 1,
            n + 1,
        ):

            if (
                a + b
                in {n + 1, n + 2}
            ):

                u = vertices[a - 1]
                v = vertices[b - 1]

                if u > v:
                    u, v = v, u

                edges.append(
                    (u, v)
                )

    # ------------------------------------------------------
    # Sanity check
    # ------------------------------------------------------

    if len(edges) != n - 1:

        raise RuntimeError(
            f"Alternating P_{n} should have "
            f"{n - 1} edges, "
            f"but {len(edges)} were generated."
        )

    return edges


# ==========================================================
# Verify absence of a blue alternating P_n
# ==========================================================

def verify_no_blue_alternating_path(
    n,
    N,
    red_edges,
):
    """
    Enumerate every increasing n-subset of [N].

    Every edge not listed in red_edges is interpreted as
    blue.

    A forbidden blue alternating P_n occurs exactly when
    all required alternating-path edges are blue.
    """

    checked = 0

    for vertices in combinations(
        range(1, N + 1),
        n,
    ):

        checked += 1

        path_edges = (
            alternating_path_edges(
                vertices
            )
        )

        all_blue = all(
            edge not in red_edges
            for edge in path_edges
        )

        if all_blue:

            return False, (
                vertices,
                path_edges,
                checked,
            )

    return True, checked


# ==========================================================
# Verify one witness
# ==========================================================

def verify_witness(file_path):
    """
    Independently verify one SAT coloring witness.

    This verifier does not use Z3.
    """

    n, N, red_edges = read_witness(
        file_path
    )

    print(
        "=" * 70
    )

    print(
        "Independent SAT witness verification"
    )

    print(
        "=" * 70
    )

    print(
        f"File = {file_path}"
    )

    print(
        f"n = {n}"
    )

    print(
        f"N = {N}"
    )

    print(
        "Number of red edges = "
        f"{len(red_edges)}"
    )

    # ======================================================
    # 1. Check red S_{1,3}
    # ======================================================

    print()

    print(
        "[1] Checking red S_(1,3)..."
    )

    ok_star, star_error = (
        verify_no_red_star(
            N,
            red_edges,
        )
    )

    if not ok_star:

        print(
            "FAILED"
        )

        print(
            star_error
        )

        return False

    print(
        "PASSED"
    )

    # ======================================================
    # 2. Check blue alternating P_n
    # ======================================================

    print()

    print(
        f"[2] Checking blue alternating P_{n}..."
    )

    result = (
        verify_no_blue_alternating_path(
            n,
            N,
            red_edges,
        )
    )

    if not result[0]:

        (
            _,
            vertices,
            path_edges,
            checked,
        ) = result

        print(
            "FAILED"
        )

        print(
            "Blue alternating path found on:"
        )

        print(
            vertices
        )

        print(
            "Path edges:"
        )

        print(
            path_edges
        )

        print(
            "Candidate n-subsets checked = "
            f"{checked}"
        )

        return False

    _, checked = result

    print(
        "PASSED"
    )

    print(
        "Candidate n-subsets checked = "
        f"{checked}"
    )

    # ======================================================
    # Success
    # ======================================================

    print()

    print(
        "=" * 70
    )

    print(
        "VERIFIED WITNESS"
    )

    print(
        "=" * 70
    )

    return True


# ==========================================================
# Command-line interface
# ==========================================================

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


# ==========================================================
# Main
# ==========================================================

if __name__ == "__main__":

    main()
