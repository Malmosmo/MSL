from pathlib import Path
import re

MINECRAFT_KEYWORDS = [
    "advancement", "attribute", "ban", "ban-ip", "banlist", "bossbar", "clear", "clone", "data", "datapack", "debug", "defaultgamemode",
    "deop", "difficult", "effect", "enchant", "execute", "experience", "fill", "forceload", "function", "gamemode", "gamerule", "give",
    "help", "item", "jfr", "kick", "kill", "list", "locate", "locatebiome", "loot", "me", "msg", "op", "pardon", "pardon-ip", "particle",
    "playsound", "publish", "recipe", "reload", "save-all", "save-off", "save-on", "say", "schedule", "scoreboard", "seed", "setblock",
    "setidletimeout", "setworldspawn", "spawnpoint", "spectate", "spreadplayers", "stop", "stopsound", "summon", "tag", "team", "teammsg",
    "teleport", "tell", "tellraw", "time", "title", "tm", "tp", "trigger", "w", "weather", "whitelist", "worldborder", "xp"
]


class PreProcesser:
    def __init__(self, inFile: str) -> None:
        self.inFile = inFile

    def add_endings(self, source: str) -> str:
        lines = source.splitlines()

        comment = False

        for idx, line in enumerate(lines):
            line = line.rstrip("\n ")
            line = line.lstrip("\t ")

            if len(line) > 0:
                if line.startswith("/*"):
                    comment = True

                if not comment:
                    if line.startswith(tuple(MINECRAFT_KEYWORDS)):
                        line += ";"

                    elif not line.endswith(tuple("{(},;")) and not line.startswith("//"):
                        line += ";"

            if line.endswith("*/"):
                comment = False

            lines[idx] = line

        return "\n".join(lines) + "\n"

    def replace(self, match: re.Match) -> str:
        start, end = match.span()
        _, name = match.string[start:end].split(" ")
        name = name[1:-1]
        path = Path(self.inFile).parent / name
        if path.is_file():
            with open(path, "r") as file:
                return file.read()

    def include(self, source: str) -> str:
        regex = re.compile(r"include <[\w\.]+>")

        lines = source.splitlines(True)
        for idx, line in enumerate(lines):
            if line.startswith("include"):
                line = re.sub(regex, self.replace, line)

            lines[idx] = line

        return "".join(lines)
