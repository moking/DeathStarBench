import argparse
import json
import os.path


parser=argparse.ArgumentParser()
parser.add_argument('-L', '--log', required=True) 

args=vars(parser.parse_args())
log=args['log']

f = open(log, 'r')
line = f.readline()

while line != "":
    if "Running args" in line:
        print(line)
    if "numactl -H" in line:
        cnt=0
        for cnt in range(10):
            line = f.readline()
            if "MB" in line:
                print(line)

        
    line = f.readline()





