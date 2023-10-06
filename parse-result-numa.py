import argparse
import json


parser=argparse.ArgumentParser()
parser.add_argument('-n', '--names-list', nargs='+', default=[])

args=vars(parser.parse_args())

logs=args['names_list']

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

for log in logs:
    f=open(log)
    num_latency=0

    while f:
        line = f.readline()
        if line == "":
            break;
        if line.find("CONFIG") != -1:
            config=line
            config_opt=parse_config_line(line)
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



def print_latency_dist(lst):
    for i in lst:
        lat = i.split(":")
        print("  ", lat[0], lat[1])

for config in avg_latencies:
    opt = parse_config_line(config)
    print("CONFIG: ", opt)
    print("Avg latency: ", avg_latencies[config])
    print("Latency dist: ")
    print_latency_dist(latencies[config])
    print("TPS: ", real_tps[config ])
    print("")

exit(0)


if latencies:
    #print(configs)
    #print(latencies)
    rs[config] = latencies

#print(rs)

# print(benches)

kvs={}
RPSs=[]

#print(perc)
titled=False

for k, v in rs.items():
    c = parse_config_line(k)
    if not titled:
        # print(c)
        titled = True
    # print(c)
    name = "rps:%s,workload:%s,numa_config:%s"%(c['RPS'], c['workload'], c['numa-config'])
    if c['RPS'] not in RPSs:
        RPSs.append(c['RPS'])

    print(v)
    kvs[name] = (v, avg_latencies[k], real_rps[k], real_tps[k]);

print(kvs)


for key,value in kvs.items():
    print(key)
    print(value)

exit(0)

print(RPSs)
for b in benches:
    print("*** workload: %s ***\n"%b)
    for rps in RPSs:
        print("RPS: ", rps)
        print("Percentile base 1-node")
        for i in range(len(perc)):
            p = perc[i]
            name = "base_rps-%s-%s"%(rps, b)
            base = kvs[name][0]
            name = "cxl_rps-%s-%s"%(rps, b)
            cxl = kvs[name][0]

            print("%s %s %s"%(p, base[p], cxl[p]))

        base = "base_rps-%s-%s"%(rps, b)
        cxl = "cxl_rps-%s-%s"%(rps, b)
        print("RPS %s %s" %(kvs[base][1], kvs[cxl][1]))
        print("TPS %s %s" %(kvs[base][2], kvs[cxl][2]))

        print("\n")
