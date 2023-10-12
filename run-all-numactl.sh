dir="socialNetwork"

cur=`pwd`
cd $dir

user=`whoami`

bin='python ./run-socialnetwork-test-numactl.py'

if [ "$user" != "root" ];then
	echo "Need to run as root"
	exit
fi

threads=48
conn=200
duration=120
rps='1000,5000,10000'
#rps='5000'
#rps='1000,5000'
replicas=5
workload="compose-post,read-home-timeline,read-user-timeline,mixed-workload"
workload="compose-post,read-user-timeline,mixed-workload"
#workload="compose-post,read-home-timeline"

suffix=`date +%H-%M-%h-%d`
log_dir="/home/fan/cxl/DeathStarBench/"

file="/tmp/dsb-${suffix}.log"

if [ "$1" != "" ];then
    file=$1
fi

for network in 's' 'f'; do
    for node_id in 0 1 2; do
        echo $bin -n $network -w $workload -r $rps -d $duration -N $replicas -m m -M $node_id -t $threads -c $conn | tee -a $file
        $bin -n $network -w $workload -r $rps -d $duration -N $replicas -m m -M $node_id -t $threads -c $conn 2>&1 | tee -a $file
        echo
    done

    for node_id in 0,1 0,2;do
        echo $bin -n $network -w $workload -r $rps -d $duration -N $replicas -m i -M $node_id -t $threads -c $conn | tee -a $file
        $bin -n $network -w $workload -r $rps -d $duration -N $replicas -m i -M $node_id -t $threads -c $conn 2>&1 | tee -a $file
        echo
    done
done


cat $file | grep -v Stopping | grep -v Removing | grep -v Creating | grep -v Untagged | grep -v "Deleted:" > $log_dir/dsb-run-conn$conn-thread$threads-$suffix.log
cd $cur
