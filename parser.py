#Done by Scott Spence 2100755

from dataclasses import dataclass, field
from typing import List, NamedTuple, Optional, Tuple

#Takes in token list from lexer and original source text
#Parses it into a DFAProgram object, or returns errors if the input is invalid
from lexer import get_tokens, column as column_of

#catches errors in parsing and returns them to the IDE for display
class ParseError(Exception):

    def __init__(self, message, line, column):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(str(self))

    def __str__(self):
        return f"{self.message} at line {self.line}, column {self.column}"
    #returns tuple of error message(format the same as rest of program)
    def as_tuple(self):
        return (str(self), self.line, self.column)

#class for names that keeps track of their position in the source text
class Name(str):
    def __new__(cls, value, line=0, column=0):
        obj = super().__new__(cls, value)
        obj.line = line
        obj.column = column
        return obj

#one transition in the DFA plus line it comes from for errors 
class Transition(NamedTuple):
    state: Name
    symbol: Name
    target: Name
    position: Tuple[int, int]


@dataclass
#output of the parser; contains all the information about the DFA. 
class DFAProgram:
    #default values for the fields
    name: Optional[Name] = None          # M in  M = (...)
    format: int = 0                      # 1 (multi-line / table) or 2 (one-line)

    # Format 1 tuple-line placeholders:  M = (Q, Σ, δ, q0, F)
    states_ref: Optional[Name] = None    # Q
    start_ref: Optional[Name] = None     # q0
    finals_ref: Optional[Name] = None    # F

    # Components (both formats)
    states: List[Name] = field(default_factory=list)
    alphabet: List[Name] = field(default_factory=list)
    start: Optional[Name] = None
    finals: List[Name] = field(default_factory=list)

    # Format 1 definition lines: the placeholder written on the left/right
    #format 1 keeps placeholder names so sematic analysis can check that the right names are used in the right places
    states_name: Optional[Name] = None   # Q in  Q = {...}
    delta_domain: Optional[Name] = None  # Q in  δ = Q × Σ → Q  (left)
    delta_codomain: Optional[Name] = None  # Q in  δ = Q × Σ → Q (right)
    start_name: Optional[Name] = None    # q0 in  q0 = q1
    finals_name: Optional[Name] = None   # F in  F = {...}

    # Format 1 table: header symbols and rows of (state, [targets])
    table_header: List[Name] = field(default_factory=list)
    table_rows: List[Tuple[Name, List[Name]]] = field(default_factory=list)

    # Format 2 transitions
    transitions: List[Transition] = field(default_factory=list)


@dataclass
#what the parser returns to ide either a DFAProgram or a list of errors
class ParseResult:
    program: Optional[DFAProgram]
    lexical_errors: list            # [(message, line, column), ...]
    syntax_errors: list             # [(message, line, column), ...]

    @property
    def errors(self):
        return list(self.lexical_errors) + list(self.syntax_errors)

    @property
    #only returns true if the program is valid and there are no errors
    def ok(self):
        return self.program is not None and not self.errors

# aliases for token types so errors are easy to read 
TOKEN_DESC = {
    'IDEN': "a name",
    'EQUALS': "'='",
    'LPAREN': "'('",
    'RPAREN': "')'",
    'LBRACE': "'{'",
    'RBRACE': "'}'",
    'COMMA': "','",
    'DELTA': "'δ' (or 'delta')",
    'SIGMA': "'Σ' (or 'sigma')",
    'RARROW': "'->' or '→'",
    'ASTER': "'*' or '×'",
    'NWLINE': "end of line",
    'EOF': "end of file",
}

#Parser

#holds token list and position  every method reads tokens
class Parser:
    #tokens from get tokens and source text for working out columns 
    def __init__(self, tokens, text):
        self.tokens = tokens
        self.text = text
        #index of current token in the list
        self.position = 0

    #token helpers 

    def peek(self):
        #Current token, without consuming it. Never runs past EOF.
        return self.tokens[min(self.position, len(self.tokens) - 1)]

    def advance(self):
        #Consume and return the current token (EOF is never consumed).
        tok = self.peek()
        if tok.type != 'EOF':
            self.position += 1
        return tok

    #build a parse error at current token with message 
    def error_at(self, tok, message):
        return ParseError(message, tok.lineno, column_of(self.text, tok.lexpos))

    #how to describe a token in an error message; used by expect() and error_at()
    def describe(self, tok):
        if tok.type == 'EOF':
            return "end of file"
        if tok.type == 'NWLINE':
            return "end of line"
        return f"'{tok.value}'"

    def expect(self, token_type):
        #Consume a token of the given type or raise ParseError.
        tok = self.peek()
        if tok.type != token_type:
            message = (f"Expected {TOKEN_DESC.get(token_type, token_type)} "
                       f"but found {self.describe(tok)}")
            #hint when closed bracket is missing 
            if token_type in ('RBRACE', 'RPAREN'):
                message += " (check that every opening bracket is closed)"
            raise self.error_at(tok, message)
        return self.advance()

    def expect_name(self):
        #expect(IDEN), returned as a position-aware Name.
        tok = self.expect('IDEN')
        return Name(tok.value, tok.lineno, column_of(self.text, tok.lexpos))

    def skip_newlines(self):
        while self.peek().type == 'NWLINE':
            self.advance()

    #building blocks 

    #parse a list of names separated by commas, e.g. "q0, q1, q2"
    def parse_idenlist(self):
        """<idenlist> ::= IDEN (COMMA IDEN)*"""
        names = [self.expect_name()]
        #the while loop allows for zero or more additional names after the first
        while self.peek().type == 'COMMA':
            self.advance()
            names.append(self.expect_name())
        return names

    #parse a set of names enclosed in braces, e.g. "{q0, q1, q2}"
    def parse_set(self):
        """<set> ::= LBRACE [ <idenlist> ] RBRACE"""
        self.expect('LBRACE')
        names = []
        #only parse an idenlist if the next token is an IDEN; otherwise it's an empty set
        if self.peek().type == 'IDEN':
            names = self.parse_idenlist()
        self.expect('RBRACE')
        return names

    #Format 1 pieces 

    def parse_statedef(self):
        placeholder = self.expect_name()
        self.expect('EQUALS')
        return placeholder, self.parse_set()

    def parse_sigmadef(self):
        self.expect('SIGMA')
        self.expect('EQUALS')
        return self.parse_set()

    def parse_tranfunc(self):
        
        self.expect('DELTA')
        self.expect('EQUALS')
        domain = self.expect_name()
        self.expect('ASTER')
        self.expect('SIGMA')
        self.expect('RARROW')
        codomain = self.expect_name()
        return domain, codomain

    def parse_startdef(self):
      
        placeholder = self.expect_name()
        self.expect('EQUALS')
        return placeholder, self.expect_name()

    def parse_finaldef(self):
        
        placeholder = self.expect_name()
        self.expect('EQUALS')
        return placeholder, self.parse_set()

    def parse_tableheader(self):
       
        self.expect('DELTA')
        symbols = [self.expect_name()]
        while self.peek().type == 'IDEN':
            symbols.append(self.expect_name())
        self.expect('NWLINE')
        return symbols

    def parse_tablerow(self):
       
        state = self.expect_name()
        targets = []
        while self.peek().type == 'IDEN':
            targets.append(self.expect_name())
        self.expect('NWLINE')
        return state, targets

    def parse_table(self):
        
        header = self.parse_tableheader()
        rows = []
        while True:
            self.skip_newlines()
            if self.peek().type != 'IDEN':
                break
            rows.append(self.parse_tablerow())
        return header, rows
    #desugar the table into a list of transitions for format 1
    def desugar_table(self, prog):
        for state, targets in prog.table_rows:
            if len(targets) != len(prog.table_header):
                continue
            for symbol, target in zip(prog.table_header, targets):
                position = (target.line, target.column)
                prog.transitions.append(
                    Transition(state, symbol, target, position)
                )

    def parse_format1(self):
       
        prog = DFAProgram(format=1)

        #IDEN COMMA SIGMA COMMA DELTA COMMA IDEN COMMA IDEN RPAREN NWLINE
        prog.states_ref = self.expect_name()
        self.expect('COMMA')
        self.expect('SIGMA')
        self.expect('COMMA')
        self.expect('DELTA')
        self.expect('COMMA')
        prog.start_ref = self.expect_name()
        self.expect('COMMA')
        prog.finals_ref = self.expect_name()
        self.expect('RPAREN')
        self.expect('NWLINE')
        self.skip_newlines()

        prog.states_name, prog.states = self.parse_statedef()
        self.expect('NWLINE')
        self.skip_newlines()
        prog.alphabet = self.parse_sigmadef()
        self.expect('NWLINE')
        self.skip_newlines()
        prog.delta_domain, prog.delta_codomain = self.parse_tranfunc()
        self.expect('NWLINE')
        self.skip_newlines()
        prog.start_name, prog.start = self.parse_startdef()
        self.expect('NWLINE')
        self.skip_newlines()
        prog.finals_name, prog.finals = self.parse_finaldef()
        self.expect('NWLINE')
        self.skip_newlines()
        prog.table_header, prog.table_rows = self.parse_table()
        self.desugar_table(prog)
        return prog

    #Format 2 pieces 

    def parse_inlinetran(self):
     
        delta = self.expect('DELTA')
        position = (delta.lineno, column_of(self.text, delta.lexpos))
        self.expect('LPAREN')
        state = self.expect_name()
        self.expect('COMMA')
        symbol = self.expect_name()
        self.expect('RPAREN')
        self.expect('EQUALS')
        target = self.expect_name()
        if self.peek().type == 'NWLINE':
            self.advance()
        return Transition(state, symbol, target, position)

    def parse_format2(self):
        #<dfaformat2>; the LPAREN was already consumed by parse_program.
        prog = DFAProgram(format=2)

        # <set> COMMA <set> COMMA DELTA COMMA IDEN COMMA <set> RPAREN NWLINE
        prog.states = self.parse_set()
        self.expect('COMMA')
        prog.alphabet = self.parse_set()
        self.expect('COMMA')
        self.expect('DELTA')
        self.expect('COMMA')
        prog.start = self.expect_name()
        self.expect('COMMA')
        prog.finals = self.parse_set()
        self.expect('RPAREN')
        self.expect('NWLINE')
        self.skip_newlines()

        #<inlinetran>+  (one required, then loop while the next token is DELTA)
        prog.transitions.append(self.parse_inlinetran())
        while True:
            self.skip_newlines()
            if self.peek().type != 'DELTA':
                break
            prog.transitions.append(self.parse_inlinetran())
        return prog

    #Top level

    def parse_program(self):
    
        name = self.expect_name()
        self.expect('EQUALS')
        self.expect('LPAREN')

        nxt = self.peek()
        if nxt.type == 'IDEN':
            prog = self.parse_format1()
        elif nxt.type == 'LBRACE':
            prog = self.parse_format2()
        else:
            raise self.error_at(
                nxt,
                f"Expected a name (multi-line format) or '{{' (one-line format) "
                f"after '(' but found {self.describe(nxt)}")
        prog.name = name

        self.expect('EOF')   # anything left over is junk after the program
        return prog



#Wrapper for the IDE

def parse(text, parse_anyway=False):
    
    tokens, lex_errors = get_tokens(text)
    lex_errors = list(lex_errors)   # the lexer reuses one global list

    if lex_errors and not parse_anyway:
        return ParseResult(None, lex_errors, [])

    parser = Parser(tokens, text)
    try:
        program = parser.parse_program()
    except ParseError as err:
        return ParseResult(None, lex_errors, [err.as_tuple()])
    return ParseResult(program, lex_errors, [])
