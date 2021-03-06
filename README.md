# approxflow
Approximate QIF for C programs

ApproxFlow.py: Script to measure (approx) info flow

usage: ./ApproxFlow.py program [function]
  program: a C source program
  function: a function over whose return variable to measure info-flow
            if omitted, measures info-flow for all functions in the C source specified in program


=================================================


Requires
--------

tcc (must be on path) - Tiny C Compiler (http://bellard.org/tcc/)

coan2 - helpful with preprocessing the C source files (C Preprocessor Chainsaw - http://coan2.sourceforge.net/)

cbmc - The C Bounded Model Checker 

scalmc (cryptominisat-based projected-cabable approximate model counter) from Kuldeep Meel and Mate Soos - binary included in util

subprocess32-py3.3-backport - https://github.com/google/python-subprocess32

pycparser - a C99 parser in python for simple static analysis and visitor-pattern style AST handling - https://github.com/eliben/pycparser

cnftools (included in util) - some useful scripts to perform some basic operations on CNFs

  vegard-cnf-utils: some tools that some of the cnftools depend on, should be in util/cnftools - https://github.com/vegard/cnf-utils


Example usage
-------------
```
python2 ApproxFlow.py test.c main
```
