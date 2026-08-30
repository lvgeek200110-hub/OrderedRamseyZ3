from itertools import combinations
from pathlib import Path
from math import comb


# ==========================================================
# Theorem 3.5 中 n = 3,...,20 的精确值
#
# 对每个 n，N = R_<(...) 是对应的 UNSAT 实例。
# ==========================================================

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


def create_edge_variables(N):
    """
    给 K_N 的每一条边分配一个 DIMACS 正整数变量编号。

    颜色约定：
        正变量 = 蓝边
        负变量 = 红边
    """
    edge_to_var = {}
    var_id = 1

    for i in range(1, N + 1):
        for j in range(i + 1, N + 1):
            edge_to_var[(i, j)] = var_id
            var_id += 1

    return edge_to_var


def get_var(edge_to_var, i, j):
    """
    返回边 ij 对应的 DIMACS 变量编号。
    """
    if i > j:
        i, j = j, i

    return edge_to_var[(i, j)]


def generate_cnf(n, N):
    """
    生成如下问题的完整 CNF：

        K_N 是否存在红蓝染色，同时满足：
        1. 不含红色 S_{1,3}；
        2. 不含蓝色 (P_n, alt)。

    True  = 蓝边
    False = 红边
    """

    if N < n:
        raise ValueError("必须满足 N >= n。")

    edge_to_var = create_edge_variables(N)

    clauses = []

    # ======================================================
    # 1. 禁止红色 S_{1,3}
    #
    # 对每个 i < j < k 加入
    #
    #     x_ij OR x_ik
    #
    # 因为 False 表示红边，
    # 所以 ij 和 ik 不能同时为红边。
    # ======================================================

    for i in range(1, N + 1):

        right_vertices = range(i + 1, N + 1)

        for j, k in combinations(right_vertices, 2):

            clauses.append([
                get_var(edge_to_var, i, j),
                get_var(edge_to_var, i, k)
            ])

    # ======================================================
    # 2. 禁止蓝色 (P_n, alt)
    #
    # 对每一个递增 n-顶点子集
    #
    #     w_1 < ... < w_n
    #
    # 交替路径的边满足
    #
    #     a + b in {n+1, n+2}.
    #
    # 为避免所有这些边同时为蓝色，
    # 加入它们的负文字析取。
    # ======================================================

    for vertices in combinations(range(1, N + 1), n):

        clause = []

        for a in range(1, n + 1):
            for b in range(a + 1, n + 1):

                if a + b in {n + 1, n + 2}:

                    u = vertices[a - 1]
                    v = vertices[b - 1]

                    var_id = get_var(
                        edge_to_var,
                        u,
                        v
                    )

                    clause.append(-var_id)

        # P_n 必须恰好有 n-1 条边
        if len(clause) != n - 1:
            raise RuntimeError(
                f"n={n}, N={N}: "
                f"交替路径边数错误，"
                f"得到 {len(clause)} 条，"
                f"应该为 {n - 1} 条。"
            )

        clauses.append(clause)

    return edge_to_var, clauses


def save_cnf(n, N):
    """
    将一个实例保存为标准 DIMACS CNF 文件。
    """

    base_dir = Path(__file__).resolve().parent

    cnf_dir = base_dir / "cnf"

    cnf_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # 统一使用下划线！
    output_file = cnf_dir / f"n{n}_N{N}.cnf"

    edge_to_var, clauses = generate_cnf(
        n=n,
        N=N
    )

    number_of_variables = len(edge_to_var)
    number_of_clauses = len(clauses)

    red_star_clauses = comb(N, 3)
    alternating_path_clauses = comb(N, n)

    expected_total = (
        red_star_clauses
        + alternating_path_clauses
    )

    # 再检查一次子句总数
    if number_of_clauses != expected_total:
        raise RuntimeError(
            f"n={n}, N={N}: "
            f"子句数不一致。"
            f"实际 {number_of_clauses}，"
            f"理论 {expected_total}。"
        )

    # ======================================================
    # 写 DIMACS CNF
    # ======================================================

    with output_file.open(
        "w",
        encoding="ascii"
    ) as file:

        file.write(
            "c Ordered Ramsey CNF instance\n"
        )

        file.write(
            f"c n = {n}, N = {N}\n"
        )

        file.write(
            "c Positive literal = blue edge\n"
        )

        file.write(
            "c Negative literal = red edge\n"
        )

        file.write(
            f"p cnf "
            f"{number_of_variables} "
            f"{number_of_clauses}\n"
        )

        for clause in clauses:

            file.write(
                " ".join(
                    str(literal)
                    for literal in clause
                )
            )

            file.write(" 0\n")

    return {
        "n": n,
        "N": N,
        "variables": number_of_variables,
        "red_star_clauses": red_star_clauses,
        "alternating_path_clauses":
            alternating_path_clauses,
        "total_clauses": number_of_clauses,
        "file": output_file
    }


def generate_all_unsat_instances():
    """
    批量生成 Theorem 3.5 中 n=3,...,20
    所对应的 18 个 UNSAT 实例。
    """

    print("=" * 72)
    print("Generating all UNSAT CNF instances")
    print("=" * 72)

    results = []

    total_instances = len(EXACT_VALUES)

    for index, (n, N) in enumerate(
        EXACT_VALUES.items(),
        start=1
    ):

        print()
        print(
            f"[{index}/{total_instances}] "
            f"Generating n = {n}, N = {N}"
        )

        result = save_cnf(
            n=n,
            N=N
        )

        results.append(result)

        print(
            f"Variables = "
            f"{result['variables']}"
        )

        print(
            f"Red-star clauses = "
            f"{result['red_star_clauses']}"
        )

        print(
            f"Alternating-path clauses = "
            f"{result['alternating_path_clauses']}"
        )

        print(
            f"Total clauses = "
            f"{result['total_clauses']}"
        )

        print(
            f"Saved: "
            f"{result['file'].name}"
        )

    print()
    print("=" * 72)
    print(
        f"全部完成：共生成 "
        f"{len(results)} 个 UNSAT CNF 实例。"
    )
    print(
        f"保存目录：{Path(__file__).resolve().parent / 'cnf'}"
    )
    print("=" * 72)


# ==========================================================
# 主程序
# ==========================================================

if __name__ == "__main__":

    generate_all_unsat_instances()