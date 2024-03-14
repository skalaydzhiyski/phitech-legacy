from phitech.logger import logger_lib as logger
from phitech.const import *
from dotted_dict import DottedDict as dotdict
from ib_insync import IB, util

import os
import yaml

# TODO: this is chaotic, ideally these should be in separate directories with
# .       appropriate names.


def validate_def_filename(fname):
    if len(fname) == 0 or fname.startswith("."):
        return False
    split = fname.split(".")
    if len(split) != 2:
        return False
    name, ext = split[0], split[1]
    return name[0].isalpha() and ext[-1].isalpha()  # there must be a better way.


def parse_yaml(path, dot=True):
    with open(path, "r") as f:
        res = yaml.full_load(f)
    return dotdict(res) if dot else res


def run_formatter():
    os.system("black .")


def make_dot_children(input_dict):
    return {key: dotdict(children) for key, children in input_dict.items()}


def mkdir_or_replace(dirname):
    if os.path.exists(dirname):
        os.system(f"rm -rf {dirname}")
    os.mkdir(dirname)


def run_tmux_cmd(tmux_id, cmd):
    os.system(f"tmux send-keys -t {tmux_id} C-c")
    os.system(f'tmux send-keys -t {tmux_id} "{cmd}" Enter')
