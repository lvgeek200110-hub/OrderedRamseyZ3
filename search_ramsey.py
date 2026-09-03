from itertools import combinations

from z3 import (
    Solver,
    Bool,
    Or,
    And,
    Not,
    sat,
    unsat,
    unknown,
    is_true
)


# ==========================================================
# 生成交替路径顺序
# ==========================================================

def alternating_order(n):
    """
    生成 (P_n, alt) 的顶点顺序

    例如:
    n=8:
    [1,3,5,7,8,6,4,2]
    """

    odd = list(range(1, n + 1, 2))

    even = list(
        range(
            n if n % 2 == 0 else n - 1,
            1,
            -2
        )
    )

    return odd + even



# ==========================================================
# 生成交替路径边模式
# ==========================================================

def alternating_path_pattern_edges(n):
    """
    返回交替路径的位置边
    """

    order = alternating_order(n)

    pos = {}

    for idx, v in enumerate(order):
        pos[v] = idx


    edges = []

    for v in range(1, n):

        a = pos[v]
        b = pos[v + 1]

        if a > b:
            a, b = b, a

        edges.append((a, b))


    return edges



# ==========================================================
# Z3 求解器
# ==========================================================

class RamseyZ3:


    def __init__(self, n, N, max_rounds=100000):

        self.n = n
        self.N = N

        self.max_rounds = max_rounds


        self.pattern_edges = (
            alternating_path_pattern_edges(n)
        )


        self.solver = Solver()


        self.edge_vars = {}


        self.block_count = 0



        # 建立变量
        #
        # x(i,j)=True  蓝边
        # x(i,j)=False 红边

        for i in range(N):

            for j in range(i+1, N):

                self.edge_vars[(i,j)] = Bool(
                    f"x_{i}_{j}"
                )



        # 禁止红 S_(1,3)

        self.add_no_red_S13()



    # ------------------------------------------------------
    # 返回边变量
    # ------------------------------------------------------

    def x(self,i,j):

        if i>j:
            i,j=j,i

        return self.edge_vars[(i,j)]



    # ------------------------------------------------------
    # 禁止红色 S_(1,3)
    #
    # 任意 i<j<k:
    #
    # 不能同时:
    #
    # ij 红
    # ik 红
    #
    # ------------------------------------------------------

    def add_no_red_S13(self):

        for i in range(self.N):

            right = range(i+1,self.N)


            for j,k in combinations(right,2):

                self.solver.add(
                    Or(
                        self.x(i,j),
                        self.x(i,k)
                    )
                )



    # ------------------------------------------------------
    # 当前模型中的蓝边
    # ------------------------------------------------------

    def blue_edges(self,model):

        result=set()


        for edge,var in self.edge_vars.items():

            if is_true(
                model.eval(
                    var,
                    model_completion=True
                )
            ):

                result.add(edge)


        return result



    # ------------------------------------------------------
    # 检查蓝色交替路径
    # ------------------------------------------------------

    def find_blue_alt_path(self,model):

        blue=self.blue_edges(model)


        for verts in combinations(
            range(self.N),
            self.n
        ):


            ok=True

            path_edges=[]


            for a,b in self.pattern_edges:


                i=verts[a]
                j=verts[b]


                if i>j:
                    i,j=j,i


                path_edges.append(
                    (i,j)
                )


                if (i,j) not in blue:

                    ok=False
                    break



            if ok:

                return path_edges



        return None



    # ------------------------------------------------------
    # 阻断一个蓝色交替路径
    # ------------------------------------------------------

    def block_blue_path(self,edges):

        self.solver.add(
            Not(
                And(
                    [
                        self.x(i,j)
                        for i,j in edges
                    ]
                )
            )
        )


        self.block_count += 1



    # ------------------------------------------------------
    # Lazy 求解
    # ------------------------------------------------------

    def solve(self,verbose=True):

        rounds=0


        while rounds < self.max_rounds:


            rounds += 1


            result=self.solver.check()


            if verbose:

                print(
                    f"round {rounds}: {result}"
                )


            # 无解

            if result == unsat:


                return False



            # 未知

            if result == unknown:

                return None



            # 找模型

            model=self.solver.model()


            bad=self.find_blue_alt_path(model)



            # 找到合法染色

            if bad is None:

                return True



            # 加阻断约束

            self.block_blue_path(bad)



        raise RuntimeError(
            "超过最大迭代次数"
        )




# ==========================================================
# 判断给定 n,N 是否存在避免染色
# ==========================================================

def exists_coloring(n,N,verbose=False):


    solver=RamseyZ3(n,N)


    result=solver.solve(verbose)


    return result



# ==========================================================
# 自动计算 Ramsey 数
# ==========================================================

def compute_ramsey_number(n):


    print()
    print("="*60)

    print(
        f"计算 n={n}"
    )

    print("="*60)



    N=n



    while True:


        print(
            f"检查 N={N}"
        )


        result=exists_coloring(
            n,
            N,
            verbose=False
        )



        if result is True:


            print(
                f"N={N}: SAT"
            )


            N+=1



        elif result is False:


            print()
            print(
                f"Ramsey number = {N}"
            )


            return N



        else:


            print(
                "UNKNOWN"
            )

            return None




# ==========================================================
# 主程序
# ==========================================================

if __name__ == "__main__":


    # 修改这里即可

    n_values = range(3,20)


    results={}



    for n in n_values:


        R=compute_ramsey_number(n)


        results[n]=R



    print()
    print("="*60)
    print("最终结果")
    print("="*60)


    for n,R in results.items():

        print(
            f"n={n}: R={R}"
        )