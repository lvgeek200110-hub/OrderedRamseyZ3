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
except ModuleNotFoundError:
    raise ModuleNotFoundError(
        "没有安装 z3-solver。请先在 PyCharm 终端运行："
        "python -m pip install z3-solver"
    )


def alternating_order(n):
    """
    生成交替有序路径 (P_n, alt) 的顶点顺序。

    例如：
    n = 7 时，返回 [1, 3, 5, 7, 6, 4, 2]
    n = 8 时，返回 [1, 3, 5, 7, 8, 6, 4, 2]
    """
    if n < 2:
        raise ValueError("n 至少应该为 2。")

    odd = list(range(1, n + 1, 2))
    even = list(range(n if n % 2 == 0 else n - 1, 1, -2))

    return odd + even


def alternating_path_pattern_edges(n):
    """
    生成交替路径 (P_n, alt) 的边模式。

    注意：
    这里生成的不是 K_N 中的具体边，
    而是当我们选出 n 个递增顶点以后，
    哪些位置之间必须是蓝边。

    返回的位置下标采用 0-based indexing。
    """
    alt_order = alternating_order(n)

    pos = {}

    for idx, v in enumerate(alt_order):
        pos[v] = idx

    edges = []

    for v in range(1, n):
        a = pos[v]
        b = pos[v + 1]

        if a > b:
            a, b = b, a

        edges.append((a, b))

    return edges


class OptimizedRamseyZ3:
    def __init__(self, n, N, max_rounds=100000):
        """
        参数：

        n:
            要避免的蓝色交替路径 (P_n, alt) 的顶点数。

        N:
            有序完全图 K_N 的顶点数。

        max_rounds:
            懒约束算法允许的最大迭代轮数。
            该参数只是程序保护参数，不属于数学模型。
        """
        if n < 2:
            raise ValueError("n 至少应该为 2。")

        if N < n:
            raise ValueError("N 应该至少大于等于 n。")

        if max_rounds <= 0:
            raise ValueError("max_rounds 必须为正整数。")

        self.n = n
        self.N = N
        self.max_rounds = max_rounds

        # 生成交替路径的边模式
        self.pattern_edges = alternating_path_pattern_edges(n)

        # 创建 Z3 求解器
        self.solver = Solver()

        # 存储 K_N 中每条边对应的布尔变量
        self.edge_vars = {}

        # 记录按需补入了多少条蓝色交替路阻断约束
        self.added_blue_obstruction_count = 0

        # True  表示蓝边
        # False 表示红边
        #
        # 程序内部顶点编号：
        # 0, 1, ..., N-1
        for i in range(N):
            for j in range(i + 1, N):
                self.edge_vars[(i, j)] = Bool(f"x_{i}_{j}")

        # 加入禁止红色 S_{1,3} 的约束
        self.add_no_red_S13_constraints()

    def x(self, i, j):
        """
        返回边 (i,j) 对应的布尔变量。

        因为边没有方向，所以自动保证 i < j。
        """
        if i == j:
            raise ValueError("不存在自环边 (i,i)。")

        if i > j:
            i, j = j, i

        return self.edge_vars[(i, j)]

    def add_no_red_S13_constraints(self):
        """
        避免红色 S_{1,3}。

        True  表示蓝边。
        False 表示红边。

        对每个顶点 i，要求它向右至多只有一条红边。

        对任意 i < j < k 加入：

            Or(x(i,j), x(i,k))

        这意味着：

            (i,j) 是蓝边
            或
            (i,k) 是蓝边。

        因而两条边不能同时为红色。
        """
        for i in range(self.N):
            right_vertices = range(i + 1, self.N)

            for j, k in combinations(right_vertices, 2):
                self.solver.add(
                    Or(
                        self.x(i, j),
                        self.x(i, k)
                    )
                )

    def model_to_blue_set(self, model):
        """
        把当前 Z3 模型中的蓝边提取出来。

        返回：
            {(i,j), ...}

        顶点编号仍使用 0-based。
        """
        blue_set = set()

        for (i, j), var in self.edge_vars.items():
            val = model.eval(var, model_completion=True)

            if is_true(val):
                blue_set.add((i, j))

        return blue_set

    def find_blue_altPn_in_model(self, model):
        """
        检查当前模型中是否存在蓝色 (P_n, alt)。

        方法：

        从 K_N 的 N 个顶点中选出任意 n 个递增顶点，
        检查它们是否按照交替路径的边模式全部为蓝边。

        如果找到：
            返回组成该蓝色交替路径的边列表。

        如果没有找到：
            返回 None。
        """
        blue_set = self.model_to_blue_set(model)

        # 枚举所有递增的 n-顶点子集
        for verts in combinations(range(self.N), self.n):

            needed_edges = []
            is_blue_copy = True

            for a, b in self.pattern_edges:
                i = verts[a]
                j = verts[b]

                if i > j:
                    i, j = j, i

                needed_edges.append((i, j))

                # 只要有一条不是蓝边，
                # 当前 n 个顶点就不是蓝色交替路径
                if (i, j) not in blue_set:
                    is_blue_copy = False
                    break

            if is_blue_copy:
                return needed_edges

        return None

    def add_blocking_clause_for_blue_copy(self, edge_list):
        """
        如果当前模型中出现了一条蓝色交替路径，
        加入阻断约束。

        假设该交替路径由：

            e_1, e_2, ..., e_{n-1}

        组成，则加入：

            Not(And(e_1, e_2, ..., e_{n-1}))

        意味着：
            这些边以后不能同时全部为蓝色。

        等价地：
            至少有一条必须是红边。
        """
        clause = [
            self.x(i, j)
            for (i, j) in edge_list
        ]

        self.solver.add(
            Not(
                And(*clause)
            )
        )

        self.added_blue_obstruction_count += 1

    def decode_model(self, model):
        """
        将 Z3 模型解码为红边列表和蓝边列表。

        返回的顶点编号仍是：
            0,1,...,N-1
        """
        red_edges = []
        blue_edges = []

        for (i, j), var in self.edge_vars.items():

            val = model.eval(
                var,
                model_completion=True
            )

            if is_true(val):
                blue_edges.append((i, j))
            else:
                red_edges.append((i, j))

        red_edges.sort()
        blue_edges.sort()

        return red_edges, blue_edges

    @staticmethod
    def to_one_based(edges):
        """
        将程序内部使用的

            0,1,...,N-1

        转换为论文中的

            1,2,...,N。
        """
        return [
            (i + 1, j + 1)
            for i, j in edges
        ]

    def solve_lazy(self, verbose=True):
        """
        懒约束求解主循环。

        1. 初始只加入禁止红色 S_{1,3} 的约束；

        2. 调用 Z3；

        3. 如果 Z3 返回 SAT，
           检查当前染色是否含有蓝色 (P_n, alt)；

        4. 如果存在蓝色 (P_n, alt)，
           加入对应的 blocking constraint；

        5. 再次调用 Z3；

        6. 如果找到一个 SAT 模型，
           且其中不存在蓝色 (P_n, alt)，
           则得到合法染色；

        7. 如果 Z3 返回 UNSAT，
           则不存在这样的染色；

        8. 如果 Z3 返回 UNKNOWN，
           则该次计算不能用于证明 SAT 或 UNSAT。
        """
        rounds = 0

        while rounds < self.max_rounds:

            rounds += 1

            result = self.solver.check()

            if verbose:
                print(f"第 {rounds} 轮: {result}")

            # -----------------------------
            # UNSAT
            # -----------------------------
            if result == unsat:
                return {
                    "status": "unsat",
                    "model": None,
                    "rounds": rounds,
                    "added_blue_obstruction_count":
                        self.added_blue_obstruction_count
                }

            # -----------------------------
            # UNKNOWN
            # -----------------------------
            if result == unknown:
                return {
                    "status": "unknown",
                    "model": None,
                    "rounds": rounds,
                    "added_blue_obstruction_count":
                        self.added_blue_obstruction_count
                }

            # -----------------------------
            # SAT
            # -----------------------------
            if result == sat:

                model = self.solver.model()

                bad_copy = self.find_blue_altPn_in_model(model)

                # 找到真正的合法染色
                if bad_copy is None:
                    return {
                        "status": "sat",
                        "model": model,
                        "rounds": rounds,
                        "added_blue_obstruction_count":
                            self.added_blue_obstruction_count
                    }

                # 当前模型有蓝色交替路，
                # 加入约束后继续求解
                self.add_blocking_clause_for_blue_copy(
                    bad_copy
                )

        raise RuntimeError(
            f"已经达到 max_rounds = {self.max_rounds}，"
            "但计算仍未结束。"
        )



def get_environment_information():
    """
    返回当前计算环境信息，供控制台输出和结果文件保存使用。
    """
    processor = platform.processor()
    if not processor:
        processor = "Not reported"

    return {
        "python_version": sys.version.replace("\n", " "),
        "python_executable": sys.executable,
        "z3_version": z3.get_version_string(),
        "operating_system": f"{platform.system()} {platform.release()}",
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": processor,
    }


def save_computation_result(
        n,
        N,
        status,
        rounds,
        blocking_count,
        elapsed_time,
        red_edges=None,
        blue_edge_count=None
):
    """
    将一次计算结果自动保存到当前脚本旁边的 results 文件夹。

    文件名示例：
        n16_N19_SAT.txt
        n16_N20_UNSAT.txt
    """
    base_dir = Path(__file__).resolve().parent
    results_dir = base_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    file_path = results_dir / f"n{n}_N{N}_{status}.txt"
    env = get_environment_information()

    with file_path.open("w", encoding="utf-8") as f:
        f.write("Ordered Ramsey Z3 computation\n")
        f.write("=" * 70 + "\n\n")

        f.write("[Environment]\n")
        f.write(f"Python version: {env['python_version']}\n")
        f.write(f"Python executable: {env['python_executable']}\n")
        f.write(f"Z3 version: {env['z3_version']}\n")
        f.write(f"Operating system: {env['operating_system']}\n")
        f.write(f"Platform: {env['platform']}\n")
        f.write(f"Machine: {env['machine']}\n")
        f.write(f"Processor: {env['processor']}\n\n")

        f.write("[Parameters]\n")
        f.write(f"n = {n}\n")
        f.write(f"N = {N}\n\n")

        f.write("[Boolean convention]\n")
        f.write("True = blue edge\n")
        f.write("False = red edge\n\n")

        f.write("[Result]\n")
        f.write(f"Status = {status}\n")
        f.write(f"Total rounds = {rounds}\n")
        f.write(
            "Added blue alternating-path blocking constraints = "
            f"{blocking_count}\n"
        )
        f.write(f"Running time = {elapsed_time:.6f} seconds\n")

        if status == "SAT" and red_edges is not None:
            f.write("\n[Coloring]\n")
            f.write(f"Number of red edges = {len(red_edges)}\n")
            if blue_edge_count is not None:
                f.write(f"Number of blue edges = {blue_edge_count}\n")

            f.write("\n[Red edges, 1-based indexing]\n")
            for i, j in red_edges:
                f.write(f"{i} {j}\n")

            f.write("\n[Red edges, LaTeX format]\n")
            latex_str = ",\\ ".join(f"({i},{j})" for i, j in red_edges)
            f.write(latex_str + "\n")

    return file_path

def exists_coloring_lazy(
        n,
        N,
        verbose=True,
        max_rounds=100000
):
    """
    判断是否存在 K_N 的一种红蓝染色，
    同时满足：

        1. 不包含红色 S_{1,3}；
        2. 不包含蓝色 (P_n, alt)。

    返回：

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
        max_rounds=max_rounds
    )

    # 开始计时
    start_time = time.perf_counter()

    result = solver.solve_lazy(
        verbose=verbose
    )

    # 结束计时
    elapsed_time = (
        time.perf_counter() - start_time
    )

    # ==================================================
    # UNSAT
    # ==================================================
    if result["status"] == "unsat":

        if verbose:
            print()
            print("=" * 60)
            print("计算结果")
            print("=" * 60)

            print(
                f"K_{N} 不可以同时避免红色 S_(1,3) "
                f"和蓝色 (P_{n}, alt)。"
            )

            print("Status = UNSAT")

            print(
                f"总轮数 = {result['rounds']}"
            )

            print(
                "按需补入的蓝色交替路阻断约束数 = "
                f"{result['added_blue_obstruction_count']}"
            )

            print(
                f"运行时间 = {elapsed_time:.6f} 秒"
            )

            print("=" * 60)

        file_path = save_computation_result(
            n=n,
            N=N,
            status="UNSAT",
            rounds=result["rounds"],
            blocking_count=result["added_blue_obstruction_count"],
            elapsed_time=elapsed_time
        )

        if verbose:
            print()
            print(f"计算结果已自动保存到：{file_path}")

        return False, None, None

    # ==================================================
    # UNKNOWN
    # ==================================================
    if result["status"] == "unknown":

        if verbose:
            print()
            print("=" * 60)
            print("计算结果")
            print("=" * 60)

            print("Status = UNKNOWN")

            print(
                "Z3 返回 UNKNOWN，"
                "因此该次计算不能用于证明 SAT 或 UNSAT。"
            )

            print(
                f"总轮数 = {result['rounds']}"
            )

            print(
                "按需补入的蓝色交替路阻断约束数 = "
                f"{result['added_blue_obstruction_count']}"
            )

            print(
                f"运行时间 = {elapsed_time:.6f} 秒"
            )

            print("=" * 60)

        file_path = save_computation_result(
            n=n,
            N=N,
            status="UNKNOWN",
            rounds=result["rounds"],
            blocking_count=result["added_blue_obstruction_count"],
            elapsed_time=elapsed_time
        )

        if verbose:
            print()
            print(f"计算结果已自动保存到：{file_path}")

        return None, None, None

    # ==================================================
    # SAT
    # ==================================================

    red_edges, blue_edges = solver.decode_model(
        result["model"]
    )

    # 转成论文中的 1-based 编号
    red_edges_1 = solver.to_one_based(
        red_edges
    )

    blue_edges_1 = solver.to_one_based(
        blue_edges
    )

    if verbose:
        print()
        print("=" * 60)
        print("计算结果")
        print("=" * 60)

        print(
            f"K_{N} 可以同时避免红色 S_(1,3) "
            f"和蓝色 (P_{n}, alt)。"
        )

        print("Status = SAT")

        print(
            f"总轮数 = {result['rounds']}"
        )

        print(
            "按需补入的蓝色交替路阻断约束数 = "
            f"{result['added_blue_obstruction_count']}"
        )

        print(
            f"红边数 = {len(red_edges_1)}"
        )

        print(
            f"蓝边数 = {len(blue_edges_1)}"
        )

        print(
            f"运行时间 = {elapsed_time:.6f} 秒"
        )

        print()
        print("红边按 LaTeX 形式输出：")

        latex_str = ",\\ ".join(
            [
                f"({i},{j})"
                for i, j in red_edges_1
            ]
        )

        print(latex_str)

        print("=" * 60)

    file_path = save_computation_result(
        n=n,
        N=N,
        status="SAT",
        rounds=result["rounds"],
        blocking_count=result["added_blue_obstruction_count"],
        elapsed_time=elapsed_time,
        red_edges=red_edges_1,
        blue_edge_count=len(blue_edges_1)
    )

    if verbose:
        print()
        print(f"计算结果已自动保存到：{file_path}")

    return True, red_edges_1, blue_edges_1



def print_environment_information():
    """
    输出计算环境信息。
    """
    env = get_environment_information()

    print("=" * 60)
    print("Ordered Ramsey Z3 computation")
    print("=" * 60)
    print(f"Python version: {env['python_version']}")
    print(f"Python executable: {env['python_executable']}")
    print(f"Z3 version: {env['z3_version']}")
    print(f"Operating system: {env['operating_system']}")
    print(f"Platform: {env['platform']}")
    print(f"Machine: {env['machine']}")
    print(f"Processor: {env['processor']}")
    print("=" * 60)


# ==========================================================
# 主程序
# ==========================================================

if __name__ == "__main__":

    print_environment_information()

    # ======================================================
    # 运行模式：
    #   "batch"  -> 自动计算 Theorem 3.5 中 n=3,...,20
    #   "single" -> 只计算一组指定的 (n,N)
    # ======================================================
    RUN_MODE = "batch"

    if RUN_MODE == "batch":

        # Theorem 3.5 中 n=3,...,20 的精确值
        exact_values = {
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
        print("开始批量计算 Theorem 3.5 中 n = 3,...,20 的精确值")
        print("对每个 n 分别检查 N=r-1 (应为 SAT) 和 N=r (应为 UNSAT)")
        print("=" * 70)

        total_cases = 2 * len(exact_values)
        finished_cases = 0
        failed_cases = []

        for current_n, ramsey_value in exact_values.items():

            print()
            print("#" * 70)
            print(
                f"n = {current_n}, "
                f"claimed exact value r = {ramsey_value}"
            )
            print("#" * 70)

            # ----------------------------------------------
            # N = r - 1，应为 SAT
            # ----------------------------------------------
            sat_N = ramsey_value - 1

            print()
            print(f"[SAT test] n = {current_n}, N = {sat_N}")

            sat_result, _, _ = exists_coloring_lazy(
                n=current_n,
                N=sat_N,
                verbose=False,
                max_rounds=100000
            )

            finished_cases += 1

            if sat_result is True:
                print("Result: SAT")
                print("Expected: SAT -> PASSED")
            elif sat_result is False:
                print("Result: UNSAT")
                print("Expected: SAT -> FAILED")
                failed_cases.append((current_n, sat_N, "expected SAT"))
            else:
                print("Result: UNKNOWN")
                print("Expected: SAT -> FAILED")
                failed_cases.append((current_n, sat_N, "expected SAT"))

            print(f"Progress: {finished_cases}/{total_cases}")

            # ----------------------------------------------
            # N = r，应为 UNSAT
            # ----------------------------------------------
            unsat_N = ramsey_value

            print()
            print(f"[UNSAT test] n = {current_n}, N = {unsat_N}")

            unsat_result, _, _ = exists_coloring_lazy(
                n=current_n,
                N=unsat_N,
                verbose=False,
                max_rounds=100000
            )

            finished_cases += 1

            if unsat_result is False:
                print("Result: UNSAT")
                print("Expected: UNSAT -> PASSED")
            elif unsat_result is True:
                print("Result: SAT")
                print("Expected: UNSAT -> FAILED")
                failed_cases.append((current_n, unsat_N, "expected UNSAT"))
            else:
                print("Result: UNKNOWN")
                print("Expected: UNSAT -> FAILED")
                failed_cases.append((current_n, unsat_N, "expected UNSAT"))

            print(f"Progress: {finished_cases}/{total_cases}")

        print()
        print("=" * 70)
        print("批量计算结束。")

        if failed_cases:
            print("存在与 Theorem 3.5 预期不一致的实例：")
            for item in failed_cases:
                print(item)
        else:
            print("36 个实例全部与 Theorem 3.5 的预期一致。")

        print("每个实例的详细结果已自动保存到 results 文件夹。")
        print("=" * 70)

    elif RUN_MODE == "single":

        # 只计算单个实例时修改这里
        single_n = 16
        single_N = 20

        print()
        print(f"单个实例：n = {single_n}, N = {single_N}")
        print()

        exists_coloring_lazy(
            n=single_n,
            N=single_N,
            verbose=True,
            max_rounds=100000
        )

    else:
        raise ValueError('RUN_MODE 只能是 "batch" 或 "single"。')
