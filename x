#!/bin/sh
# ./x <script> [args...]  ->  uv run scripts/<script>.py [args...]
root=$(cd "$(dirname "$0")" && pwd)
scripts="$root/scripts"

show_scripts() {
    echo "usage: ./x <script> [args...]"
    echo "scripts:"
    for f in "$scripts"/*.py; do
        name=${f##*/}
        echo "  ${name%.py}"
    done
}

if [ $# -eq 0 ]; then
    show_scripts
    exit 1
fi

name=$1
shift
if [ ! -f "$scripts/$name.py" ]; then
    echo "no such script: $name"
    show_scripts
    exit 1
fi

exec uv run --project "$root" "$scripts/$name.py" "$@"
