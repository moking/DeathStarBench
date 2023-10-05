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

parser.add_argument('-m','--mode', help='numa mode to test: m->membind, i->interleave', required=True, default="m")
parser.add_argument('-M','--memnode', help='numa node(s) to use for memory allocation', required=True, default="0")

parser.add_argument('-N','--node', help='number of nodes in cluster', required=False, default=1)
parser.add_argument('-d','--duration', help='seconds to run', required=False, default=30)
parser.add_argument('-t','--threads', help='number of threads', required=False, default=16)
parser.add_argument('-c','--connections', help='number of connections', required=False, default=16)

parser.add_argument('-r','--rps', help='rps seperated with \",\"', required=False, default="")
parser.add_argument('-o','--output', help='path to store output', required=False, default="")
parser.add_argument('-y','--yml', help='yml file for docker compose', required=False, default="./docker-compose-sharding.yml")
parser.add_argument('-C','--clean', help='flag to cleanup', required=False, type=bool, default=False)
parser.add_argument('-f','--file', help='python script to run one config test', required=False, default="./run-socialnetwork-one-config-numactl.py")
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


def gen_image_suffix(mode, node_list):
    if mode != "m" and mode != "i":
        print("numa mode %s not supported"%mode)
        exit(1)
    if mode == "m":
        if not node_list.isdigit():    
            print("membind can be applied to only one numa node in the test")
            eixt(1)
        return "-numa-membind-%s"%node_list
    else:
        cols=node_list.split(",")
        for col in cols:
            if not col.isdigit():
                print("Invalid interleave node list: %s"%node_list)
                eixt(1)
        return "-numa-interleave-node-%s"%("-".join(cols))


numa_mode=args['mode']
node_list=args['memnode']
duration=args['duration']
threads=args['threads']
connections=args['connections']
workload=args['workload']
network=args['network']
output=args['output']
wrk='../wrk2/wrk'

node=args['node']
msize=args['msize']

image_suffix=gen_image_suffix(numa_mode, node_list)

if args['output'] == "":
    outdir="/home/fan/cxl/DeathStarBench/logs/"
    if not os.path.exists(outdir):
        cmd("mkdir -p %s"%outdir)

    output="%s/dsb-result_node%s_threads%s_conn%s_%s_network_%s.log"%(outdir, node, threads, connections, workload, networks[network])
log("setup test environment: create docker instances, redis cluster, establish network")
cmd_str="python %s -r %s -N %s -d %s -t %s -c %s -i %s -w %s -n %s -o %s -b %s"%(script, \
                                                                                           0, node, duration, threads, 
                                                                                           connections, yml, workload, network, output, True)
cmd(cmd_str)

rs=open(output, 'w+')
for rps in QPS:
    cmd_str='%s -D exp'%wrk+ \
    ' -t %s'%threads + ' -c %s'%connections + ' -d %s'%duration + \
    ' -L -s ./wrk2/scripts/social-network/%s'%workloads[workload] + " -R %s"%rps
    out=cmd(cmd_str)

    rs.write("\nCONFIG: node:%s msize:%s threads:%s conn:%s workload:%s network:%s RPS:%s\n"%(node, msize, threads, connections, workload, networks[network], rps))
    rs.write("*************************************************************\n")
    rs.write(out+"\n")
    rs.write("*************************************************************\n")
rs.close()
cleanup(yml)

exit(0)
if False:
    if args['output'] == "":
        output="/tmp/dsb-result_node%s_msize%s_threads%s_conn%s_%s_network%s.log"%(node, msize, threads, connections, workload, networks[network])
    cmd_str="python %s -r %s -N %s -m %s -p %s -d %s -t %s -c %s -i %s -w %s -n %s -o %s -b %s"%(script,
                                                                                               rps, node, msize, duration, threads, 
                                                                                               connections, yml, workload, network, output, True)
    cmd(cmd_str)

    rs=open(output, 'w+')
    for rps in QPS:
        cmd_str='%s -D exp'%wrk+ \
        ' -t %s'%threads + ' -c %s'%connections + ' -d %s'%duration + \
        ' -L -s ./wrk2/scripts/social-network/%s'%workloads[workload] + " -R %s"%rps
        out=cmd(cmd_str)

        rs.write("\nCONFIG: node:%s msize:%s threads:%s conn:%s workload:%s network:%s RPS:%s\n"%(node, msize, threads, connections, workload, networks[network], rps))
        rs.write("*************************************************************\n")
        rs.write(out+"\n")
        rs.write("*************************************************************\n")
    rs.close()
    cleanup(yml)

