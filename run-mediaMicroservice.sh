user=`whoami`
if [ "$user" != "root" ];then
	echo "Please run as root, exit..."
	exit
fi
cd mediaMicroservices/
rps=1000000
duration=60
sizes='50m 100m 200m 500m 1g'
num_threads=32
num_con=64
data=/tmp/data.txt

echo > $data

echo sizes: $sizes
for size in $sizes; do
	echo "cleanup docker containers"
	docker-compose down
	echo "**set memory size $size for cache and db docker instances"
	cp docker-compose.yml.100m docker-compose.yml
	sed -i 's/100m/'$size'/' docker-compose.yml
	cnt=`cat docker-compose.yml | grep -c $size`
	if [ "$cnt" == "0" ];then
		echo set memory size to $size failed, exit
		exit
	fi
	echo "Start docker containers"
	docker-compose up -d 

	echo "Register users and movie information"
	{ python3 scripts/write_movie_info.py -c  ./datasets/tmdb/casts.json -m ./datasets/tmdb/movies.json && scripts/register_users.sh && scripts/register_movies.sh;}>/dev/null

	echo "Compose reviews"
	echo "View Jaeger traces by accessing http://localhost:16686 "

	../wrk2/wrk -D exp -t $num_threads -c $num_con -d $duration -L -s ./wrk2/scripts/media-microservices/compose-review.lua  http://localhost:8080/wrk2-api/review/compose -R $rps | tee /tmp/docker.log

echo "****************">>$data
echo "Memsize: $size" >>$data
tail -10 /tmp/docker.log >>$data
echo >>$data
echo "****************">>$data
echo "cleanup docker containers"
docker-compose down
done
docker image prune
docker volume prune

cd ..
