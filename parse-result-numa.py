import argparse
import json
import os.path


parser=argparse.ArgumentParser()
parser.add_argument('-n', '--names-list', nargs='+', default=[])
parser.add_argument('-d', '--dire', default="") 
parser.add_argument('-D','--dist', help='flag to show latency distribution', action='store_true')
parser.add_argument('-P','--p99', help='flag to show 99% latency', action='store_true')
parser.set_defaults(feature=False)

args=vars(parser.parse_args())

logs=args['names_list']
dire = args['dire']
print_lat_dist=args['dist']
print_lat99=args['p99']

if dire != "":
    if not os.path.exists(dire):
        print("Directory: %s not exist"%dire);
        exit(1)
    else:
        print("Parsing files under %s\n"%dire)
        ents=os.listdir(dire)
        for ent in ents:
            ent="%s/%s"%(dire, ent)
            if os.path.isfile(ent):
                logs.append(ent)
        # print(logs)
else:
    print("Parsing logs: ", logs)

def parse_config_line(line):
    rs={}
    if line.find("CONFIG") == -1:
        print("*** NO config found ****")
        return 

    config=line.split()[1:]
    # print(config)
    for c in config:
        p = c.split(":")
        key=p[0]
        value=p[1]
        rs[key] = value

    return rs

rs={}
config=""
configs={}
latencies={}
avg_latencies={}
perc=[]
real_rps={}
real_tps={}
benches=[]

threads=[]
connections=[]
workloads=[]
rpss=[]
numa_config=[]
replicas=[]
networks=[]

for log in logs:
    f=open(log)
    num_latency=0

    while f:
        line = f.readline()
        if line == "":
            break;
        if line.find("CONFIG") != -1:
            config=line
            config_opt=config.replace("CONFIG:", "")
            cols = config_opt.split()

            r = cols[0].split(":")[1]
            if r not in replicas:
                replicas.append(r)

            r = cols[1].split(":")[1]
            if r not in threads:
                threads.append(r)

            r = cols[2].split(":")[1]
            if r not in connections:
                connections.append(r)


            r = cols[3].split(":")[1]
            if r not in workloads:
                workloads.append(r)

            r = cols[4].split(":")[1]
            if r not in networks:
                networks.append(r)

            r = cols[5].split(":")[1]
            if r not in rpss:
                rpss.append(r)

            r = cols[6].split(":")[1]
            if r not in numa_config:
                numa_config.append(r)
        elif line.find("Latency Dist") != -1:
            num_latency=8
            per=[]
            for i in range(num_latency):
                line = f.readline()
                per.append(":".join(line.split()))
            latencies[config] = per
        elif line.find("Requests/sec") != -1:
            real_rps[config] = line.split(":")[1].strip()
        elif line.find("Transfer/sec") != -1:
            real_tps[config] = line.split(":")[1].strip()
        elif line.find("Latency") != -1:
            avg_latencies[config] = line.split()[1].strip()


# print(workloads)
# print(rpss)
# print(numa_config)
numa_config.sort()

def print_latency_dist(lst):
    for i in lst:
        lat = i.split(":")
        print("  ", lat[0], lat[1])

def print_latency99(lst):
        lat = lst[3].split(":")
        print("  ", lat[0], lat[1])

def latency99(lst):
    lat = lst[3].split(":")
    return lat[1]

for replica in replicas:
    for thread in threads:
        for conn in connections:
            for network in networks:
                print("Network:%s"%network)
                for workload in workloads:
                    for rps in rpss:
                        for numa in numa_config:
                            config="CONFIG: node:%s threads:%s conn:%s workload:%s network:%s RPS:%s numa-config:%s\n"%(replica, thread, conn, workload, network, rps, numa)
                            # print(config)
                            # print(real_tps[config])
                            if (numa == numa_config[0]):
                                print("workload:%s,request-rate:%s"%(workload,rps))
                                print("NUMA-policy\tAvg-lat\tp99-lat\tTPS\tRPS")

                            numa = numa.replace("numa-membind-", "membind:")
                            numa = numa.replace("numa-interleave-node-", "interleave:")
                            numa = numa.replace("-", ",")
                            if print_lat99:
                                print(numa, avg_latencies[config],latency99(latencies[config]), real_tps[config], real_rps[config])
                            else:
                                print(numa, avg_latencies[config],"---", real_tps[config],  real_rps[config])

                            if print_lat_dist:
                                print_latency_dist(latencies[config])
                            if numa == numa_config[-1]:
                                print("\n")

exit(1)

for config in avg_latencies:
    opt = parse_config_line(config)
    print("CONFIG: ", config)
    print("Avg latency: ", avg_latencies[config])
    # print("Latency dist: ")
    # print_latency_dist(latencies[config])
    print("TPS: ", real_tps[config ])
    print("")

exit(0)

