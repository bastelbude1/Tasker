#!/bin/bash
# Helper script to generate various formatted outputs for testing stdout_split/stderr_split

case "$1" in
    "space")
        echo "alpha beta gamma delta epsilon"
        ;;
    "tab")
        echo -e "alpha\tbeta\tgamma\tdelta\tepsilon"
        ;;
    "comma")
        echo "alpha,beta,gamma,delta,epsilon"
        ;;
    "semicolon")
        echo "alpha;beta;gamma;delta;epsilon"
        ;;
    "pipe")
        echo "alpha|beta|gamma|delta|epsilon"
        ;;
    "colon")
        echo "alpha:beta:gamma:delta:epsilon"
        ;;
    "newline")
        echo -e "alpha\nbeta\ngamma\ndelta\nepsilon"
        ;;
    "mixed")
        echo "alpha beta,gamma;delta|epsilon:zeta"
        ;;
    "empty")
        echo ""
        ;;
    "single")
        echo "singlevalue"
        ;;
    "consecutive")
        echo "alpha,,gamma,,epsilon"
        ;;
    "trailing")
        echo "alpha,beta,gamma,"
        ;;
    "stderr_test")
        >&2 echo "error1 error2 error3 error4"
        ;;
    *)
        echo "Usage: $0 {space|tab|comma|semicolon|pipe|colon|newline|mixed|empty|single|consecutive|trailing|stderr_test}"
        exit 1
        ;;
esac