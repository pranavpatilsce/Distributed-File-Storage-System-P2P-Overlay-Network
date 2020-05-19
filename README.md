# Distributed-Systems-P2P-Network

This project can stream audio, video, and image files from client to server via gRPC. The main goal of the project is to build an overlay network.

### Operation
0. You will have to generate the proto files using proto.sh. You can also run the project Makefile. Before the 1st bootup, delete the cache.txt and data folder. 
1. From main directory, do `cd project`
2. Then type `source bin/activate`
3. Open another terminal window and do steps 1 and 2 again in the directory
4. In the 1st terminal window: python ../server.py which will launch the server.
5. In the 2nd terminal window: python ../client.py which will launch the client at localhost:5000
6. The server port is `22222` and use `localhost` running of the project on localhost.
