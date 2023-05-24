#!/usr/bin/env python3
import os
import re
import logging
import argparse
import subprocess


log=open("/tmp/bench-run.log", "a+")

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

def generate_yml(yml, new_yml='./docker-compose-run.yml', msize='100m', cpus='1', replicas=2):
    if not (os.path.exists(yml)):
        print(yml+" not found.\n ")
        return None

    file = open(yml, 'r')
    file_w = open(new_yml, 'w')

    lines=file.readlines()
    for line in lines:
        i = line.find("replicas")
        if i == -1:
            j = line.find("memory")
            if j == -1:
                k = line.find("cpus")
                if k == -1:
                    file_w.write(line)
                else:
                    file_w.write(line[:k]+"cpus: %s\n"%cpus)
            else:
                file_w.write(line[:j]+"memory: %s\n"%msize)
        else:
            file_w.write(line[:i]+"replicas: %s\n"%replicas)

    file_w.close()
    file.close()
    
    conf="Docker config:  %s memory %s cpus and %s nodes"%(msize, cpus, replicas)
    print(conf)

    return new_yml, conf

suffix=cmd("date +%H-%M-%h-%d")

if cmd("whoami") != "root":
    print("Need root to run the script.")
    log.close()
    exit(1)

script_dir="./wrk2/scripts/social-network/"
workload=""
network=""

if not os.path.exists(script_dir):
    print("Error: please copy the script to the socialNetwork directory in DeathStarBench")
    exit(1)

def validate_arguments(args):
    global workload
    global network
    print(args)
    if not os.path.isfile(args['input']):
        print(args['input']+" does not exist or is not a file\n");
        return False;
    if args["network"] not in networks:
        print("network should be s/m/l for small/middle/large size network\n")
        return False;
    else:
        network=networks[args['network']]
    if args["workload"] not in workloads:
        print("workload not support. Supported workload: \n ", workloads)
        return False;
    else:
        workload=workloads[args['workload']]

    return True


networks={'s': "socfb-Reed98",
          'm': "ego-twitter",
          'l': "soc-twitter-follows-mun"}

workloads={'compose-post': "compose-post.lua http://localhost:8080/wrk2-api/post/compose ",
           'read-home-timeline': "read-home-timeline.lua http://localhost:8080/wrk2-api/home-timeline/read ",
           'read-user-timeline': "read-user-timeline.lua http://localhost:8080/wrk2-api/user-timeline/read ",
           'mixed-workload': "mixed-workload.lua"}


parser = argparse.ArgumentParser(description='A script to run socialNetowork test in DeadStarBench', formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('-r','--rps', help='read/sec', required=False, default=1000)
parser.add_argument('-N','--node', help='read/sec', required=False, default=1)
parser.add_argument('-m','--memory', help='docker limit: memory size (e.g., 100m, 1g)', required=False, default='100m')
parser.add_argument('-p','--cpus', help='docker limit: number of cpu (e.g., 100m, 1g)', required=False, default='1')
parser.add_argument('-d','--duration', help='seconds to run', required=False, default=30)
parser.add_argument('-t','--threads', help='number of threads', required=False, default=16)
parser.add_argument('-c','--connections', help='number of connections', required=False, default=16)
parser.add_argument('-i','--input', help='path to docker compose yml file', required=False, default= "./docker-compose.yml")
parser.add_argument('-w','--workload', help="valid workload: \n %s" %list(workloads.keys()), required=False, default="compose-post")
parser.add_argument('-n','--network', required=False, default="socfb-Reed98",
                    help="network to simulate:\n"+
	"\t s: a small social network Reed98 Facebook Networks\n"+
	"\t m:  a medium social network Ego Twitter\n"+
	"\t l:  a large social network TWITTER-FOLLOWS-MUN")
parser.add_argument('-o','--output', help='path to output file', required=False, default='/tmp/data.txt')

args = vars(parser.parse_args())
output=args['output']
yml=args['input']
rps=args['rps']
duration=args['duration']
num_threads=args['threads']
num_con=args['connections']

if not validate_arguments(args):
    exit(1)

if os.path.exists(output):
    print("mv %s %s"%(output, output+".old"))
    cmd("mv %s %s"%(output, output+".old"))

yml, conf = generate_yml(yml, msize=args['memory'], cpus=args['cpus'], replicas=args['node'])

f=open(args['output'], "w+")

cmd("docker-compose -f %s down"%yml)
cmd("docker-compose -f %s up -d"%yml) 

print("Register users and construct social graph: %s\n"%network)
cmd("python3 scripts/init_social_graph.py --graph=%s"%network)

cmd_str='../wrk2/wrk -D exp -t %s'%num_threads + ' -c %s'%num_con + ' -d %s'%duration +' -L -s ./wrk2/scripts/social-network/%s'%workload + " -R %s"%rps
print("Run workload: %s\n"%cmd_str)
out=cmd(cmd_str)

print(cmd_str)
print("View Jaeger traces by accessing http://localhost:16686\n")
f.write(conf)
f.write("\n*------------OUTPUT: Start-------------*\n")
f.write(out)
f.write("\n*------------OUTPUT: END---------------*\n")

cmd("docker-compose -f %s down"%yml)
cmd("yes|docker image prune")
cmd("yes|docker volume prune")

f.close()
log.close()

#os.system("mv %s %s"%(output, output+"."+suffix))
print("\nCheck results here: %s"%(output))
os.system("mv %s /tmp/"%yml)
