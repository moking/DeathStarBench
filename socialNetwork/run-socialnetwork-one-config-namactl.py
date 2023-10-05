#!/usr/bin/env python3
import os
import re
import argparse
import subprocess


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

def generate_yml(yml, new_yml='./docker-compose-run.yml', replicas=2, enable_numactl=False, image_map={}, numactl_prefix=""):
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
           'mixed-workload': "mixed-workload.lua http://localhost:8080"}


parser = argparse.ArgumentParser(description='A script to run socialNetowork test in DeadStarBench', formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('-b','--build', help='flag showing whether to construct the network without testing', required=False, default=False)
parser.add_argument('-r','--rps', help='read/sec', required=False, default=1000)
parser.add_argument('-N','--node', help='number of nodes in cluster', required=False, default=1)
parser.add_argument('-m','--memory', help='docker limit: memory size (e.g., 100m, 1g)', required=False, default='100m')
parser.add_argument('-p','--cpus', help='docker limit: number of cpu (e.g., 100m, 1g)', required=False, default='1')
parser.add_argument('-d','--duration', help='seconds to run', required=False, default=30)
parser.add_argument('-t','--threads', help='number of threads', required=False, default=16)
parser.add_argument('-c','--connections', help='number of connections', required=False, default=16)
parser.add_argument('-i','--input', help='path to docker compose yml file', required=False, default= "./docker-compose-sharding.yml")
parser.add_argument('-w','--workload', help="valid workload: \n %s" %list(workloads.keys()), required=False, default="compose-post")
parser.add_argument('-n','--network', required=False, default="socfb-Reed98",
                    help="network to simulate:\n"+
	"\t s: a small social network Reed98 Facebook Networks\n"+
	"\t m:  a medium social network Ego Twitter\n"+
	"\t l:  a large social network TWITTER-FOLLOWS-MUN")
parser.add_argument('-o','--output', help='path to output file', required=False, default='/tmp/data.txt')

args = vars(parser.parse_args())

if not validate_arguments(args):
    exit(1)

output=args['output']
yml=args['input']
rps=args['rps']
duration=args['duration']
num_threads=args['threads']
num_con=args['connections']
build_only=args['build']
num_nodes=args['node']
msize=args['memory']
num_cpus=args['cpus']

image_map = {}
image2numactl_prefix={}
image_suffix="-numa-membind-2"

for node in [0, 1, 2]:
    image="-numa-membind-%d"%node
    prefix="numactl --cpunodebind=0 --membind=%d"%node
    image2numactl_prefix[image] = prefix

for nodes in ["0,1", "0,2"]:
    prefix="numactl --cpunodebind=0 --interleave=%s"%nodes
    image="-numa-interleave-node-%s"%("-".join(nodes.split(",")))
    image2numactl_prefix[image] = prefix
print(image2numactl_prefix)

numactl_prefix = image2numactl_prefix[image_suffix]

yml, conf = generate_yml(yml, replicas=num_nodes, image_map={}, numactl_prefix = numactl_prefix)

# cmd("docker-compose -f %s down"%yml)
# cmd("docker-compose -f %s up -d"%yml) 

ps_file="/tmp/ps"
cmd("docker ps > ps_file")

file = open(ps_file, 'r')
lines=file.readlines()

def docker_exec(ins, cmd_str):
    cmd_str="docker exec -u root -it %s bash -c \"%s\"  "%(ins, cmd_str)
    cmd(cmd_str)

def docker_copy_out(ins, src, dst):
    cmd_str = "docker cp %s:%s %s"%(ins, src, dst)
    cmd(cmd_str)

def docker_copy_in(ins, src, dst):
    cmd_str = "docker cp %s %s:%s"%(src, ins, dst)
    cmd(cmd_str)

for line in lines:
    if "CONTAINER ID" not in line:
        cols=line.split()
        image=cols[1]
        ins=cols[-1]

        new_image_name=image
        if "jaeger" not in ins:
            new_image_name = new_image_name.split("/")[-1]
            new_image_name = new_image_name.split(":")[0]
            new_image_name = new_image_name+image_suffix

            print("Install numactl tools")
            cmd_str="apt-get update 2>&1 1>&/dev/null; apt-get install -y numactl procps vim 2>&1 1>&/dev/null"
            docker_exec(ins, cmd_str)

            cmd_str="numactl -H"
            docker_exec(ins, cmd_str)


            exit(1)

        image_map[image] = new_image_name
        

print(image_map)

exit(0)
print("Register users and construct social graph: %s\n"%network)
cmd("python3 scripts/init_social_graph.py --graph=%s"%network)

cmd_str='../wrk2/wrk -D exp -t %s'%num_threads + ' -c %s'%num_con + ' -d %s'%duration +' -L -s ./wrk2/scripts/social-network/%s'%workload + " -R %s"%rps
if not build_only:
    print("Run workload: %s\n"%cmd_str)
    out=cmd(cmd_str)

    print(cmd_str)
    print("View Jaeger traces by accessing http://localhost:16686\n")

    if os.path.exists(output):
        print("mv %s %s"%(output, output+".old"))
        cmd("mv %s %s"%(output, output+".old"))
    f=open(output, "w+")
    f.write(conf)
    f.write("\n*------------OUTPUT: Start-------------*\n")
    f.write(out)
    f.write("\n*------------OUTPUT: END---------------*\n")

    cmd("docker-compose -f %s down"%yml)
    cmd("yes|docker image prune")
    cmd("yes|docker volume prune")
    f.close()

else:
    print("\nRun the workload as below:\n")
    print(cmd_str)

#os.system("mv %s %s"%(output, output+"."+suffix))
print("\nCheck results here: %s"%(output))
os.system("mv %s /tmp/"%yml)
