import time
from flask import Flask, request, jsonify, Response
import pickle
import json
import numpy as np
import base64
from PIL import Image
from io import BytesIO

# Communication to TensorFlow server via gRPC
from grpc.beta import implementations
import tensorflow as tf

# TensorFlow serving stuff to send messages
from tensorflow_serving.apis import predict_pb2
from tensorflow_serving.apis import prediction_service_pb2
from tensorflow.contrib.util import make_tensor_proto

app = Flask(__name__)

host = '35.244.20.1'
port = 443
channel = implementations.insecure_channel(host, port)
stub = prediction_service_pb2.beta_create_PredictionService_stub(channel)

f = open("imagenet_labels.txt", "r")
label_array = f.readlines()
f.close()
VGG_MEAN = [103.94, 116.78, 123.68]

def sendRequest(im):
    """

    """

    r = im[:, :, :, 0] - VGG_MEAN[0]
    g = im[:, :, :, 1] - VGG_MEAN[1]
    b = im[:, :, :, 2] - VGG_MEAN[2]
    im2 = np.stack([b, g, r], axis=-1)
    print(im2.shape)
    req = predict_pb2.PredictRequest()
    req.model_spec.name = 'vgg16_with_signature'
    req.model_spec.signature_name = 'serving_default'
    req.inputs['bgr'].CopyFrom(make_tensor_proto(im2, shape=[1, 224, 224, 3], dtype=tf.float32))
    result = stub.Predict(req, 60.0)
    # print(result)
    predictions = np.array(result.outputs['output_0'].float_val)
    max_val = np.argmax(predictions, axis=-1)
    return label_array[max_val], predictions[max_val], int(max_val)+1


@app.route('/ping')
def ping():
    """

    """

    print(request.get_json())
    return "pong"

@app.route('/image', methods=['POST'])
def api():
    """

    """

    img = Image.open(request.files.get("image"))
    numpy_img = np.array(img)
    nis = numpy_img.shape
    if nis[0] != nis[1]:
        if nis[0] > nis[1]:
            numpy_img = np.pad(numpy_img, [(0, 0), ((nis[0]-nis[1])//2, (nis[0]-nis[1]+1)//2), (0, 0)], 'constant')
        if nis[1] > nis[0]:
            numpy_img = np.pad(numpy_img, [((nis[1]-nis[0])//2, (nis[1]-nis[0]+1)//2), (0, 0), (0, 0)], 'constant')
    img = Image.fromarray(numpy_img)
    img = img.resize((224, 224), Image.NEAREST)
    # img.save("temp.png", "PNG")
    reshaped_im = np.array(img).reshape([1, 224, 224, 3])
    preds = sendRequest(reshaped_im)
    # print({"shape": list(numpy_im.shape)})
    result = json.dumps({"name": preds[0], "prob": preds[1], "value": preds[2]})
    resp = Response(result)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=443)
