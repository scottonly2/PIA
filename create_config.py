import random

import requests
import yaml
from flask import Flask, render_template, request
import sys
import os
import subprocess
import time

processed = {

}


app = Flask(__name__)

data = {
    "base": "",
    "prompts": [],
    "n_prompt":[],
    "validation_data": {
      "input_name": 'lighthouse',
      "validation_input_path": 'example/img',
      "save_path": 'example/result',
   "mask_sim_range": [0]
    }

}
base_root = sys.argv[1]
config_root=f"{base_root}/config/"
img_root = f"{base_root}/img/"
result_root=f"{base_root}/result/"

print("Using base root=", base_root)

def list_config_yaml(directory):
    yaml_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.yaml'):
                yaml_files.append(os.path.join(root, file))
    return yaml_files


@app.route("/")
def root():
    return render_template("root.html", configs = list_config_yaml(config_root))

@app.route("/check?p=<key>")
def check_sub(key):
    print(f"Checking {key}")
    return "OK"

@app.route("/run", methods=['POST'])
def run_config():
    config_2_run = request.form['config']
    act = request.form['act']
    print("To run", config_2_run)
    key = f"{config_2_run}"
    try:
        cmd = ["python3" , f"{act}.py", "--config", config_2_run]
        print(cmd)
        output = subprocess.Popen(cmd)
        processed[key]= output
        return f"Check <a href='/check?p={key}'>Check</a>"
    except subprocess.SubprocessError as e:
        return f"ERROR: {e}\r\n {e.output}"
    return f"OK :{output}"
if __name__=="__main__":
    app.run(debug=True, port=8199, host="0.0.0.0")