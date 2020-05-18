import uuid
import datetime
import logging
import json
from flask import Flask, flash, request, redirect, url_for, render_template_string

import grpc
import dataverse_pb2 as service
import dataverse_pb2_grpc as rpc
from google.protobuf.json_format import MessageToJson

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', '.gif','mp4','.mp4', 'mp3', '.mp3'}
CHUNK_SIZE = 1024 * 1024  # decrease the value here to evaluate memory usage

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

#stub = None
stub = None
channel = None

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.template_filter('json_loads')
def json_loads_filter(s):
    return json.loads(s) if s else None

@app.route('/selectServer', methods=['GET','POST'])
def selectServer():
    if request.method == 'POST':
        serverip = request.form["serverip"]
        serverport = request.form["serverport"]
        print('serverip is'+serverip)
        global channel
        if channel!=None:
            print('Channel connection exists!')
            channel.close()
        print('Creating Connection!')
        channel = grpc.insecure_channel(serverip+':'+serverport)
        global stub
        stub = rpc.GreeterStub(channel)
        print(stub)
        logging.info('Connection to'+serverip+':'+serverport+' created successfully')
        return 'Connection to '+serverip+':'+serverport+' created successfully' # we need a safe string to pass as url param
    return render_template_string('''
    <!doctype html>
    <title>Select Server</title>
    <h1>Select Server</h1>
    <form method=post enctype=multipart/form-data>
      Enter Server IP: <input type=text name=serverip>
      Enter Server Port: <input type=text name=serverport>
      <input type=submit value=Select>
    </form>
    {% if json_response %}
    <h1>Client connected with the server</h1>
    {% endif %}
    ''', json_response=request.args.get('json'))

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'selected_files' not in request.files:
            flash("No 'selected_files' part")
            return redirect(request.url)
        selected_files = request.files.getlist("selected_files")
        results = []
        uname = request.form["username"]

        for i, file in enumerate(selected_files, 1):
            if file.filename == '':
                flash('You must select at least one file')
                return redirect(request.url)

            if file and allowed_file(file.filename):
                fileid = f'{datetime.datetime.utcnow().isoformat()}-{uuid.uuid4()}'

                def upload_request_generator():  # this generates our grpc `stream ImageUploadRequest`
                    i = 1
                    # username = request.form.get("username")
                    # logging.info(f'{request}')
                    while True:
                        b = file.read(CHUNK_SIZE)
                        if b:
                            result = service.ImageUploadRequest(Content=b, Id=file.filename, StatusCode=service.ImageUploadStatusCode.InProgress, Username=uname)  # noqa
                        else:
                            result = service.ImageUploadRequest(Id=file.filename, StatusCode=service.ImageUploadStatusCode.Ok, Username=uname)  # noqa

                        yield result
                        if not b:
                            break
                global stub
                result = stub.Upload(upload_request_generator())
                logging.info(f'file {i} {file.name} was upload successfully')
                results.append(MessageToJson(result))
        return redirect(url_for('upload_file', json=json.dumps(results)))  # we need a safe string to pass as url param
    return render_template_string('''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=selected_files multiple>
      <input type=text name=username>
      <input type=submit value=Upload>
    </form>
    {% if json_response %}
    <h1>Last upload</h1>
    <ol>
    {% for item in (json_response|json_loads) %}
    <li>
        {{ (item|json_loads) }}
    </li>
    {% endfor %}
    </ol>
    {% endif %}
    ''', json_response=request.args.get('json'))

@app.route('/search', methods=['GET', 'POST'])
def search_file():
    if request.method == 'POST':
        results = []
        IP = request.form["IP"]
        PORT = request.form["PORT"]
        uname = request.form["username"]
        fname = request.form["filename"]
        logging.info(f' Params Uname {fname} | Fname {fname}')
        connectTo(IP,PORT)
        global stub

        # searchlogic
        visited = [] # List to keep track of visited nodes.
        queue = []     #Initialize a queue
        queue.append(IP+':'+PORT)
        while queue:
            size = len(queue)
            for i in range (size):
                s = queue.pop(0) 
                print (s, end = " ") 
                arr = s.split(":")
                connectTo(arr[0],arr[1])
                result = stub.Search(service.SearchRequest(Filename=fname, Username=uname))
                results.append(MessageToJson(result))
                visited.append(s)
                if result.found == "YES":
                    break
                for node in result.nodeConnections:
                    queue.append(node)
                for node in result.nodeConnections:
                    if node not in visited:
                        queue.append(node)

        # result = stub.Search(service.SearchRequest(Filename=fname, Username=uname))
        # print(result)
        # print(result.found)


        results.append(MessageToJson(result))
        # print("----------------")
        # print(json.dumps(results))
        # print("----------------")
        return redirect(url_for('search_file', json=json.dumps(results)))  # we need a safe string to pass as url param
    return render_template_string('''
    <!doctype html>
    <title>Search File</title>
    <h1>Search File</h1>
    <form method=post>
      <h3>Server 1 </h3>
      IPv4 Address <input type=text name=IP><br><br>
      Port Number <input type=text name=PORT><br><br>
      Username <input type=text name=username><br><br>
      Filename <input type=text name=filename><br><br>
      <input type=submit value=Search>
    </form>
    {% if json_response %}
    <h1>Files Found</h1>
    <ol>
    {% for item in (json_response|json_loads) %}
    <li>
        {{ (item|json_loads) }}
    </li>
    {% endfor %}
    </ol>
    {% endif %}
    ''', json_response=request.args.get('json'))

@app.route('/config', methods=['GET', 'POST'])
def config():
    if request.method == 'POST':
        results = []
        
        IP1 = request.form["IP1"]
        PORT1 = request.form["PORT1"]
        IP2 = request.form["IP2"]
        PORT2 = request.form["PORT2"]

        connectTo(IP1, PORT1)
        # global channel
        # if channel!=None:
        #     print('Closed the existing channel!')
        #     channel.close()
        # print('Creating Connection! ' +IP1+':'+PORT1)
        # channel = grpc.insecure_channel(IP1+':'+PORT1)
        global stub
        # stub = rpc.GreeterStub(channel)
        # print("stub1", stub)
        result1 = stub.Config(service.ConfigRequest(Server=IP2+':'+PORT2 ))
        connectTo(IP2,PORT2)
        # global channel
        # if channel!=None:
        #     print('Closed the existing channel!')
        #     channel.close()
        # print('Creating Connection! ' +IP2+':'+PORT2)
        # channel = grpc.insecure_channel(IP2+':'+PORT2)
        # # global stub
        # stub = rpc.GreeterStub(channel)
        # global stub
        # print(stub)
        result2 = stub.Config(service.ConfigRequest(Server=IP1+':'+PORT1 ))

        logging.info(f' Server1 Params IP {IP1} | PORT {PORT1}')
        logging.info(f' Server2 Params IP {IP2} | PORT {PORT2}')
        results.append(MessageToJson(result1))
        results.append(MessageToJson(result2))
        print("----------------")
        print(json.dumps(results))
        print("----------------")
        return redirect(url_for('config', json=json.dumps(results)))  # we need a safe string to pass as url param
    return render_template_string('''
    <!doctype html>
    <title>Connect to a Node</title>
    <h1>Connect to a Node</h1>
    <form method=post>
        <h3>Server 1 </h3>
      IPv4 Address: <input type=text name=IP1><br><br>
      Port Number:<input type=text name=PORT1><br>
      <h3>Server 2 </h3>
      IPv4 Address: <input type=text name=IP2><br><br>
      Port Number:<input type=text name=PORT2><br>
      <input type=submit value=Connect>
    </form>
    {% if json_response %}
    <h1>Response from server</h1>
    <ol>
    {% for item in (json_response|json_loads) %}
    <li>
        {{ (item|json_loads) }}
    </li>
    {% endfor %}
    </ol>
    {% endif %}
    ''', json_response=request.args.get('json'))

def connectTo(serverip, serverport):
    global channel
    if channel!=None:
        print('Closed the existing channel!')
        channel.close()
    print('Creating Connection! ' +serverip+':'+serverport)
    channel = grpc.insecure_channel(serverip+':'+serverport)
    global stub
    stub = rpc.GreeterStub(channel)

if __name__ == "__main__":
    print('hellllllllllllllllladkjashdjhasjdkhasjdhjaskdhjk')
    app.run(host='0.0.0.0', debug=True)
