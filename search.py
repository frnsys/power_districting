from tqdm import tqdm


def _default_hash_func(state):
    return hash(frozenset(state.items()))

def hill_climbing(root, succ_func, goal_func, max_depth=None, hash_func=_default_hash_func):
    """always choose the best state next.
    this only terminates if the succ_func eventually returns nothing.
    assumes the succ_func returns child states in descending order of value.
    this may not find the highest-scoring path (since it's possible that the highest-scoring path
    goes through a low-scoring state), but this saves _a lot_ of time"""
    seen = set()
    fringe = [[root]]

    pbar = tqdm()
    max_seen_depth = 0
    while fringe:
        pbar.set_postfix(fringe=len(fringe), max_depth=max_seen_depth)

        path = fringe.pop(0)
        state = path[-1]

        # extended list filtering:
        # skip states we have already seen
        shash = hash_func(state)
        if shash in seen: continue
        seen.add(shash)

        if goal_func(state):
            break

        # if we terminate at a certain depth, break when we reach it
        depth = len(path)
        if max_depth is not None and depth > max_depth:
            break

        if depth > max_seen_depth:
            max_seen_depth = depth

        succs = succ_func(state)
        # if no more successors, we're done
        if not succs:
            break

        # assumed that these are best-ordered successors
        fringe = [path + [succ] for succ in succs] + fringe
        pbar.update()

    return path[-1]