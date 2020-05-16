from concurrent import futures
import os
import io
from collections import defaultdict
import logging

import requests
import grpc

import helloworld_pb2 as service
import helloworld_pb2_grpc as rpc

CLIENT_ID = os.environ['IMGUR_CLIENT_ID']


class ImageServiceServer(rpc.GreeterServicer):  # inheriting here from the protobuf rpc file which is generated

    def __init__(self):
        self.images = defaultdict(io.BytesIO)
        logging.info("successfuly created the images store")

    def Upload(self, request_iterator, context):
        for request in request_iterator:
            if request.StatusCode == service.ImageUploadStatusCode.InProgress:
                logging.info(f'> {request.Id} - receiving image')
                self.images[request.Id].write(request.Content)
                result = service.ImageUploadResponse(Id=request.Id, StatusCode=service.ImageUploadStatusCode.Ok, Message='waiting for more')

            if request.StatusCode == service.ImageUploadStatusCode.Ok and not request.Content:
                logging.info('transfer completed!')
                logging.info(f'> {request.Id} - sending image')
                image = self.images[request.Id].getvalue()
                payload = {'image': image}
                headers = {'Authorization': f'Client-ID {CLIENT_ID}'}
                url = "https://api.imgur.com/3/image"
                response = requests.request("POST", url, headers=headers, data=payload, files=[])
                response.raise_for_status()
                logging.info(f'> {request.Id} - deleting image from mem')
                del self.images[request.Id]

                logging.info(f'> {request.Id} - returning status')
                result = service.ImageUploadResponse(Id=request.Id, StatusCode=service.ImageUploadStatusCode.Ok, Message=response.text.encode('utf8'))
                return result


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    port = 22222
    grpc_server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    rpc.add_GreeterServicer_to_server(ImageServiceServer(), grpc_server)
    logging.info(f'Starting server. Listening at {port}...')
    grpc_server.add_insecure_port(f'[::]:{port}')
    grpc_server.start()
    grpc_server.wait_for_termination()