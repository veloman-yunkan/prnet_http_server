import os
from multipart import parse_form_data
import tempfile
import shutil

class TempDir:
    def __init__(self):
        self.tempdir = tempfile.mkdtemp()
        print 'Created temporary directory ' + self.tempdir

    def __del__(self):
        print 'Removing temporary directory ' + self.tempdir
        shutil.rmtree(self.tempdir)

    def join(self, fname):
        return os.path.join(self.tempdir, fname)

tempdir = TempDir()

import numpy as np
from skimage.io import imread
from skimage.transform import rescale

from PRNet.api import PRN

from PRNet.utils.write import write_obj_with_colors

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

PRNET_MAX_IMAGE_SIZE = int(os.environ.get('PRNET_MAX_IMAGE_SIZE', '5000000'))

from httplib import HTTPException

def validate_request(environ):
    path = environ['PATH_INFO']
    if environ['REQUEST_METHOD'] != 'POST' or path != '/':
        raise HTTPException('405 Method Not Allowed')

    content_length = int(environ.get('CONTENT_LENGTH', '-1'))
    if content_length == -1:
        raise HTTPException('411 Length Required')
    elif content_length > PRNET_MAX_IMAGE_SIZE:
        raise HTTPException('413 Payload Too Large')

def read_file_chunks(file_path):
    with open(file_path, 'rb') as f:
        while True:
            file_data = f.read(32768)
            if file_data is None or len(file_data) == 0:
                break
            yield file_data

def handle_request(environ, start_response):
    try:
        validate_request(environ)
        forms, files = parse_form_data(environ)
        img = files['image']
        imgfile=tempdir.join(img.filename)
        img.save_as(imgfile)
        modelfile=prnet(imgfile)
        filesize = os.stat(modelfile).st_size
        fname = modelfile.split('/')[-1]
        response_headers = [
                    ('Content-Type', 'application/octet-stream'),
                    ('Content-Length', str(filesize)),
                    ('Content-Disposition', 'attachment; filename="%s"' % fname)
                ]
        start_response('200 OK', response_headers)
        for file_chunk in read_file_chunks(modelfile):
            yield file_chunk
    except HTTPException as e:
        start_response(e[0], ())