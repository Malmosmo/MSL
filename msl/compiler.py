from __future__ import annotations
from .ast import Context

from .lexer import Lexer
from .parser import Parser, ParserState
from .preprocesser import PreProcesser, MINECRAFT_KEYWORDS


MINECRAFT = {
    "EXEC": "(align|anchored|as|at|facing|if|in|positioned|rotated|unless|store)(?!\w)",

    "COMMENT": r"(/\*([^*]|[\r\n]|(\*+([^*/]|[\r\n])))*\*+/)|(//.*)",
    "MCCMD": "(" + "|".join(MINECRAFT_KEYWORDS) + r").*(?!\n)",

    "SCORE": r"score(?!\w)",
}

KEYWORDS = {
    "FUNC": r"func(?!\w)",

    "FOR": r"for(?!\w)",
    "WHILE": r"while(?!\w)",
}

OPERATORS = {
    "PLUSEQ": r"\+\=",
    "MINUSEQ": r"\-\=",
    "MULTEQ": r"\*\=",
    "DIVEQ": r"\/\=",

    "PLUS": r"\+",
    "MINUS": r"\-",
    "MULT": r"\*",
    "DIV": r"\/",

    "<<": r"\<\<",
    ">>": r"\>\>",
    "><": r"\>\<",

    "==": r"\=\=",
    ">=": r"\>\=",
    "<=": r"\<\=",
    "!=": r"\!\=",
    "<": r"\<",
    ">": r"\>",
    "!": r"\!",

    "AND": r"\&\&",
    "OR": r"\|\|",

    "=": r"\=",
}

LITERALS = {
    "FLOAT": r"\d[.]\d+",
    "INTEGER": r"\d+",
    "STRING": r'\"[^\"]*\"',
    "BOOLEAN": r"(?<!\w)(true|false)(?!\w)"
}

PUNCTUATORS = {
    "(": r"\(",
    ")": r"\)",

    "{": r"\{",
    "}": r"\}",

    ",": r"\,",
    ":": r"\:",

    ";": r"\;",
}

IDENTIFIERS = {
    "IDENTIFIER": r"[_a-zA-Z][_a-zA-Z0-9]{0,31}",
}

TOKENTYPES = MINECRAFT | KEYWORDS | OPERATORS | LITERALS | PUNCTUATORS | IDENTIFIERS


##################################################
# Compiler
##################################################
class Compiler:
    @staticmethod
    def compile(inFile: str, outFile: str):
        with open(inFile, 'r') as file:
            source = file.read()

        if len(source) > 0:

            processor = PreProcesser(inFile)
            source = processor.include(source)
            source = processor.add_endings(source)

            # lexer
            lexer = Lexer(TOKENTYPES, r'[ \n\t\r\f\v]+')
            tokens = lexer.lex(source)

            # parser
            state = ParserState()
            parser = Parser(list(TOKENTYPES), [
                ('right', ['PLUS', 'MINUS']),
                ('left', ['MULT', 'DIV']),
                ('left', ['AND', 'OR', ]),
            ], inFile, source)

            # ast
            ast = parser.parse(tokens, state)

            context = Context(inFile, outFile, source)
            result = ast.interpret(context)

            if result.error:
                return result.error

            commands = result.value

            with open(outFile, "w") as file:
                file.write(commands.toStr())

        return 0
