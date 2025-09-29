import numpy as np
# import matplotlib.pyplot as plt
# import matplotlib.patches as patches


# --- 1. Bézier Math Functions (Unchanged) ---

def cubic_bezier_point(t, control_points):
    """Calculates a point on a cubic Bézier curve at parameter t."""
    p0, p1, p2, p3 = control_points
    t_inv = 1.0 - t
    return (t_inv ** 3 * p0 +
            3 * t_inv ** 2 * t * p1 +
            3 * t_inv * t ** 2 * p2 +
            t ** 3 * p3)


def cubic_bezier_derivative(t, control_points):
    """Calculates the derivative (tangent vector) of a cubic Bézier curve."""
    p0, p1, p2, p3 = control_points
    t_inv = 1.0 - t
    return (3 * t_inv ** 2 * (p1 - p0) +
            6 * t_inv * t * (p2 - p1) +
            3 * t ** 2 * (p3 - p2))


# --- 2. The Updated Stroking Algorithm with Capping ---

def _stroke_single_segment(control_points, offset_distance, num_segments=50):
    """Helper function to generate the raw offset strokes for a single 4-point Bézier segment."""
    offset_points_a, offset_points_b = [], []
    t_values = np.linspace(0, 1, num_segments + 1)
    last_good_normal = None

    for t in t_values:
        point = cubic_bezier_point(t, control_points)
        tangent = cubic_bezier_derivative(t, control_points)
        norm_of_tangent = np.linalg.norm(tangent)

        if norm_of_tangent < 1e-6:
            if last_good_normal is not None:
                unit_normal = last_good_normal
            else:
                continue
        else:
            normal = np.array([-tangent[1], tangent[0]])
            unit_normal = normal / np.linalg.norm(normal)
            last_good_normal = unit_normal

        offset_points_a.append(point + offset_distance * unit_normal)
        offset_points_b.append(point - offset_distance * unit_normal)

    return np.array(offset_points_a), np.array(offset_points_b)


def _apply_caps(stroke_a, stroke_b, start_control_points, end_control_points, offset_distance, cap_style, cap_segments):
    """Helper function to apply caps to a completed pair of stroke polylines."""
    if cap_style == 'butt':
        full_polygon = np.concatenate([stroke_a, stroke_b[::-1]])
        return [full_polygon]

    elif cap_style == 'round':
        end_center = cubic_bezier_point(1, end_control_points)
        end_arc = _create_arc_points(end_center, stroke_a[-1], stroke_b[-1], cap_segments)
        start_center = cubic_bezier_point(0, start_control_points)
        start_arc = _create_arc_points(start_center, stroke_b[0], stroke_a[0], cap_segments)
        full_polygon = np.concatenate([stroke_a, end_arc, stroke_b[::-1], start_arc])
        return [full_polygon]

    elif cap_style == 'square':
        start_tangent = cubic_bezier_derivative(0.001, start_control_points)
        start_tangent_unit = start_tangent / np.linalg.norm(start_tangent)
        end_tangent = cubic_bezier_derivative(0.999, end_control_points)
        end_tangent_unit = end_tangent / np.linalg.norm(end_tangent)

        cap_start_a = stroke_a[0] - offset_distance * start_tangent_unit
        cap_start_b = stroke_b[0] - offset_distance * start_tangent_unit
        cap_end_a = stroke_a[-1] + offset_distance * end_tangent_unit
        cap_end_b = stroke_b[-1] + offset_distance * end_tangent_unit

        full_polygon = np.concatenate(
            [[cap_start_b], [cap_start_a], stroke_a, [cap_end_a], [cap_end_b], stroke_b[::-1]])
        return [full_polygon]

    else:
        raise ValueError("cap_style must be one of 'butt', 'round', or 'square'")


# --- 3. New Main Function for Poly-Bézier Curves ---

def stroke_poly_bezier(all_control_points, offset_distance, num_segments_per_curve=50, cap_style='round',
                       cap_segments=15):
    """
    Strokes a continuous Poly-Bézier curve defined by a list of control points.
    The number of points must be 3*N + 1 (e.g., 4, 7, 10, ...).
    """
    all_control_points = np.array(all_control_points)

    # # Validate the number of control points
    # if len(all_control_points) < 4 or (len(all_control_points) - 1) % 3 != 0:
    #     raise ValueError("Number of control points must be 3*N + 1 (e.g., 4, 7, 10...).")

    # Break the points into 4-point segments
    # segments = []
    # for i in range(0, len(all_control_points) - 1, 3):
    #     segment = all_control_points[i:i + 4]
    #     segments.append(segment)

    # Stroke each segment and stitch the results together
    full_stroke_a, full_stroke_b = [], []
    for i, segment in enumerate(all_control_points):
        stroke_a, stroke_b = _stroke_single_segment(segment, offset_distance, num_segments_per_curve)

        if i == 0:
            full_stroke_a.append(stroke_a)
            full_stroke_b.append(stroke_b)
        else:
            # Append, skipping the first point to avoid duplicates at joins
            full_stroke_a.append(stroke_a[1:])
            full_stroke_b.append(stroke_b[1:])

    # Combine the lists of arrays into single arrays
    final_stroke_a = np.concatenate(full_stroke_a, axis=0)
    final_stroke_b = np.concatenate(full_stroke_b, axis=0)

    # Apply caps to the start and end of the complete stitched curve
    start_cps = all_control_points[0]
    end_cps = all_control_points[-1]
    return _apply_caps(final_stroke_a, final_stroke_b, start_cps, end_cps, offset_distance, cap_style, cap_segments)


def stroke_bezier(control_points, offset_distance, num_segments=100, cap_style='butt', cap_segments=10):
    """
    Performs discrete offsetting (stroking) on a cubic Bézier curve with end caps.

    Args:
        control_points (list or np.ndarray): The four [x, y] control points P0, P1, P2, P3.
        offset_distance (float): The distance to offset the curve on each side.
        num_segments (int): Number of segments to approximate the curve.
        cap_style (str): The style of the end caps. One of 'butt', 'round', or 'square'.
        cap_segments (int): Number of segments for 'round' caps.

    Returns:
        list[np.ndarray]: A list of numpy arrays. For 'butt' caps, this will be two
                          separate polylines. For 'round' and 'square' caps, it will
                          be a single closed polygon.
    """
    control_points = np.array(control_points)

    # Generate the two offset strokes (polylines)
    offset_points_a = []
    offset_points_b = []
    t_values = np.linspace(0, 1, num_segments + 1)
    last_good_normal = None

    for t in t_values:
        point = cubic_bezier_point(t, control_points)
        tangent = cubic_bezier_derivative(t, control_points)
        norm_of_tangent = np.linalg.norm(tangent)

        if norm_of_tangent < 1e-6:
            if last_good_normal is not None:
                unit_normal = last_good_normal
            else:  # Cannot determine a normal, skip
                continue
        else:
            normal = np.array([-tangent[1], tangent[0]])
            unit_normal = normal / np.linalg.norm(normal)
            last_good_normal = unit_normal

        offset_points_a.append(point + offset_distance * unit_normal)
        offset_points_b.append(point - offset_distance * unit_normal)

    stroke_a = np.array(offset_points_a)
    stroke_b = np.array(offset_points_b)

    # If strokes are empty, return nothing
    if len(stroke_a) == 0:
        return []

    # --- Capping Logic ---
    if cap_style == 'butt':
        # End cap (t=1)
        end_center = cubic_bezier_point(1, control_points)
        end_arc = _create_arc_points(end_center, stroke_b[-1], stroke_a[-1], cap_segments)

        # Start cap (t=0)
        start_center = cubic_bezier_point(0, control_points)
        start_arc = _create_arc_points(start_center, stroke_a[0], stroke_b[0], cap_segments)

        # Combine into a single closed polygon
        # Order: Stroke A -> End Cap Arc -> Reversed Stroke B -> Start Cap Arc
        full_polygon = np.concatenate([
            stroke_a,
            end_arc,
            stroke_b[::-1],  # Reversed stroke B
            start_arc
        ])
        return [full_polygon]

    elif cap_style == 'round':
        # End cap (t=1)
        end_center = cubic_bezier_point(1, control_points)
        end_arc = _create_arc_points(end_center, stroke_a[-1], stroke_b[-1], cap_segments)

        # Start cap (t=0)
        start_center = cubic_bezier_point(0, control_points)
        start_arc = _create_arc_points(start_center, stroke_b[0], stroke_a[0], cap_segments)

        # Combine into a single closed polygon
        # Order: Stroke A -> End Cap Arc -> Reversed Stroke B -> Start Cap Arc
        full_polygon = np.concatenate([
            stroke_a,
            end_arc,
            stroke_b[::-1],  # Reversed stroke B
            start_arc
        ])
        return [full_polygon]

    elif cap_style == 'square':
        # Start cap (t=0)
        start_tangent = cubic_bezier_derivative(0, control_points)
        start_tangent_unit = start_tangent / np.linalg.norm(start_tangent)
        cap_start_a = stroke_a[0] - offset_distance * start_tangent_unit
        cap_start_b = stroke_b[0] - offset_distance * start_tangent_unit

        # End cap (t=1)
        end_tangent = cubic_bezier_derivative(1, control_points)
        end_tangent_unit = end_tangent / np.linalg.norm(end_tangent)
        cap_end_a = stroke_a[-1] + offset_distance * end_tangent_unit
        cap_end_b = stroke_b[-1] + offset_distance * end_tangent_unit

        # Combine into a single closed polygon
        full_polygon = np.concatenate([
            [cap_start_a],
            stroke_a,
            [cap_end_a, cap_end_b],
            stroke_b[::-1],
            [cap_start_b]
        ])
        return [full_polygon]

    else:
        raise ValueError("cap_style must be one of 'butt', 'round', or 'square'")


def _create_arc_points(center, start_point, end_point, num_segments):
    """Helper function to create points for a semicircle."""
    v_start = start_point - center
    v_end = end_point - center

    radius = np.linalg.norm(v_start)

    start_angle = np.arctan2(v_start[1], v_start[0])
    end_angle = np.arctan2(v_end[1], v_end[0])

    # Ensure the arc travels in the correct direction (less than 180 degrees)
    if np.cross(v_start, v_end) < 0:
        if end_angle < start_angle:
            start_angle += 2 * np.pi
    else:
        if end_angle > start_angle:
            end_angle -= 2 * np.pi

    angles = np.linspace(start_angle, end_angle, num_segments)
    arc_points = center + radius * np.array([np.cos(angles), np.sin(angles)]).T
    return arc_points


# --- 3. Example Usage & Visualization ---

def single_main():
    # Define a sample cubic Bézier curve (S-curve)
    control_points = np.array([[100, 200], [250, 400], [450, 600], [600, 200]])

    # --- Parameters to change ---
    OFFSET_DISTANCE = 3.0
    NUM_SEGMENTS = 100
    CAP_STYLE = 'round'  # Options: 'butt', 'round', 'square'
    CAP_SEGMENTS = 12

    # Run the stroking algorithm
    stroke_polygons = stroke_bezier(control_points, OFFSET_DISTANCE, NUM_SEGMENTS, cap_style=CAP_STYLE, cap_segments=CAP_SEGMENTS)

    # --- Visualization ---
    fig, ax = plt.subplots(figsize=(10, 8))

    # Plot the original curve as a thin line
    t_plot = np.linspace(0, 1, 200)
    curve_points = np.array([cubic_bezier_point(t, np.array(control_points)) for t in t_plot])
    ax.plot(curve_points[:, 0], curve_points[:, 1], 'k-', linewidth=1, alpha=0.5, label='Original Bézier Curve')

    # Plot the control points and polygon
    ax.plot(control_points[:, 0], control_points[:, 1], 'co--', alpha=0.5, label='Control Polygon')
    ax.plot(control_points[:, 0], control_points[:, 1], 'c*', markersize=10)

    # Plot the resulting stroke polygon(s)
    for poly_points in stroke_polygons:
            polygon = patches.Polygon(poly_points, closed=True, facecolor='steelblue', edgecolor='darkblue')
            ax.add_patch(polygon)

    ax.set_title(f"Bézier Stroke with '{CAP_STYLE.capitalize()}' Caps")
    ax.set_xlabel('X Coordinate')
    ax.set_ylabel('Y Coordinate')
    ax.legend()
    ax.grid(True)
    ax.set_aspect('equal', adjustable='box')  # Use an equal aspect ratio
    plt.show()


def poly_main():
    # A list of 7 control points, defining TWO connected cubic Bézier segments
    poly_control_points = np.array([
        [100, 400],  # P0
        [200, 100],  # P1
        [300, 400],  # P2
        [400, 250],  # P3 - Join point
        [500, 100],  # P4
        [600, 350],  # P5
        [700, 200]  # P6
    ])

    # --- Parameters to change ---
    OFFSET_DISTANCE = 25.0
    CAP_STYLE = 'round'  # Options: 'butt', 'round', 'square'

    # Use the new function for Poly-Bézier curves
    stroke_polygons = stroke_poly_bezier(poly_control_points, OFFSET_DISTANCE, cap_style=CAP_STYLE)

    fig, ax = plt.subplots(figsize=(12, 8))

    # Plot the original composite curve
    full_curve_points = []
    num_segments = (len(poly_control_points) - 1) // 3
    for i in range(num_segments):
        segment_cps = poly_control_points[i * 3:i * 3 + 4]
        t_plot = np.linspace(0, 1, 100)
        # Skip first point of subsequent segments to avoid duplication
        start_index = 1 if i > 0 else 0
        full_curve_points.extend(cubic_bezier_point(t, segment_cps) for t in t_plot[start_index:])

    full_curve_points = np.array(full_curve_points)
    ax.plot(full_curve_points[:, 0], full_curve_points[:, 1], 'k-', linewidth=1, alpha=0.5,
            label='Original Poly-Bézier Curve')

    # Plot the control points
    ax.plot(poly_control_points[:, 0], poly_control_points[:, 1], 'co--', alpha=0.5, label='Control Polygon')
    ax.plot(poly_control_points[:, 0], poly_control_points[:, 1], 'c*', markersize=10)

    # Draw the resulting stroke polygon(s)
    for poly_points in stroke_polygons:
        polygon = patches.Polygon(poly_points, closed=True, facecolor='lightcoral', edgecolor='darkred')
        ax.add_patch(polygon)

    ax.set_title(f"Stroked Poly-Bézier Curve with '{CAP_STYLE.capitalize()}' Caps")
    ax.legend()
    ax.grid(True)
    ax.set_aspect('equal', adjustable='box')
    plt.show()

if __name__ == '__main__':
    single_main()
    # poly_main()