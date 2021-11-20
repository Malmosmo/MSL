from rply import LexerGenerator


class Lexer:
    def __init__(self, token_dict: dict, ignore: str) -> None:
        self.lg = LexerGenerator()
        self.token_dict = token_dict
        self.ignore = ignore
        self.lexer = self.init()

    def init(self):
        for key, value in self.token_dict.items():
            self.lg.add(key, value)

        self.lg.ignore(self.ignore)

        return self.lg.build()

    def lex(self, text: str):
        return self.lexer.lex(text)
