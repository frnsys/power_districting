from tqdm import tqdm


def _default_hash_func(state):
    return hash(frozenset(state.items()))

def hill_climbing(root, succ_func, goal_func, score_func, max_depth=None, hash_func=_default_hash_func):
    """always choose the best state next.
    this only terminates if the succ_func eventually returns nothing.
    assumes the succ_func returns child states in descending order of value.
    this may not find the highest-scoring path (since it's possible that the highest-scoring path
    goes through a low-scoring state), but this saves _a lot_ of time"""
    seen = set()
    init_score = score_func(root)
    fringe = [((root, init_score), 0)]

    pbar = tqdm()
    max_seen_depth = 0
    best_score = init_score
    while fringe:
        (state, score), depth = fringe.pop(0)
        best_score = max(score, best_score)
        pbar.set_postfix(fringe=len(fringe), max_depth=max_seen_depth, best=best_score, improvement=best_score-init_score)

        # extended list filtering:
        # skip states we have already seen
        shash = hash_func(state)
        if shash in seen: continue
        seen.add(shash)

        if goal_func(state):
            break

        # if we terminate at a certain depth, break when we reach it
        if max_depth is not None and depth > max_depth:
            break

        if depth > max_seen_depth:
            max_seen_depth = depth

        succs = succ_func(state)
        # if no more successors, we're done
        if not succs:
            break

        # assumed that these are best-ordered successors
        fringe = [(succ, depth+1) for succ in succs] + fringe
        fringe.sort(key=lambda x: x[0][1], reverse=True)
        pbar.update()

    return state, score