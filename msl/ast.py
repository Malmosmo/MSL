from __future__ import annotations

from .errors import NameError, ValueError

import re
from pathlib import Path
from typing import Tuple

from rply.token import BaseBox, SourcePosition

WRITE_COMMENTS = True
MAX_REC_LIMIT = 10
REGEX = re.compile(r"\$\([_a-zA-Z][_a-zA-Z0-9]{0,31}\)")


class RTResult:
    def __init__(self) -> None:
        self.value = None
        self.error = None

    def register(self, result: RTResult):
        if result.error:
            self.error = result.error

        return result.value

    def success(self, value):
        self.value = value
        return self

    def failure(self, error):
        self.error = error
        return self


class Context:
    def __init__(self, srcFile: str, dstFile: str, src: str, parent: Context = None) -> None:
        self.srcFile = srcFile
        self.dstFile = dstFile
        self.src = src
        self.variables = {}
        self.scores = {}
        self.parent = parent

    def isVariable(self, name: str) -> bool:
        result = name in self.variables

        if not result and self.parent:
            return self.parent.isVariable(name)

        return result

    def getVariable(self, name: str) -> str | None:
        result = self.variables.get(name, None)

        if result is None and self.parent:
            return self.parent.getVariable(name)

        return result

    def isScore(self, name: str) -> bool:
        result = name in self.scores

        if not result and self.parent:
            return self.parent.isScore(name)

        return result

    def getScore(self, name: str) -> Tuple[str, str] | Tuple[None, None]:
        result = self.scores.get(name, (None, None))

        if result == (None, None) and self.parent:
            return self.parent.getScore(name)

        return result


class NullValue:
    def __str__(self) -> str:
        return f"null"


NULL = NullValue()


class MinecraftCommand:
    def __init__(self, value: str) -> None:
        self.value = value

    def toStr(self):
        return self.value


class ExecuteCommand:
    def __init__(self, value: str) -> None:
        self.value = value

    def toStr(self):
        return "execute " + self.value


class MinecraftComment:
    def __init__(self, value: str) -> None:
        self.value = value

    def toStr(self):
        return self.value


class MinecraftCommandList:
    def __init__(self) -> None:
        self.commands = []

    def add(self, command) -> None:
        self.commands.append(command)

    def extend(self, commandList) -> None:
        self.commands.extend(commandList.commands)

    def toStr(self):
        return "\n".join(command.toStr() for command in self.commands)


##################################################
# Nodes
##################################################
class Node(BaseBox):
    def __init__(self, value: Node | str, position: SourcePosition) -> None:
        self.value = value
        self.position = position

    def rep(self) -> str:
        if isinstance(self.value, Node):
            return f"{self.__class__.__name__}({self.value.rep()})"

        else:
            return f"{self.__class__.__name__}({self.value})"

    def getsourcepos(self) -> SourcePosition:
        return self.position

    def interpret(self, context: Context) -> RTResult:
        return RTResult()


##################################################
# Program
##################################################
class ProgramNode(Node):
    def interpret(self, context: Context) -> RTResult:
        return self.value.interpret(context)


##################################################
# Comment
##################################################
class CommentNode(Node):
    def rep(self) -> str:
        return f"{self.__class__.__name__}({self.value})"

    def interpret(self, context: Context) -> RTResult:
        result = RTResult()

        if WRITE_COMMENTS:
            comment = self.value.lstrip("/*\n ").rstrip("*/\n ")
            comments = comment.split("\n")

            if comments[0].startswith(">"):
                comments[0] = comments[0].lower()

            else:
                comments[0] = " " + comments[0]

            comments = "\n# ".join(comments)

            return result.success(MinecraftComment("#" + comments))

        return result.success(NULL)


##################################################
# Block
##################################################
class BlockNode(Node):
    def __init__(self, value: Node, position: SourcePosition) -> None:
        self.block = [value]
        self.position = position

    def add(self, value: Node) -> None:
        self.block.append(value)

    def rep(self) -> str:
        return f"{self.__class__.__name__}([{', '.join((element.rep() for element in self.block))}])"

    def interpret(self, context: Context) -> RTResult:
        result = RTResult()

        commands = MinecraftCommandList()

        for element in self.block:
            value = result.register(element.interpret(context))

            if result.error:
                return result

            if isinstance(value, (MinecraftComment, ExecuteCommand, MinecraftCommand)):
                commands.add(value)

            elif isinstance(value, MinecraftCommandList):
                commands.extend(value)

        return result.success(commands)


##################################################
# Minecraft
##################################################
class FuncNode(Node):
    def __init__(self, name: str, body: Node, position: SourcePosition) -> None:
        self.name = name[1:-1]
        self.body = body
        self.position = position

    def rep(self) -> str:
        return f"{self.__class__.__name__}({self.name}, {self.body.rep()})"

    def interpret(self, context: Context) -> RTResult:
        result = RTResult()

        commands = result.register(self.body.interpret(context))

        if result.error:
            return result

        path = Path(context.dstFile)
        dstPath = path.parent / (path.name.replace(path.stem, self.name))

        with open(dstPath, "w") as file:
            file.write(commands.toStr())

        return result.success(NULL)


class ScoreDeclNode(Node):
    def __init__(self, name: str, scoreboard: str, scoreboard_name: str, position: SourcePosition) -> None:
        self.name = name
        self.scoreboard = scoreboard
        self.scoreboard_name = scoreboard_name
        self.position = position

    def rep(self):
        return f"{self.__class__.__name__}({self.name}, {self.scoreboard}, {self.scoreboard_name})"

    def interpret(self, context: Context) -> RTResult:
        result = RTResult()

        if not context.isScore(self.name):
            context.scores[self.name] = [self.scoreboard, self.scoreboard_name]

            return result.success(NULL)

        return result.failure(NameError(
            self.position,
            context.srcFile,
            context.src,
            f"unable to redeclare score '{self.name}'"
        ))


class ScoreInitNode(Node):
    def __init__(self, decl: Node, value: Node, position: SourcePosition) -> None:
        self.decl = decl
        super().__init__(value, position)

    def rep(self):
        return f"{self.__class__.__name__}({self.decl.rep()}, {self.value.rep()})"

    def interpret(self, context: Context) -> RTResult:
        result = RTResult()

        result.register(self.decl.interpret(context))

        if result.error:
            return result

        value = result.register(self.value.interpret(context))

        if result.error:
            return result

        scoreboard, scoreboard_name = context.getScore(self.decl.name)

        return result.success(MinecraftCommand(f"scoreboard players set {scoreboard_name} {scoreboard} {value}"))


class GroupNode(Node):
    def __init__(self, specifier: Node, body: Node, position: SourcePosition) -> None:
        self.specifier = specifier
        self.body = body
        self.position = position

    def rep(self) -> str:
        return f"{self.__class__.__name__}({self.specifier.rep()}, {self.body.rep()})"

    def interpret(self, context: Context) -> RTResult:
        result = RTResult()

        specifier = result.register(self.specifier.interpret(context))

        if result.error:
            return result

        value = result.register(self.body.interpret(context))

        if result.error:
            return result

        commands = MinecraftCommandList()

        if isinstance(value, MinecraftCommandList):
            for command in value.commands:
                if isinstance(command, MinecraftCommand):
                    commands.add(
                        ExecuteCommand(f"{specifier} run {command.value}")
                    )

                elif isinstance(command, ExecuteCommand):
                    commands.add(
                        ExecuteCommand(f"{specifier} {command.value}")
                    )

                elif isinstance(command, MinecraftComment):
                    commands.add(command)

        else:
            print("Big Error!")

        return result.success(commands)


class GroupSpecNode(Node):
    def __init__(self, keyword: str, target: str, position: SourcePosition) -> None:
        self.value = f"{keyword} {target[1:-1]}"
        self.position = position

    def append(self, other: GroupSpecNode) -> None:
        self.value += " " + other.value

    def rep(self) -> str:
        return f"{self.__class__.__name__}({self.value})"

    def interpret(self, context: Context) -> RTResult:
        result = RTResult()
        return result.success(self.value)


class McCmdNode(Node):
    def __init__(self, value: str, position: SourcePosition) -> None:
        self.loop = True
        self.ctr = 0
        super().__init__(value, position)

    def interpret(self, context: Context) -> str:
        result = RTResult()
        string = self.value

        while self.loop and self.ctr < MAX_REC_LIMIT:
            self.loop = False
            self.ctr += 1

            string = re.sub(REGEX, lambda match: self.replace(match, context), string)

        self.loop = True

        if self.ctr >= MAX_REC_LIMIT:
            return result.failure("Max recursion error!")

        self.ctr = 0

        return result.success(MinecraftCommand(string))

    def replace(self, match: re.Match, context: Context) -> str:
        self.loop = True

        start, end = match.span()
        var = match.string[start + 2:end - 1]

        value = context.get_var(var)

        if value is not None:
            return str(value)

        return var


##################################################
# Variables
##################################################
class VariableAssignNode(Node):
    def __init__(self, name: str, value: Node, position: SourcePosition) -> None:
        self.name = name
        super().__init__(value, position)

    def rep(self) -> str:
        return f"{self.__class__.__name__}({self.name}, {self.value.rep()})"

    def interpret(self, context: Context) -> RTResult:
        result = RTResult()

        value = result.register(self.value.interpret(context))

        if result.error:
            return result

        if context.isScore(self.name):
            scoreboard, scoreboard_name = context.getScore(self.name)

            if isinstance(value, str):
                scoreboard_2, scoreboard_name_2 = context.getScore(value)

                return result.success(MinecraftCommand(f"scoreboard players operation {scoreboard_name} {scoreboard} = {scoreboard_name_2} {scoreboard_2}"))

            return result.success(MinecraftCommand(f"scoreboard players set {scoreboard_name} {scoreboard} {value}"))

        context.variables[self.name] = value

        return result.success(NULL)


class VariableAccessNode(Node):
    def __init__(self, name: str, position: SourcePosition) -> None:
        self.name = name
        self.position = position

    def rep(self) -> str:
        return f"{self.__class__.__name__}({self.name})"

    def interpret(self, context: Context) -> RTResult:
        result = RTResult()

        if context.isVariable(self.name):
            value = context.getVariable(self.name)

            return result.success(value)

        elif context.isScore(self.name):
            return result.success(self.name)

        return result.failure(NameError(
            self.position,
            context.srcFile,
            context.src,
            f"variable or score '{self.name}' not found"
        ))


class VariableIncrementNode(Node):
    def __init__(self, name: str, position: SourcePosition) -> None:
        self.name = name
        self.position = position

    def rep(self) -> str:
        return f"{self.__class__.__name__}({self.name})"

    def interpret(self, context: Context) -> RTResult:
        result = RTResult()

        if context.isVariable(self.name):
            value = context.getVariable(self.name)

            context.variables[self.name] = value + 1

            return result.success(NULL)

        elif context.isScore(self.name):
            scoreboard, scoreboard_name = context.getScore(self.name)

            return result.success(MinecraftCommand(f"scoreboard players add {scoreboard_name} {scoreboard} 1"))

        return result.failure(NameError(
            self.position,
            context.srcFile,
            context.src,
            f"variable or score '{self.name}' not found"
        ))


class VariableDecrementNode(Node):
    def __init__(self, name: str, position: SourcePosition) -> None:
        self.name = name
        self.position = position

    def rep(self) -> str:
        return f"{self.__class__.__name__}({self.name})"

    def interpret(self, context: Context) -> RTResult:
        result = RTResult()

        if context.isVariable(self.name):
            value = context.getVariable(self.name)

            context.variables[self.name] = value - 1

            return result.success(NULL)

        elif context.isScore(self.name):
            scoreboard, scoreboard_name = context.getScore(self.name)

            return result.success(MinecraftCommand(f"scoreboard players remove {scoreboard_name} {scoreboard} 1"))

        return result.failure(NameError(
            self.position,
            context.srcFile,
            context.src,
            f"variable or score '{self.name}' not found"
        ))


##################################################
# Self Expr Nodes
##################################################
class ScoreOpNode(Node):
    def __init__(self, target: str, source: str, position: SourcePosition) -> None:
        self.target = target
        self.source = source
        self.position = position

    def rep(self) -> str:
        return f"{self.__class__.__name__}({self.target}, {self.source})"


class ScoreOpLeftNode(ScoreOpNode):
    def interpret(self, context: Context) -> RTResult:
        result = RTResult()

        if context.isScore(self.target):
            if context.isScore(self.source):
                scoreboard_target, scoreboard_name_target = context.getScore(self.target)
                scoreboard_source, scoreboard_name_source = context.getScore(self.source)

                return result.success(MinecraftCommand(f"scoreboard players operation {scoreboard_name_target} {scoreboard_target} < {scoreboard_name_source} {scoreboard_source}"))

            return result.failure(NameError(
                self.position,
                context.srcFile,
                context.src,
                f"score '{self.source}' not found"
            ))

        return result.failure(NameError(
            self.position,
            context.srcFile,
            context.src,
            f"score '{self.target}' not found"
        ))


class ScoreOpRightNode(ScoreOpNode):
    def interpret(self, context: Context) -> RTResult:
        result = RTResult()

        if context.isScore(self.target):
            if context.isScore(self.source):
                scoreboard_target, scoreboard_name_target = context.getScore(self.target)
                scoreboard_source, scoreboard_name_source = context.getScore(self.source)

                return result.success(MinecraftCommand(f"scoreboard players operation {scoreboard_name_target} {scoreboard_target} > {scoreboard_name_source} {scoreboard_source}"))

            return result.failure(NameError(
                self.position,
                context.srcFile,
                context.src,
                f"score '{self.source}' not found"
            ))

        return result.failure(NameError(
            self.position,
            context.srcFile,
            context.src,
            f"score '{self.target}' not found"
        ))


class ScoreOpSwapNode(ScoreOpNode):
    def interpret(self, context: Context) -> RTResult:
        result = RTResult()

        if context.isScore(self.target):
            if context.isScore(self.source):
                scoreboard_target, scoreboard_name_target = context.getScore(self.target)
                scoreboard_source, scoreboard_name_source = context.getScore(self.source)

                return result.success(MinecraftCommand(f"scoreboard players operation {scoreboard_name_target} {scoreboard_target} >< {scoreboard_name_source} {scoreboard_source}"))

            return result.failure(NameError(
                self.position,
                context.srcFile,
                context.src,
                f"score '{self.source}' not found"
            ))

        return result.failure(NameError(
            self.position,
            context.srcFile,
            context.src,
            f"score '{self.target}' not found"
        ))


##################################################
# Self Expr Nodes
##################################################
class SelfOpNode(Node):
    def __init__(self, name: str, value: Node, position: SourcePosition) -> None:
        self.name = name
        super().__init__(value, position)

    def rep(self) -> str:
        return f"{self.__class__.__name__}({self.name}, {self.value.rep()})"


class SelfAddNode(SelfOpNode):
    def interpret(self, context: Context) -> RTResult:
        result = RTResult()

        value = result.register(self.value.interpret(context))

        if result.error:
            return result

        if context.isVariable(self.name):
            _value = context.getVariable(self.name)

            context.variables[self.name] = _value + value
            return result.success(NULL)

        elif context.isScore(self.name):
            scoreboard, scoreboard_name = context.getScore(self.name)

            if isinstance(value, str):
                scoreboard_2, scoreboard_name_2 = context.getScore(value)

                return result.success(MinecraftCommand(f"scoreboard players operation {scoreboard_name} {scoreboard} += {scoreboard_name_2} {scoreboard_2}"))

            else:
                return result.success(MinecraftCommand(f"scoreboard players add {scoreboard_name} {scoreboard} {value}"))

        return result.failure(NameError(
            self.position,
            context.srcFile,
            context.src,
            f"variable or score '{self.name}' not found"
        ))


class SelfSubNode(SelfOpNode):
    def interpret(self, context: Context) -> RTResult:
        result = RTResult()

        value = result.register(self.value.interpret(context))

        if result.error:
            return result

        if context.isVariable(self.name):
            _value = context.getVariable(self.name)

            context.variables[self.name] = _value - value

            return result.success(NULL)

        elif context.isScore(self.name):
            scoreboard, scoreboard_name = context.getScore(self.name)

            if isinstance(value, str):
                scoreboard_2, scoreboard_name_2 = context.getScore(value)

                return result.success(MinecraftCommand(f"scoreboard players operation {scoreboard_name} {scoreboard} -= {scoreboard_name_2} {scoreboard_2}"))

            else:
                return result.success(MinecraftCommand(f"scoreboard players remove {scoreboard_name} {scoreboard} {value}"))

        return result.failure(NameError(
            self.position,
            context.srcFile,
            context.src,
            f"variable or score '{self.name}' not found"
        ))


class SelfMultNode(SelfOpNode):
    def interpret(self, context: Context) -> RTResult:
        result = RTResult()

        value = result.register(self.value.interpret(context))

        if result.error:
            return result

        if context.isVariable(self.name):
            _value = context.getVariable(self.name)

            context.variables[self.name] = _value * value

            return result.success(NULL)

        elif context.isScore(self.name):
            scoreboard, scoreboard_name = context.getScore(self.name)

            if isinstance(value, str):
                scoreboard_2, scoreboard_name_2 = context.getScore(value)

                return result.success(MinecraftCommand(f"scoreboard players operation {scoreboard_name} {scoreboard} *= {scoreboard_name_2} {scoreboard_2}"))

            return result.failure(ValueError(
                self.position,
                context.srcFile,
                context.src,
                f"cannot multiply '{value}' to score '{self.name}'"
            ))

        return result.failure(NameError(
            self.position,
            context.srcFile,
            context.src,
            f"variable or score '{self.name}' not found"
        ))


class SelfDivNode(SelfOpNode):
    def interpret(self, context: Context) -> RTResult:
        result = RTResult()

        value = result.register(self.value.interpret(context))

        if result.error:
            return result

        if context.isVariable(self.name):
            _value = context.getVariable(self.name)

            context.variables[self.name] = _value / value

            return result.success(NULL)

        elif context.isScore(self.name):
            scoreboard, scoreboard_name = context.getScore(self.name)

            if isinstance(value, str):
                scoreboard_2, scoreboard_name_2 = context.getScore(value)

                return result.success(MinecraftCommand(f"scoreboard players operation {scoreboard_name} {scoreboard} /= {scoreboard_name_2} {scoreboard_2}"))

            return result.failure(ValueError(
                self.position,
                context.srcFile,
                context.src,
                f"cannot divide score '{self.name}' by '{value}'"
            ))

        return result.failure(NameError(
            self.position,
            context.srcFile,
            context.src,
            f"variable or score '{self.name}' not found"
        ))


##################################################
# BinaryOpNode
##################################################
class BinaryOpNode(Node):
    def __init__(self, left: Node, right: Node, position: SourcePosition) -> None:
        self.left = left
        self.right = right
        self.position = position

    def rep(self) -> str:
        return f"{self.__class__.__name__}({self.left.rep()}, {self.right.rep()})"

    def interpret(self, context: Context) -> RTResult:
        result = RTResult()

        left = result.register(self.left.interpret(context))

        if result.error:
            return result

        right = result.register(self.right.interpret(context))

        if result.error:
            return result

        return result.success(self.operation(left, right))


class BinaryMultNode(BinaryOpNode):
    def operation(self, left, right):
        return left * right


class BinaryDivNode(BinaryOpNode):
    def operation(self, left, right):
        return left / right


class BinaryAddNode(BinaryOpNode):
    def operation(self, left, right):
        return left + right


class BinarySubNode(BinaryOpNode):
    def operation(self, left, right):
        return left - right


class BinaryLENode(BinaryOpNode):
    def operation(self, left, right):
        return left < right


class BinaryGENode(BinaryOpNode):
    def operation(self, left, right):
        return left > right


class BinaryLETNode(BinaryOpNode):
    def operation(self, left, right):
        return left <= right


class BinaryGETNode(BinaryOpNode):
    def operation(self, left, right):
        return left >= right


class BinaryEQNode(BinaryOpNode):
    def operation(self, left, right):
        return left == right


class BinaryNEQNode(BinaryOpNode):
    def operation(self, left, right):
        return left != right


class BinaryAndNode(BinaryOpNode):
    def operation(self, left, right):
        return left and right


class BinaryOrNode(BinaryOpNode):
    def operation(self, left, right):
        return left or right


##################################################
# UnaryOp
##################################################
class UnaryAddNode(Node):
    def interpret(self, context: Context) -> RTResult:
        result = RTResult()

        value = result.register(self.value.interpret(context))

        if result.error:
            return result

        return result.success(+value)


class UnarySubNode(Node):
    def interpret(self, context: Context) -> RTResult:
        result = RTResult()

        value = result.register(self.value.interpret(context))

        if result.error:
            return result

        return result.success(-value)


class UnaryNotNode(Node):
    def interpret(self, context: Context) -> RTResult:
        result = RTResult()

        value = result.register(self.value.interpret(context))

        if result.error:
            return result

        return result.success(not value)


##################################################
# Literals
##################################################
class IntegerNode(Node):
    def interpret(self, context: Context) -> RTResult:
        result = RTResult()

        return result.success(self.value)


class FloatNode(Node):
    def interpret(self, context: Context) -> RTResult:
        result = RTResult()

        return result.success(self.value)


class StringNode(Node):
    def __init__(self, value: str, position: SourcePosition) -> None:
        super().__init__(value[1:-1], position)

    def interpret(self, context: Context) -> RTResult:
        result = RTResult()

        return result.success(self.value)


class BooleanNode(Node):
    def interpret(self, context: Context) -> RTResult:
        result = RTResult()

        return result.success(self.value)


##################################################
# For
##################################################
class ForNode(Node):
    def __init__(self, assgn: Node, condition: Node, increment: Node, body: Node, position: SourcePosition) -> None:
        self.assgn = assgn
        self.condition = condition
        self.increment = increment
        self.body = body
        self.position = position

    def rep(self) -> str:
        return f"{self.__class__.__name__}({self.assgn.rep()}, {self.condition.rep()}, {self.increment.rep()}, {self.body.rep()}"

    def interpret(self, context: Context) -> RTResult:
        result = RTResult()

        result.register(self.assgn.interpret(context))

        if result.error:
            return result

        condition = result.register(self.condition.interpret(context))

        if result.error:
            return result

        commands = MinecraftCommandList()

        while condition:
            value = result.register(self.body.interpret(context))

            if result.error:
                return result

            if isinstance(value, (MinecraftComment, ExecuteCommand, MinecraftCommand)):
                commands.add(value)

            elif isinstance(value, MinecraftCommandList):
                commands.extend(value)

            result.register(self.increment.interpret(context))

            if result.error:
                return result

            condition = result.register(self.condition.interpret(context))

            if result.error:
                return result

        return result.success(commands)


##################################################
# While
##################################################
class WhileNode(Node):
    def __init__(self, condition: Node, body: Node, position: SourcePosition) -> None:
        self.condition = condition
        self.body = body
        self.position = position

    def rep(self) -> str:
        return f"{self.__class__.__name__}({self.condition.rep()}, {self.body.rep()}"

    def interpret(self, context: Context) -> RTResult:
        result = RTResult()

        condition = result.register(self.condition.interpret(context))

        if result.error:
            return result

        commands = MinecraftCommandList()

        while condition:
            value = result.register(self.body.interpret(context))

            if result.error:
                return result

            if isinstance(value, (MinecraftComment, ExecuteCommand, MinecraftCommand)):
                commands.add(value)

            elif isinstance(value, MinecraftCommandList):
                commands.extend(value)

            condition = result.register(self.condition.interpret(context))

            if result.error:
                return result

        return result.success(commands)
