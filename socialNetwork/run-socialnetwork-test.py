#!/usr/bin/env python3
import os
import re
import logging
import argparse
import subprocess

def info(args):
    print("Info: ", args);

def error(args):
    print("Err: ", args);

def log(args):
    print("Log: ", args);

def cmd(cmd):
    log("Exec: "+cmd)
    proc=subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    out,err=proc.communicate()
    if err:
        error("CMD: %s failed\n"%cmd)
        return None
    else:
        out=out.decode().strip()
        if out == "":
            log("Result: suceed\n")
        else:
            log("Result: "+out)
            # log("\n")
        return out

def cleanup(yml):
    cmd("docker-compose -f %s down"%yml)
    cmd("yes|docker image prune")
    cmd("yes|docker volume prune")

if cmd("whoami") != "root":
    error("Need root to run the script.")
    exit(1)

networks={'s': "socfb-Reed98",
          'm': "ego-twitter",
          'l': "soc-twitter-follows-mun"}

workloads={'compose-post': "compose-post.lua http://localhost:8080/wrk2-api/post/compose ",
           'read-home-timeline': "read-home-timeline.lua http://localhost:8080/wrk2-api/home-timeline/read ",
           'read-user-timeline': "read-user-timeline.lua http://localhost:8080/wrk2-api/user-timeline/read ",
           'mixed-workload': "mixed-workload.lua http://localhost:8080"}


parser = argparse.ArgumentParser(description='A script to run socialNetowork test in DeadStarBench', formatter_class=argparse.RawTextHelpFormatter)


parser.add_argument('-r','--rps', help='rps seperated with \",\"', required=False, default="")
parser.add_argument('-o','--output', help='path to store output', required=False, default="")
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
    cleanup(yml)
    exit(0)

script=args['file']
if not os.path.exists(script):
    error("script %s not found"%script)
    exit(1);

suffix=cmd("date +%H-%M-%h-%d")

rpss=args['rps']
if rpss == "":
    QPS=[1000, 2000, 3000, 4000, 5000]
else:
    QPS=rpss.split(",")


cpus='16'
duration=10
threads=cpus
connections=cpus
workload=args['workload']
network=args['network']
output=args['output']
wrk='../wrk2/wrk'



node=2
msize='1g'
if args['output'] == "":
    output="/tmp/dsb-result_node%s_msize%s_cpu%s_threads%s_conn%s_%s_network%s.log"%(node, msize, cpus, threads, connections, workload, networks[network])
log("setup test environment: create docker instances, redis cluster, establish network")
cmd_str="python %s -r %s -N %s -m %s -p %s -d %s -t %s -c %s -i %s -w %s -n %s -o %s -b %s"%(script, \
                                                                                           0, node, msize, cpus, duration, threads, 
                                                                                           connections, yml, workload, network, output, True)
cmd(cmd_str)

rs=open(output, 'w+')
for rps in QPS:
    cmd_str='%s -D exp'%wrk+ \
    ' -t %s'%threads + ' -c %s'%connections + ' -d %s'%duration + \
    ' -L -s ./wrk2/scripts/social-network/%s'%workloads[workload] + " -R %s"%rps
    out=cmd(cmd_str)

    rs.write("\nCONFIG: node:%s msize:%s cpus:%s threads:%s conn:%s workload:%s network:%s RPS:%s\n"%(node, msize, cpus, threads, connections, workload, networks[network], rps))
    rs.write("*************************************************************\n")
    rs.write(out+"\n")
    rs.write("*************************************************************\n")
rs.close()
cleanup(yml)

node=1
msize='2g'
if args['output'] == "":
    output="/tmp/dsb-result_node%s_msize%s_cpu%s_threads%s_conn%s_%s_network%s.log"%(node, msize, cpus, threads, connections, workload, networks[network])
cmd_str="python %s -r %s -N %s -m %s -p %s -d %s -t %s -c %s -i %s -w %s -n %s -o %s -b %s"%(script,
                                                                                           rps, node, msize, cpus, duration, threads, 
                                                                                           connections, yml, workload, network, output, True)
cmd(cmd_str)

rs=open(output, 'w+')
for rps in QPS:
    cmd_str='%s -D exp'%wrk+ \
    ' -t %s'%threads + ' -c %s'%connections + ' -d %s'%duration + \
    ' -L -s ./wrk2/scripts/social-network/%s'%workloads[workload] + " -R %s"%rps
    out=cmd(cmd_str)

    rs.write("\nCONFIG: node:%s msize:%s cpus:%s threads:%s conn:%s workload:%s network:%s RPS:%s\n"%(node, msize, cpus, threads, connections, workload, networks[network], rps))
    rs.write("*************************************************************\n")
    rs.write(out+"\n")
    rs.write("*************************************************************\n")
rs.close()
cleanup(yml)

