#! /bin/bash

while getopts n: flag
do
    case "${flag}" in
        n) name=${OPTARG};;
    esac
done

apt update
apt install -y dnsutils

ip_addrs=$(dig +short $name | tr '\n' ' ')
ip_addrs=${ip_addrs// /:6379 }

echo "ip_addrs: $ip_addrs"

num_nodes=`echo $ip_addrs | wc -w`
if [ $num_nodes -eq 1 ];then
	ip_addrs=`echo $ip_addrs $ip_addrs $ip_addrs`
elif [ $num_nodes -eq 2 ];then
	ip_addrs=`echo $ip_addrs $ip_addrs`
fi
echo "ip_addrs: $ip_addrs"

redis-cli --cluster create $ip_addrs --cluster-replicas 0 --cluster-yes

