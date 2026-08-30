# Reproducible computations for ordered Ramsey numbers

This repository contains the computational material used to verify exact small values for the ordered Ramsey problem

\[
R_<\bigl(\mathcal S_{1,3},(\mathcal P_n,\triangleleft_{\mathrm{alt}})\bigr).
\]

The repository is designed so that the computational lower bounds and upper bounds can be checked independently:

- **Lower bounds** are supported by explicit SAT coloring witnesses.
- **Upper bounds** are supported by DIMACS CNF instances, CaDiCaL-generated textual DRAT certificates, and independent verification with DRAT-trim.

For the 18 cases \(3\le n\le 20\), the repository currently contains

- **18/18 SAT witnesses independently verified**;
- **18/18 UNSAT certificates independently verified**.

---

## 1. Boolean convention

For every edge \(1\le i<j\le N\), use one Boolean variable \(x_{i,j}\).

- `True` means that edge \(ij\) is **blue**.
- `False` means that edge \(ij\) is **red**.

The same convention is used by the Python/Z3 code and by the DIMACS CNF generator.

---

## 2. CNF encoding

For fixed \(n\) and \(N\), the CNF is satisfiable if and only if there exists a red/blue coloring of the ordered complete graph \(K_N\) containing neither a red \(\mathcal S_{1,3}\) nor a blue alternating \((\mathcal P_n,\triangleleft_{\mathrm{alt}})\).

### 2.1 No red \(\mathcal S_{1,3}\)

For every \(i<j<k\), add the clause

\[
x_{i,j}\lor x_{i,k}.
\]

Because `False` means red, this clause prevents both \(ij\) and \(ik\) from being red. Equivalently, every vertex has at most one red edge to its right.

### 2.2 No blue alternating \((\mathcal P_n,\triangleleft_{\mathrm{alt}})\)

For every increasing \(n\)-set

\[
v_1<\cdots<v_n,
\]

the alternating path uses precisely the pairs of positions \(a<b\) satisfying

\[
a+b\in\{n+1,n+2\}.
\]

For each such \(n\)-set, add the clause

\[
\bigvee_{\substack{1\le a<b\le n\\a+b\in\{n+1,n+2\}}}
\neg x_{v_a,v_b}.
\]

Thus at least one required alternating-path edge is red, so the candidate path is not entirely blue.

The total numbers of graph variables and clauses are

\[
\binom{N}{2}
\qquad\text{and}\qquad
\binom{N}{3}+\binom{N}{n},
\]

respectively.

---

## 3. Repository structure

```text
OrderedRamseyZ3/
├── README.md
├── environment.txt
├── generate_cnf.py
├── ramsey_z3_batch_autosave.py
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
    └── witness_verification.txt
```

The DRAT files are stored using **Git LFS** because the largest certificates exceed the ordinary GitHub file-size limit.

---

## 4. Computational environment

The exact environment used for the reported computations is recorded in

```text
environment.txt
```

The recorded setup includes:

- Microsoft Windows 11 Home, Chinese edition, version 10.0.26200;
- AMD Ryzen 5 4600U with Radeon Graphics;
- 16 GB RAM;
- Python 3.13.5;
- Z3 4.16.0;
- CaDiCaL 2.0.1;
- GCC 16.2.0;
- DRAT-trim from the `master` branch at commit `2e3b2dc` (2024-11-25).

CaDiCaL is used as the proof-producing SAT solver for the UNSAT upper-bound instances. Textual DRAT proofs are generated with

```text
--no-binary
```

DRAT-trim is used as an independent proof checker.

---

## 5. Generate all upper-bound CNF instances

Run

```bash
python generate_cnf.py
```

The script generates all 18 upper-bound DIMACS instances for \(3\le n\le 20\) and writes them to

```text
cnf/
```

The script is path-independent: it uses the directory containing `generate_cnf.py` as the repository root.

For example, the final case is generated as

```text
cnf/n20_N24.cnf
```

with 276 Boolean edge variables and 12,650 clauses.

---

## 6. Verify one SAT lower-bound witness

A SAT result file lists the red edges of an avoiding coloring. Every unlisted edge is blue.

For example:

```bash
python verify_witness.py results/n4_N5_SAT.txt
```

The verifier independently checks:

1. that no vertex has two red edges to its right, hence there is no red \(\mathcal S_{1,3}\);
2. every increasing \(n\)-vertex subset, to confirm that none induces a blue alternating \((\mathcal P_n,\triangleleft_{\mathrm{alt}})\).

A valid witness ends with

```text
VERIFIED WITNESS
```

The verifier does **not** use Z3.

---

## 7. Verify all SAT lower-bound witnesses

Run

```bash
python verify_all_witnesses.py
```

The script independently verifies every `*_SAT.txt` file in `results/` and writes the summary to

```text
results/witness_verification.txt
```

The current result is

```text
VERIFIED = 18
FAILED   = 0
```

Thus all 18 lower-bound coloring witnesses for \(3\le n\le 20\) pass the independent checker.

---

## 8. Produce and verify all UNSAT upper-bound certificates

The publication-grade upper-bound route is

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

It is path-independent and expects CaDiCaL and DRAT-trim either to be available in `PATH` or to be supplied through environment variables.

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

1. reads the corresponding CNF from `cnf/`;
2. runs CaDiCaL with `--no-binary`;
3. writes a textual DRAT proof to `proofs/`;
4. records the CaDiCaL transcript in `logs/`;
5. checks the proof with DRAT-trim;
6. records the DRAT-trim transcript in `logs/`;
7. writes the final batch summary to `logs/verification_summary.csv`.

The current result is

```text
VERIFIED = 18
FAILED   = 0
```

A solver log that merely states `UNSATISFIABLE` is not treated as the proof. The independently checked DRAT certificate is the checkable UNSAT evidence.

---

## 9. Claimed exact values and corresponding certificates

For each exact value \(R\), the repository supplies

- a SAT coloring witness on \(K_{R-1}\), proving \(R_<\ge R\);
- a verified UNSAT certificate for the CNF on \(K_R\), proving \(R_<\le R\).

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

The corresponding DRAT certificate for each upper instance is stored in `proofs/` with suffix `_ascii.drat`.

---

## 10. Logs and running times

The repository keeps both solver and checker transcripts.

- CaDiCaL logs: `logs/*_cadical.log`
- DRAT-trim logs: `logs/*_drat_trim.log`
- UNSAT batch summary: `logs/verification_summary.csv`
- SAT witness batch summary: `results/witness_verification.txt`
- Original Z3 computation outputs: `results/*_SAT.txt` and `results/*_UNSAT.txt`

The individual files record the corresponding running times and computation details.

---

## 11. Original Z3 search

`ramsey_z3_batch_autosave.py` contains the original Python/Z3 search used to obtain the SAT/UNSAT computational data.

The independent verification scripts are intentionally separate from the search procedure:

```text
Z3 search
    ↓
SAT witness
    ↓
verify_witness.py
```

and

```text
CNF generator
    ↓
CaDiCaL
    ↓
DRAT
    ↓
DRAT-trim
```

This separation reduces reliance on a single implementation.

---

## 12. Reproducibility principle

For a claimed exact value \(R\):

\[
\boxed{\text{verified SAT witness on }K_{R-1}}
\]

proves

\[
R_<\ge R,
\]

while

\[
\boxed{\text{verified UNSAT certificate on }K_R}
\]

proves

\[
R_<\le R.
\]

Together they certify the reported exact value.

For the current range \(3\le n\le 20\):

```text
SAT witnesses:
VERIFIED = 18
FAILED   = 0

UNSAT certificates:
VERIFIED = 18
FAILED   = 0
```

Thus both computational sides of all 18 reported exact values are independently checkable from the material in this repository.
