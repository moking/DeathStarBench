dir="socialNetwork"

cur=`pwd`
cd $dir

user=`whoami`

bin='python ./run-socialnetwork-test.py'

if [ "$user" != "root" ];then
	echo "Need to run as root"
	exit
fi

rps='1000,2000,3000,5000,10000,100000,1000000'
for network in 'm' 'l'; do
	for workload in 'compose-post' 'read-home-timeline' 'read-user-timeline' 'mixed-workload'; do
		echo $bin -n $network -w $workload -r $rps
		$bin -n $network -w $workload -r $rps
	done
done

cd $cur
