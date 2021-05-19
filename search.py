from tqdm import tqdm


def _default_hash_func(state):
    return hash(frozenset(state.items()))


def _ida(path, depth, max_depth, succ_func, goal_func, heur_func, hash_func, seen):
    """subroutine for iterative deepening A*"""
    state = path[-1]

    f = depth + heur_func(state)
    if f > max_depth: return f, None

    if goal_func(state):
        return f, path

    # extended list filtering:
    # skip nodes we have already seen
    shash = hash_func(state)
    if shash in seen: return f, None
    seen.add(shash)

    minimum = float('inf')
    best_path = None
    for child in succ_func(state):
        # g(n) = distance(n)
        thresh, new_path = _ida(path + [child],
                                depth + 1,
                                max_depth,
                                succ_func,
                                goal_func,
                                heur_func,
                                hash_func,
                                seen)
        if new_path is not None and thresh < minimum:
            minimum = thresh
            best_path = new_path
    return minimum, best_path


def ida(root, succ_func, goal_func, heur_func=lambda s: 0, hash_func=_default_hash_func):
    """iterative deepening A*

    - root: the initial state to search from
    - succ_func: func that takes a state and returns all successor states
    - goal_func: func that takes a state and returns if it satisfies goal criteria
    - heur_func: func that takes a state and returns estimated distance to goal (should never overestimate the distance)
        - default: returns 0, which is a valid but uninformative heuristic
    - hash_func: func that takes a state and returns a hash of it (to determine if a state has already been visited)
        - default: assumes states are dictionaries, returns a hash of the dict
    """
    solution = None
    max_depth = heur_func(root)
    while solution is None:
        _, solution = _ida(
                [root], # path
                0,            # current depth
                max_depth,    # max depth
                succ_func,
                goal_func,
                heur_func,
                hash_func,
                set())        # seen
        max_depth += 1
    return solution


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