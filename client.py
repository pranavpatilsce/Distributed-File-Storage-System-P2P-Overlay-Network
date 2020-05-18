import uuid
import datetime
import logging
import json
from flask import Flask, flash, request, redirect, url_for, render_template_string, send_file

from pathlib import Path
import os
import grpc
import dataverse_pb2 as service
import dataverse_pb2_grpc as rpc
from google.protobuf.json_format import MessageToJson

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', '.gif','mp4','.mp4', 'mp3', '.mp3'}
CHUNK_SIZE = 1024 * 1024  # decrease the value here to evaluate memory usage
global fileName_g
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

#stub = None
stub = None
channel = None

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.after_request
def add_header(r):
    """
    """
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    return r

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
        IP = request.form["IP"]
        PORT = request.form["PORT"]
        connectTo(IP,PORT)
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
                output_result = stub.Upload(upload_request_generator())
                if output_result.nodeConnections:
                    arr = output_result.nodeConnections[0].split(":")
                    connectTo(arr[0],arr[1])
                    replicate = stub.Upload(upload_request_generator())
                    print(replicate)
                logging.info(f'file {i} {file.name} was upload successfully')
                results.append(MessageToJson(output_result))
        return redirect(url_for('upload_file', json=json.dumps(results)))  # we need a safe string to pass as url param
    return render_template_string('''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>

    <form method=post enctype=multipart/form-data>
        <h3>Server</h3>
            IPv4 Address <input type=text name=IP required><br><br>
            Port Number  <input type=text name=PORT required><br><br>
        <input type=file name=selected_files multiple required>
        <input type=text name=username required>
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

@app.route('/download')
def download_file():
    global fileName_g
    path="./downloadsTemp/"+fileName_g
    print("FILENAME----------------------------------")
    print(fileName_g)
    file = send_file(path, as_attachment=True)
    os.remove(path)
    return file


@app.route('/search', methods=['GET', 'POST'])
def search_file():
    if request.method == 'POST':
        results = []
        IP = request.form["IP"]
        PORT = request.form["PORT"]
        uname = request.form["username"]
        fname = request.form["filename"]

        logging.info(f' Params Uname {fname} | Fname {fname}')
        # connectTo(IP,PORT)
        global stub

        # searchlogic
        visited = []    # List to keep track of visited nodes.
        queue = []      #Initialize a queue
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
                print(result)
                if result.found == "YES":
                    print("HERE ", result.found)
                    break
                for node in result.nodeConnections:
                    if node not in visited:
                        queue.append(node)

        #result = stub.Search(service.SearchRequest(Filename=fname, Username=uname))
        logging.info(f' Params Uname {uname} | Fname {fname}')
        #results.append(MessageToJson(result))
        t = json.loads(results[len(results) - 1])
        print("187", t)
        global fileName_g
        fileName_g = t['File']
        print("----------------")
        print(t['File'])
        print("----------------")
        path = "./downloadsTemp"
        Path(path).mkdir(parents=True, exist_ok=True)
        f = open('./downloadsTemp/'+fileName_g,'wb')
        # bytearray(b'\xff\xd8\xff\xe0')
        f.write(result.Content)
        f.close()

        return redirect(url_for('search_file', json=json.dumps("{'bar': ('baz', None, 1.0, 2)}" )))  # we need a safe string to pass as url param
    return render_template_string('''
    <!doctype html>
    <title>Search File</title>
    <h1>Search File</h1>
    <form method=post>
      <h3>Server </h3>
      IPv4 Address <input type=text name=IP required><br><br>
      Port Number <input type=text name=PORT required><br><br>
      Username <input type=text name=username required><br><br>
      Filename <input type=text name=filename required><br><br>
      <input type=submit value=Search>
    </form>
    <a href = "/download">Download</a>
    ''', json_response="dummy")

@app.route('/config', methods=['GET', 'POST'])
def config():
    if request.method == 'POST':
        results = []

        IP1 = request.form["IP1"]
        PORT1 = request.form["PORT1"]
        IP2 = request.form["IP2"]
        PORT2 = request.form["PORT2"]

        connectTo(IP1, PORT1)
        global stub
        result1 = stub.Config(service.ConfigRequest(Server=IP2+':'+PORT2 ))
        connectTo(IP2,PORT2)
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
      IPv4 Address: <input type=text name=IP1 required><br><br>
      Port Number:  <input type=text name=PORT1 required><br>
      <h3>Server 2 </h3>
      IPv4 Address: <input type=text name=IP2 required><br><br>
      Port Number:  <input type=text name=PORT2 required><br><br>
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
    app.run(host='0.0.0.0', port = 5001, debug=True)
