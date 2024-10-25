from difflib import SequenceMatcher
import numpy as np
from scipy.optimize import linear_sum_assignment



def assign_options_to_targets(options, targets, case_sensitive=True, similarity_threshold=0.5):
    def string_similarity(a, b):
        if not case_sensitive:
            a, b = a.lower(), b.lower()
        return SequenceMatcher(None, a, b).ratio()

    # If there are no options or targets, return empty results
    if not options or not targets:
        return {}, options[:], targets[:]
    
    # Create a cost matrix based on string similarity (we use 1 - similarity as cost)
    num_options = len(options)
    num_targets = len(targets)
    cost_matrix = np.ones((num_options, num_targets))  # Initialize with 1 (i.e., max cost)

    for i, option in enumerate(options):
        for j, target in enumerate(targets):
            similarity = string_similarity(option, target)
            if similarity >= similarity_threshold:
                cost_matrix[i, j] = 1 - similarity  # Cost is (1 - similarity)
            else:
                cost_matrix[i, j] = 1  # Set max cost for pairs below the threshold

    # Solve the assignment problem using the Hungarian algorithm
    row_ind, col_ind = linear_sum_assignment(cost_matrix)

    # Build the assignment dict
    assignments = {}
    assigned_options = []
    assigned_targets = []
    
    for r, c in zip(row_ind, col_ind):
        if cost_matrix[r, c] < 1:  # Only consider assignments with similarity above threshold
            assignments[options[r]] = targets[c]
            assigned_options.append(options[r])
            assigned_targets.append(targets[c])

    # Unassigned options and targets
    unassigned_options = [opt for opt in options if opt not in assigned_options]
    unassigned_targets = [tgt for tgt in targets if tgt not in assigned_targets]

    return assignments, unassigned_options, unassigned_targets

