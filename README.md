# approxflow
*The following is an adaption of https://github.com/approxflow/approxflow to support Java programs*

Approximate QIF for ~~C~~ Java programs

ApproxFlow.py: Script to measure (approx) info flow

usage: ApproxFlow.py class classpath
     class: main class that is placed in the default package
 classpath: classpath with a main class that has a static ___val variable for output
 use env variable declaration CNF_ONLY=1 to create only CNF file



=================================================


Requires
--------

cbmc - The C Bounded Model Checker (including jbmc)

scalmc (cryptominisat-based projected-cabable approximate model counter) from Kuldeep Meel and Mate Soos - binary included in util

subprocess32-py3.3-backport - https://github.com/google/python-subprocess32

cnftools (included in util) - some useful scripts to perform some basic operations on CNFs

vegard-cnf-utils: some tools that some of the cnftools depend on, should be in util/cnftools - https://github.com/vegard/cnf-utils


Example usage
-------------
```
python2 ApproxFlow.py Simple test
```