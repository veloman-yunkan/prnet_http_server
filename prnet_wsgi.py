import json
import numpy as np
import os
import re
import sys
import tempfile

from multipart import parse_form_data
from shutil import rmtree

from skimage.io import imread
from skimage.transform import rescale

from PRNet.api import PRN
from PRNet.utils.write import write_obj_with_colors
from httplib import HTTPException


PRNET_MAX_IMAGE_SIZE = int(os.environ.get('PRNET_MAX_IMAGE_SIZE', '5000000'))

class TempDir:
    def __init__(self):
        self.tempdir = tempfile.mkdtemp()
        print 'Created temporary directory ' + self.tempdir

    def __del__(self):
        print 'Removing temporary directory ' + self.tempdir
        rmtree(self.tempdir)

    def join(self, fname):
        return os.path.join(self.tempdir, fname)

    def cleanup(self):
        for f in os.listdir(self.tempdir):
            os.remove(self.join(f))


tempdir = TempDir()
prn = PRN(is_dlib = True)

def prnet(image_path):
    image = imread(image_path)
    [h, w, c] = image.shape
    if c>3:
        image = image[:,:,:3]

    max_size = max(image.shape[0], image.shape[1])
    if max_size> 1000:
        image = rescale(image, 1000./max_size)
        image = (image*255).astype(np.uint8)
    pos = prn.process(image) # use dlib to detect face

    image = image/255.
    if pos is None:
        raise Exception("No face in the image")

    vertices = prn.get_vertices(pos)
    save_vertices = vertices.copy()
    save_vertices[:,1] = h - 1 - save_vertices[:,1]

    colors = prn.get_colors(image, vertices)
    obj_path = image_path + '.obj'
    write_obj_with_colors(obj_path, save_vertices, prn.triangles, colors)
    return obj_path


def get_posted_image(environ):
    path = environ['PATH_INFO']
    if environ['REQUEST_METHOD'] != 'POST' or path != '/':
        raise HTTPException('405 Method Not Allowed')

    content_length = int(environ.get('CONTENT_LENGTH', '-1'))
    if content_length == -1:
        raise HTTPException('411 Length Required')
    elif content_length > PRNET_MAX_IMAGE_SIZE:
        raise HTTPException('413 Payload Too Large')

    forms, files = parse_form_data(environ)
    if len(files) != 1 or 'image' not in files:
        raise HTTPException("400 Bad Request")

    img = files['image']
    imgfile_path = tempdir.join(img.filename)
    img.save_as(imgfile_path)
    return imgfile_path


def read_file_chunks(file_path):
    with open(file_path, 'rb') as f:
        while True:
            file_data = f.read(32768)
            if file_data is None or len(file_data) == 0:
                break
            yield file_data


def get_response_headers(result_file_path):
    result_file_size = os.stat(result_file_path).st_size
    file_name = result_file_path.split('/')[-1]
    return [
            ('Content-Type', 'application/octet-stream'),
            ('Content-Length', str(result_file_size)),
            ('Content-Disposition', 'attachment; filename="%s"' % file_name)
        ]


msg_replacement_rules = (
    (
        r"^cannot identify image file <open file u'.*/(.+)', mode 'rb' at .*>$",
        r"cannot identify image file '\1'"
    ),
)

msg_replacement_rules = [(re.compile(r),t) for r,t in msg_replacement_rules]

def improve_error_message(msg):
    for r,t in msg_replacement_rules:
        m = r.match(msg)
        if m:
            return m.expand(t)
    return msg


def make_error_response(err):
    err_msg = improve_error_message(err.message)
    body = json.dumps({ 'error' : err_msg }) + "\n"
    headers = (
                ('Content-Type', 'application/json'),
                ('Content-Length', str(len(body))),
        )
    return headers, body


def handle_request(environ, start_response):
    try:
        imgfile_path = get_posted_image(environ)
        result_file_path = prnet(imgfile_path)
        start_response('200 OK', get_response_headers(result_file_path))
        for file_chunk in read_file_chunks(result_file_path):
            yield file_chunk
    except HTTPException as e:
        start_response(e[0], (('Content-Length', '0'),))
    except Exception as e:
        headers, body = make_error_response(e)
        start_response('500 Internal Server Error', headers, sys.exc_info())
        yield body
    finally:
        tempdir.cleanup()
