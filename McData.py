from __future__ import annotations

import argparse
import base64
import json
import os
import pathlib
import sys
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from compiler import Compiler, parser

VERSION = 7
DESCRIPTION = "Created by MSL"
IMAGE = "iVBORw0KGgoAAAANSUhEUgAAAA4AAAAOCAYAAAAfSC3RAAABhWlDQ1BJQ0MgcHJvZmlsZQAAKJF9kT1Iw0AcxV9TpaItDlYQcchQnSyIFnWUKhbBQmkrtOpgcukXNGlIWlwcBdeCgx+LVQcXZ10dXAVB8APEzc1J0UVK/F9SaBHjwXE/3t173L0DhEaZqWbXBKBqVSMZi4qZ7Kroe0UfAhhEBDMSM/V4ajEN1/F1Dw9f78I8y/3cnyOg5EwGeETiOaYbVeIN4unNqs55nzjIipJCfE48btAFiR+5Ljv8xrlgs8Azg0Y6OU8cJBYLHSx3MCsaKnGEOKSoGuULGYcVzluc1XKNte7JX+jPaSsprtMcQQxLiCMBETJqKKGMKsK0aqSYSNJ+1MU/bPsT5JLJVQIjxwIqUCHZfvA/+N2tmZ+adJL8UaD7xbI+RgHfLtCsW9b3sWU1TwDvM3Cltf2VBjD7SXq9rYWOgP5t4OK6rcl7wOUOMPSkS4ZkS16aQj4PvJ/RN2WBgVugd83prbWP0wcgTV0t3wAHh8BYgbLXXd7d09nbv2da/f0ACGBy49LMaX0AAAAGYktHRAD/AP8A/6C9p5MAAAAJcEhZcwAACxMAAAsTAQCanBgAAAAHdElNRQflCw0VOBwWlEhyAAAA2ElEQVQoz63RIUhDYRiF4ecXw8WwImLQgVos5oHJLsJYMJhMNkGGUTDYRYQF60CwmcQ8QRDMFosu3AURkSFckCG/Qa5scDHsetrhnI+XjxMgfXqOhjS/tBiGfVE+YUxNQpqmf5aK8nLEz8EAZFkGbjudkZ/e+32QJEl5YoAYY4TpmVlwur89Uto7boO315efoxBCOeLFyWGEj68pjXodLK+ugce7G9BuHZhbWAFbzaOSO/a6D6BSrf0GOSlXpVrT697/0445aX2jYXNnt7B4ftZyfZW7y/GJ3yYWPhgqbUlpAAAAAElFTkSuQmCC"


class FileHandler(FileSystemEventHandler):
    def __init__(self, config):
        self.config = config
        self.last_modified = time.time()

    def on_modified(self, event):
        if time.time() - self.last_modified < 1:
            return
        else:
            self.last_modified = time.time()

        compile_(self.config)


class Path(type(pathlib.Path())):
    def replace_sub(self, __old: pathlib._P, __new: pathlib._P) -> pathlib._P:
        return Path(str(self).replace(str(__old), str(__new)))


class Parser(argparse.ArgumentParser):
    def print_help(self, file=None) -> None:
        print("""Usage for the MSL Compiler
    msl mode [-h] [-v] [-w WORLD] [-d DATAPACK] [-n NAMESPACE] [-m MINECRAFT]
    
    -v          show version
    -h          show this help message

Commands:
    create      creates a new datapack
        -w      world name in which the datapack is created (required)
        -d      name of the datapack (required)

        -m      path to your '.minecraft' folder (optional)
    
    new         creates a new namespace
        -n      namespace (required)

    compile     compiles all *.msl Files
        -n      specifies a namespace, only this namespace is compiled (optional)

    run         ...

Examples:
    msl -h
    msl create -w myWorld -d myDatapack
    msl new -n myNamespace
    msl compile
    msl compile -n myNamespace""")

    def _check_value(self, action, value):
        if action.choices is not None and value not in action.choices:
            print(f"unkown mode: {value}")
            print(f"see '{self.prog} -h' for more information")
            sys.exit(2)

    def error(self, message):
        print(f"Unkown arguments... try '{self.prog} -h'")
        sys.exit(2)


def loadConfigPaths(config):
    configPath = config["basePath"] / "pack.mcmeta"

    if os.path.isfile(configPath):
        with open(configPath, "rb") as file:
            jsonConfig = json.load(file)

        if "msl" in jsonConfig:
            if "srcDir" in jsonConfig["msl"]:
                srcDirPath = Path(jsonConfig["msl"]["srcDir"])

            else:
                print("No source directory in pack.mcmeta")
                sys.exit()

            if "dstDir" in jsonConfig["msl"]:
                dstDirPath = Path(jsonConfig["msl"]["dstDir"])

            else:
                print("No destination directory in pack.mcmeta")
                sys.exit()

        else:
            print("msl config not found in pack.mcmeta")
            sys.exit()

    else:
        print("could not find 'pack.mcmeta', are you sure you are in your datapack folder?")
        sys.exit()

    return srcDirPath, dstDirPath


def create_datapack(config):
    path = config["minecraft"] / "saves" / config["world"] / "datapacks" / config["datapack"]

    if path.is_dir():
        if input(f"datapack '{config['datapack']}' already exists! Are you sure u want to proceed? (y/N) ") == "N":
            sys.exit()

    (path / "data/minecraft/tags/functions").mkdir(parents=True, exist_ok=True)
    (path / "msl").mkdir(parents=True, exist_ok=True)

    with open(path / "pack.mcmeta", "w") as file:
        json.dump({
            "pack": {
                "pack_format": VERSION,
                "description": DESCRIPTION
            },
            "msl": {
                "srcDir": str(path / "msl"),
                "dstDir": str(path / "data")
            }
        }, file, indent=4)

    with open(path / "pack.png", "wb") as file:
        file.write(base64.b64decode(IMAGE))


def new_namespace(config):
    namespace = config["namespace"]
    namespacePath = Path(config["srcDir"]) / namespace

    if namespacePath.is_dir():
        if input(f"namespace '{namespace}' already exists! Are you sure u want to proceed? (y/N) ") == "N":
            sys.exit()

    namespacePath.mkdir(parents=True, exist_ok=True)

    with open(namespacePath / "main.msl", "w") as file:
        file.write(f"//> main_{namespace}\n")

    with open(namespacePath / "init.msl", "w") as file:
        file.write(f"//> init_{namespace}\n")

    mcPath = config["basePath"] / "data/minecraft/tags/functions"

    for fileName, name in zip(["load.json", "tick.json"], ["init", "main"]):
        content = {
            "values": []
        }
        filePath = mcPath / fileName

        if filePath.is_file():
            with open(filePath, "rb") as file:
                fileContent = file.read()
                if len(fileContent) > 0:
                    content = json.loads(fileContent)

        content["values"].append(f"{namespace}:{name}")

        with open(filePath, "w") as file:
            json.dump(content, file, indent=4)


def compile_(config):
    if config["namespace"]:
        namespacePaths = [config["srcDir"] / config["namespace"]]

    else:
        namespacePaths = [config["srcDir"] / namespace for namespace in os.listdir(config["srcDir"])]

    compile_namespaces(config, namespacePaths, config["srcDir"], config["dstDir"])


def compile_namespaces(config, namespaces, srcDirPath, dstDirPath):
    for namespacePath in namespaces:
        for root, _, files in os.walk(namespacePath):
            for name in files:
                rootPath = Path(root)
                srcFilePath = rootPath / name

                dstFilePath = srcFilePath.replace_sub(namespacePath, namespacePath / "functions")
                dstFilePath = dstFilePath.replace_sub(srcDirPath, dstDirPath).with_suffix(".mcfunction")

                dstFilePath.parent.mkdir(parents=True, exist_ok=True)

                print(f"\033[33mcompiling\033[0m {srcFilePath.replace_sub(config['basePath'], Path('.'))}... ", end="")

                error = Compiler.compile(srcFilePath, dstFilePath)

                if error:
                    print("\033[31mfailed\033[0m")
                    error.raiseError()
                    break

                else:
                    print("\033[92msuccess\033[0m")


def run(config):
    if config["namespace"]:
        compilePath = config["srcDir"] / config["namespace"]

    else:
        compilePath = config["srcDir"]

    event_handler = FileHandler(config)
    observer = Observer()
    observer.schedule(event_handler, path=str(compilePath), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        print("interrupt!")
        observer.stop()
    observer.join()


if __name__ == "__main__":
    parser = Parser(prog="msl", add_help=False)
    parser.version = "MSL 1.0.1"
    parser.add_argument('mode', metavar='mode', type=str, choices=['create', 'new', "compile", "run"])
    parser.add_argument('-w', '--world', metavar='world', type=str)
    parser.add_argument('-d', '--datapack', metavar='datapack', type=str)
    parser.add_argument('-m', '--minecraft', metavar='minecraft', type=str)
    parser.add_argument('-n', '--namespace', metavar='namespace', type=str)
    parser.add_argument('-h', '--help', action='help')
    parser.add_argument('-v', action='version')

    args = parser.parse_args()
    config = vars(args)

    #   = Path(os.getcwd()
    # )
    # config["basePath"] = Path("...AppData\Roaming\.minecraft\saves\NEW\datapacks\ray")  # TODO: CHANGE!

    if config["mode"] == "create":
        if config["world"] and config["datapack"]:
            if not config["minecraft"]:
                config["minecraft"] = Path(os.getenv("APPDATA")) / ".minecraft"

            else:
                config["minecraft"] = Path(config["minecraft"])

            create_datapack(config)

        else:
            print("Missing world name or datapack name")

    else:
        srcDir, dstDir = loadConfigPaths(config)

        config["srcDir"] = srcDir
        config["dstDir"] = dstDir

        if config["mode"] == "new":
            if config["namespace"]:
                new_namespace(config)

            else:
                print("please provide a namespace with '-n NAMESPACE'")

        elif config["mode"] == "compile":
            compile_(config)

        elif config["mode"] == "run":
            run(config)
