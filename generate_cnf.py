from itertools import combinations
from pathlib import Path
from math import comb


# ==========================================================
# Claimed exact values for n = 3,...,20
#
# For each n, the corresponding claimed value R is used
# to generate the upper-bound CNF instance on K_R.
#
# This script only generates the DIMACS CNF instances.
# It does NOT itself establish that these instances are
# UNSAT.
#
# Their UNSAT status is established separately using
# CaDiCaL, and the resulting DRAT certificates are
# independently checked using DRAT-trim.
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
# Edge variables
# ==========================================================

def create_edge_variables(N):
    """
    Assign one positive DIMACS variable number to every
    edge of the ordered complete graph K_N.

    For each edge ij with 1 <= i < j <= N, a variable x_ij
    is created.

    Boolean convention
    ------------------
    x_ij = True:
        edge ij is blue.

    x_ij = False:
        edge ij is red.

    Therefore, in DIMACS notation:

        positive literal  x_ij
            means that edge ij is blue;

        negative literal -x_ij
            means that edge ij is red.

    Returns
    -------
    dict
        A dictionary mapping each edge (i,j) to its DIMACS
        variable number.
    """

    if N < 2:
        raise ValueError("N must be at least 2.")

    edge_to_var = {}

    var_id = 1

    for i in range(1, N + 1):

        for j in range(i + 1, N + 1):

            edge_to_var[(i, j)] = var_id

            var_id += 1

    return edge_to_var


def get_var(edge_to_var, i, j):
    """
    Return the DIMACS variable number corresponding to edge
    ij.

    Since graph edges are undirected, the order of i and j
    is normalized automatically.
    """

    if i == j:
        raise ValueError("A loop edge (i,i) does not exist.")

    if i > j:
        i, j = j, i

    return edge_to_var[(i, j)]


# ==========================================================
# Generate one complete CNF instance
# ==========================================================

def generate_cnf(n, N):
    """
    Generate the complete CNF encoding for the following
    decision problem:

        Does K_N admit a red/blue edge coloring containing
        neither

            a red S_{1,3}

        nor

            a blue (P_n, triangleleft_alt)?

    Boolean convention
    ------------------
    True  = blue edge
    False = red edge

    The CNF consists of two families of clauses:

    1. clauses excluding a red S_{1,3};

    2. clauses excluding a blue alternating P_n.

    Returns
    -------
    edge_to_var:
        dictionary assigning DIMACS variable numbers to
        edges;

    clauses:
        list of CNF clauses.
    """

    if n < 2:
        raise ValueError("n must be at least 2.")

    if N < n:
        raise ValueError("N must satisfy N >= n.")

    # ------------------------------------------------------
    # Create the Boolean edge variables.
    # ------------------------------------------------------

    edge_to_var = create_edge_variables(N)

    clauses = []

    # ======================================================
    # 1. Exclude a red S_{1,3}
    #
    # For every i < j < k, add
    #
    #     x_ij OR x_ik.
    #
    # Since False means red, this clause prevents both
    # edges ij and ik from being red simultaneously.
    #
    # Hence every vertex has at most one red edge to its
    # right, so no red S_{1,3} occurs.
    # ======================================================

    for i in range(1, N + 1):

        right_vertices = range(
            i + 1,
            N + 1,
        )

        for j, k in combinations(
            right_vertices,
            2,
        ):

            clauses.append(
                [
                    get_var(
                        edge_to_var,
                        i,
                        j,
                    ),
                    get_var(
                        edge_to_var,
                        i,
                        k,
                    ),
                ]
            )

    # ======================================================
    # 2. Exclude a blue alternating P_n
    #
    # For every increasing n-subset
    #
    #     w_1 < w_2 < ... < w_n,
    #
    # the edges of the alternating ordered path are exactly
    # the pairs of positions a < b satisfying
    #
    #     a + b in {n+1, n+2}.
    #
    # To prevent all these n-1 edges from being blue
    # simultaneously, add the clause
    #
    #     OR(-x_{w_a,w_b}),
    #
    # over all required alternating-path edges.
    #
    # Thus at least one required edge must be red.
    # ======================================================

    for vertices in combinations(
        range(1, N + 1),
        n,
    ):

        clause = []

        for a in range(1, n + 1):

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

                    var_id = get_var(
                        edge_to_var,
                        u,
                        v,
                    )

                    # Negative literal:
                    # this required path edge is red.
                    clause.append(
                        -var_id
                    )

        # --------------------------------------------------
        # Sanity check:
        #
        # P_n must have exactly n-1 edges.
        # --------------------------------------------------

        if len(clause) != n - 1:

            raise RuntimeError(
                f"n={n}, N={N}: "
                "incorrect number of alternating-path "
                f"edges: obtained {len(clause)}, "
                f"expected {n - 1}."
            )

        clauses.append(clause)

    return edge_to_var, clauses


# ==========================================================
# Save one DIMACS CNF instance
# ==========================================================

def save_cnf(n, N):
    """
    Generate one CNF instance and save it in standard
    DIMACS format in the cnf/ directory.

    File naming convention
    ----------------------
    n{n}_N{N}.cnf

    Example
    -------
    n16_N20.cnf
    """

    base_dir = (
        Path(__file__)
        .resolve()
        .parent
    )

    cnf_dir = (
        base_dir
        / "cnf"
    )

    cnf_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        cnf_dir
        / f"n{n}_N{N}.cnf"
    )

    edge_to_var, clauses = generate_cnf(
        n=n,
        N=N,
    )

    # ------------------------------------------------------
    # Number of Boolean variables.
    # ------------------------------------------------------

    number_of_variables = len(
        edge_to_var
    )

    expected_variables = comb(
        N,
        2,
    )

    if (
        number_of_variables
        != expected_variables
    ):

        raise RuntimeError(
            f"n={n}, N={N}: "
            "variable count mismatch: "
            f"obtained {number_of_variables}, "
            f"expected {expected_variables}."
        )

    # ------------------------------------------------------
    # Number of clauses.
    #
    # Red-star clauses:
    #
    #     C(N,3)
    #
    # Alternating-path clauses:
    #
    #     C(N,n)
    #
    # Therefore:
    #
    #     total = C(N,3) + C(N,n).
    # ------------------------------------------------------

    red_star_clauses = comb(
        N,
        3,
    )

    alternating_path_clauses = comb(
        N,
        n,
    )

    expected_total = (
        red_star_clauses
        + alternating_path_clauses
    )

    number_of_clauses = len(
        clauses
    )

    if (
        number_of_clauses
        != expected_total
    ):

        raise RuntimeError(
            f"n={n}, N={N}: "
            "clause count mismatch: "
            f"obtained {number_of_clauses}, "
            f"expected {expected_total}."
        )

    # ======================================================
    # Write DIMACS CNF
    # ======================================================

    with output_file.open(
        "w",
        encoding="ascii",
        newline="\n",
    ) as file:

        # --------------------------------------------------
        # Comments
        # --------------------------------------------------

        file.write(
            "c Ordered Ramsey CNF instance\n"
        )

        file.write(
            "c Problem: "
            "S_{1,3} versus alternating P_n\n"
        )

        file.write(
            f"c n = {n}\n"
        )

        file.write(
            f"c N = {N}\n"
        )

        file.write(
            "c Positive literal = blue edge\n"
        )

        file.write(
            "c Negative literal = red edge\n"
        )

        file.write(
            "c Red-star clauses = "
            f"{red_star_clauses}\n"
        )

        file.write(
            "c Alternating-path clauses = "
            f"{alternating_path_clauses}\n"
        )

        # --------------------------------------------------
        # DIMACS header
        # --------------------------------------------------

        file.write(
            f"p cnf "
            f"{number_of_variables} "
            f"{number_of_clauses}\n"
        )

        # --------------------------------------------------
        # Clauses
        # --------------------------------------------------

        for clause in clauses:

            file.write(
                " ".join(
                    str(literal)
                    for literal in clause
                )
            )

            file.write(
                " 0\n"
            )

    return {
        "n": n,
        "N": N,
        "variables": number_of_variables,
        "red_star_clauses":
            red_star_clauses,
        "alternating_path_clauses":
            alternating_path_clauses,
        "total_clauses":
            number_of_clauses,
        "file":
            output_file,
    }


# ==========================================================
# Generate all upper-bound CNF instances
# ==========================================================

def generate_all_upper_bound_instances():
    """
    Generate the 18 upper-bound CNF instances corresponding
    to the claimed values for

        n = 3,4,...,20.

    For each n, the CNF is generated on

        N = CLAIMED_VALUES[n].

    This script does not assert that these instances are
    UNSAT.

    Their UNSAT status is established separately by
    CaDiCaL, and the resulting DRAT certificates are checked
    independently using DRAT-trim.
    """

    print(
        "=" * 72
    )

    print(
        "Generating all upper-bound CNF instances"
    )

    print(
        "=" * 72
    )

    results = []

    total_instances = len(
        CLAIMED_VALUES
    )

    for index, (n, N) in enumerate(
        CLAIMED_VALUES.items(),
        start=1,
    ):

        print()

        print(
            f"[{index}/{total_instances}] "
            f"Generating n={n}, N={N}"
        )

        result = save_cnf(
            n=n,
            N=N,
        )

        results.append(
            result
        )

        print(
            "Variables = "
            f"{result['variables']}"
        )

        print(
            "Red-star clauses = "
            f"{result['red_star_clauses']}"
        )

        print(
            "Alternating-path clauses = "
            f"{result['alternating_path_clauses']}"
        )

        print(
            "Total clauses = "
            f"{result['total_clauses']}"
        )

        print(
            "Saved: "
            f"{result['file'].name}"
        )

    # ======================================================
    # Final summary
    # ======================================================

    print()

    print(
        "=" * 72
    )

    print(
        "Generation finished."
    )

    print(
        "Number of generated upper-bound "
        f"CNF instances = {len(results)}"
    )

    output_directory = (
        Path(__file__)
        .resolve()
        .parent
        / "cnf"
    )

    print(
        "Output directory:"
    )

    print(
        output_directory
    )

    print(
        "=" * 72
    )


# ==========================================================
# Main program
# ==========================================================

if __name__ == "__main__":

    generate_all_upper_bound_instances()
