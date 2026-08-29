# Reproducible computations for ordered Ramsey numbers

This repository contains the computational material for the ordered Ramsey problem

\[
R_<\bigl(\mathcal S_{1,3},(\mathcal P_n,\triangleleft_{\mathrm{alt}})\bigr).
\]

The repository provides the source code, computational results, CNF instances, DRAT certificates, solver/checker logs, and summary tables used to support the small-parameter exact values for `3 <= n <= 20`.

The main reproducibility chain is

```text
Python/Z3 search
    -> SAT lower-bound coloring or UNSAT candidate
    -> DIMACS CNF generation
    -> CaDiCaL 2.0.1
    -> textual DRAT certificate
    -> independent verification with DRAT-trim
```

For the 18 upper-bound instances corresponding to `n = 3,...,20`, all DRAT certificates were independently checked successfully:

```text
VERIFIED = 18
FAILED   = 0
```

The verification summary is stored in `logs/verification_summary.csv`.

## 1. Boolean convention

For every edge `1 <= i < j <= N`, introduce one Boolean variable `x_{i,j}`.

- `x_{i,j} = True` means that edge `ij` is **blue**.
- `x_{i,j} = False` means that edge `ij` is **red**.

The same convention is used by the Z3 program and by the DIMACS CNF generator.

## 2. SAT/CNF encoding

For fixed `n` and `N`, the formula is satisfiable if and only if there exists a red/blue coloring of the ordered complete graph `K_N` containing neither a red `S_{1,3}` nor a blue alternating `P_n`.

### 2.1 No red `S_{1,3}`

For every `i < j < k`, add

\[
x_{i,j}\lor x_{i,k}.
\]

Since `False` means red, this prevents the two edges `ij` and `ik` from being red simultaneously. Equivalently, every vertex has at most one red edge to its right.

### 2.2 No blue alternating `P_n`

For every increasing `n`-set

\[
v_1<\cdots<v_n,
\]

the alternating path uses exactly the pairs of positions `a<b` satisfying

\[
a+b\in\{n+1,n+2\}.
\]

For every such `n`-set, add

\[
\bigvee_{\substack{1\le a<b\le n\\a+b\in\{n+1,n+2\}}}
\neg x_{v_a,v_b}.
\]

Thus at least one edge of every candidate alternating path is red, so no candidate is entirely blue.

The number of graph variables and clauses is

\[
\binom{N}{2}
\quad\text{and}\quad
\binom{N}{3}+\binom{N}{n},
\]

respectively.

For example, for `(n,N)=(16,20)`, the generated CNF contains

```text
Variables = 190
Red-star clauses = 1140
Alternating-path clauses = 4845
Total clauses = 5985
```

## 3. Exact values checked computationally

The computations cover the following exact values:

| `n` | exact value |
|---:|---:|
| 3 | 5 |
| 4 | 6 |
| 5 | 7 |
| 6 | 8 |
| 7 | 10 |
| 8 | 11 |
| 9 | 12 |
| 10 | 13 |
| 11 | 14 |
| 12 | 15 |
| 13 | 17 |
| 14 | 18 |
| 15 | 19 |
| 16 | 20 |
| 17 | 21 |
| 18 | 22 |
| 19 | 23 |
| 20 | 24 |

For each claimed exact value `R`, two instances are recorded:

- `N = R-1`: SAT, giving an avoiding coloring and hence the lower bound;
- `N = R`: UNSAT, with a DRAT certificate independently verified by DRAT-trim.

Thus the computational certification principle is

```text
SAT at N = R-1  ->  R_< >= R
verified UNSAT at N = R  ->  R_< <= R
```

and together these certify the exact value.

## 4. Repository structure

```text
OrderedRamseyZ3/
├── README.md
├── generate_cnf.py
├── ramsey_z3_batch_autosave.py
├── summarize_results.py
├── verify_all_unsat.sh
│
├── results/
│   ├── computational_results.csv
│   ├── n3_N4_SAT.txt
│   ├── n3_N5_UNSAT.txt
│   ├── ...
│   └── n20_N24_UNSAT.txt
│
├── cnf/
│   ├── n3_N5.cnf
│   ├── ...
│   └── n20_N24.cnf
│
├── proofs/
│   ├── n3_N5_ascii.drat
│   ├── ...
│   └── n20_N24_ascii.drat
│
└── logs/
    ├── verification_summary.csv
    ├── n3_N5_cadical.log
    ├── n3_N5_drat_trim.log
    ├── ...
    └── n20_N24_drat_trim.log
```

The third-party source directories used locally to compile CaDiCaL and DRAT-trim are not required to be included in the repository. Their versions/commits should instead be recorded in the computational environment information.

## 5. Main files

### `ramsey_z3_batch_autosave.py`

Runs the original lazy-constraint Z3 search. It checks whether an avoiding coloring exists and records:

- SAT / UNSAT / UNKNOWN status;
- number of lazy rounds;
- number of added blue-path blocking constraints;
- running time;
- SAT colorings, including the red-edge list.

The Z3 convention is `True = blue`, `False = red`.

### `generate_cnf.py`

Generates the 18 DIMACS CNF instances corresponding to the claimed upper bounds for `3 <= n <= 20`.

Run with

```bash
python generate_cnf.py
```

The generated files are written to `cnf/`.

### `summarize_results.py`

Reads the individual computation records in `results/` and creates

```text
results/computational_results.csv
```

which summarizes the parameters, expected status, actual status, number of rounds, number of blocking constraints, and running times.

### `verify_all_unsat.sh`

Runs CaDiCaL on every upper-bound CNF instance, writes textual DRAT proofs, and checks every proof independently with DRAT-trim.

Run from MSYS2 UCRT64 with

```bash
cd /e/OrderedRamseyZ3
bash verify_all_unsat.sh
```

The script creates/updates `proofs/` and `logs/` and produces

```text
logs/verification_summary.csv
```

A successful complete run ends with

```text
VERIFIED = 18
FAILED   = 0
```

## 6. SAT lower-bound witnesses

For a SAT instance `N=R-1`, the corresponding file in `results/` contains the red-edge list using 1-based vertex numbering. All unlisted edges are blue.

For example, `results/n16_N19_SAT.txt` records an avoiding coloring on `K_19`, certifying

\[
R_<\bigl(\mathcal S_{1,3},(\mathcal P_{16},\triangleleft_{\mathrm{alt}})\bigr)\ge 20.
\]

The result files also contain solver/environment information and running times.

## 7. UNSAT certificates

The upper-bound CNF instances are stored in `cnf/`.

For each instance, CaDiCaL is run with textual proof output, using the `--no-binary` option. A typical command is

```bash
cadical --no-binary INPUT.cnf PROOF.drat
```

CaDiCaL uses exit code `20` for an UNSAT instance.

The resulting DRAT proof is then checked independently with DRAT-trim:

```bash
./drat-trim INPUT.cnf PROOF.drat
```

A successfully checked proof contains

```text
s VERIFIED
```

All 18 upper-bound instances in the current computation passed this independent verification.

## 8. Solver and checker

The final UNSAT certification used:

- **CaDiCaL 2.0.1** as the proof-producing SAT solver;
- **DRAT-trim** as the independent proof checker;
- textual DRAT proofs generated with `--no-binary`.

CaDiCaL and DRAT-trim were compiled locally under **MSYS2 UCRT64 on Windows**.

For archival reproducibility, the final repository/release should additionally record the exact DRAT-trim commit, Python version, Z3 version, Windows version, CPU, RAM, and command-line options used.

## 9. Computational logs and summary files

`results/computational_results.csv` summarizes the Z3 computations.

`logs/verification_summary.csv` summarizes the certificate verification. In the current run, all 18 upper-bound instances have status `VERIFIED`.

The `logs/` directory also contains per-instance CaDiCaL and DRAT-trim transcripts, so each upper-bound computation can be audited individually.

## 10. Reproducing the upper-bound certification

A typical full reproduction is:

```text
1. Run generate_cnf.py
2. Compile/install CaDiCaL and DRAT-trim
3. Run verify_all_unsat.sh from MSYS2 UCRT64
4. Check logs/verification_summary.csv
```

The expected final summary is

```text
VERIFIED = 18
FAILED   = 0
```

## 11. Notes for the paper and archive

The paper should record at least:

- the Boolean/CNF encoding;
- source code and input generator;
- solver name and version;
- checker name and version/commit;
- operating system and hardware;
- command-line options;
- running times;
- satisfying colorings for lower bounds;
- DRAT certificates and independent checker results for computational upper bounds;
- a table distinguishing analytically proved values from computationally certified values.

For a permanent archival release, it is also recommended to include SHA-256 checksums for the CNF, proof, log, and result files.
