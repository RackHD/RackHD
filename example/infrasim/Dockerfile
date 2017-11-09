#Copyright © 2017 Dell Inc. or its subsidiaries.  All Rights Reserved. 

FROM infrasim/infrasim-compute:3.5.1

COPY default.yml /root/.infrasim/.node_map/

COPY start_infrasim.sh .

RUN apt-get install -y dos2unix
RUN dos2unix start_infrasim.sh 

ENTRYPOINT ./start_infrasim.sh
