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

networks={'s': "socfb-Reed98",
          'm': "ego-twitter",
          'l': "soc-twitter-follows-mun"}

workloads={'compose-post': "compose-post.lua http://localhost:8080/wrk2-api/post/compose ",
           'read-home-timeline': "read-home-timeline.lua http://localhost:8080/wrk2-api/home-timeline/read ",
           'read-user-timeline': "read-user-timeline.lua http://localhost:8080/wrk2-api/user-timeline/read ",
           'mixed-workload': "mixed-workload.lua http://localhost:8080"}


parser = argparse.ArgumentParser(description='A script to run socialNetowork test in DeadStarBench', formatter_class=argparse.RawTextHelpFormatter)


parser.add_argument('-y','--yml', help='yml file for docker compose', required=False, default="./docker-compose-sharding-base.yml")
parser.add_argument('-c','--clean', help='flag to cleanup', required=False, type=bool, default=False)
parser.add_argument('-f','--file', help='python script to run one config test', required=False, default="./run-socialnetwork-one-config.py")
parser.add_argument('-w','--workload', help="valid workload: \n %s" %list(workloads.keys()), required=False, default="compose-post")
parser.add_argument('-n','--network', required=False, default="s",
                    help="network to simulate:\n"+
	"\t s: a small social network Reed98 Facebook Networks\n"+
	"\t m:  a medium social network Ego Twitter\n"+
	"\t l:  a large social network TWITTER-FOLLOWS-MUN")

args = vars(parser.parse_args())

yml=args['yml']
if args['clean']:
    cmd("docker-compose -f %s down"%yml)
    cmd("yes|docker image prune")
    cmd("yes|docker volume prune")
    log.close()
    exit(0)

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
workload=args['workload']
network=args['network']
output="/tmp/dsb-result.log.%s"%suffix


rps=100

node=2
msize='1g'
output="/tmp/dsb-result.log.%s-base"%(suffix)
cmd_str="python %s -r %s -N %s -m %s -p %s -d %s -t %s -c %s -i %s -w %s -n %s -o %s -b %s"%(script,
                                                                                           rps, node, msize, cpus, duration, threads, 
                                                                                           connections, yml, workload, network, output, True)
os.system(cmd_str)

exit(0)

for rps in QPS:
    pass

node=1
msize='2g'
output="/tmp/dsb-result.log.%s-1node"%(suffix)
cmd_str="python %s -r %s -N %s -m %s -p %s -d %s -t %s -c %s -i %s -w %s -n %s -o %s -b %s"%(script,
                                                                                           rps, node, msize, cpus, duration, threads, 
                                                                                           connections, yml, workload, network, output, True)
os.system(cmd_str)
for rps in QPS:
    pass

log.close()
