from rply import ParserGenerator
from rply.token import Token

from .ast import *
from .errors import *


class ParserState:
    def __init__(self):
        pass

    def add_variable(self, var):
        self.variables.append(var)

    def add_constant(self, var):
        self.constants.append(var)


class Parser:
    def __init__(self, tokens: list, precedence: list, filename: str, source: str) -> None:
        self.pg = ParserGenerator(tokens, precedence)
        self.parser = self.init()
        self.filename = filename
        self.source = source

    def init(self):
        ##################################################
        # Program
        ##################################################
        @self.pg.production('program : stmtList')
        def prgm(state: ParserState, p):
            return ProgramNode(p[0], p[0].getsourcepos())

        ##################################################
        # Statment-List
        ##################################################
        @self.pg.production('stmtList : stmtList stmtFull')
        def stmtList_stmt(state: ParserState, p):
            block = p[0]
            block.add(p[1])

            return block

        @self.pg.production('stmtList : stmtFull')
        def stmtList(state: ParserState, p):
            return BlockNode(p[0], p[0].getsourcepos())

        @self.pg.production('stmtFull : stmt')
        @self.pg.production('stmtFull : func')
        def stmtFull(state: ParserState, p):
            return p[0]

        ##################################################
        # Block
        ##################################################
        @self.pg.production('block : block stmt')
        def block_stmt(state: ParserState, p):
            block = p[0]
            block.add(p[1])

            return block

        @self.pg.production('block : stmt')
        def block(state: ParserState, p):
            return BlockNode(p[0], p[0].getsourcepos())

        ##################################################
        # Statement
        ##################################################
        @self.pg.production('stmt : mccmd ;')
        def stmt(state: ParserState, p):
            return p[0]

        @self.pg.production('stmt : assgn ;')
        @self.pg.production('stmt : expr ;')
        @self.pg.production('stmt : group')
        @self.pg.production('stmt : for-expr')
        @self.pg.production('stmt : while-expr')
        def stmt_(state: ParserState, p):
            return p[0]

        @self.pg.production('stmt : COMMENT')
        def stmt_comment(state: ParserState, p):
            return CommentNode(p[0].getstr(), p[0].getsourcepos())

        ##################################################
        # Minecraft
        ##################################################
        @self.pg.production('func : FUNC STRING { block }')
        def func(state: ParserState, p):
            return FuncNode(p[1].getstr(), p[3], p[0].getsourcepos())

        @self.pg.production('mccmd : MCCMD')
        def mccmd(state: ParserState, p):
            return McCmdNode(p[0].getstr(), p[0].getsourcepos())

        @self.pg.production('mccmd : score-decl')
        @self.pg.production('mccmd : score-init')
        def mccmd_decl(state: ParserState, p):
            return p[0]

        # Scores
        @self.pg.production('score-decl : SCORE IDENTIFIER : IDENTIFIER')
        def score_decl(state: ParserState, p):
            return ScoreDeclNode(p[1].getstr(), p[3].getstr(), p[1].getstr(), p[0].getsourcepos())

        @self.pg.production('score-decl : SCORE IDENTIFIER : ( IDENTIFIER , IDENTIFIER )')
        def score_decl_1(state: ParserState, p):
            return ScoreDeclNode(p[1].getstr(), p[4].getstr(), p[6].getstr(), p[0].getsourcepos())

        @self.pg.production('score-init : score-decl = expr')
        def score_init(state: ParserState, p):
            return ScoreInitNode(p[0], p[2], p[0].getsourcepos())

        # group
        @self.pg.production('group : group-specifier { block }')
        def group(state: ParserState, p):
            return GroupNode(p[0], p[2], p[0].getsourcepos())

        @self.pg.production('group-specifier : EXEC ( STRING )')
        def group_spec(state: ParserState, p):
            return GroupSpecNode(p[0].getstr(), p[2].getstr(), p[0].getsourcepos())

        @self.pg.production('group-specifier : group-specifier , EXEC ( STRING )')
        def group_spec_rec(state: ParserState, p):
            p[0].append(
                GroupSpecNode(p[2].getstr(), p[4].getstr(), p[0].getsourcepos())
            )

            return p[0]

        ##################################################
        # Variables
        ##################################################
        @self.pg.production('assgn : decl')
        def assgn(state: ParserState, p):
            return p[0]

        @self.pg.production('assgn : IDENTIFIER PLUS PLUS')
        def assgn_incr(state: ParserState, p):
            return VariableIncrementNode(p[0].getstr(), p[0].getsourcepos())

        @self.pg.production('assgn : IDENTIFIER MINUS MINUS')
        def assgn_decr(state: ParserState, p):
            return VariableDecrementNode(p[0].getstr(), p[0].getsourcepos())

        @self.pg.production('decl : IDENTIFIER = expr')
        def decl(state: ParserState, p):
            return VariableAssignNode(p[0].getstr(), p[2], p[0].getsourcepos())

        ##################################################
        # Expression
        ##################################################
        @self.pg.production('expr : comp')
        def expr(state: ParserState, p):
            return p[0]

        @self.pg.production('expr : expr AND expr')
        def expr_and(state: ParserState, p):
            return BinaryAndNode(p[0], p[2], p[0].getsourcepos())

        @self.pg.production('expr : expr OR expr')
        def expr_or(state: ParserState, p):
            return BinaryOrNode(p[0], p[2], p[0].getsourcepos())

        ##################################################
        # comp-expr
        ##################################################
        @self.pg.production('comp : arith')
        def comp(state: ParserState, p):
            return p[0]

        @self.pg.production('comp : ! comp')
        def comp_not(state: ParserState, p):
            return UnaryNotNode(p[1], p[0].getsourcepos())

        @self.pg.production('comp : arith < arith')
        def comp_le(state: ParserState, p):
            return BinaryLENode(p[0], p[2], p[0].getsourcepos())

        @self.pg.production('comp : arith > arith')
        def comp_ge(state: ParserState, p):
            return BinaryGENode(p[0], p[2], p[0].getsourcepos())

        @self.pg.production('comp : arith <= arith')
        def comp_let(state: ParserState, p):
            return BinaryLETNode(p[0], p[2], p[0].getsourcepos())

        @self.pg.production('comp : arith >= arith')
        def comp_get(state: ParserState, p):
            return BinaryGETNode(p[0], p[2], p[0].getsourcepos())

        @self.pg.production('comp : arith == arith')
        def comp_eq(state: ParserState, p):
            return BinaryEQNode(p[0], p[2], p[0].getsourcepos())

        @self.pg.production('comp : arith != arith')
        def comp_neq(state: ParserState, p):
            return BinaryNEQNode(p[0], p[2], p[0].getsourcepos())

        ##################################################
        # arith-expr
        ##################################################
        @self.pg.production('arith : term')
        def arith(state: ParserState, p):
            return p[0]

        @self.pg.production('arith : arith PLUS arith')
        def arith_plus(state: ParserState, p):
            return BinaryAddNode(p[0], p[2], p[0].getsourcepos())

        @self.pg.production('arith : arith MINUS arith')
        def arith_minus(state: ParserState, p):
            return BinarySubNode(p[0], p[2], p[0].getsourcepos())

        ##################################################
        # Term
        ##################################################
        @self.pg.production('term : factor')
        def term(state: ParserState, p):
            return p[0]

        @self.pg.production('term : term MULT term')
        def term_mul(state: ParserState, p):
            return BinaryMultNode(p[0], p[2], p[0].getsourcepos())

        @self.pg.production('term : term DIV term')
        def term_div(state: ParserState, p):
            return BinaryDivNode(p[0], p[2], p[0].getsourcepos())

        ##################################################
        # Factor
        ##################################################
        @self.pg.production('factor : atom')
        def fac_lit(state: ParserState, p):
            return p[0]

        @self.pg.production('factor : PLUS factor')
        def fac_add(state: ParserState, p):
            return UnaryAddNode(p[1], p[0].getsourcepos())

        @self.pg.production('factor : MINUS factor')
        def fac_sub(state: ParserState, p):
            return UnarySubNode(p[1], p[0].getsourcepos())

        ##################################################
        # atom
        ##################################################
        @self.pg.production('atom : literal')
        def atom(state: ParserState, p):
            return p[0]

        @self.pg.production('atom : ( expr )')
        def atom_expr(state: ParserState, p):
            return p[1]

        @self.pg.production('atom : IDENTIFIER')
        def atom_var(state: ParserState, p):
            return VariableAccessNode(p[0].getstr(), p[0].getsourcepos())

        ##################################################
        # Literals
        ##################################################
        @self.pg.production('literal : INTEGER')
        def literal_int(state: ParserState, p):
            return IntegerNode(int(p[0].getstr()), p[0].getsourcepos())

        @self.pg.production('literal : FLOAT')
        def literal_float(state: ParserState, p):
            return FloatNode(float(p[0].getstr()), p[0].getsourcepos())

        @self.pg.production('literal : STRING')
        def literal_str(state: ParserState, p):
            return StringNode(p[0].getstr(), p[0].getsourcepos())

        @self.pg.production('literal : BOOLEAN')
        def literal_bool(state: ParserState, p):
            boolean = p[0].getstr()

            if boolean == "true":
                boolean = 1

            else:
                boolean = 0

            return BooleanNode(bool(boolean), p[0].getsourcepos())

        ##################################################
        # For
        ##################################################
        @self.pg.production('for-expr : FOR ( decl ; expr ; assgn ) { block }')
        def for_expr(state: ParserState, p):
            return ForNode(p[2], p[4], p[6], p[9], p[0].getsourcepos())

        ##################################################
        # While
        ##################################################
        @self.pg.production('while-expr : WHILE ( expr ) { block }')
        def while_expr(state: ParserState, p):
            return WhileNode(p[2], p[5], p[0].getsourcepos())

        ##################################################
        # Errors
        ##################################################
        @self.pg.error
        def error_handler(state: ParserState, token: Token):
            pos = token.getsourcepos()

            if pos:
                SynatxError(
                    pos,
                    self.filename,
                    self.source,
                    f"Unexpected Token '{token.name}'"
                ).raiseError()

            elif token.gettokentype() == '$end':
                UnexpectedEndError(
                    pos,
                    self.filename,
                    self.source,
                    f"Unexpected End"
                ).raiseError()

            else:
                SynatxError(
                    None,
                    self.filename,
                    self.source,
                    f"Unexpected Token: {token.name}"
                ).raiseError()

        return self.pg.build()

    def parse(self, text: str, state: ParserState = None):
        return self.parser.parse(text, state)
