user=`whoami`
if [ "$user" != "root" ];then
	echo "Please run as root, exit..."
	exit
fi

rps=1000000
duration=60
num_threads=32
num_con=64
data=/tmp/data.txt

help() {
	echo -e "Info: choose one of the three networks to run:"
	echo -e "  socfb-Reed98 : a small social network Reed98 Facebook Networks"
	echo -e "  ego-twitter :  a medium social network Ego Twitter"
	echo -e "  soc-twitter-follows-mun :  a large social network TWITTER-FOLLOWS-MUN"
}

bench=socfb-Reed98

if [ "$1" != "socfb-Reed98" -a "$1" != "ego-twitter" -a "$1" != "soc-twitter-follows-mun" ];then
	help
	exit
else
	bench=$1
fi

yml=docker-compose.yml

if [ "$2" != "" ];then
	yml=$2
fi

mv $data $data.orig
echo > $data

echo "cleanup docker containers"
docker-compose -f $yml down

echo "Start docker containers"
docker-compose -f $yml up -d 

echo "Register users and construct social graph"

python3 scripts/init_social_graph.py --graph=$bench

echo "Compose posts"
echo "****************">>$data
../wrk2/wrk -D exp -t $num_threads -c $num_con -d $duration -L -s ./wrk2/scripts/social-network/compose-post.lua http://localhost:8080/wrk2-api/post/compose -R $rps | tee $data
echo "****************">>$data

echo "Read home timelines"
echo "****************">>$data
../wrk2/wrk -D exp -t $num_threads -c $num_con -d $duration -L -s ./wrk2/scripts/social-network/read-home-timeline.lua http://localhost:8080/wrk2-api/home-timeline/read -R $rps | tee -a $data
echo "****************">>$data

echo "Read user timelines"
echo "****************">>$data
../wrk2/wrk -D exp -t $num_threads -c $num_con -d $duration -L -s ./wrk2/scripts/social-network/read-user-timeline.lua http://localhost:8080/wrk2-api/user-timeline/read -R $rps | tee -a $data
echo "****************">>$data

echo "View Jaeger traces by accessing http://localhost:16686 "


echo "cleanup docker containers"
docker-compose -f $yml down

docker image prune
docker volume prune
