# Ordered Ramsey Numbers for Alternating Paths and Stars

This repository contains the computational material used to determine
and independently verify exact small values for the ordered Ramsey
problem

$$
R_<\bigl(
\mathcal S_{1,3},
(\mathcal P_n,\triangleleft_{\mathrm{alt}})
\bigr).
$$

The computations cover the 18 cases

$$
3\le n\le 20.
$$

The repository separates the search procedure from the independent
verification procedures.

- **Automatic search:** a Python/Z3 program searches for the first value
  of \(N\) for which no avoiding coloring exists.
- **Lower bounds:** explicit SAT coloring witnesses are independently
  checked without using Z3.
- **Upper bounds:** complete DIMACS CNF instances are solved by CaDiCaL,
  textual DRAT certificates are produced, and the certificates are
  independently checked by DRAT-trim.

For the 18 cases \(3\le n\le 20\), the current verification results are

```text
SAT witnesses:
VERIFIED = 18
FAILED   = 0

UNSAT certificates:
VERIFIED = 18
FAILED   = 0
```

Thus both sides of all 18 reported exact values are independently
checkable from the material in this repository.

---

## 1. Quick verification

After cloning the repository and installing the required software, the
main verification steps are as follows.

### Verify all SAT lower-bound witnesses

```bash
python verify_all_witnesses.py
```

Expected summary:

```text
VERIFIED = 18
FAILED   = 0
```

### Verify all UNSAT upper-bound certificates

If `cadical` and `drat-trim` are available in `PATH`, run

```bash
bash verify_all_unsat.sh
```

Expected summary:

```text
EXPECTED = 18
VERIFIED = 18
FAILED   = 0
```

### Summarize the 36 Z3 boundary computations

```bash
python summarize_results.py
```

A successful run reports

```text
Expected boundary instances = 36
Successfully parsed instances = 36
Parsing errors = 0
Duplicate instances = 0
Missing expected instances = 0
Unexpected instances = 0
Status mismatches = 0
```

and writes the summary table to

```text
results/computational_results.csv
```

---

## 2. Boolean convention

For every edge \(1\le i<j\le N\), one Boolean variable
\(x_{i,j}\) is used.

- `True` means that edge \(ij\) is **blue**.
- `False` means that edge \(ij\) is **red**.

The same convention is used by the Python/Z3 programs and by the
DIMACS CNF generator.

In DIMACS notation:

- a positive literal \(x_{i,j}\) represents that edge \(ij\) is blue;
- a negative literal \(-x_{i,j}\) represents that edge \(ij\) is red.

---

## 3. CNF encoding

For fixed positive integers \(n\) and \(N\), the CNF is satisfiable if
and only if there exists a red-blue edge-coloring of the ordered
complete graph \(K_N\) containing neither

- a red copy of \(\mathcal S_{1,3}\), nor
- a blue copy of
  \((\mathcal P_n,\triangleleft_{\mathrm{alt}})\).

### 3.1 Excluding a red \(\mathcal S_{1,3}\)

For every

$$
1\le i<j<k\le N,
$$

the CNF contains the clause

$$
x_{i,j}\lor x_{i,k}.
$$

Since `False` represents a red edge, this clause prevents both
\(ij\) and \(ik\) from being red simultaneously.

Equivalently, every vertex has at most one red edge to its right.
Therefore the coloring contains no red ordered
\(\mathcal S_{1,3}\).

The number of such clauses is

$$
\binom{N}{3}.
$$

### 3.2 Excluding a blue alternating
\((\mathcal P_n,\triangleleft_{\mathrm{alt}})\)

Let

$$
v_1<v_2<\cdots<v_n
$$

be any increasing \(n\)-vertex subset of \(K_N\).

The edges of the alternating ordered path are precisely the pairs of
positions \(a<b\) satisfying

$$
a+b\in\left\{n+1,n+2\right\}.
$$

For convenience, define

$$
I_n=
\left\{
(a,b):
1\le a<b\le n,\ 
a+b\in\left\{n+1,n+2\right\}
\right\}.
$$

Thus the edge set of the alternating path on the vertices
\(v_1,\ldots,v_n\) is

$$
\left\{
v_av_b:(a,b)\in I_n
\right\}.
$$

For every increasing \(n\)-set, the CNF therefore contains the clause

$$
\bigvee_{(a,b)\in I_n}
\neg x_{v_a,v_b}.
$$

This clause requires at least one required alternating-path edge to be
red. Hence the \(n\)-set cannot induce an entirely blue copy of

$$
(\mathcal P_n,\triangleleft_{\mathrm{alt}}).
$$

There is one such clause for every increasing \(n\)-vertex subset, so
the number of alternating-path clauses is

$$
\binom{N}{n}.
$$

Consequently, the complete CNF has

$$
\binom{N}{2}
$$

Boolean variables and

$$
\binom{N}{3}+\binom{N}{n}
$$

clauses.

---

## 4. Repository structure

```text
OrderedRamseyZ3/
├── README.md
├── environment.txt
├── search_ramsey.py
├── ramsey_z3_batch_autosave.py
├── generate_cnf.py
├── summarize_results.py
├── verify_witness.py
├── verify_all_witnesses.py
├── verify_all_unsat.sh
├── .gitattributes
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
├── logs/
│   ├── verification_summary.csv
│   ├── *_cadical.log
│   └── *_drat_trim.log
│
└── results/
    ├── *_SAT.txt
    ├── *_UNSAT.txt
    ├── computational_results.csv
    ├── witness_verification.txt
    ├── search_trace.csv
    └── search_ramsey_values.csv
```

The two Z3 scripts have different purposes:

- `search_ramsey.py` automatically searches for the first UNSAT value
  of \(N\);
- `ramsey_z3_batch_autosave.py` verifies the two boundary instances
  associated with each claimed value and saves the corresponding
  computation results and SAT witnesses.

The DRAT files in `proofs/` are stored using **Git LFS**, since the
largest certificates exceed the ordinary GitHub file-size limit.

---

## 5. Computational environment

The exact computational environment used for the reported calculations
is recorded in

```text
environment.txt
```

The recorded setup includes:

- Microsoft Windows 11 Home, Chinese edition, version/build
  `10.0.26200`;
- AMD Ryzen 5 4600U with Radeon Graphics;
- 16 GB RAM;
- Python 3.13.5;
- Z3 4.16.0;
- CaDiCaL 2.0.1;
- GCC 16.2.0;
- DRAT-trim from the `master` branch at commit `2e3b2dc`
  dated 2024-11-25.

The exploratory Boolean satisfiability computations and lower-bound
coloring witnesses were obtained using Python and the `z3-solver`
Python package.

CaDiCaL is used separately as the proof-producing SAT solver for the
upper-bound CNF instances.

Textual DRAT proofs are generated using the CaDiCaL option

```text
--no-binary
```

and are independently checked using DRAT-trim.

---

## 6. Automatic Z3 search

The script

```text
search_ramsey.py
```

performs an automatic search for the smallest value of \(N\) for which
there is no coloring avoiding both forbidden ordered graphs.

For each fixed \(n\), the search starts at

$$
N=n
$$

and increases \(N\) one at a time.

The logic is

```text
SAT
  -> an avoiding coloring exists
  -> increase N

UNSAT
  -> no avoiding coloring exists
  -> the first UNSAT value is the candidate Ramsey number

UNKNOWN
  -> the computation is inconclusive
```

The claimed Ramsey values are **not hard-coded into this search**.

The program uses a lazy-constraint procedure. Initially, only the
constraints excluding a red \(\mathcal S_{1,3}\) are given to Z3.

Whenever the current model contains a blue alternating
\((\mathcal P_n,\triangleleft_{\mathrm{alt}})\), a blocking constraint
for that copy is added and Z3 is called again.

The search is carried out for

$$
3\le n\le20.
$$

The detailed search trace is saved to

```text
results/search_trace.csv
```

and the values found by the automatic search are saved to

```text
results/search_ramsey_values.csv
```

---

## 7. Boundary Z3 computations and witness generation

The script

```text
ramsey_z3_batch_autosave.py
```

has a different role from `search_ramsey.py`.

It takes the claimed value \(R\) for each \(3\le n\le20\) and checks
the two boundary instances

$$
N=R-1
$$

and

$$
N=R.
$$

The expected outcomes are

```text
N = R-1 : SAT
N = R   : UNSAT
```

For a SAT boundary instance, the program saves an explicit coloring
witness in `results/`.

Only the red edges need to be stored; every unlisted edge is interpreted
as blue.

The result files also record information such as

- \(n\);
- \(N\);
- SAT/UNSAT status;
- number of lazy-constraint rounds;
- number of blue-path blocking constraints;
- running time;
- the red-edge witness for SAT instances.

This script is therefore a **boundary verification and witness
generation program**, rather than the automatic search program.

---

## 8. Generate all upper-bound CNF instances

Run

```bash
python generate_cnf.py
```

The script generates the 18 complete DIMACS CNF instances corresponding
to the claimed upper-bound values for

$$
3\le n\le20.
$$

The files are written to

```text
cnf/
```

using names of the form

```text
n{n}_N{N}.cnf
```

For example,

```text
cnf/n20_N24.cnf
```

has

$$
\binom{24}{2}=276
$$

Boolean edge variables.

Its red-star clauses number

$$
\binom{24}{3}=2024,
$$

and its alternating-path clauses number

$$
\binom{24}{20}=10626.
$$

Hence the total number of clauses is

$$
2024+10626=12650.
$$

The generator checks the expected variable and clause counts before
writing each DIMACS file.

The script itself does **not** claim that the generated instances are
UNSAT. Their UNSAT status is established separately using CaDiCaL and
verified using DRAT-trim.

---

## 9. Verify one SAT lower-bound witness

A SAT result file lists the red edges of an avoiding coloring.

Every edge not listed as red is interpreted as blue.

For example:

```bash
python verify_witness.py results/n4_N5_SAT.txt
```

The independent verifier checks:

1. the witness-file format and the validity of all listed red edges;
2. that no vertex has two red edges to its right, hence no red
   \(\mathcal S_{1,3}\) occurs;
3. every increasing \(n\)-vertex subset of \([N]\), to verify that no
   blue alternating
   \((\mathcal P_n,\triangleleft_{\mathrm{alt}})\) occurs.

The verifier also rejects malformed input such as

- invalid vertex labels;
- loop edges;
- duplicate red edges;
- malformed red-edge lines;
- inconsistent parameters.

A valid witness ends with

```text
VERIFIED WITNESS
```

and the verifier exits with status code `0`.

The verifier does **not** use Z3.

---

## 10. Verify all SAT lower-bound witnesses

Run

```bash
python verify_all_witnesses.py
```

The script locates the expected SAT witness files in `results/` and
checks each one using `verify_witness.py`.

For the range

$$
3\le n\le20,
$$

exactly 18 boundary SAT witnesses are expected.

The script therefore checks not only whether the available witnesses
are valid, but also whether all 18 expected witness files are present.

The summary is written to

```text
results/witness_verification.txt
```

The current result is

```text
VERIFIED = 18
FAILED   = 0
```

The batch verifier terminates with a nonzero exit status if

- an expected witness is missing;
- a witness fails verification; or
- the number of witness files is not the expected number.

Thus all 18 lower-bound coloring witnesses pass an independent checker
that does not use Z3.

---

## 11. Produce and verify all UNSAT upper-bound certificates

The publication-grade upper-bound verification route is

```text
DIMACS CNF
    ↓
CaDiCaL
    ↓
textual DRAT certificate
    ↓
DRAT-trim
    ↓
VERIFIED
```

The batch script is

```text
verify_all_unsat.sh
```

It expects CaDiCaL and DRAT-trim either to be available in `PATH` or to
be supplied through environment variables.

### If both programs are in `PATH`

```bash
bash verify_all_unsat.sh
```

### If explicit executable paths are needed

```bash
CADICAL=/path/to/cadical \
DRATTRIM=/path/to/drat-trim \
bash verify_all_unsat.sh
```

For each of the 18 upper-bound instances, the script:

1. checks that the corresponding CNF file exists;
2. removes any old proof file for that instance;
3. runs CaDiCaL using `--no-binary`;
4. requires the CaDiCaL UNSAT exit code `20`;
5. writes a textual DRAT certificate to `proofs/`;
6. checks that the proof file was actually produced and is nonempty;
7. records the CaDiCaL transcript in `logs/`;
8. checks the DRAT certificate using DRAT-trim;
9. requires both a successful checker exit status and the message
   `s VERIFIED`;
10. records the DRAT-trim transcript in `logs/`;
11. writes the final batch summary to
    `logs/verification_summary.csv`.

The current result is

```text
EXPECTED = 18
VERIFIED = 18
FAILED   = 0
```

The script terminates successfully only if all 18 expected certificates
are independently verified.

A solver log that merely states `UNSATISFIABLE` is not treated as the
upper-bound proof.

The independently checked DRAT certificate is the checkable UNSAT
evidence.

---

## 12. Summarize the 36 boundary computations

Run

```bash
python summarize_results.py
```

For each claimed value \(R\), two Z3 boundary result files are expected:

```text
N = R-1 : SAT
N = R   : UNSAT
```

Since there are 18 values of \(n\), there should be exactly

$$
18\times2=36
$$

boundary computation results.

The summary script checks:

- that all 36 expected \((n,N)\) instances are present;
- that there are no duplicate instances;
- that there are no unexpected instances;
- that the filename agrees with the metadata stored inside the file;
- that \(N=R-1\) has status SAT;
- that \(N=R\) has status UNSAT;
- that all result files can be parsed correctly.

The output table is written to

```text
results/computational_results.csv
```

A successful run reports

```text
Expected boundary instances = 36
Successfully parsed instances = 36
Parsing errors = 0
Duplicate instances = 0
Missing expected instances = 0
Unexpected instances = 0
Status mismatches = 0
```

The script exits with a nonzero status if the collection of boundary
results is incomplete or inconsistent.

---

## 13. Claimed exact values and corresponding certificates

For each claimed exact value \(R\), the repository supplies

- a verified SAT coloring witness on \(K_{R-1}\), proving

  $$
  R_<\ge R;
  $$

- a verified UNSAT certificate for the CNF on \(K_R\), proving

  $$
  R_<\le R.
  $$

The corresponding instances are as follows.

| \(n\) | Claimed exact value \(R\) | SAT lower witness | UNSAT upper instance |
|---:|---:|---|---|
| 3 | 5 | `results/n3_N4_SAT.txt` | `cnf/n3_N5.cnf` |
| 4 | 6 | `results/n4_N5_SAT.txt` | `cnf/n4_N6.cnf` |
| 5 | 7 | `results/n5_N6_SAT.txt` | `cnf/n5_N7.cnf` |
| 6 | 8 | `results/n6_N7_SAT.txt` | `cnf/n6_N8.cnf` |
| 7 | 10 | `results/n7_N9_SAT.txt` | `cnf/n7_N10.cnf` |
| 8 | 11 | `results/n8_N10_SAT.txt` | `cnf/n8_N11.cnf` |
| 9 | 12 | `results/n9_N11_SAT.txt` | `cnf/n9_N12.cnf` |
| 10 | 13 | `results/n10_N12_SAT.txt` | `cnf/n10_N13.cnf` |
| 11 | 14 | `results/n11_N13_SAT.txt` | `cnf/n11_N14.cnf` |
| 12 | 15 | `results/n12_N14_SAT.txt` | `cnf/n12_N15.cnf` |
| 13 | 17 | `results/n13_N16_SAT.txt` | `cnf/n13_N17.cnf` |
| 14 | 18 | `results/n14_N17_SAT.txt` | `cnf/n14_N18.cnf` |
| 15 | 19 | `results/n15_N18_SAT.txt` | `cnf/n15_N19.cnf` |
| 16 | 20 | `results/n16_N19_SAT.txt` | `cnf/n16_N20.cnf` |
| 17 | 21 | `results/n17_N20_SAT.txt` | `cnf/n17_N21.cnf` |
| 18 | 22 | `results/n18_N21_SAT.txt` | `cnf/n18_N22.cnf` |
| 19 | 23 | `results/n19_N22_SAT.txt` | `cnf/n19_N23.cnf` |
| 20 | 24 | `results/n20_N23_SAT.txt` | `cnf/n20_N24.cnf` |

The corresponding DRAT certificate for each upper-bound instance is
stored in `proofs/` using the filename

```text
n{n}_N{N}_ascii.drat
```

For example,

```text
cnf/n16_N20.cnf
```

is paired with

```text
proofs/n16_N20_ascii.drat
```

---

## 14. Logs and running times

The repository keeps both solver and independent-checker transcripts.

### CaDiCaL logs

```text
logs/*_cadical.log
```

### DRAT-trim logs

```text
logs/*_drat_trim.log
```

### UNSAT verification summary

```text
logs/verification_summary.csv
```

### SAT witness verification summary

```text
results/witness_verification.txt
```

### Z3 boundary computation outputs

```text
results/*_SAT.txt
results/*_UNSAT.txt
```

### Boundary computation summary

```text
results/computational_results.csv
```

### Automatic-search outputs

```text
results/search_trace.csv
results/search_ramsey_values.csv
```

The individual Z3 result files record the corresponding running times,
numbers of lazy-constraint rounds, and numbers of added alternating-path
blocking constraints.

The CaDiCaL and DRAT-trim transcripts are stored separately so that the
proof-producing computation and the independent certificate check can
both be inspected.

---

## 15. Separation of search and verification

The repository intentionally separates discovery from verification.

The automatic-search route is

```text
search_ramsey.py
        ↓
candidate Ramsey value
```

The lower-bound verification route is

```text
ramsey_z3_batch_autosave.py
        ↓
SAT coloring witness on K_(R-1)
        ↓
verify_witness.py
        ↓
VERIFIED WITNESS
```

The upper-bound verification route is

```text
generate_cnf.py
        ↓
DIMACS CNF on K_R
        ↓
CaDiCaL
        ↓
textual DRAT certificate
        ↓
DRAT-trim
        ↓
VERIFIED
```

Thus the lower-bound witness checker does not depend on Z3, and the
upper-bound certificate checker does not depend on the Python/Z3
implementation.

This separation reduces reliance on a single program or SAT solver.

---

## 16. Reproducibility principle

For a claimed exact value \(R\), a verified avoiding coloring on
\(K_{R-1}\) proves

$$
R_<\ge R.
$$

A verified UNSAT certificate for the complete CNF instance on \(K_R\)
proves

$$
R_<\le R.
$$

Therefore,

$$
R_<\bigl(
\mathcal S_{1,3},
(\mathcal P_n,\triangleleft_{\mathrm{alt}})
\bigr)
=
R.
$$

For the current range \(3\le n\le20\), the repository contains

```text
SAT witnesses:
VERIFIED = 18
FAILED   = 0

UNSAT certificates:
VERIFIED = 18
FAILED   = 0
```

Hence both computational sides of all 18 reported exact values are
independently checkable from the files and scripts contained in this
repository.
