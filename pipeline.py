from parser import parse
from semantic import analyze_semantics

def pipeliner_run(text):
    parsed = parse(text)
    if not parsed.ok:
        return None, parsed.errors

    semantic_result = analyze_semantics(parsed.program)
    if not semantic_result.ok:
        return None, semantic_result.errors

    # Code Generation
    # code = code_generation(ast)

    return parsed.program, None