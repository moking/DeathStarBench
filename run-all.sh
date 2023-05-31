dir="socialNetwork"

cur=`pwd`
cd $dir

user=`whoami`

bin='python ./run-socialnetwork-test.py'

if [ "$user" != "root" ];then
	echo "Need to run as root"
	exit
fi

cpus=4
duration=60
rps='1000,2000,3000,5000,10000,100000,1000000'
for network in 's'; do
	for workload in 'compose-post' 'read-home-timeline' 'read-user-timeline' 'mixed-workload'; do
		p=$cpus
		echo $bin -n $network -w $workload -r $rps -p $p -d $duration -m 500m -N 2
		$bin -n $network -w $workload -r $rps -p $cpus -d $duration

		
		p=`echo $(($p/2))`
		echo $bin -n $network -w $workload -r $rps -p $p -d $duration -m 1g -N 1
		$bin -n $network -w $workload -r $rps -p $cpus -d $duration
	done
done

cd $cur
