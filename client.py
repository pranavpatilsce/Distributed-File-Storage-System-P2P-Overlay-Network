import uuid
import datetime
import logging
import json
from flask import Flask, flash, request, redirect, url_for, render_template_string, send_file

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

@app.route('/download')
def download_file():
    global fileName_g
    path="./downloads/"+fileName_g
    print("FILENAME----------------------------------")
    print(fileName_g)
    return send_file(path, as_attachment=True)

global fileName_g
@app.route('/search', methods=['GET', 'POST'])
def search_file():
    if request.method == 'POST':
        results = []
        uname = request.form["username"]
        fname = request.form["filename"]
        global stub
        result = stub.Search(service.SearchRequest(Filename=fname, Username=uname))
        logging.info(f' Params Uname {uname} | Fname {fname}')
        results.append(MessageToJson(result))
        t = json.loads(results[0])
        print( type(t))
        
        global fileName_g
        fileName_g = t['File']
        print("----------------")
        print(t['File'])
        print("----------------")
        f = open('./downloads/'+fileName_g,'wb')
        # bytearray(b'\xff\xd8\xff\xe0')
        f.write(result.Content)
        f.close()

        return redirect(url_for('search_file', json=json.dumps(results)))  # we need a safe string to pass as url param
    return render_template_string('''
    <!doctype html>
    <title>Search File</title>
    <h1>Search File</h1>
    <form method=post>
      Username<input type=text name=username><br>
      Filename<input type=text name=filename><br>
      <input type=submit value=Search>
    </form>
    {% if json_response %}
    <h1>Files Found</h1>
    <ol>
    {% for item in (json_response|json_loads) %}
    <a href="/download">Download</a>
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
        IP = request.form["IP"]
        PORT = request.form["PORT"]
        global stub
        result = stub.Config(service.ConfigRequest(Server=IP+':'+PORT))
        logging.info(f' Params IP {IP} | PORT {PORT}')
        results.append(MessageToJson(result))
        print("----------------")
        print(json.dumps(results))
        print("----------------")
        return redirect(url_for('config', json=json.dumps(results)))  # we need a safe string to pass as url param
    return render_template_string('''
    <!doctype html>
    <title>Connect to a Node</title>
    <h1>Connect to a Node</h1>
    <form method=post>
      IPv4 Address: <input type=text name=IP><br>
      Port Number:<input type=text name=PORT><br>
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

if __name__ == "__main__":
    print('hellllllllllllllllladkjashdjhasjdkhasjdhjaskdhjk')
    app.run(host='0.0.0.0', port = 5001, debug=True)
