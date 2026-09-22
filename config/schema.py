def ordenar_paths(result, generator, request, public):
    result["paths"] = dict(sorted(result["paths"].items()))
    return result