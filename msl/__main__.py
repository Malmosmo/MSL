from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

from .compiler import Compiler


class Path(type(pathlib.Path())):
    def substitute(self, __old: pathlib._P, __new: pathlib._P) -> pathlib._P:
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


def loadMcMeta(config: dict) -> dict:
    metaPath = config["basePath"] / "pack.mcmeta"

    if os.path.isfile(metaPath):
        with open(metaPath, "rb") as file:
            metaConfig = json.load(file)

        if "msl" in metaConfig:
            if not "srcDir" in metaConfig["msl"]:
                print("No source directory in pack.mcmeta")
                sys.exit()

            if not "dstDir" in metaConfig["msl"]:
                print("No destination directory in pack.mcmeta")
                sys.exit()

            return {
                "srcDir": Path(metaConfig["msl"]["srcDir"]),
                "dstDir": Path(metaConfig["msl"]["dstDir"])
            }

        print("msl config not found in pack.mcmeta")
        sys.exit()

    print("could not find 'pack.mcmeta', are you sure you are in your datapack folder?")
    sys.exit()


def createDatapack(config: dict):
    datapackPath = config["minecraft"] / "saves" / config["world"] / "datapacks" / config["datapack"]

    if datapackPath.is_dir():
        if input(f"datapack '{config['datapack']}' already exists! Are you sure u want to override? (y/N) ") == "y":
            (datapackPath / "data/minecraft/tags/functions").mkdir(parents=True, exist_ok=True)
            (datapackPath / "msl").mkdir(parents=True, exist_ok=True)

            with open(datapackPath / "pack.mcmeta", "w") as file:
                json.dump({
                    "pack": {
                        "pack_format": 7,
                        "description": "Created by MSL Compiler"
                    },
                    "msl": {
                        "srcDir": str(datapackPath / "msl"),
                        "dstDir": str(datapackPath / "data")
                    }
                }, file, indent=4)

        else:
            sys.exit()


def createNamespace(config: dict):
    namespace = config["namespace"]
    namespacePath = Path(config["srcDir"]) / namespace

    if not namespacePath.is_dir():
        namespacePath.mkdir(parents=True, exist_ok=True)

    else:
        if input(f"namespace '{namespace}' already exists! Are you sure u want to proceed? (y/N) ") != "y":
            pass

        else:
            sys.exit()

    with open(namespacePath / "main.msl", "w") as file:
        file.write(f"//> main_{namespace}\n")

    with open(namespacePath / "init.msl", "w") as file:
        file.write(f"//> init_{namespace}\n")

    mcPath = config["basePath"] / "data/minecraft/tags/functions"

    for fileName, function in zip(["load.json", "tick.json"], ["init", "main"]):
        content = {
            "values": []
        }
        filePath = mcPath / fileName

        if filePath.is_file():
            with open(filePath, "rb") as file:
                fileContent = file.read()

                if len(fileContent) > 0:
                    content = json.loads(fileContent)

        content["values"].append(f"{namespace}:{function}")

        with open(filePath, "w") as file:
            json.dump(content, file, indent=4)


def compileNamespace(config: dict, namespace: str) -> None:
    for root, _, files in os.walk(namespace):
        for fileName in files:
            rootPath = Path(root)
            filePath = rootPath / fileName

            dstFilePath = filePath.substitute(namespace, namespace / "functions")
            dstFilePath = dstFilePath.substitute(config["srcDir"], config["dstDir"]).with_suffix(".mcfunction")

            dstFilePath.parent.mkdir(parents=True, exist_ok=True)

            print(f"\033[33mcompiling\033[0m {filePath}... ", end="")

            error = Compiler.compile(filePath, dstFilePath)

            if error:
                print("\033[31mfailed\033[0m")
                error.raiseError()
                break

            else:
                print("\033[92msuccess\033[0m")


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

    config["basePath"] = Path(os.getcwd())

    if config["mode"] == "create":
        if config["world"] and config["datapack"]:
            if not config["minecraft"]:
                config["minecraft"] = Path(os.getenv("APPDATA")) / ".minecraft"

            else:
                config["minecraft"] = Path(config["minecraft"])

            createDatapack(config)

        else:
            print("Missing world name or datapack name")

    else:
        config |= loadMcMeta(config)

        if config["mode"] == "new":
            if config["namespace"]:
                createNamespace(config)

            else:
                print("please provide a namespace with '-n NAMESPACE'")

        elif config["mode"] == "compile":
            if config["namespace"]:
                compileNamespace(config, config["srcDir"] / config["namespace"])

            else:
                for namespace in os.listdir(config["srcDir"]):
                    compileNamespace(config, config["srcDir"] / namespace)
