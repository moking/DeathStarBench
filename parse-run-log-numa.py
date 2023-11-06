import argparse
import json
import os.path


parser=argparse.ArgumentParser()
parser.add_argument('-L', '--log', required=True) 

args=vars(parser.parse_args())
log=args['log']

f = open(log, 'r')
line = f.readline()

res_avg={}
res_p99={}
res_tput={}
mode=""
moment=""
while line != "":
    if "MODE:" in line:
        mode=line.split(":")[1]
        moment=line.strip()
        line = f.readline()
        nodes=0
        while line != "" and "numactl -H" not in line:
            line = f.readline()
        while line != "" and "available" not in line:
            line = f.readline()

        nodes = line.split(":")[-1].split()[0]
        # print("NODES", nodes)
        nodes = int(nodes)
        node_list="MB\t"
        for i in range(nodes):
            node_list = node_list + "node-%d\t"%i
        # print(node_list)

        line = f.readline()
        sizes="size\t"
        frees="free\t"
        while line != "" and "node distances" not in line:
            if "size" in line:
                sizes=sizes + line.split(":")[-1].strip().split()[0] + "\t"
            if "free" in line:
                frees = frees + line.split(":")[-1].strip().split()[0] + "\t"
            line = f.readline()


        line = f.readline()
        while line != "" and "Test Results" not in line:
            line = f.readline()

        line = f.readline().strip()
        title=line.strip().strip()
        latency = f.readline().strip()
        while line != "" and "Requests/sec" not in line:
            line = f.readline()
        if latency != "":
            avg_lat = latency.split()[1]
            p99_lat = latency.split()[3]
            tput=line.split(":")[1].strip()
            print("")
            # print(moment)
            config=moment.split(",")[0].split(":")[1]
            config=config.strip()
            print(config)
            if config not in res_avg:
                res_avg[config] = []
                res_p99[config] = []
                res_tput[config] = []
            else:
                res_avg[config].append(avg_lat)
                res_p99[config].append(p99_lat)
                res_tput[config].append(tput)
            print(node_list)
            print(sizes)
            print(frees)
            # print(avg_lat, p99_lat, tput)

    line = f.readline()

labels=["Avg_latency", "P99_latency", "Throughput: Req/sec"]
for k in res_avg.keys():
    i=0
    print("#", k)
    for v in [res_avg[k], res_p99[k], res_tput[k]]:
        compose = [v[i] for i in range(0, len(v), 2)]
        mixed = [v[i] for i in range(1, len(v), 2)]
        print("#", labels[i])
        print("Compose-post\t", compose)
        print("Mixed-workload\t", mixed)
        i=i+1
        print("")
    # print("Tput: ", res_tput[k])
# print(res_avg)
# print(res_p99)
# print(res_tput)


f.close()




