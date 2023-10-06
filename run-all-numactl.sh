dir="socialNetwork"

cur=`pwd`
cd $dir

user=`whoami`

bin='python ./run-socialnetwork-test-numactl.py'

if [ "$user" != "root" ];then
	echo "Need to run as root"
	exit
fi

cpus=4
duration=60
rps='1000,5000,10000,100000'
replicas=5
workload="compose-post,read-home-timeline,read-user-timeline,mixed-workload"
for network in 's'; do
    for node_id in 2 0 1;do
        echo $bin -n $network -w $workload -r $rps -d $duration -N $replicas -m m -M $node_id
        $bin -n $network -w $workload -r $rps -d $duration -N $replicas -m m -M $node_id
        echo
    done
    for node_id in 0,1 0,2;do
        echo $bin -n $network -w $workload -r $rps -d $duration -N $replicas -m i -M $node_id
        $bin -n $network -w $workload -r $rps -d $duration -N $replicas -m i -M $node_id
        echo
    done
done

cd $cur
