import sys

import numpy as np
import pytest

from bookscan.remote_ocr import RemoteOCR
from bookscan.vision import OCR


def worker_command(body):
    return [sys.executable, "-u", "-c", body]


READY = '''import sys,json
def send(value):
    print('BOOKSCAN_RPC '+json.dumps(value),flush=True)
print('library log',flush=True)
send({'detection_name':'det','recognition_name':'rec','hashes':{'detection':'a','recognition':'b'}})
'''


def test_remote_dispatch_and_lossless_transport():
    command = worker_command(READY + '''import base64,cv2,numpy as np
for line in sys.stdin:
    request=json.loads(line)
    image=cv2.imdecode(np.frombuffer(base64.b64decode(request['image']),dtype=np.uint8),1)
    send({'result':[str(image[0,0].tolist()),0.99] if request['operation']=='recognize' else [{'bbox':[0,0,image.shape[1],image.shape[0]]}]})
''')
    ocr = OCR({'models': {'remote_command': command}})
    try:
        assert isinstance(ocr, RemoteOCR)
        image = np.full((10,20,3), [17,29,83], dtype=np.uint8)
        assert ocr.recognize(image) == ('[17, 29, 83]', .99)
        assert ocr.detect(image) == [{'bbox': [0,0,20,10]}]
        assert ocr.recognize(np.zeros((0,0,3),dtype=np.uint8)) == ('',None)
        assert ocr.hashes == {'detection':'a','recognition':'b'}
    finally:
        ocr.close()
    assert ocr.process.poll() == 0


def test_remote_error_closes_worker():
    ocr = RemoteOCR({'models': {'remote_command': worker_command(
        READY + "sys.stdin.readline(); send({'error':'GPU unavailable'})")}})
    with pytest.raises(RuntimeError, match='GPU unavailable'):
        ocr.detect(np.zeros((10,10,3),dtype=np.uint8))
    assert ocr.process.poll() is not None


def test_remote_timeout():
    with pytest.raises(TimeoutError):
        RemoteOCR({'models': {'remote_timeout': .1, 'remote_command':
            worker_command('import time; time.sleep(10)')}})
