#Done by Joshaun Gibson
"""
Semantic Analyzer for the DFA Formal Description Language.
Performs semantic checks on the parsed AST (Program object).
"""
class SemanticError(Exception):
    def __init__(self, message, line=1, column=1):
        super().__init__(message)
        self.message = message
        self.line = line
        self.column = column

    def __str__(self):
        return f"Semantic Error at line {self.line}, column {self.column}: {self.message}"


class SemanticResult:
    def __init__(self):
        self.ok = True
        self.errors = []  # List of tuples: (message, line, column)

    def add_error(self, message, line=1, column=1):
        self.ok = False
        self.errors.append((message, line, column))


def analyze_semantics(prog):
    """
    Performs comprehensive semantic analysis on a parsed DFA Program.
    """
    result = SemanticResult()

    # 1. Extract sets and components
    states = set(prog.states)
    alphabet = set(prog.alphabet)
    start_state = prog.start
    final_states = set(prog.finals)

    # Check that Q is non-empty
    if not states:
        result.add_error("Semantic Error: Set of states (Q) cannot be empty.", 1, 1)

    # Check that start state is in Q
    if start_state and start_state not in states:
        result.add_error(f"Semantic Error: Start state '{start_state}' is not defined in Q.", 1, 1)

    # Check that all final states are in Q
    for f_state in final_states:
        if f_state not in states:
            result.add_error(f"Semantic Error: Final state '{f_state}' is not defined in Q.", 1, 1)

    # Map transitions: state -> {symbol: target_state}
    transition_map = {q: {} for q in states}

    if prog.format == 1:
        # Format 1: Table rows
        header_symbols = prog.table_header

        # Validate header symbols belong to alphabet Σ
        for sym in header_symbols:
            if sym not in alphabet:
                result.add_error(f"Semantic Error: Transition table header symbol '{sym}' is not in alphabet Σ.", 1, 1)

        for row in prog.table_rows:
            state, targets = row
            if state not in states:
                result.add_error(f"Semantic Error: State '{state}' in transition table is not defined in Q.", 1, 1)
                continue

            if len(targets) != len(header_symbols):
                result.add_error(
                    f"Semantic Error: State '{state}' has {len(targets)} targets, but table header defines {len(header_symbols)} symbols.",
                    1, 1)
                continue

            for sym, target in zip(header_symbols, targets):
                if target not in states:
                    result.add_error(
                        f"Semantic Error: Target state '{target}' for transition ({state}, {sym}) is not defined in Q.",
                        1, 1)

                # Check for duplicate / non-deterministic transitions
                if sym in transition_map[state]:
                    result.add_error(
                        f"Semantic Error: Non-deterministic transition detected. Multiple transitions for ({state}, {sym}).",
                        1, 1)
                else:
                    transition_map[state][sym] = target

    elif prog.format == 2:
        # Format 2: Inline transitions
        for tr in prog.transitions:
            st = tr.state
            sym = tr.symbol
            target = tr.target
            line, col = tr.position

            # Check epsilon rule
            if sym in ('ε', 'eps', 'epsilon'):
                result.add_error(
                    f"Semantic Error: Illegal epsilon transition δ({st}, {sym}) = {target}. DFAs cannot have epsilon transitions.",
                    line, col)
                continue

            if st not in states:
                result.add_error(f"Semantic Error: Source state '{st}' in transition is not defined in Q.", line, col)
            if sym not in alphabet:
                result.add_error(f"Semantic Error: Symbol '{sym}' in transition is not in alphabet Σ.", line, col)
            if target not in states:
                result.add_error(f"Semantic Error: Target state '{target}' in transition is not defined in Q.", line,
                                 col)

            # Check determinism
            if st in transition_map:
                if sym in transition_map[st]:
                    result.add_error(f"Semantic Error: Non-deterministic transition detected for ({st}, {sym}).", line,
                                     col)
                else:
                    transition_map[st][sym] = target

    # 3. Completeness Check: Every state must have a transition defined for EVERY symbol in alphabet Σ
    for q in states:
        for sym in alphabet:
            if sym not in transition_map.get(q, {}):
                result.add_error(
                    f"Semantic Error: Missing transition for state '{q}' on symbol '{sym}'. In a complete DFA, all transitions must be defined.",
                    1, 1)

    return result