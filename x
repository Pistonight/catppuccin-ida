#!/bin/sh
# ./x <script> [args...] [<script> [args...]]...
#   ->  sh scripts/<script> [args...] if that shell script exists, else
#       uv run scripts/<script>.py [args...]; for each script in order,
#       stopping at the first one that fails.
# An argument that names a script starts the next step; any other argument
# goes to the script before it.
root=$(cd "$(dirname "$0")" && pwd)
scripts="$root/scripts"

#########################################################
# TODO: this script needs to be chmod'ed but i am on windows right now
#########################################################

show_scripts() {
    echo "usage: ./x <script> [args...] [<script> [args...]]..."
    echo "scripts:"
    for f in "$scripts"/*; do
        name=${f##*/}
        name=${name%.py}
        is_shell_script "$name" || is_python_script "$name" || continue
        echo "  $name"
    done | sort -u
}

# scripts/<name>: a shell script (a file without an extension)
is_shell_script() {
    case $1 in *.* | */* | "") return 1 ;; esac
    [ -f "$scripts/$1" ]
}

is_python_script() {
    case $1 in */* | "") return 1 ;; esac
    [ -f "$scripts/$1.py" ]
}

is_script() {
    is_shell_script "$1" || is_python_script "$1"
}

# step_line <colour> <text>: "==> <text>", in the ANSI colour on a terminal
step_line() {
    if [ -t 1 ]; then
        printf '\033[%sm==> %s\033[0m\n' "$1" "$2"
    else
        echo "==> $2"
    fi
}

step_header() { step_line 92 "$1"; }    # bright green
step_failed() { step_line 91 "$1"; }    # bright red

# run_step <script> <n> <args...>: run the script with the first n args
run_step() {
    name=$1 n=$2
    shift 2
    rest=$(($# - n))
    i=0
    while [ $i -lt "$n" ]; do
        a=$1
        shift
        set -- "$@" "$a"
        i=$((i + 1))
    done
    shift "$rest"
    if is_shell_script "$name"; then
        sh "$scripts/$name" "$@"
        return
    fi
    uv run --project "$root" "$scripts/$name.py" "$@"
}

if [ $# -eq 0 ]; then
    show_scripts
    exit 1
fi
if ! is_script "$1"; then
    echo "no such script: $1"
    show_scripts
    exit 1
fi

steps=0
for a in "$@"; do
    is_script "$a" && steps=$((steps + 1))
done

while [ $# -gt 0 ]; do
    name=$1
    shift
    n=0
    for a in "$@"; do
        is_script "$a" && break
        n=$((n + 1))
    done
    [ "$steps" -gt 1 ] && step_header "$name"
    run_step "$name" "$n" "$@" || {
        status=$?
        [ "$steps" -gt 1 ] && step_failed "$name failed (exit $status); stopping"
        exit "$status"
    }
    shift "$n"
done
