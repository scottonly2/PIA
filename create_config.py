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

def list_imgs(directory):
    print("listing images in ", directory)
    list_to_return = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.jpg') or file.endswith(".jpeg") or file.endswith(".png"):
                list_to_return.append( os.path.splitext(file)[0] )
    return list_to_return



class CustomDumper(yaml.SafeDumper):
    pass

def mask_sim_range_representer(dumper, data):
    print(dumper.represented_objects)
    if isinstance(data, list) and 'mask_sim_range' in dumper.represented_objects:
        print("SIM")
        return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=True)
    print("NOT SIM")
    return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=True)
    # return yaml.SafeDumper.represent_sequence(dumper, data)

# Add custom representer only for 'mask_sim_range'
CustomDumper.add_representer(list, mask_sim_range_representer)


class Config:
    def __init__(self,  as_name, input_name, prompts,
                 n_prompt, mask_sim_range,
                 path, db_or_lora):
        self.base = 'example/config/base.yaml'
        self.as_name = as_name
        self.prompts = prompts
        self.n_prompt = n_prompt
        self.input_name = input_name
        self.mask_sim_range =( [int(x) for x in mask_sim_range.split()])
        self.use_lora=False
        self.use_db = False
        self.lora_path = ""
        self.db_path = "models/DreamBooth_LoRA/realisticVisionV51_v51VAE.safetensors"
        self.global_seed = abs(hash(as_name))
        if db_or_lora:
            self.use_db = True
        else:
            self.use_lora= True
            self.lora_path = path
        pass

    def to_yaml_data(self):
        cfg =  {
            "base": self.base,
            "prompts": self.prompts,
            "n_prompt": self.n_prompt,
            "validation_data": {
                "input_name": self.input_name,
                "validation_input_path": img_root,
                "save_path": result_root,
                "mask_sim_range": self.mask_sim_range,
            },
            "generate": {
                "use_lora": self.use_lora,
                "lora_path": self.lora_path,
                "use_db": self.use_db,
                "db_path": self.db_path,
                "global_seed": self.global_seed,
                "lora_alpha": 0.8
            }
        }
        print("CFG as DICT:", cfg)
        return yaml.dump(data=cfg, indent=2, Dumper=CustomDumper, default_flow_style=None)

@app.route("/")
def root():
    return render_template("root.html", configs = list_config_yaml(config_root))

@app.route("/mf")
def mf():
    host = request.host
    return render_template("mf.html",
        host = host[:host.index(':')])


@app.route("/create", methods=['GET'])
def create_form():
    data ={
        "validation_data": {
            "input_name": '',
            "mask_sim_range": [0]
        },
        "prompts":[[]],
        "n_prompt":[],
        "mask_sim_range":[0]
    }
    sim = data['validation_data']['mask_sim_range']
    return render_template("create_form.html",
                           imgs = list_imgs(img_root),
                           as_name='',
                           pmpts="",
                           cfgyaml=data,
                           sim =' '.join([str(p) for p in sim])
                           )

@app.route("/load")
def load():
    cfg = request.args['cfg']
    with open(cfg, 'r') as file:
        data = yaml.safe_load(file)
        pmpts = '\r\n'.join( ['\r\n'.join([ l.strip() for l in inner_list]) for inner_list in data.get("prompts") ] ).strip()
        sim = data['validation_data']['mask_sim_range']
    as_name=cfg[len(config_root):cfg.index('.yaml')]

    return render_template("create_form.html", imgs=list_imgs(img_root),
                           as_name=as_name,
                           cfgyaml=data,
                           pmpts =pmpts,
                           sim=' '.join([str(p) for p in sim]))


@app.route("/create",  methods=['POST'])
def do_create():
    as_name = request.form['as_name']
    img = request.form['img']
    prompts = request.form['prompts']
    if prompts :
        prompts= [prompts.splitlines()]
    n_prompts = request.form['n_prompt']
    if n_prompts:
        n_prompts = n_prompts.splitlines()
    mask_sim_range= request.form['mask_sim_range']
    b = Config(as_name=as_name, input_name=img, prompts=prompts,
               n_prompt=n_prompts, mask_sim_range=mask_sim_range,
               db_or_lora=True, path='')
    d =  b.to_yaml_data()
    with open(os.path.join(config_root, as_name+'.yaml'), 'w') as file:
        file.write(d)
    print(d)
    return d

@app.route("/check")
def check_sub():
    key = request.args.get("p")
    found: subprocess.Popen = None
    found = processed.get(key)
    if found :
        poll_result = found.poll()
        print(f"Checking {key} {poll_result} {found}")
        allines = processed.get(key+"_all_lines")

        stdout = found.stdout.readline()
        if allines :
            allines.append(f"{stdout}")
        else:
            allines=[f"{stdout}"]
        processed[key + "_all_lines"]=allines
        return render_template("check.html", key_to_check=key, done=poll_result, lines=allines)

    return "No such subprocess"

@app.route("/run", methods=['POST'])
def run_config():
    config_2_run = request.form['config']
    act = request.form['act']
    print("To run", config_2_run)
    key = f"{config_2_run}_{act}_{time.time()}"
    try:
        cmd = ["python3" , f"{act}.py", "--config", config_2_run]
        print(cmd)
        output = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        processed[key]= output
        processed[key + "_all_lines"] = [f"Started at {time.time()}"]
        return render_template("check.html", key_to_check=key, done=False, lines=[])
    except subprocess.SubprocessError as e:
        return f"ERROR: {e}\r\n {e.output}"
    return f"OK :{output}"
if __name__=="__main__":
    app.run(debug=True, port=8199, host="0.0.0.0")