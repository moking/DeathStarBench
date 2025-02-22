#!/usr/bin/env python3
import os
import re
import argparse
import subprocess
import os.path
import time

def basename(s):
    return os.path.basename(s)

def dirname(s):
    return os.path.dirname(s)

def tee(s, file):
    print(s)
    out = open(file, 'a+')
    out.write(s)
    out.close()

def cmd(cmd):
    proc=subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    out,err=proc.communicate()
    if err:
        print("CMD: %s failed\n"%cmd)
        return None
    else:
        out=out.decode().strip()
        print("CMD: "+cmd+"\n")
        if out == "":
            print("Result: suceed\n")
        else:
            print("Result: "+out)
            print("\n")
        return out

def cmd_tee(cmd_str, file="/dev/null"):
    out = cmd(cmd_str)
    if out:
        tee(out, file)

def generate_yml(yml, new_yml='./docker-compose-run.yml', replicas=2, enable_numactl=False, image_map={}, numactl_prefix="", db_numactl_only=True):
    if not (os.path.exists(yml)):
        print(yml+" not found.\n ")
        return None

    file = open(yml, 'r')
    file_w = open(new_yml, 'w')

    lines=file.readlines()
    for line in lines:
        i = line.find("image:")
        if i != -1: 
            image_name = line.split()[-1]
            new_image_name = image_map.get(image_name)
            if new_image_name:
                line=line[:i] + "image: " + new_image_name + "\n"
            file_w.write(line)
            if not enable_numactl:
                line=line[:i] + "privileged: true\n"
                file_w.write(line)
        else:
            i = line.find("replicas")
            if i != -1:
                file_w.write(line[:i]+"replicas: %s\n"%replicas)
            else:
                if not db_numactl_only:
                    if enable_numactl:
                        i = line.find("entrypoint:")
                        ep_len = len("entrypoint:")
                        if i != -1:
                            line = line[:i+ep_len] + "  " + numactl_prefix + line[i+ep_len:]
                        
                file_w.write(line)
                
    file_w.close()
    file.close()
    
    conf="Docker config:  %s nodes, numactl %s"%(replicas, enable_numactl)
    print(conf)

    return new_yml, conf

suffix=cmd("date +%H-%M-%h-%d")

if cmd("whoami") != "root":
    print("Need root to run the script.")
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
    # print(args)
    if not os.path.isfile(args['input']):
        print(args['input']+" does not exist or is not a file\n");
        return False;
    if args["network"] not in networks:
        print("network should be s/f/m/l for small/facebook/middle/large size network\n")
        return False;
    else:
        network=networks[args['network']]
    if not args["build"] and args["workload"] not in workloads:
        print("workload not support. Supported workload: \n ", workloads)
        return False;
    else:
        if args["build"]:
            workload="build"
        else:
            workload=workloads[args['workload']]

    return True


networks={'s': "socfb-Reed98",
          'f': "facebook",
          'm': "ego-twitter",
          'l': "soc-twitter-follows-mun"}

workloads={'compose-post': "compose-post.lua http://localhost:8080/wrk2-api/post/compose ",
           'read-home-timeline': "read-home-timeline.lua http://localhost:8080/wrk2-api/home-timeline/read ",
           'read-user-timeline': "read-user-timeline.lua http://localhost:8080/wrk2-api/user-timeline/read ",
           'mixed-workload': "mixed-workload.lua http://localhost:8080"}


parser = argparse.ArgumentParser(description='A script to run socialNetowork test in DeadStarBench', formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('-b','--build', help='flag showing whether to construct the network without testing', required=False, default=False)
parser.add_argument('-r','--rps', help='read/sec', required=False, default=1000)
parser.add_argument('-N','--node', help='number of nodes in cluster', required=False, default=1)
parser.add_argument('-p','--cpus', help='docker limit: number of cpu (e.g., 100m, 1g)', required=False, default='1')
parser.add_argument('-d','--duration', help='seconds to run', required=False, default=30)
parser.add_argument('-t','--threads', help='number of threads', required=False, default=16)
parser.add_argument('-c','--connections', help='number of connections', required=False, default=16)
parser.add_argument('-i','--input', help='path to docker compose yml file', required=False, default= "./docker-compose-sharding.yml")
parser.add_argument('-w','--workload', help="valid workload: \n %s" %list(workloads.keys()), required=False, default="compose-post")
parser.add_argument('-n','--network', required=False, default="socfb-Reed98",
                    help="network to simulate:\n"+
	"\t s: a small social network Reed98 Facebook Networks\n"+
	"\t f:  a larger social network facebook\n"+
	"\t m:  a medium social network Ego Twitter\n"+
	"\t l:  a large social network TWITTER-FOLLOWS-MUN")
parser.add_argument('-o','--output', help='path to output file', required=False, default='/tmp/data.txt')
# for numa configuration
parser.add_argument('-m','--mode', help='numa mode to test: m->membind, i->interleave', required=True, default="m")
parser.add_argument('-M','--memnode', help='numa node(s) to use for memory allocation', required=True, default="0")

def gen_image_suffix(mode, node_list):
    if mode != "m" and mode != "i":
        print("numa mode %s not supported"%mode)
        exit(1)
    if mode == "m":
        if not node_list.isdigit():    
            print("membind can be applied to only one numa node in the test")
            exit(1)
        return "-numa-membind-%s"%node_list
    else:
        cols=node_list.split(",")
        for col in cols:
            if not col.isdigit():
                print("Invalid interleave node list: %s"%node_list)
                exit(1)
        return "-numa-interleave-node-%s"%("-".join(cols))


args = vars(parser.parse_args())
if not validate_arguments(args):
    exit(1)

def prepare_system_setup():
    path="/sys/kernel/mm/transparent_hugepage/enabled"
    cmd_str="cat %s"%path
    cmd(cmd_str)
    cmd_str="echo never > %s"%path
    cmd(cmd_str)
    cmd_str="cat %s"%path
    cmd(cmd_str)

    cmd_str="apt-get install -y cpufrequtils"
    cmd(cmd_str)
    cmd_str="cpufreq-set -g performance"
    cmd(cmd_str)
    cmd_str="cpufreq-info -p"
    cmd(cmd_str)

    path="/proc/sys/kernel/numa_balancing"
    cmd_str="echo 0 > %s"%path
    cmd(cmd_str)
    cmd_str="cat %s"%path
    cmd(cmd_str)

prepare_system_setup()

output=args['output']
yml=args['input']
rps=args['rps']
duration=args['duration']
num_threads=args['threads']
num_con=args['connections']
build_only=args['build']
num_nodes=args['node']
num_cpus=args['cpus']

image_map = {}
image2numactl_prefix={}

numa_mode=args['mode']
node_list=args['memnode']

image_suffix=gen_image_suffix(numa_mode, node_list)

for node in [0, 1, 2]:
    image="-numa-membind-%d"%node
    prefix="numactl --cpunodebind=0 --membind=%d"%node
    image2numactl_prefix[image] = prefix

for nodes in ["0,1", "0,2"]:
    prefix="numactl --cpunodebind=0 --interleave=%s"%nodes
    image="-numa-interleave-node-%s"%("-".join(nodes.split(",")))
    image2numactl_prefix[image] = prefix

# print(image2numactl_prefix)
if image_suffix not in image2numactl_prefix:
    print("image suffix: %s not valid", image_suffix)
    exit(1)

print("Running args:", args)
print("\n")

numactl_prefix = image2numactl_prefix[image_suffix]

yml, conf = generate_yml(yml, replicas=num_nodes, image_map={}, numactl_prefix = numactl_prefix)

cmd("docker-compose -f %s down"%yml)

cmd("docker-compose -f %s up -d"%yml) 

ps_file="/tmp/ps"
cmd("docker ps > %s"%ps_file)

file = open(ps_file, 'r')
lines=file.readlines()

def docker_exec(ins, cmd_str):
    cmd_str="docker exec -u root -it %s bash -c \"%s\"  "%(ins, cmd_str)
    return cmd(cmd_str)

def docker_copy_out(ins, src, dst):
    cmd_str = "docker cp %s:%s %s"%(ins, src, dst)
    return cmd(cmd_str)

def docker_copy_in(src, ins, dst):
    cmd_str = "docker cp %s %s:%s"%(src, ins, dst)
    return cmd(cmd_str)

for line in lines:
    if "CONTAINER ID" not in line:
        cols=line.split()
        image=cols[1]
        ins=cols[-1]

        if image in image_map:
            continue

        new_image_name=image
        if "jaeger" not in ins:
            new_image_name = new_image_name.split("/")[-1]
            new_image_name = new_image_name.split(":")[0]
            new_image_name = new_image_name+image_suffix

            print("Install numactl tools on docker image: %s"%new_image_name)
            cmd_str="apt-get update 2>&1 1>&/dev/null; apt-get install -y numactl procps 2>&1 1>&/dev/null"
            docker_exec(ins, cmd_str)

            # cmd_str="numactl -H"
            # docker_exec(ins, cmd_str)

            tmp="/tmp/"
            if "redis" in image or "memcached" in image or "mongo" in image:
                if "redis" in image:
                    script="/usr/local/bin/docker-entrypoint.sh"
                    key="set -- redis-server"
                    target_key="set -- %s redis-server"%numactl_prefix

                if "memcached" in image:
                    script="/usr/local/bin/docker-entrypoint.sh"
                    key="set -- memcached"
                    target_key="set -- %s memcached"%numactl_prefix
                if "mongo" in image:
                    script="/usr/local/bin/docker-entrypoint.sh"
                    key="numactl --interleave=all"
                    target_key="%s"%numactl_prefix

                dst=tmp+basename(script)

                cmd_str="if test -f %s.orig; then echo 1; else echo 0; fi"%script
                ret = docker_exec(ins, cmd_str)
                if ret == "0":
                    print("orig file not exist, creating")
                    cmd_str="cp %s %s.orig"%(script, script)
                    docker_exec(ins, cmd_str)
                else:
                    print("orig file exist, restoring")
                    cmd_str="cp %s.orig %s"%(script, script)
                    docker_exec(ins, cmd_str)

                docker_copy_out(ins, script, dst)
                # cmd("cat %s"%dst)
                new_src=dst+".new"


                f1=open(dst, 'r')
                f2=open(new_src, 'w')

                lines=f1.readlines()
                for line in lines:
                    line = line.replace(key, target_key)
                    f2.write(line)
                f1.close()
                f2.close()

                cmd("chmod 755 %s"%new_src)

                docker_copy_in(new_src, ins, script)
                docker_exec(ins, "ls -lh %s"%script)
                docker_exec(ins, "cat %s | grep numa"%script)

            # all images need to have numactl installed except jaeger
            cmd_str="docker image rm -f %s"%(new_image_name)
            cmd(cmd_str)
            cmd_str="docker commit %s %s"%(ins, new_image_name)
            cmd(cmd_str)

        image_map[image] = new_image_name
        

cmd("docker-compose -f %s down"%yml)
cmd("yes|docker image prune")
cmd("yes|docker volume prune")

print("******************************")
print("Create yml file with new image")
new_yml=dirname(yml)+"/numactl-"+basename(yml)
yml, conf = generate_yml(yml, new_yml = new_yml, replicas=num_nodes, image_map= image_map, numactl_prefix = numactl_prefix, enable_numactl=True)

cmd("docker-compose -f %s up -d"%yml) 
print("******************************")


numa_file="/tmp/numactl.txt"
tee(output, numa_file)
tee("MODE: %s: Before construct socialNetwork\n"%image_suffix[1:], numa_file)
cmd_tee("numactl -H", numa_file)

print("Register users and construct social graph: %s\n"%network)
cmd("python3 scripts/init_social_graph.py --graph=%s"%network)

for ins in ["socialnetwork_social-graph-redis_1", "socialnetwork_home-timeline-redis_1", "socialnetwork_user-timeline-redis_1"]:
    cmd_str="docker exec -u root -it %s redis-cli cluster info"%ins
    cmd(cmd_str)

cmd_str='../wrk2/wrk -D exp -t %s'%num_threads + ' -c %s'%num_con + ' -d %s'%duration +' -L -s ./wrk2/scripts/social-network/%s'%workload + " -R %s"%rps
if not build_only:
    print("Run workload: %s\n"%cmd_str)
    out=cmd(cmd_str)

    # print(cmd_str)
    # print("View Jaeger traces by accessing http://localhost:16686\n")

    if os.path.exists(output):
        print("mv %s %s"%(output, output+".old"))
        cmd("mv %s %s"%(output, output+".old"))
    f=open(output, "w+")
    f.write(conf)
    f.write("\n*------------OUTPUT: Start-------------*\n")
    f.write(out)
    f.write("\n*------------OUTPUT: END---------------*\n")

    tee("MODE: %s, rps: %s, workload: %s: after running test\n"%(image_suffix[1:], rps, workload), "/tmp/numactl.txt")
    cmd_tee("numactl -H", numa_file)

    cmd_tee("docker-compose -f %s down"%yml)
    cmd_tee("yes|docker image prune")
    cmd_tee("yes|docker volume prune")
    f.close()
    print("\nCheck results here: %s"%(output))

else:
    print("\nRun the workload as below:\n")
    print(cmd_str)

cmd("mv %s /tmp/"%yml)
