#!/usr/bin/env bash

# ==========================================================
# Batch production and independent verification of
# UNSAT certificates for the upper-bound CNF instances.
#
# Pipeline:
#
#     DIMACS CNF
#         |
#         v
#     CaDiCaL
#         |
#         v
#     textual DRAT certificate
#         |
#         v
#     DRAT-trim
#         |
#         v
#     VERIFIED
#
# Expected range:
#
#     n = 3,4,...,20
#
# There are 18 upper-bound instances in total.
# ==========================================================


# ----------------------------------------------------------
# Directory containing this script.
#
# This makes the script independent of the user's current
# working directory and local absolute path.
# ----------------------------------------------------------

BASE="$(
    cd "$(dirname "${BASH_SOURCE[0]}")"
    pwd
)"


# ----------------------------------------------------------
# External programs
#
# By default, search for:
#
#     cadical
#     drat-trim
#
# in PATH.
#
# Custom executable paths may be supplied through:
#
#     CADICAL
#     DRATTRIM
#
# Example:
#
# CADICAL=/path/to/cadical \
# DRATTRIM=/path/to/drat-trim \
# bash verify_all_unsat.sh
# ----------------------------------------------------------

CADICAL="${CADICAL:-cadical}"
DRATTRIM="${DRATTRIM:-drat-trim}"


# ----------------------------------------------------------
# Repository directories
# ----------------------------------------------------------

CNF_DIR="$BASE/cnf"
PROOF_DIR="$BASE/proofs"
LOG_DIR="$BASE/logs"


# ==========================================================
# Check required external programs
# ==========================================================

if ! command -v "$CADICAL" >/dev/null 2>&1
then
    echo "ERROR: CaDiCaL was not found."
    echo
    echo "Install CaDiCaL or set the CADICAL environment variable."
    echo
    echo "Example:"
    echo
    echo "  CADICAL=/path/to/cadical \\"
    echo "  DRATTRIM=/path/to/drat-trim \\"
    echo "  bash verify_all_unsat.sh"
    exit 1
fi


if ! command -v "$DRATTRIM" >/dev/null 2>&1
then
    echo "ERROR: DRAT-trim was not found."
    echo
    echo "Install DRAT-trim or set the DRATTRIM environment variable."
    echo
    echo "Example:"
    echo
    echo "  CADICAL=/path/to/cadical \\"
    echo "  DRATTRIM=/path/to/drat-trim \\"
    echo "  bash verify_all_unsat.sh"
    exit 1
fi


# ==========================================================
# Check required directories
# ==========================================================

if [ ! -d "$CNF_DIR" ]
then
    echo "ERROR: CNF directory was not found:"
    echo "$CNF_DIR"
    exit 1
fi


mkdir -p "$PROOF_DIR"
mkdir -p "$LOG_DIR"


# ==========================================================
# Upper-bound instances
#
# Each pair is:
#
#     n  N
#
# where N is the claimed Ramsey value.
#
# The corresponding CNF is checked to be UNSAT.
# ==========================================================

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


EXPECTED_CASES=18


# ==========================================================
# Sanity check on the number of cases
# ==========================================================

if [ "${#CASES[@]}" -ne "$EXPECTED_CASES" ]
then
    echo "ERROR: Incorrect number of upper-bound cases."
    echo
    echo "Expected: $EXPECTED_CASES"
    echo "Found:    ${#CASES[@]}"
    exit 1
fi


# ==========================================================
# Output summary
# ==========================================================

SUMMARY="$LOG_DIR/verification_summary.csv"

echo \
"n,N,cadical_exit,drat_trim_exit,verification" \
> "$SUMMARY"


passed=0
failed=0


# ==========================================================
# Process every upper-bound instance
# ==========================================================

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


    # ======================================================
    # Check the CNF file
    # ======================================================

    if [ ! -f "$cnf" ]
    then

        echo "FAILED: CNF file not found."
        echo "$cnf"

        echo \
"$n,$N,NA,NA,CNF_NOT_FOUND" \
        >> "$SUMMARY"

        failed=$((failed + 1))

        continue
    fi


    # ======================================================
    # Remove any old proof before generating a new one.
    #
    # This prevents an old certificate from being mistaken
    # for a certificate produced by the current run.
    # ======================================================

    rm -f "$proof"


    # ======================================================
    # 1. Run CaDiCaL
    # ======================================================

    echo "[1] Running CaDiCaL..."


    "$CADICAL" \
        --no-binary \
        "$cnf" \
        "$proof" \
        > "$solver_log" 2>&1

    cadical_exit=$?


    # ------------------------------------------------------
    # Standard SAT competition exit codes:
    #
    #     10 = SAT
    #     20 = UNSAT
    #
    # For an upper-bound instance we require UNSAT.
    # ------------------------------------------------------

    if [ "$cadical_exit" -ne 20 ]
    then

        echo \
"CaDiCaL FAILED: expected UNSAT exit code 20, got $cadical_exit"

        echo \
"$n,$N,$cadical_exit,NA,CADICAL_FAILED" \
        >> "$SUMMARY"

        failed=$((failed + 1))

        continue
    fi


    echo "CaDiCaL: UNSAT"


    # ======================================================
    # Check that a proof was actually produced
    # ======================================================

    if [ ! -s "$proof" ]
    then

        echo "FAILED: DRAT proof file was not produced or is empty."

        echo \
"$n,$N,$cadical_exit,NA,PROOF_MISSING" \
        >> "$SUMMARY"

        failed=$((failed + 1))

        continue
    fi


    # ======================================================
    # 2. Independently verify the DRAT certificate
    # ======================================================

    echo "[2] Verifying DRAT proof..."


    "$DRATTRIM" \
        "$cnf" \
        "$proof" \
        > "$verify_log" 2>&1

    drat_trim_exit=$?


    # ------------------------------------------------------
    # Require BOTH:
    #
    #     successful checker exit status
    #
    # and
    #
    #     the explicit "s VERIFIED" message.
    # ------------------------------------------------------

    if \
        [ "$drat_trim_exit" -eq 0 ] \
        && grep -q "s VERIFIED" "$verify_log"
    then

        echo "DRAT-trim: VERIFIED"

        echo \
"$n,$N,$cadical_exit,$drat_trim_exit,VERIFIED" \
        >> "$SUMMARY"

        passed=$((passed + 1))

    else

        echo "DRAT-trim: NOT VERIFIED"

        echo \
"$n,$N,$cadical_exit,$drat_trim_exit,NOT_VERIFIED" \
        >> "$SUMMARY"

        failed=$((failed + 1))

    fi

done


# ==========================================================
# Final summary
# ==========================================================

echo
echo "============================================================"
echo "Finished"
echo "============================================================"

echo "EXPECTED = $EXPECTED_CASES"
echo "VERIFIED = $passed"
echo "FAILED   = $failed"

echo
echo "Summary:"
echo "$SUMMARY"

echo "============================================================"


# ==========================================================
# Final exit status
#
# The script succeeds only when all 18 expected certificates
# have been independently verified.
# ==========================================================

if [ "$failed" -ne 0 ]
then

    echo
    echo "ERROR: At least one upper-bound certificate failed."
    exit 1

fi


if [ "$passed" -ne "$EXPECTED_CASES" ]
then

    echo
    echo "ERROR: Not all expected certificates were verified."
    exit 1

fi


echo
echo "All 18 upper-bound UNSAT certificates were independently verified."

exit 0
