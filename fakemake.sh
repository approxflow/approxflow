#!/bin/bash
depfile="DEPENDENCY_OUTPUT.TXT"
cwd=$(pwd)
progdir=$(dirname $1)

cd $progdir
./configure
make -k -d > $depfile
#make -k -d -B > $depfile
make clean

# now parse it
./../fakemake_parser.py $depfile
rm $depfile
cd $cwd
