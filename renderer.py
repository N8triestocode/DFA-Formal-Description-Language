#Shared assisted by LLM
def dfa_to_dot(dfa):
    # Merge parallel edges: (src, dst) -> [symbols]
    edges = {}
    for (src, sym), dst in dfa["transitions"].items():
        edges.setdefault((src, dst), []).append(sym)

    lines = [
        "digraph DFA {",
        "  rankdir=LR;",
        '  node [fontname="Helvetica", style=filled, fillcolor="#FF4B4B"];',
        '  __start [shape=point, label="", width=0.2, style=invis];',
    ]
    for s in dfa["states"]:
        shape = "doublecircle" if s in dfa["finals"] else "circle"
        lines.append(f'  "{s}" [shape={shape}];')
    lines.append(f'  __start -> "{dfa["start"]}";')

    order = {sym: i for i, sym in enumerate(dfa["alphabet"])}
    for (src, dst), syms in edges.items():
        label = ",".join(sorted(syms, key=lambda x: order.get(x, 0)))
        lines.append(f'  "{src}" -> "{dst}" [label="{label}"];')

    lines.append("}")
    return "\n".join(lines)

def program_to_dfa(program):
    """Convert the parser's program object into the dict dfa_to_dot expects."""
    states = [str(s) for s in program.states]
    alphabet = [str(a) for a in program.alphabet]

    transitions = {}
    if program.format == 2:
        for t in program.transitions:
            transitions[(str(t.state), str(t.symbol))] = str(t.target)
    else:
        header = [str(h) for h in program.table_header]
        for state, targets in program.table_rows:
            for symbol, target in zip(header, targets):
                transitions[(str(state), symbol)] = str(target)

    return {
        "name": str(program.name),
        "states": states,
        "alphabet": alphabet,
        "start": str(program.start),
        "finals": [str(f) for f in program.finals],
        "transitions": transitions,
    }
