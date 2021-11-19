import sys

from rply.token import SourcePosition


class BaseError(Exception):
    def __init__(self, position: SourcePosition, file: str, source: str, message: str) -> None:
        self.position = position
        self.file = file
        self.source = source.splitlines()
        self.message = message

    def raiseError(self):
        print(self)
        sys.exit()

    def __str__(self) -> str:
        result = "\n\033[95mError\033[0m:\n"

        if self.position is None:
            line_number = len(self.source)
            col_number = len(self.source[-1])

        else:
            line_number = self.position.lineno
            col_number = self.position.colno - 1

        result += f"  \033[36mFile \"{self.file}\", line {line_number}\033[0m\n"
        result += f"    {self.source[line_number - 1]}\n"
        result += "    " + " " * col_number + "\033[91m^\033[0m\n"
        result += f"\033[95m{self.__class__.__name__}\033[0m: {self.message}"

        return result


class SynatxError(BaseError):
    pass


class UnexpectedEndError(BaseError):
    pass


class NameError(BaseError):
    pass
