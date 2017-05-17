Dell Microservices

### Introduction
Not all the microservices need to run.  You have the option of starting only the ones needed.

### How to start

1. log in as a privileged user, or use SUDO for the docker related commands.  Docker requires root access to run.

2. Clone down the RackHD repo if you don't already have it.
~~~
git clone http://github.com/rackhd/rackhd
~~~

4.  Change into the "rackhd/docker/dell" folder
~~~
cd rackhd/docker/dell
~~~

3. set some environment variables in a .env file to be used by the docker-compose file
~~~
echo REGISTRY_IP=172.31.128.1 >> .env
echo HOST_IP=100.68.123.164 >> .env
~~~

5. Start Consul only in detached mode
~~~
sudo docker-compose up -d consul
~~~
You can view the consul UI by navigating to http://<your_HOST_IP_address>:8500

6. Post in microservice key/value properties into consul
~~~
chmod +x set_config.sh
./set_config.sh
~~~
You can view the key/value data in consul by clicking on the Key/Value tab.

7. Start remaining containers (or just the ones you want to start) in detached mode
~~~
sudo docker-compose up -d
~~~
It takes about 2 minutes for the services to come up. To start just the containers you want, specify the names of the containers to start at the end of the command seperated by a space.

8. Verify your services are online
~~~
sudo docker ps -a
~~~
You can also look for your services to register in the consul UI
You can examine the logs by typing:
~~~
sudo docker logs <name of the service>
~~~ 
You can navigate to the swagger UI in a browser using the port for the service.. example 
~~~
http://<<your ip>>:<port>/swagger-ui.html
~~~

9. Tell RackHD about the IP/port of the microservices
~~~
curl -X POST -H 'Content-Type: application/json' -d '{"name": "Graph.Dell.Wsman.ConfigServices", "options":{ "defaults": {"configServer": "http://localhost:46020"}}}' 'http://172.31.128.1:8080/api/2.0/workflows'
~~~

Note: to start just the containers you want, specify the names of the containers to start at the end of the command seperated by a space.

### Services required for the dell discovery graph
consul gateway device-discovery dell-chassis-inventory dell-server-inventory
