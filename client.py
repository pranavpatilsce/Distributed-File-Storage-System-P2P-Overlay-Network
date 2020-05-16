import uuid
import datetime
import logging
import json
from flask import Flask, flash, request, redirect, url_for, render_template_string

import grpc
import helloworld_pb2 as service
import helloworld_pb2_grpc as rpc
from google.protobuf.json_format import MessageToJson

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', '.gif'}
CHUNK_SIZE = 1024 * 1024  # decrease the value here to evaluate memory usage

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.template_filter('json_loads')
def json_loads_filter(s):
    return json.loads(s) if s else None

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'selected_files' not in request.files:
            flash("No 'selected_files' part")
            return redirect(request.url)
        selected_files = request.files.getlist("selected_files")
        results = []
        for i, file in enumerate(selected_files, 1):
            if file.filename == '':
                flash('You must select at least one file')
                return redirect(request.url)

            if file and allowed_file(file.filename):
                fileid = f'{datetime.datetime.utcnow().isoformat()}-{uuid.uuid4()}'

                def upload_request_generator():  # this generates our grpc `stream ImageUploadRequest`
                    i = 1
                    while True:
                        b = file.read(CHUNK_SIZE)
                        if b:
                            result = service.ImageUploadRequest(Content=b, Id=fileid, StatusCode=service.ImageUploadStatusCode.InProgress)  # noqa
                        else:
                            result = service.ImageUploadRequest(Id=fileid, StatusCode=service.ImageUploadStatusCode.Ok)  # noqa
                        yield result
                        if not b:
                            break

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
      <input type=submit value=Upload>
    </form>
    {% if json_response %}
    <h1>Last upload</h1>
    <ol>
    {% for item in (json_response|json_loads) %}
    <li>
        <a href="{{ ((item|json_loads)['Message']|json_loads)['data']['link'] }}">{{ (item|json_loads)['Id'] }}</a><br>
        <pre style="overflow: auto;">{{ item }}</pre>
    </li>
    {% endfor %}
    </ol>
    {% endif %}
    ''', json_response=request.args.get('json'))


if __name__ == "__main__":
    channel = grpc.insecure_channel('grpc_service:22222')
    stub = rpc.GreeterStub(channel)
    print('hellllllllllllllllladkjashdjhasjdkhasjdhjaskdhjk')
    print(stub)
    app.run(host='0.0.0.0')