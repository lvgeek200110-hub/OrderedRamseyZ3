#!/usr/bin/env bash

BASE="/e/OrderedRamseyZ3"

CADICAL="$BASE/cadical-master/build/cadical"
DRATTRIM="$BASE/drat-trim-master/drat-trim"

CNF_DIR="$BASE/cnf"
PROOF_DIR="$BASE/proofs"
LOG_DIR="$BASE/logs"

mkdir -p "$PROOF_DIR"
mkdir -p "$LOG_DIR"

CASES=(
"3 5"
"4 6"
"5 7"
"6 8"
"7 10"
"8 11"
"9 12"
"10 13"
"11 14"
"12 15"
"13 17"
"14 18"
"15 19"
"16 20"
"17 21"
"18 22"
"19 23"
"20 24"
)

SUMMARY="$LOG_DIR/verification_summary.csv"

echo "n,N,cadical_exit,verification" > "$SUMMARY"

passed=0
failed=0

for case in "${CASES[@]}"
do
    read -r n N <<< "$case"

    cnf="$CNF_DIR/n${n}_N${N}.cnf"
    proof="$PROOF_DIR/n${n}_N${N}_ascii.drat"

    solver_log="$LOG_DIR/n${n}_N${N}_cadical.log"
    verify_log="$LOG_DIR/n${n}_N${N}_drat_trim.log"

    echo
    echo "============================================================"
    echo "Checking n=$n, N=$N"
    echo "============================================================"

    echo "[1] Running CaDiCaL..."

    "$CADICAL" \
        --no-binary \
        "$cnf" \
        "$proof" \
        > "$solver_log" 2>&1

    cadical_exit=$?

    if [ "$cadical_exit" -ne 20 ]; then
        echo "CaDiCaL FAILED: exit code = $cadical_exit"
        echo "$n,$N,$cadical_exit,CADICAL_FAILED" >> "$SUMMARY"

        failed=$((failed + 1))
        continue
    fi

    echo "CaDiCaL: UNSAT"

    echo "[2] Verifying DRAT proof..."

    "$DRATTRIM" \
        "$cnf" \
        "$proof" \
        > "$verify_log" 2>&1

    if grep -q "s VERIFIED" "$verify_log"; then
        echo "drat-trim: VERIFIED"

        echo "$n,$N,$cadical_exit,VERIFIED" >> "$SUMMARY"

        passed=$((passed + 1))
    else
        echo "drat-trim: NOT VERIFIED"

        echo "$n,$N,$cadical_exit,NOT_VERIFIED" >> "$SUMMARY"

        failed=$((failed + 1))
    fi
done

echo
echo "============================================================"
echo "Finished"
echo "============================================================"
echo "VERIFIED = $passed"
echo "FAILED   = $failed"
echo
echo "Summary:"
echo "$SUMMARY"
echo "============================================================"