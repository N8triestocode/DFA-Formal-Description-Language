import token

import ply.lex as lex
#Necessary Tokens involved in the lexer
tokens = ('IDEN', 'EQUALS', 'LPAREN', 'LBRACE', 
          'COMMA', 'RPAREN','RBRACE', 'DELTA', 'SIGMA', 
          'RARROW', 'NWLINE', 'ASTER', )
#Reserved words are defined in the reserved dictionary, 
#mapping various case variations of 'delta' and 'sigma' to their respective token types.
reserved = {
    'delta': 'DELTA',
    'Delta': 'DELTA',
    'DELTA': 'DELTA',
    'sigma': 'SIGMA',
    'Sigma': 'SIGMA',
    'SIGMA': 'SIGMA',
}

#test cases for the lexer, including various valid and invalid inputs to test the lexer's functionality and error handling.
tests = [
    #'delta',
    #'q0 = q1',
    #'δ(q1,ε)=q1',
    #'δ = Q * Σ → Q',
    #'deltas',
    #'a\n\n  b'
    #'q₀ = q₁',
    #'a\r\nb',
    #'δ = Q × Σ → Q',
    #'12',
    #'1abc',
    #'123',
    #'\n\na',
    #'a',
    #'a\n',
    #'a @ b',
    #'!comment test',
    #''
]

#function to get tokens from the input text, handling leading newlines and appending an EOF token at the end. 
# It also collects any lexer errors encountered during tokenization.
def get_tokens(text):
    lexer_errors.clear()      
    lexer.lineno = 1
    lexer.input(text)

    result = []
    for tok in lexer:
        if tok.type == 'NWLINE' and len(result)==0:
            continue  # skip leading newlines
        else:
            result.append(tok)
    
    if result and result[-1].type != 'NWLINE':
        nlex = lex.LexToken()
        nlex.type = 'NWLINE'
        nlex.value = '\n'
        nlex.lineno = lexer.lineno
        nlex.lexpos=len(text)  
        result.append(nlex) 

    eof = lex.LexToken()
    eof.type = 'EOF'
    eof.value = None
    eof.lineno = lexer.lineno
    eof.lexpos=len(text)
    result.append(eof)

    return result, lexer_errors

#Token definitions for the lexer, specifying the regular expressions for each token type.
t_EQUALS = r'='
t_LPAREN = r'\('
t_LBRACE = r'\{'
t_COMMA = r','
t_RPAREN = r'\)'
t_RBRACE = r'\}'
t_DELTA = r'δ'
t_SIGMA = r'Σ'
t_RARROW = r'->|→'
t_ASTER = r'\*|×'

t_ignore = ' \t'
t_ignore_COMMENT = r'\![^\n]*'

#Error handling for the lexer, capturing illegal characters and their positions in the input text.
lexer_errors = []
def t_error(t):
    ch = t.value[0]
    message = f"Illegal character '{ch}' at line {t.lexer.lineno}, column {column(t.lexer.lexdata, t.lexpos)}"
    lexer_errors.append((message, t.lexer.lineno, column(t.lexer.lexdata, t.lexpos)))
    t.lexer.skip(1)

#Token definition for identifiers, which can be either a letter followed by letters or digits, or a single digit. It also checks if the identifier is a reserved word and assigns the appropriate token type.
def t_IDEN(t):
    r'[A-Za-z][A-Za-z0-9]*|[0-9]'
    t.type = reserved.get(t.value, 'IDEN')  # Check for reserved words
    return t

#Token definition for newlines, which can be either Unix-style or Windows-style line endings, and updates the line number in the lexer accordingly.
def t_NWLINE(t):
    r'(\r?\n[ \t]*)+'
    t.lexer.lineno += t.value.count("\n")
    return t

#Function to calculate the column number of a token based on its position in the input text, by finding the last newline character before the token's position and calculating the offset.
def column(lexdata, pos):
    last_nl = lexdata.rfind('\n', 0, pos)
    return pos - last_nl

#Build the lexer using the PLY library, which compiles the token definitions and prepares the lexer for use.
lexer = lex.lex()

#Function to run the lexer on a file, reading its contents, tokenizing it, and printing the resulting tokens and any errors encountered during tokenization.
def run_file(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    toks, errs = get_tokens(text)
    print("\n", path)
    print([t.type for t in toks])
    print("errors:", errs)

#Main block to execute the lexer on the test cases and specified files, printing the tokens and their details for each input text.
if __name__ == "__main__":
    for text in tests:
        print("\n", repr(text))
        toks, errs = get_tokens(text)
        for tok in toks:
            print("Token: ", tok.type,
                    "\tValue: ", repr(tok.value),
                    "\tLine: ", tok.lineno,
                    "\tColumn: ", column(lexer.lexdata, tok.lexpos))
    run_file("tests/format1.txt")
    run_file("tests/format2.txt")
            
