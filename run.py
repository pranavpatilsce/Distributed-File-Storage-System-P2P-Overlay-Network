import json
import os
import io
import requests

API_URL = 'http://0.0.0.0/'

with open('./chai.png', 'rb') as fp:
    content = fp.read()

response = requests.post(
    '{}/addimage/chai.png'.format(API_URL), data=content
)

print(response.status_code())
