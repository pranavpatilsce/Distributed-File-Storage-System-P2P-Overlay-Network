server3:
	python3 server.py

client3:
	python3 client.py

proto3:
	python3 -m grpc_tools.protoc -I=. --python_out=. --grpc_python_out=. ./dataverse.proto

server:
	python server.py

client:
	python client.py

proto:
	python -m grpc_tools.protoc -I=. --python_out=. --grpc_python_out=. ./dataverse.proto


