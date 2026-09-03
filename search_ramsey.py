from itertools import combinations
from pathlib import Path
import csv
import time

try:
    from z3 import (
        Solver,
        Bool,
        Or,
        Not,
        sat,
        unsat,
        unknown,
        is_true,
    )
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError(
        "z3-solver is not installed. "
        "Please install it with:\n"
        "python -m pip install z3-solver"
    ) from exc


# ==========================================================
# Alternating ordered path
# ==========================================================

def alternating_order(n):
    """
    Return the alternating order of P_n.

    Examples
    --------
    n = 7:
        [1, 3, 5, 7, 6, 4, 2]

    n = 8:
        [1, 3, 5, 7, 8, 6, 4, 2]
    """

    if n < 2:
        raise ValueError("n must be at least 2.")

    odd = list(range(1, n + 1, 2))

    even = list(
        range(
            n if n % 2 == 0 else n - 1,
            1,
            -2,
        )
    )

    return odd + even


def alternating_path_pattern_edges(n):
    """
    Return the edge pattern of
    (P_n, triangleleft_alt).

    The returned pairs use 0-based positions.

    If

        v_1 < v_2 < ... < v_n

    is an increasing n-set in K_N, then a returned pair
    (a,b) means that the edge between verts[a] and verts[b]
    is required by the alternating path.

    This is equivalent to the usual description

        i + j in {n+1, n+2}

    in 1-based positions.
    """

    order = alternating_order(n)

    position = {
        vertex: index
        for index, vertex in enumerate(order)
    }

    edges = []

    for vertex in range(1, n):

        a = position[vertex]
        b = position[vertex + 1]

        if a > b:
            a, b = b, a

        edges.append((a, b))

    return edges


# ==========================================================
# Z3 solver for a fixed pair (n,N)
# ==========================================================

class RamseyZ3:
    """
    Search for a red/blue coloring of K_N containing neither

        a red S_{1,3}

    nor

        a blue (P_n, triangleleft_alt).

    Boolean convention
    ------------------
    True  = blue edge
    False = red edge
    """

    def __init__(self, n, N, max_rounds=100000):

        if n < 2:
            raise ValueError("n must be at least 2.")

        if N < n:
            raise ValueError("N must satisfy N >= n.")

        if max_rounds <= 0:
            raise ValueError("max_rounds must be positive.")

        self.n = n
        self.N = N
        self.max_rounds = max_rounds

        self.pattern_edges = alternating_path_pattern_edges(n)

        self.solver = Solver()

        # edge_vars[(i,j)] is the Boolean variable for edge ij.
        # Vertices are internally numbered 0,...,N-1.
        self.edge_vars = {}

        for i in range(N):
            for j in range(i + 1, N):
                self.edge_vars[(i, j)] = Bool(
                    f"x_{i}_{j}"
                )

        # Number of blue-path blocking clauses inserted lazily.
        self.block_count = 0

        # Initial constraints:
        # no red S_{1,3}.
        self.add_no_red_S13_constraints()

    # ------------------------------------------------------
    # Edge variable
    # ------------------------------------------------------

    def x(self, i, j):
        """
        Return the Boolean variable corresponding to edge ij.
        """

        if i == j:
            raise ValueError("A loop edge (i,i) does not exist.")

        if i > j:
            i, j = j, i

        return self.edge_vars[(i, j)]

    # ------------------------------------------------------
    # No red S_{1,3}
    # ------------------------------------------------------

    def add_no_red_S13_constraints(self):
        """
        For every i < j < k, add

            x_ij OR x_ik.

        Since False means red, this forbids both ij and ik
        from being red simultaneously.

        Hence every vertex has at most one red edge to its
        right, so there is no red S_{1,3}.
        """

        for i in range(self.N):

            right_vertices = range(i + 1, self.N)

            for j, k in combinations(right_vertices, 2):

                self.solver.add(
                    Or(
                        self.x(i, j),
                        self.x(i, k),
                    )
                )

    # ------------------------------------------------------
    # Read current Z3 model
    # ------------------------------------------------------

    def model_to_blue_set(self, model):
        """
        Return the set of blue edges in the current model.

        Internal vertex numbering is 0-based.
        """

        blue_set = set()

        for edge, variable in self.edge_vars.items():

            value = model.eval(
                variable,
                model_completion=True,
            )

            if is_true(value):
                blue_set.add(edge)

        return blue_set

    # ------------------------------------------------------
    # Search for a blue alternating P_n
    # ------------------------------------------------------

    def find_blue_alt_path(self, model):
        """
        Search the current coloring for a blue copy of
        (P_n, triangleleft_alt).

        Every increasing n-subset of [N] is checked.

        Returns
        -------
        list of edges:
            if a blue alternating path is found;

        None:
            if no blue alternating path exists.
        """

        blue_set = self.model_to_blue_set(model)

        # Each tuple verts is automatically increasing.
        for verts in combinations(
            range(self.N),
            self.n,
        ):

            path_edges = []
            is_blue_copy = True

            for a, b in self.pattern_edges:

                i = verts[a]
                j = verts[b]

                if i > j:
                    i, j = j, i

                path_edges.append((i, j))

                if (i, j) not in blue_set:

                    is_blue_copy = False
                    break

            if is_blue_copy:
                return path_edges

        return None

    # ------------------------------------------------------
    # Block one blue alternating path
    # ------------------------------------------------------

    def add_blocking_clause(self, edge_list):
        """
        Suppose edge_list consists of the n-1 edges of one
        blue alternating path.

        Add

            OR(Not(x_e) : e in edge_list),

        which means that at least one of these edges must be
        red in every future model.

        This is equivalent to

            Not(And(x_e : e in edge_list)).
        """

        blocking_clause = Or(
            *[
                Not(self.x(i, j))
                for i, j in edge_list
            ]
        )

        self.solver.add(blocking_clause)

        self.block_count += 1

    # ------------------------------------------------------
    # Lazy-constraint solving
    # ------------------------------------------------------

    def solve(self, verbose=False):
        """
        Solve the fixed (n,N) instance using lazy constraints.

        Initially only the no-red-S_{1,3} constraints are
        included.

        Whenever Z3 returns a model containing a blue
        alternating P_n, a blocking clause for that copy is
        added and Z3 is called again.

        Returns a dictionary with status:

            "SAT"
            "UNSAT"
            "UNKNOWN"
            "MAX_ROUNDS"
        """

        rounds = 0

        while rounds < self.max_rounds:

            rounds += 1

            z3_result = self.solver.check()

            if verbose:
                print(
                    f"    round {rounds}: {z3_result}"
                )

            # ----------------------------------------------
            # UNSAT
            # ----------------------------------------------

            if z3_result == unsat:

                return {
                    "status": "UNSAT",
                    "model": None,
                    "rounds": rounds,
                    "blocking_constraints": self.block_count,
                }

            # ----------------------------------------------
            # UNKNOWN
            # ----------------------------------------------

            if z3_result == unknown:

                return {
                    "status": "UNKNOWN",
                    "model": None,
                    "rounds": rounds,
                    "blocking_constraints": self.block_count,
                }

            # ----------------------------------------------
            # SAT
            # ----------------------------------------------

            if z3_result == sat:

                model = self.solver.model()

                bad_copy = self.find_blue_alt_path(model)

                # The model avoids both forbidden objects.
                if bad_copy is None:

                    return {
                        "status": "SAT",
                        "model": model,
                        "rounds": rounds,
                        "blocking_constraints": self.block_count,
                    }

                # Current model contains a blue alternating
                # path, so block that copy and continue.
                self.add_blocking_clause(bad_copy)

        return {
            "status": "MAX_ROUNDS",
            "model": None,
            "rounds": rounds,
            "blocking_constraints": self.block_count,
        }


# ==========================================================
# Solve one fixed instance (n,N)
# ==========================================================

def solve_instance(
    n,
    N,
    verbose=False,
    max_rounds=100000,
):
    """
    Solve one fixed pair (n,N).

    Returns a dictionary containing

        n
        N
        status
        rounds
        blocking_constraints
        elapsed_seconds
    """

    solver = RamseyZ3(
        n=n,
        N=N,
        max_rounds=max_rounds,
    )

    start_time = time.perf_counter()

    result = solver.solve(
        verbose=verbose
    )

    elapsed = (
        time.perf_counter()
        - start_time
    )

    return {
        "n": n,
        "N": N,
        "status": result["status"],
        "rounds": result["rounds"],
        "blocking_constraints":
            result["blocking_constraints"],
        "elapsed_seconds": elapsed,
    }


# ==========================================================
# Automatically compute one Ramsey number
# ==========================================================

def compute_ramsey_number(
    n,
    trace_rows,
    max_rounds=100000,
):
    """
    Automatically search for

        R_<(S_{1,3}, (P_n, triangleleft_alt)).

    The search starts at N=n and increases N one at a time.

    SAT:
        an avoiding coloring exists, so R > N.

    UNSAT:
        no avoiding coloring exists.

    Therefore the first UNSAT value of N is the ordered
    Ramsey number.
    """

    print()
    print("=" * 70)
    print(
        f"Computing "
        f"R_<(S_(1,3),(P_{n},alt))"
    )
    print("=" * 70)

    N = n

    while True:

        print(
            f"Checking n={n}, N={N} ..."
        )

        result = solve_instance(
            n=n,
            N=N,
            verbose=False,
            max_rounds=max_rounds,
        )

        trace_rows.append(result)

        status = result["status"]

        print(
            f"    status = {status}"
        )

        print(
            f"    rounds = {result['rounds']}"
        )

        print(
            "    blue-path blocking constraints = "
            f"{result['blocking_constraints']}"
        )

        print(
            "    elapsed time = "
            f"{result['elapsed_seconds']:.6f} seconds"
        )

        # ----------------------------------------------
        # SAT
        # ----------------------------------------------

        if status == "SAT":

            # An avoiding coloring exists on K_N.
            # Hence R > N.
            N += 1
            continue

        # ----------------------------------------------
        # UNSAT
        # ----------------------------------------------

        if status == "UNSAT":

            print()
            print(
                f"First UNSAT value found at N={N}."
            )

            print(
                f"Therefore "
                f"R_<(S_(1,3),(P_{n},alt)) = {N}."
            )

            return N

        # ----------------------------------------------
        # UNKNOWN / MAX_ROUNDS
        # ----------------------------------------------

        print()
        print(
            f"The search for n={n} is inconclusive "
            f"because the solver returned {status}."
        )

        return None


# ==========================================================
# Save CSV files
# ==========================================================

def save_search_trace(
    trace_rows,
    output_path,
):
    """
    Save every tested (n,N) instance.
    """

    fieldnames = [
        "n",
        "N",
        "status",
        "rounds",
        "blocking_constraints",
        "elapsed_seconds",
    ]

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for row in trace_rows:

            output_row = dict(row)

            output_row["elapsed_seconds"] = (
                f"{row['elapsed_seconds']:.6f}"
            )

            writer.writerow(output_row)


def save_ramsey_values(
    ramsey_values,
    output_path,
):
    """
    Save the exact values found by the automatic search.
    """

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.writer(file)

        writer.writerow(
            [
                "n",
                "Ramsey_number",
            ]
        )

        for n in sorted(ramsey_values):

            writer.writerow(
                [
                    n,
                    ramsey_values[n],
                ]
            )


# ==========================================================
# Main program
# ==========================================================

if __name__ == "__main__":

    # ------------------------------------------------------
    # IMPORTANT:
    #
    # range(3,21) means
    #
    #     n = 3,4,...,20.
    #
    # The endpoint 21 itself is not included.
    # ------------------------------------------------------

    n_values = range(3, 21)

    max_rounds = 100000

    # Repository directory containing this script.
    base_dir = Path(__file__).resolve().parent

    # Store output in the existing results directory.
    results_dir = base_dir / "results"

    results_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    search_trace_path = (
        results_dir
        / "search_trace.csv"
    )

    ramsey_values_path = (
        results_dir
        / "search_ramsey_values.csv"
    )

    trace_rows = []

    ramsey_values = {}

    overall_start = time.perf_counter()

    # ======================================================
    # Automatic search for n=3,...,20
    # ======================================================

    for n in n_values:

        R = compute_ramsey_number(
            n=n,
            trace_rows=trace_rows,
            max_rounds=max_rounds,
        )

        # Save the trace after every completed n.
        # This prevents losing all progress if a later case
        # is interrupted.
        save_search_trace(
            trace_rows,
            search_trace_path,
        )

        if R is None:

            print()
            print("=" * 70)
            print(
                f"Search stopped at n={n}: "
                "no certified Ramsey value was obtained."
            )
            print("=" * 70)

            break

        ramsey_values[n] = R

        save_ramsey_values(
            ramsey_values,
            ramsey_values_path,
        )

    overall_elapsed = (
        time.perf_counter()
        - overall_start
    )

    # ======================================================
    # Final output
    # ======================================================

    print()
    print("=" * 70)
    print("FINAL AUTOMATIC SEARCH RESULTS")
    print("=" * 70)

    for n in sorted(ramsey_values):

        print(
            f"n={n}: "
            f"R_<(S_(1,3),(P_{n},alt))"
            f"={ramsey_values[n]}"
        )

    print()
    print(
        "Number of completed values = "
        f"{len(ramsey_values)}"
    )

    print(
        "Total running time = "
        f"{overall_elapsed:.6f} seconds"
    )

    print()
    print(
        "Detailed search trace saved to:"
    )
    print(search_trace_path)

    print()
    print(
        "Computed Ramsey values saved to:"
    )
    print(ramsey_values_path)

    print("=" * 70)
