import json
import os
import time
import numpy as np
from multiprocessing import Process, Queue
from flask import Flask, send_from_directory, request, jsonify


app = Flask(__name__, static_folder='dist')

# 全局变量存储数据
latest_data = {"jawopen": 0.0, "mouthclose": 0.0, "mouthfunnel": 0.0, "mouthpucker": 0.0, "mouthstretchleft": 0.0,
               "mouthstretchright": 0.0, "mouthleft": 0.0, "mouthright": 0.0, "mouthsmile": 0.0,
               "mouthfrownleft": 0.0, "mouthfrownright": 0.0, "mouthshrugupper": 0.0, "mouthshruglower": 0.0,
               "mouthupperupleft": 0.0, "mouthupperupright": 0.0, "mouthlowerdownleft": 0.0, "mouthlowerdownright": 0.0,
               "mouthrollupper": 0.0, "mouthrolllower": 0.0, "mouthpressleft": 0.0, "mouthpressright": 0.0,
               "mouthcheekpuff": 0.0, "mouthdimpleleft": 0.0, "mouthdimpleright": 0.0,
               "headx": 0.0, "heady": 0.0, "headz": 0.0}

@app.route('/')
def index():
    return app.send_static_file('index.html')


@app.route('/assets/<path:path>')
def serve_static(path):
    return send_from_directory('./dist/assets', path)

@app.route('/api/send_mouth_y', methods=['POST'])
def receive_data():
    global latest_data
    try:
        data = request.get_json()
        if data and "reset" in data and data["reset"] == True:
            latest_data = {"jawopen": 0.0, "mouthclose": 0.0, "mouthfunnel": 0.0, "mouthpucker": 0.0, "mouthstretchleft": 0.0,
               "mouthstretchright": 0.0, "mouthleft": 0.0, "mouthright": 0.0, "mouthsmile": 0.0,
               "mouthfrownleft": 0.0, "mouthfrownright": 0.0, "mouthshrugupper": 0.0, "mouthshruglower": 0.0,
               "mouthupperupleft": 0.0, "mouthupperupright": 0.0, "mouthlowerdownleft": 0.0, "mouthlowerdownright": 0.0,
               "mouthrollupper": 0.0, "mouthrolllower": 0.0, "mouthpressleft": 0.0, "mouthpressright": 0.0,
               "mouthcheekpuff": 0.0, "mouthdimpleleft": 0.0, "mouthdimpleright": 0.0,
               "headx": 0.0, "heady": 0.0, "headz": 0.0} # 处理终止信号，重置数据
        elif data:
            latest_data = data
        else:
            latest_data = {"jawopen": 0.0, "mouthclose": 0.0, "mouthfunnel": 0.0, "mouthpucker": 0.0, "mouthstretchleft": 0.0,
               "mouthstretchright": 0.0, "mouthleft": 0.0, "mouthright": 0.0, "mouthsmile": 0.0,
               "mouthfrownleft": 0.0, "mouthfrownright": 0.0, "mouthshrugupper": 0.0, "mouthshruglower": 0.0,
               "mouthupperupleft": 0.0, "mouthupperupright": 0.0, "mouthlowerdownleft": 0.0, "mouthlowerdownright": 0.0,
               "mouthrollupper": 0.0, "mouthrolllower": 0.0, "mouthpressleft": 0.0, "mouthpressright": 0.0,
               "mouthcheekpuff": 0.0, "mouthdimpleleft": 0.0, "mouthdimpleright": 0.0,
               "headx": 0.0, "heady": 0.0, "headz": 0.0} # 保持默认值
    except Exception as e:
        print(f"Error occurred: {e}")
        latest_data = {"jawopen": 0.0, "mouthclose": 0.0, "mouthfunnel": 0.0, "mouthpucker": 0.0, "mouthstretchleft": 0.0,
               "mouthstretchright": 0.0, "mouthleft": 0.0, "mouthright": 0.0, "mouthsmile": 0.0,
               "mouthfrownleft": 0.0, "mouthfrownright": 0.0, "mouthshrugupper": 0.0, "mouthshruglower": 0.0,
               "mouthupperupleft": 0.0, "mouthupperupright": 0.0, "mouthlowerdownleft": 0.0, "mouthlowerdownright": 0.0,
               "mouthrollupper": 0.0, "mouthrolllower": 0.0, "mouthpressleft": 0.0, "mouthpressright": 0.0,
               "mouthcheekpuff": 0.0, "mouthdimpleleft": 0.0, "mouthdimpleright": 0.0,
               "headx": 0.0, "heady": 0.0, "headz": 0.0} # 保持默认值

    return jsonify({"status": "success"})

@app.route('/api/get_mouth_y')
def api_get_one_account():
    return jsonify(latest_data)

if __name__ == '__main__':
    app.run(port=4800, debug=True, host="0.0.0.0")