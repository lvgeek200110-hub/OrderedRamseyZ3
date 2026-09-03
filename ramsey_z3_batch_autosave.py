from itertools import combinations
from pathlib import Path
import sys
import platform
import time

try:
    import z3
    from z3 import (
        Solver,
        Bool,
        Or,
        And,
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
    Generate the vertex order of the alternating ordered path.

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
    Generate the edge pattern of
    (P_n, triangleleft_alt).

    The returned pairs use 0-based positions.

    If

        v_1 < v_2 < ... < v_n

    is an increasing n-subset of K_N, then each returned
    pair (a,b) indicates that the edge between verts[a]
    and verts[b] is required by the alternating path.
    """

    order = alternating_order(n)

    position = {}

    for index, vertex in enumerate(order):
        position[vertex] = index

    edges = []

    for vertex in range(1, n):

        a = position[vertex]
        b = position[vertex + 1]

        if a > b:
            a, b = b, a

        edges.append((a, b))

    return edges


# ==========================================================
# Z3 solver
# ==========================================================

class OptimizedRamseyZ3:
    """
    For fixed n and N, search for a red/blue coloring of K_N
    containing neither

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

        # Edge pattern of the alternating path
        self.pattern_edges = alternating_path_pattern_edges(n)

        # Z3 solver
        self.solver = Solver()

        # Boolean variables for the edges of K_N
        self.edge_vars = {}

        # Number of lazily added blue-path blocking constraints
        self.added_blue_obstruction_count = 0

        # Internal vertex numbering:
        # 0,1,...,N-1
        #
        # True  = blue
        # False = red
        for i in range(N):
            for j in range(i + 1, N):

                self.edge_vars[(i, j)] = Bool(
                    f"x_{i}_{j}"
                )

        # Initial constraints:
        # no red S_{1,3}
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

            x(i,j) OR x(i,k).

        Since False means red, this prevents both edges
        (i,j) and (i,k) from being red simultaneously.

        Hence every vertex has at most one red edge to its
        right, so no red S_{1,3} occurs.
        """

        for i in range(self.N):

            right_vertices = range(
                i + 1,
                self.N,
            )

            for j, k in combinations(
                right_vertices,
                2,
            ):

                self.solver.add(
                    Or(
                        self.x(i, j),
                        self.x(i, k),
                    )
                )

    # ------------------------------------------------------
    # Extract the blue edges of a model
    # ------------------------------------------------------

    def model_to_blue_set(self, model):
        """
        Return the set of blue edges in the current Z3 model.

        Internal vertex numbering is 0-based.
        """

        blue_set = set()

        for (i, j), variable in self.edge_vars.items():

            value = model.eval(
                variable,
                model_completion=True,
            )

            if is_true(value):
                blue_set.add((i, j))

        return blue_set

    # ------------------------------------------------------
    # Find a blue alternating P_n
    # ------------------------------------------------------

    def find_blue_altPn_in_model(self, model):
        """
        Check whether the current model contains a blue copy
        of (P_n, triangleleft_alt).

        Every increasing n-subset of the vertices is checked.

        Returns
        -------
        list:
            the edges of one blue alternating path;

        None:
            if no such blue alternating path exists.
        """

        blue_set = self.model_to_blue_set(model)

        for verts in combinations(
            range(self.N),
            self.n,
        ):

            needed_edges = []
            is_blue_copy = True

            for a, b in self.pattern_edges:

                i = verts[a]
                j = verts[b]

                if i > j:
                    i, j = j, i

                needed_edges.append((i, j))

                if (i, j) not in blue_set:

                    is_blue_copy = False
                    break

            if is_blue_copy:
                return needed_edges

        return None

    # ------------------------------------------------------
    # Block one blue alternating path
    # ------------------------------------------------------

    def add_blocking_clause_for_blue_copy(
        self,
        edge_list,
    ):
        """
        If edge_list consists of the n-1 edges of one blue
        alternating path, add

            Not(And(x_e : e in edge_list)).

        Thus these edges cannot all be blue simultaneously
        in any later model.

        Equivalently, at least one of them must be red.
        """

        clause = [
            self.x(i, j)
            for i, j in edge_list
        ]

        self.solver.add(
            Not(
                And(*clause)
            )
        )

        self.added_blue_obstruction_count += 1

    # ------------------------------------------------------
    # Decode a Z3 model
    # ------------------------------------------------------

    def decode_model(self, model):
        """
        Decode the model into red-edge and blue-edge lists.

        Internal vertex numbering remains 0-based.
        """

        red_edges = []
        blue_edges = []

        for (i, j), variable in self.edge_vars.items():

            value = model.eval(
                variable,
                model_completion=True,
            )

            if is_true(value):
                blue_edges.append((i, j))

            else:
                red_edges.append((i, j))

        red_edges.sort()
        blue_edges.sort()

        return red_edges, blue_edges

    # ------------------------------------------------------
    # Convert to 1-based vertex numbering
    # ------------------------------------------------------

    @staticmethod
    def to_one_based(edges):
        """
        Convert internal numbering

            0,1,...,N-1

        to the paper's numbering

            1,2,...,N.
        """

        return [
            (i + 1, j + 1)
            for i, j in edges
        ]

    # ------------------------------------------------------
    # Lazy-constraint solving
    # ------------------------------------------------------

    def solve_lazy(self, verbose=True):
        """
        Lazy-constraint solving procedure.

        1. Initially impose only the constraints excluding
           a red S_{1,3}.

        2. Ask Z3 for a model.

        3. If the model contains a blue alternating P_n,
           add a blocking constraint for that copy.

        4. Repeat.

        5. If a model contains no blue alternating P_n,
           return SAT.

        6. If Z3 returns UNSAT, then no avoiding coloring
           exists.

        7. If Z3 returns UNKNOWN, the computation is
           inconclusive.
        """

        rounds = 0

        while rounds < self.max_rounds:

            rounds += 1

            result = self.solver.check()

            if verbose:
                print(
                    f"Round {rounds}: {result}"
                )

            # ----------------------------------------------
            # UNSAT
            # ----------------------------------------------

            if result == unsat:

                return {
                    "status": "unsat",
                    "model": None,
                    "rounds": rounds,
                    "added_blue_obstruction_count":
                        self.added_blue_obstruction_count,
                }

            # ----------------------------------------------
            # UNKNOWN
            # ----------------------------------------------

            if result == unknown:

                return {
                    "status": "unknown",
                    "model": None,
                    "rounds": rounds,
                    "added_blue_obstruction_count":
                        self.added_blue_obstruction_count,
                }

            # ----------------------------------------------
            # SAT
            # ----------------------------------------------

            if result == sat:

                model = self.solver.model()

                bad_copy = (
                    self.find_blue_altPn_in_model(
                        model
                    )
                )

                # A genuine avoiding coloring was found.
                if bad_copy is None:

                    return {
                        "status": "sat",
                        "model": model,
                        "rounds": rounds,
                        "added_blue_obstruction_count":
                            self.added_blue_obstruction_count,
                    }

                # The current model contains a forbidden
                # blue alternating path. Block it.
                self.add_blocking_clause_for_blue_copy(
                    bad_copy
                )

        raise RuntimeError(
            f"Maximum number of rounds "
            f"({self.max_rounds}) reached "
            "before the computation finished."
        )


# ==========================================================
# Environment information
# ==========================================================

def get_environment_information():
    """
    Return basic environment information for inclusion in
    the output files.

    Absolute Python executable paths are intentionally not
    stored, since they may contain machine-specific or
    user-specific directory names.
    """

    processor = platform.processor()

    if not processor:
        processor = "Not reported"

    return {
        "python_version":
            sys.version.replace("\n", " "),
        "z3_version":
            z3.get_version_string(),
        "operating_system":
            f"{platform.system()} {platform.release()}",
        "platform":
            platform.platform(),
        "machine":
            platform.machine(),
        "processor":
            processor,
    }


# ==========================================================
# Save one computation result
# ==========================================================

def save_computation_result(
    n,
    N,
    status,
    rounds,
    blocking_count,
    elapsed_time,
    red_edges=None,
    blue_edge_count=None,
):
    """
    Save one computation result in the results/ directory.

    Examples
    --------
    n16_N19_SAT.txt
    n16_N20_UNSAT.txt
    """

    base_dir = Path(__file__).resolve().parent

    results_dir = (
        base_dir
        / "results"
    )

    results_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_path = (
        results_dir
        / f"n{n}_N{N}_{status}.txt"
    )

    environment = (
        get_environment_information()
    )

    with file_path.open(
        "w",
        encoding="utf-8",
    ) as file:

        file.write(
            "Ordered Ramsey Z3 computation\n"
        )

        file.write(
            "=" * 70 + "\n\n"
        )

        # ----------------------------------------------
        # Environment
        # ----------------------------------------------

        file.write("[Environment]\n")

        file.write(
            "Python version: "
            f"{environment['python_version']}\n"
        )

        file.write(
            "Z3 version: "
            f"{environment['z3_version']}\n"
        )

        file.write(
            "Operating system: "
            f"{environment['operating_system']}\n"
        )

        file.write(
            "Platform: "
            f"{environment['platform']}\n"
        )

        file.write(
            "Machine: "
            f"{environment['machine']}\n"
        )

        file.write(
            "Processor: "
            f"{environment['processor']}\n\n"
        )

        # ----------------------------------------------
        # Parameters
        # ----------------------------------------------

        file.write("[Parameters]\n")

        file.write(
            f"n = {n}\n"
        )

        file.write(
            f"N = {N}\n\n"
        )

        # ----------------------------------------------
        # Boolean convention
        # ----------------------------------------------

        file.write(
            "[Boolean convention]\n"
        )

        file.write(
            "True = blue edge\n"
        )

        file.write(
            "False = red edge\n\n"
        )

        # ----------------------------------------------
        # Result
        # ----------------------------------------------

        file.write("[Result]\n")

        file.write(
            f"Status = {status}\n"
        )

        file.write(
            f"Total rounds = {rounds}\n"
        )

        file.write(
            "Added blue alternating-path "
            "blocking constraints = "
            f"{blocking_count}\n"
        )

        file.write(
            "Running time = "
            f"{elapsed_time:.6f} seconds\n"
        )

        # ----------------------------------------------
        # SAT coloring witness
        # ----------------------------------------------

        if (
            status == "SAT"
            and red_edges is not None
        ):

            file.write(
                "\n[Coloring]\n"
            )

            file.write(
                "Number of red edges = "
                f"{len(red_edges)}\n"
            )

            if blue_edge_count is not None:

                file.write(
                    "Number of blue edges = "
                    f"{blue_edge_count}\n"
                )

            file.write(
                "\n[Red edges, 1-based indexing]\n"
            )

            for i, j in red_edges:

                file.write(
                    f"{i} {j}\n"
                )

            file.write(
                "\n[Red edges, LaTeX format]\n"
            )

            latex_string = ",\\ ".join(
                f"({i},{j})"
                for i, j in red_edges
            )

            file.write(
                latex_string + "\n"
            )

    return file_path


# ==========================================================
# Solve one fixed instance
# ==========================================================

def exists_coloring_lazy(
    n,
    N,
    verbose=True,
    max_rounds=100000,
):
    """
    Determine whether K_N admits a red/blue coloring
    containing neither

        a red S_{1,3}

    nor

        a blue (P_n, triangleleft_alt).

    Returns
    -------
    SAT:
        (True, red_edges, blue_edges)

    UNSAT:
        (False, None, None)

    UNKNOWN:
        (None, None, None)
    """

    solver = OptimizedRamseyZ3(
        n=n,
        N=N,
        max_rounds=max_rounds,
    )

    start_time = (
        time.perf_counter()
    )

    result = solver.solve_lazy(
        verbose=verbose
    )

    elapsed_time = (
        time.perf_counter()
        - start_time
    )

    # ======================================================
    # UNSAT
    # ======================================================

    if result["status"] == "unsat":

        if verbose:

            print()
            print("=" * 60)
            print("Computation result")
            print("=" * 60)

            print(
                f"K_{N} cannot simultaneously avoid "
                f"a red S_(1,3) and a blue "
                f"(P_{n}, alt)."
            )

            print(
                "Status = UNSAT"
            )

            print(
                "Total rounds = "
                f"{result['rounds']}"
            )

            print(
                "Added blue alternating-path "
                "blocking constraints = "
                f"{result['added_blue_obstruction_count']}"
            )

            print(
                "Running time = "
                f"{elapsed_time:.6f} seconds"
            )

            print("=" * 60)

        file_path = (
            save_computation_result(
                n=n,
                N=N,
                status="UNSAT",
                rounds=result["rounds"],
                blocking_count=
                    result[
                        "added_blue_obstruction_count"
                    ],
                elapsed_time=elapsed_time,
            )
        )

        if verbose:

            print()

            print(
                "Result saved to:"
            )

            print(file_path)

        return False, None, None

    # ======================================================
    # UNKNOWN
    # ======================================================

    if result["status"] == "unknown":

        if verbose:

            print()
            print("=" * 60)
            print("Computation result")
            print("=" * 60)

            print(
                "Status = UNKNOWN"
            )

            print(
                "Z3 returned UNKNOWN. "
                "This computation therefore cannot "
                "be used to establish SAT or UNSAT."
            )

            print(
                "Total rounds = "
                f"{result['rounds']}"
            )

            print(
                "Added blue alternating-path "
                "blocking constraints = "
                f"{result['added_blue_obstruction_count']}"
            )

            print(
                "Running time = "
                f"{elapsed_time:.6f} seconds"
            )

            print("=" * 60)

        file_path = (
            save_computation_result(
                n=n,
                N=N,
                status="UNKNOWN",
                rounds=result["rounds"],
                blocking_count=
                    result[
                        "added_blue_obstruction_count"
                    ],
                elapsed_time=elapsed_time,
            )
        )

        if verbose:

            print()

            print(
                "Result saved to:"
            )

            print(file_path)

        return None, None, None

    # ======================================================
    # SAT
    # ======================================================

    red_edges, blue_edges = (
        solver.decode_model(
            result["model"]
        )
    )

    red_edges_1 = (
        solver.to_one_based(
            red_edges
        )
    )

    blue_edges_1 = (
        solver.to_one_based(
            blue_edges
        )
    )

    if verbose:

        print()
        print("=" * 60)
        print("Computation result")
        print("=" * 60)

        print(
            f"K_{N} admits a coloring avoiding "
            f"a red S_(1,3) and a blue "
            f"(P_{n}, alt)."
        )

        print(
            "Status = SAT"
        )

        print(
            "Total rounds = "
            f"{result['rounds']}"
        )

        print(
            "Added blue alternating-path "
            "blocking constraints = "
            f"{result['added_blue_obstruction_count']}"
        )

        print(
            "Number of red edges = "
            f"{len(red_edges_1)}"
        )

        print(
            "Number of blue edges = "
            f"{len(blue_edges_1)}"
        )

        print(
            "Running time = "
            f"{elapsed_time:.6f} seconds"
        )

        print()
        print(
            "Red edges in LaTeX format:"
        )

        latex_string = ",\\ ".join(
            f"({i},{j})"
            for i, j in red_edges_1
        )

        print(latex_string)

        print("=" * 60)

    file_path = (
        save_computation_result(
            n=n,
            N=N,
            status="SAT",
            rounds=result["rounds"],
            blocking_count=
                result[
                    "added_blue_obstruction_count"
                ],
            elapsed_time=elapsed_time,
            red_edges=red_edges_1,
            blue_edge_count=
                len(blue_edges_1),
        )
    )

    if verbose:

        print()

        print(
            "Result saved to:"
        )

        print(file_path)

    return (
        True,
        red_edges_1,
        blue_edges_1,
    )


# ==========================================================
# Print environment information
# ==========================================================

def print_environment_information():
    """
    Print the environment used for the current Z3 run.
    """

    environment = (
        get_environment_information()
    )

    print("=" * 60)

    print(
        "Ordered Ramsey Z3 computation"
    )

    print("=" * 60)

    print(
        "Python version: "
        f"{environment['python_version']}"
    )

    print(
        "Z3 version: "
        f"{environment['z3_version']}"
    )

    print(
        "Operating system: "
        f"{environment['operating_system']}"
    )

    print(
        "Platform: "
        f"{environment['platform']}"
    )

    print(
        "Machine: "
        f"{environment['machine']}"
    )

    print(
        "Processor: "
        f"{environment['processor']}"
    )

    print("=" * 60)


# ==========================================================
# Main program
# ==========================================================

if __name__ == "__main__":

    print_environment_information()

    # ======================================================
    # Running modes
    #
    # "batch"
    #
    #     Batch verification of the claimed exact values
    #     for n = 3,...,20.
    #
    #     For every claimed value r, check:
    #
    #         N = r-1  should be SAT;
    #         N = r    should be UNSAT.
    #
    # "single"
    #
    #     Solve only one specified pair (n,N).
    #
    # The automatic discovery of the Ramsey values is
    # performed separately by search_ramsey.py.
    # ======================================================

    RUN_MODE = "batch"

    # ======================================================
    # Batch verification
    # ======================================================

    if RUN_MODE == "batch":

        # --------------------------------------------------
        # Claimed exact values to be independently checked.
        #
        # These values are NOT discovered by this script.
        # The purpose of this script is to verify the two
        # boundary instances N=r-1 and N=r and to save the
        # corresponding computational outputs.
        # --------------------------------------------------

        claimed_values = {
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

        print()
        print("=" * 70)

        print(
            "Starting batch verification of the "
            "claimed exact values for n=3,...,20."
        )

        print(
            "For each claimed value r:"
        )

        print(
            "    N=r-1 should be SAT;"
        )

        print(
            "    N=r   should be UNSAT."
        )

        print("=" * 70)

        total_cases = (
            2 * len(claimed_values)
        )

        finished_cases = 0

        failed_cases = []

        for (
            current_n,
            ramsey_value,
        ) in claimed_values.items():

            print()
            print("#" * 70)

            print(
                f"n={current_n}, "
                f"claimed exact value r={ramsey_value}"
            )

            print("#" * 70)

            # ==============================================
            # Lower-bound boundary:
            # N = r-1 should be SAT
            # ==============================================

            sat_N = (
                ramsey_value - 1
            )

            print()

            print(
                f"[SAT boundary test] "
                f"n={current_n}, "
                f"N={sat_N}"
            )

            (
                sat_result,
                _,
                _,
            ) = exists_coloring_lazy(
                n=current_n,
                N=sat_N,
                verbose=False,
                max_rounds=100000,
            )

            finished_cases += 1

            if sat_result is True:

                print(
                    "Result: SAT"
                )

                print(
                    "Expected: SAT -> PASSED"
                )

            elif sat_result is False:

                print(
                    "Result: UNSAT"
                )

                print(
                    "Expected: SAT -> FAILED"
                )

                failed_cases.append(
                    (
                        current_n,
                        sat_N,
                        "expected SAT",
                    )
                )

            else:

                print(
                    "Result: UNKNOWN"
                )

                print(
                    "Expected: SAT -> FAILED"
                )

                failed_cases.append(
                    (
                        current_n,
                        sat_N,
                        "expected SAT",
                    )
                )

            print(
                "Progress: "
                f"{finished_cases}/{total_cases}"
            )

            # ==============================================
            # Upper-bound boundary:
            # N = r should be UNSAT
            # ==============================================

            unsat_N = (
                ramsey_value
            )

            print()

            print(
                f"[UNSAT boundary test] "
                f"n={current_n}, "
                f"N={unsat_N}"
            )

            (
                unsat_result,
                _,
                _,
            ) = exists_coloring_lazy(
                n=current_n,
                N=unsat_N,
                verbose=False,
                max_rounds=100000,
            )

            finished_cases += 1

            if unsat_result is False:

                print(
                    "Result: UNSAT"
                )

                print(
                    "Expected: UNSAT -> PASSED"
                )

            elif unsat_result is True:

                print(
                    "Result: SAT"
                )

                print(
                    "Expected: UNSAT -> FAILED"
                )

                failed_cases.append(
                    (
                        current_n,
                        unsat_N,
                        "expected UNSAT",
                    )
                )

            else:

                print(
                    "Result: UNKNOWN"
                )

                print(
                    "Expected: UNSAT -> FAILED"
                )

                failed_cases.append(
                    (
                        current_n,
                        unsat_N,
                        "expected UNSAT",
                    )
                )

            print(
                "Progress: "
                f"{finished_cases}/{total_cases}"
            )

        # ==================================================
        # Final batch summary
        # ==================================================

        print()
        print("=" * 70)

        print(
            "Batch verification finished."
        )

        if failed_cases:

            print(
                "Some instances did not match "
                "the claimed boundary status:"
            )

            for item in failed_cases:

                print(item)

        else:

            print(
                "All 36 boundary instances "
                "matched the claimed exact values."
            )

        print(
            "Detailed result files have been "
            "saved in the results/ directory."
        )

        print("=" * 70)

    # ======================================================
    # Single-instance mode
    # ======================================================

    elif RUN_MODE == "single":

        # Modify only these two values when testing
        # one particular instance.

        single_n = 16
        single_N = 20

        print()
        print(
            f"Single instance: "
            f"n={single_n}, N={single_N}"
        )
        print()

        exists_coloring_lazy(
            n=single_n,
            N=single_N,
            verbose=True,
            max_rounds=100000,
        )

    else:

        raise ValueError(
            'RUN_MODE must be either '
            '"batch" or "single".'
        )
