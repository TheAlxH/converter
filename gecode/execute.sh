#/bin/bash

#find /mnt/scratch/ostrowsk/MINIZINK/combinedmznc2015_probs/ -name "*.mzn" -exec sh -c 'mzn2fzn --output-to-stdout -G clingcon {} > {}.fzn' \;

find /mnt/scratch/ostrowsk/MINIZINK/combinedmznc2015_probs/ -name "*.fzn" -exec sh -c './check.py {}' \;
