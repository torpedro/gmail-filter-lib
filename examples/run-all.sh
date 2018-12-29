#!/bin/bash
ANY_FAILED=false
for f in examples/*.py; do
	if $f >/dev/null; then
		echo $f passed
	else	
		echo $f failed
		ANY_FAILED=true
	fi
done

if $ANY_FAILED; then
	exit 1
else
	exit 0
fi