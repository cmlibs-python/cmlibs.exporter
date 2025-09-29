

def find_continuous_segments(partition_info, connected_segments):
    """
    Breaks down partitioned ID lists into ordered, continuous segments.

    Args:
        partition_info: The dictionary describing the partition by name and element ids.
        connected_segments: A list of lists, where each inner list defines
                            an ordered, connected path of element IDs.

    Returns:
        A new dictionary with the same structure, but where each ID list
        is replaced by a list of its constituent connected segments.
    """
    # Step 1: Create the successor map for O(1) lookups.
    successor_map = {}
    for segment in connected_segments:
        for i in range(len(segment) - 1):
            successor_map[segment[i]] = segment[i + 1]

    continuous_segments = {}
    for node_name, exclusive_ids in partition_info.items():
        # Use a set for efficient lookups and removals.
        ids_to_process = set(exclusive_ids)
        node_segments = []

        # Step 3: Find all continuous segments for the current node.
        while ids_to_process:
            # Start a new segment with an arbitrary element.
            # Sort the remaining IDs to ensure deterministic starting points.
            start_id = sorted(list(ids_to_process))[0]

            current_segment = [start_id]
            ids_to_process.remove(start_id)

            # Trace the segment forward using the successor map.
            current_id = start_id
            while successor_map.get(current_id) in ids_to_process:
                current_id = successor_map[current_id]
                current_segment.append(current_id)
                ids_to_process.remove(current_id)

            node_segments.append(current_segment)

        if len(node_segments) == 1:
            continuous_segments[node_name] = node_segments[0]

    return continuous_segments
