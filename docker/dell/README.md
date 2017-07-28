## System Management Integration (SMI) Microservices

### Introduction
The SMI Microservices are add-on services that are used by rackhd workflows and tasks, primarily focused on adding value for the managemenet of Dell servers.   These services use a Zuul gateway and Consul Registry service to present a unified API.   Documentation for each service is avialiable on Github in repositories that begin with "smi-service" or on the dockerhub page for the service.

Note: Not all the microservices need to run.  You have the option of starting only the ones needed, or manually editing the docker-compose.yml file.

### How to start

1. Log in as a privileged user, or use SUDO for the docker related commands.  Docker requires root access to run.

2. Clone down the RackHD repo if you don't already have it.
~~~
git clone http://github.com/rackhd/rackhd
~~~

3.  Change into the "rackhd/docker/dell" folder
~~~
cd rackhd/docker/dell
~~~

4. Edit the .env file with your IP addresses.  By default the IP addresses are set to 172.31.128.1 to match the default southbound IP for RackHD. 
Optionally, if you wish to have available the PDF generation feature of the swagger-aggregator, the "HOST_IP" setting in the .env file should be changed to your "Northbound" IP.

5. Start Consul only in detached mode
~~~
sudo docker-compose up -d consul
~~~
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;You can view the consul UI by navigating to http://<your_HOST_IP_address>:8500

6. Post in microservice key/value properties into consul
~~~
./set_config.sh
~~~
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;You can view the key/value data in consul by clicking on the Key/Value tab.

7. Start remaining containers (or just the ones you want to start) in detached mode
~~~
sudo docker-compose up -d
~~~
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;It takes about 2 minutes for the services to come up. To start just the containers you want, specify the names of the containers to start at the end of the command seperated by a space.

8. Verify your services are online
~~~
sudo docker ps -a
~~~
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;You can also look for your services to register in the consul UI

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;You can examine the logs by typing:
~~~
sudo docker logs <name of the service>
~~~ 
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;You can navigate to the swagger UI in a browser using the port for the service.. example 
~~~
http://<<your ip>>:<port>/swagger-ui.html
~~~

9. Tell RackHD about the IP/port of the microservices 
(Note: You pay need to modify the port from 8080 to 9090 for the dockerized version of RackHD)  
~~~
curl -X POST -H 'Content-Type: application/json' -d '{"name": "Graph.Dell.Wsman.ConfigServices", "options":{ "defaults": {"configServer": "http://localhost:46020"}}}' 'http://172.31.128.1:8080/api/2.0/workflows'
~~~

