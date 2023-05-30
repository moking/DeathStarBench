import argparse
import json


parser=argparse.ArgumentParser()
parser.add_argument('-n', '--names-list', nargs='+', default=[])

args=vars(parser.parse_args())

logs=args['names_list']

def parse_config_line(line):
    rs={}
    if line.find("CONFIG") == -1:
        print("*** NO config found ****")
        return 

    config=line.split()[1:]
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
perc=[]
real_rps={}
real_tps={}

for log in logs:
    f=open(log)
    lines=f.readlines()
    num_latency=0


    for line in lines:
        if line.find("CONFIG") != -1:
            if latencies:
                #print(configs)
                #print(latencies)
                rs[config] = latencies
                #rs[str(configs)] = latencies
                configs={}
                latencies={}

            config=line
            configs=parse_config_line(line)
        elif line.find("Latency Dist") != -1:
            num_latency=8
        elif num_latency > 0:
            latency=line.split()
            num_latency = num_latency-1
            latencies[latency[0]] = latency[1]
            if latency[0] not in perc:
                perc.append(latency[0])
        elif line.find("Requests/sec") != -1:
            real_rps[config] = line.split(":")[1].strip()
        elif line.find("Transfer/sec") != -1:
            real_tps[config] = line.split(":")[1].strip()



if latencies:
    #print(configs)
    #print(latencies)
    rs[config] = latencies

#print(rs)


kvs={}
RPSs=[]

#print(perc)

for k, v in rs.items():
    c = parse_config_line(k)
    #print(c['node'])
    #print(c['msize'])
    #print(c)
    if c['node'] == "1":
        name = "cxl_rps-%s"%c['RPS']
        if c['RPS'] not in RPSs:
            RPSs.append(c['RPS'])

    elif c['node'] == "2":
        name = "base_rps-%s"%c['RPS']

    kvs[name] = (v, real_rps[k], real_tps[k]);


for rps in RPSs:
    print("RPS: ", rps)
    print("Percentile base 1-node")
    for i in range(len(perc)):
        p = perc[i]
        name = "base_rps-%s"%(rps)
        base = kvs[name][0]
        name = "cxl_rps-%s"%(rps)
        cxl = kvs[name][0]

        print("%s %s %s"%(p, base[p], cxl[p]))

    base = "base_rps-%s"%(rps)
    cxl = "cxl_rps-%s"%(rps)
    print("RPS %s %s" %(kvs[base][1], kvs[cxl][1]))
    print("TPS %s %s" %(kvs[base][2], kvs[cxl][2]))

    print("\n")
