from concurrent import futures
import os
import io
from collections import defaultdict
import logging
from pathlib import Path

import grpc

import dataverse_pb2 as service
import dataverse_pb2_grpc as rpc


cache = set()

class ImageServiceServer(rpc.GreeterServicer):  # inheriting here from the protobuf rpc file which is generated

    def __init__(self):
        self.images = defaultdict(io.BytesIO)
        logging.info("successfuly created the images store")
        my_file = Path("./cache.txt")
        if my_file.is_file():
            with open('cache.txt', 'r') as filehandle:
                filecontents = filehandle.readlines()
                for line in filecontents:
                    cache.add(line[:-1])
        logging.info("successfuly initialized the cache")


    def Upload(self, request_iterator, context):
        for request in request_iterator:
            if request.StatusCode == service.ImageUploadStatusCode.InProgress:
                logging.info(f'> {request.Id} - receiving image')
                self.images[request.Id].write(request.Content)
                result = service.ImageUploadResponse(Id=request.Id, StatusCode=service.ImageUploadStatusCode.Ok, Message='waiting for more', Username=request.Username)

            if request.StatusCode == service.ImageUploadStatusCode.Ok and not request.Content:
                logging.info('transfer completed!')
                logging.info(f'> {request.Id} - storing image')
                image = self.images[request.Id].getvalue()
                path = "./data/"+request.Username
                file = path+'/'+request.Id
                Path(path).mkdir(parents=True, exist_ok=True)
                f = open(file,'wb')
                f.write(image)
                f.close()
                logging.info(f'> {request.Id} - deleting image from mem')
                del self.images[request.Id]
                cache.add(file)

                logging.info(f'> Username - {request.Username}')
                logging.info(f'> {request.Id} - returning status')
                result = service.ImageUploadResponse(Id=request.Id, StatusCode=service.ImageUploadStatusCode.Ok, Message="Uploaded", Username=request.Username)
                return result

    def Search(self, request, context):
        print(request)
        uname = request.Username
        fname = request.Filename
        file = './data/'+uname +'/'+fname
        print(file)
        print(cache)
        if(file in cache):
            return service.SearchResponse(found="YES")
        return service.SearchResponse(found="NO")

if __name__ == '__main__':
    try:
        logging.basicConfig(level=logging.INFO)
        port = 22222
        grpc_server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        rpc.add_GreeterServicer_to_server(ImageServiceServer(), grpc_server)
        logging.info(f'Starting server. Listening at {port}...')
        grpc_server.add_insecure_port(f'[::]:{port}')
        grpc_server.start()
        grpc_server.wait_for_termination()
    except KeyboardInterrupt:
        with open('cache.txt', 'w') as filehandle:
            cacheList = list(cache)
            for listitem in cache:
                filehandle.write('%s\n' % listitem)
        print("LOLLOLOLOLOLOOLOLOOOOOOOOOOLL")
        print(cache)
