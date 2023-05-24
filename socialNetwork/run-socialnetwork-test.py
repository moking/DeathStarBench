#!/usr/bin/env python3
import os
import re
import logging
import argparse
import subprocess

log=open("/tmp/run-info.log", "a+")
def cmd(cmd):
    proc=subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    out,err=proc.communicate()
    if err:
        log.write("CMD: %s failed\n"%cmd)
        return None
    else:
        out=out.decode().strip()
        log.write("CMD: "+cmd+"\n")
        if out == "":
            log.write("Result: suceed\n")
        else:
            log.write("Result: "+out)
            log.write("\n")
        return out

if cmd("whoami") != "root":
    print("Need root to run the script.")
    log.close()
    exit(1)

parser = argparse.ArgumentParser(description='A script to run socialNetowork test in DeadStarBench', formatter_class=argparse.RawTextHelpFormatter)


parser.add_argument('-f','--file', help='python script to run one config test', required=False, default="./run-socialnetwork-one-config.py")

args = vars(parser.parse_args())

script=args['file']
if not os.path.exists(script):
    print("script %s not found"%script)
    exit(1);

suffix=cmd("date +%H-%M-%h-%d")

QPS=[1000, 2000, 3000, 4000, 5000]

cpus='16'
duration=60
threads=cpus
connections=cpus
yml="./docker-compose-sharding-base.yml"
workload='compose-post'
network='s'
output="/tmp/dsb-result.log.%s"%suffix

for rps in QPS:
    node=2
    msize='1g'
    output="/tmp/dsb-result.log.%s-base-rps%s"%(suffix, rps)
    cmd_str="python %s -r %s -N %s -m %s -p %s -d %s -t %s -c %s -i %s -w %s -n %s -o %s"%(script,
                                                                                           rps, node, msize, cpus, duration, threads, 
                                                                                           connections, yml, workload, network, output)
    os.system(cmd_str)

    node=1
    msize='2g'
    output="/tmp/dsb-result.log.%s-1node-rps%s"%(suffix, rps)
    cmd_str="python %s -r %s -N %s -m %s -p %s -d %s -t %s -c %s -i %s -w %s -n %s -o %s"%(script,
                                                                                           rps, node, msize, cpus, duration, threads, 
                                                                                           connections, yml, workload, network, output)
    os.system(cmd_str)
log.close()
