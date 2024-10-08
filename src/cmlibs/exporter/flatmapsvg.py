"""
Export an Argon document to source document(s) suitable for the generating
flatmaps from.
"""
import csv
import json
import logging

import math
import os
import random
from decimal import Decimal

from svgpathtools import svg2paths
from xml.dom.minidom import parseString

from cmlibs.zinc.field import Field, FieldFindMeshLocation
from cmlibs.zinc.result import RESULT_OK

from cmlibs.exporter.base import BaseExporter
from cmlibs.maths.vectorops import sub, div, add, magnitude
from cmlibs.utils.zinc.field import get_group_list
from cmlibs.utils.zinc.finiteelement import get_highest_dimension_mesh
from cmlibs.utils.zinc.general import ChangeManager

logger = logging.getLogger(__name__)

SVG_COLOURS = [
    "aliceblue", "aquamarine", "azure", "blanchedalmond", "blue", "blueviolet", "brown", "burlywood",
    "cadetblue", "chartreuse", "chocolate", "coral", "cornflowerblue", "cornsilk", "crimson", "cyan",
    "darkblue", "darkcyan", "darkgoldenrod", "darkgray", "darkgreen", "darkgrey", "darkkhaki", "darkmagenta",
    "darkolivegreen", "darkorange", "darkorchid", "darkred", "darksalmon", "darkseagreen", "darkslateblue",
    "darkslategray", "darkslategrey", "darkturquoise", "darkviolet", "deeppink", "deepskyblue", "dimgray",
    "dimgrey", "dodgerblue", "firebrick", "floralwhite", "forestgreen", "fuchsia", "gainsboroghost",
    "whitegold", "goldenrod", "gray", "green", "greenyellow", "grey", "honeydew", "hotpink", "indianred",
    "indigo", "ivorykhakilavender", "lavenderblush", "lawngreen", "lemonchiffon", "lightblue", "lightcoral",
    "lightcyan", "lightgolden", "rodyellow", "lightgray", "lightgreen", "lightgrey", "lightpink",
    "lightsalmon", "lightseagreen",
]


class ArgonSceneExporter(BaseExporter):
    """
    Export a visualisation described by an Argon document to webGL.
    """

    def __init__(self, output_target=None, output_prefix=None):
        """
        :param output_target: The target directory to export the visualisation to.
        :param output_prefix: The prefix for the exported file(s).
        """
        super(ArgonSceneExporter, self).__init__("ArgonSceneExporterWavefrontSVG" if output_prefix is None else output_prefix)
        self._output_target = output_target
        self._annotations_csv_file = None

    def export(self, output_target=None):
        """
        Export the current document to *output_target*. If no *output_target* is given then
        the *output_target* set at initialisation is used.

        If there is no current document then one will be loaded from the current filename.

        :param output_target: Output directory location.
        """
        super().export()

        if output_target is not None:
            self._output_target = output_target

        self.export_flatmapsvg()

    def export_from_scene(self, scene, scene_filter=None):
        """
        Export graphics from a Zinc Scene into Flatmap SVG format.

        :param scene: The Zinc Scene object to be exported.
        :param scene_filter: Optional; A Zinc Scenefilter object associated with the Zinc scene, allowing the user to filter which
            graphics are included in the export.
        """
        self.export_flatmapsvg_from_scene(scene, scene_filter)

    def export_flatmapsvg(self):
        """
        Export graphics into JSON format, one json export represents one Zinc graphics.
        """
        scene = self._document.getRootRegion().getZincRegion().getScene()
        self.export_flatmapsvg_from_scene(scene)

    def export_flatmapsvg_from_scene(self, scene, scene_filter=None):
        """
        Export graphics from a Zinc Scene into Flatmap SVG format.

        :param scene: The Zinc Scene object to be exported.
        :param scene_filter: Optional; A Zinc Scenefilter object associated with the Zinc scene, allowing the user to filter which
            graphics are included in the export.
        """
        region = scene.getRegion()
        path_points, svg_id_group_map = _analyze_elements(region, "coordinates")
        bezier = _calculate_bezier_control_points(path_points)
        markers = _calculate_markers(region, "coordinates")
        connected_segments = _collect_curves_into_segments(bezier)
        end_point_data = _collate_end_points(connected_segments, svg_id_group_map)
        network_plan, network_points = _determine_network(region, end_point_data, "coordinates")
        svg_string = _write_into_svg_format(connected_segments, markers, network_points)

        view_box = _calculate_view_box(svg_string)
        svg_string = svg_string.replace('viewBox="WWW XXX YYY ZZZ"', f'viewBox="{view_box[0]} {view_box[1]} {view_box[2]} {view_box[3]}"')

        svg_string = parseString(svg_string).toprettyxml()

        reversed_annotations_map = self._read_reversed_annotations_map()
        networks = [_create_vagus_network(network_plan, {v: k for k, v in svg_id_group_map.items()}, reversed_annotations_map)]

        features = {}
        for marker in markers:
            feature = {
                "name": marker[2],
                "models": marker[3],
                "colour": "orange"
            }
            features[marker[0]] = feature

        properties = {"networks": networks}
        if features:
            properties["features"] = features

        with open(f'{os.path.join(self._output_target, self._prefix)}.svg', 'w') as f:
            f.write(svg_string)

        with open(os.path.join(self._output_target, 'properties.json'), 'w') as f:
            json.dump(properties, f, default=lambda o: o.__dict__, sort_keys=True, indent=2)

    def set_annotations_csv_file(self, filename):
        self._annotations_csv_file = filename

    def _read_reversed_annotations_map(self):
        reversed_map = None
        if self._annotations_csv_file is not None:
            with open(self._annotations_csv_file) as fh:
                result = csv.reader(fh)

                is_annotation_csv_file = _is_annotation_csv_file(result)

                if is_annotation_csv_file:
                    fh.seek(0)
                    reversed_map = _reverse_map_annotations(result)

        return reversed_map


def _calculate_markers(region, coordinate_field_name):
    fm = region.getFieldmodule()
    with ChangeManager(fm):
        coordinate_field = fm.findFieldByName(coordinate_field_name).castFiniteElement()
        name_field = fm.findFieldByName('marker_name')
        location_field = fm.findFieldByName('marker_location')
        annotation_field = fm.findFieldByName('marker_annotation')

        marker_coordinate_field = fm.createFieldEmbedded(coordinate_field, location_field)

        markers_group = fm.findFieldByName("marker").castGroup()

        marker_data = []
        if markers_group.isValid():
            marker_node_set = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
            marker_points = markers_group.getNodesetGroup(marker_node_set)
            marker_iterator = marker_points.createNodeiterator()
            components_count = marker_coordinate_field.getNumberOfComponents()

            marker = marker_iterator.next()
            fc = fm.createFieldcache()

            i = 0
            while marker.isValid():
                fc.setNode(marker)
                result, values = marker_coordinate_field.evaluateReal(fc, components_count)
                if name_field.isValid():
                    name = name_field.evaluateString(fc)
                else:
                    name = f"Unnamed marker {i + 1}"

                if annotation_field.isValid():
                    onto_id = annotation_field.evaluateString(fc)
                else:
                    rand_num = random.randint(1, 99999)
                    onto_id = f"UBERON:99{rand_num:0=5}"
                marker_data.append((f"marker_{marker.getIdentifier()}", values[:2], name, onto_id))
                marker = marker_iterator.next()
                i += 1

    return marker_data


def _group_svg_id(group_name):
    return group_name.replace("group_", "nerve_feature_")


def _group_number(index, size_of_digits):
    return f"{index + 1}".rjust(size_of_digits, '0')


def _define_group_label(group_index, size_of_digits):
    return f"group_{_group_number(group_index, size_of_digits)}"


def _define_point_title(index, size_of_digits):
    return f"point_{_group_number(index, size_of_digits)}"


def _create_xi_array(size, location):
    xi = [0.5] * size
    xi[0] = location
    return xi


def _analyze_elements(region, coordinate_field_name):
    fm = region.getFieldmodule()
    mesh = get_highest_dimension_mesh(fm)
    coordinates = fm.findFieldByName(coordinate_field_name).castFiniteElement()

    if mesh is None:
        return []

    if mesh.getSize() == 0:
        return []

    group_list = get_group_list(fm)
    grouped_path_points = {
        "ungrouped": []
    }
    svg_id_group_map = {}

    size_of_digits = len(f'{len(group_list)}')
    for group_index, group in enumerate(group_list):
        group_name = group.getName()
        if group_name != "marker":
            group_label = _define_group_label(group_index, size_of_digits)
            grouped_path_points[group_label] = []
            # grouped_element_info[group_label] = []
            svg_id_group_map[_group_svg_id(group_label)] = group_name

    with ChangeManager(fm):
        xi_1_derivative = fm.createFieldDerivative(coordinates, 1)

        el_iterator = mesh.createElementiterator()
        element = el_iterator.next()
        while element.isValid():

            xi_start = _create_xi_array(element.getDimension(), 0.0)
            xi_end = _create_xi_array(element.getDimension(), 1.0)
            values_1 = _evaluate_field_data(element, xi_start, coordinates)
            values_2 = _evaluate_field_data(element, xi_end, coordinates)
            derivatives_1 = _evaluate_field_data(element, xi_start, xi_1_derivative)
            derivatives_2 = _evaluate_field_data(element, xi_end, xi_1_derivative)

            line_path_points = None
            if values_1 and values_2 and derivatives_1 and derivatives_2:
                line_path_points = [(values_1, derivatives_1), (values_2, derivatives_2)]

            if line_path_points is not None:
                in_group = False
                for group_index, group in enumerate(group_list):
                    mesh_group = group.getMeshGroup(mesh)
                    if mesh_group.containsElement(element):
                        group_label = _define_group_label(group_index, size_of_digits)
                        grouped_path_points[group_label].append(line_path_points)
                        in_group = True

                    del mesh_group

                if not in_group:
                    grouped_path_points["ungrouped"].append(line_path_points)

            element = el_iterator.next()

        del xi_1_derivative

    return grouped_path_points, svg_id_group_map


def _calculate_view_box(svg_string):
    paths, attributes = svg2paths(svg_string)
    bbox = [999999999, -999999999, 999999999, -999999999]
    for p in paths:
        path_bbox = p.bbox()
        bbox[0] = min(path_bbox[0], bbox[0])
        bbox[1] = max(path_bbox[1], bbox[1])
        bbox[2] = min(path_bbox[2], bbox[2])
        bbox[3] = max(path_bbox[3], bbox[3])

    view_margin = 10
    return (int(bbox[0] + 0.5) - view_margin,
            int(bbox[2] + 0.5) - view_margin,
            int(bbox[1] - bbox[0] + 0.5) + 2 * view_margin,
            int(bbox[3] - bbox[2] + 0.5) + 2 * view_margin)


def _determine_network(region, end_point_data, coordinate_field_name):
    fm = region.getFieldmodule()
    mesh = get_highest_dimension_mesh(fm)
    mesh_1d = fm.findMeshByDimension(1)
    # data_point_set = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
    coordinates = fm.findFieldByName(coordinate_field_name).castFiniteElement()
    vagus_coordinates = fm.findFieldByName("vagus coordinates").castFiniteElement()
    find_mesh_location_field = fm.createFieldFindMeshLocation(coordinates, coordinates, mesh_1d)
    # find_mesh_location_field.setSearchMode(FieldFindMeshLocation.SEARCH_MODE_EXACT)
    find_mesh_location_field.setSearchMode(FieldFindMeshLocation.SEARCH_MODE_NEAREST)
    # data_point_coordinate_field = fm.createFieldFiniteElement(3)
    fc = fm.createFieldcache()

    if mesh is None:
        return [], []

    if mesh.getSize() == 0:
        return [], []

    group_list = get_group_list(fm)

    # Map the 3D element groups to 1D elements with the same identifier.
    # This relies on the fact that the 3D elements are built from the
    # underlying 1D elements and that their is an exact 1-to-1 match
    # between identifiers.
    group_1d_group_map = {}
    for group in group_list:
        group_1d_group_map[group.getName()] = None
        mesh_group = group.getMeshGroup(mesh)
        if mesh_group.getSize():
            field_group_1d = fm.createFieldGroup()
            group_1d_group_map[group.getName()] = field_group_1d
            mesh_1d_group = field_group_1d.createMeshGroup(mesh_1d)
            field_group_1d.setName(f"{group.getName()} 1D")
            group_iterator = mesh_group.createElementiterator()
            group_element = group_iterator.next()
            group_element_ids = []
            while group_element.isValid():
                element_1d = mesh_1d.findElementByIdentifier(group_element.getIdentifier())
                mesh_1d_group.addElement(element_1d)
                group_element_ids.append(group_element.getIdentifier())
                group_element = group_iterator.next()

    # with ChangeManager(fm):
    #     node_template = data_point_set.createNodetemplate()
    #     node_template.defineField(data_point_coordinate_field)
    #     datapoint = data_point_set.createNode(-1, node_template)
    #     fc.setNode(datapoint)

    min_value = {}
    start_value = {}
    end_value = {}
    network_points_1 = []
    for group_name, end_points in end_point_data.items():
        start_coordinate = [0.0] * 3
        end_coordinate = [0.0] * 3
        network_points_1.extend([end_points[0][0], end_points[0][1]])
        start_coordinate[:2] = end_points[0][0]
        end_coordinate[:2] = end_points[0][1]

        group_1d = group_1d_group_map.get(group_name, None)
        if group_1d is not None:
            mesh_group = group_1d.getMeshGroup(mesh_1d)
            find_mesh_location_field.setSearchMesh(mesh_group)
            fc.setFieldReal(coordinates, end_coordinate)
            mesh_location = find_mesh_location_field.evaluateMeshLocation(fc, 1)
            fc.setMeshLocation(mesh_location[0], mesh_location[1])
            end_value[group_name] = vagus_coordinates.evaluateReal(fc, 3)[1]
            fc.setFieldReal(coordinates, start_coordinate)
            mesh_location = find_mesh_location_field.evaluateMeshLocation(fc, 1)
            fc.setMeshLocation(mesh_location[0], mesh_location[1])
            start_value[group_name] = vagus_coordinates.evaluateReal(fc, 3)[1]

        min_value[group_name] = [math.inf, None, None, None]
        for group in group_list:
            group_1d = group_1d_group_map[group.getName()]
            if group_1d is not None:
                mesh_group = group_1d.getMeshGroup(mesh_1d)
                if mesh_group.getSize() and group_name != group.getName():

                    find_mesh_location_field.setSearchMesh(mesh_group)
                    fc.setFieldReal(coordinates, start_coordinate)
                    mesh_location = find_mesh_location_field.evaluateMeshLocation(fc, 1)
                    if mesh_location[0].isValid():
                        fc.setMeshLocation(mesh_location[0], mesh_location[1])
                        result_1, values = coordinates.evaluateReal(fc, 3)
                        result_2, material_values = vagus_coordinates.evaluateReal(fc, 3)
                        if result_1 == RESULT_OK and result_2 == RESULT_OK:
                            tolerance = _calculate_tolerance(start_coordinate + values)
                            diff = magnitude(sub(start_coordinate, values))
                            if diff < tolerance and diff < min_value[group_name][0]:
                                min_value[group_name] = [diff, group.getName(), material_values, values]

    network_points = {}
    for group_name, end_points in end_point_data.items():
        network_points[group_name] = network_points.get(group_name, [(0.0, end_points[0][0]), (1.0, end_points[0][1])])
        if group_name in min_value:
            values = min_value[group_name]
            int_branch = values[1]
            int_location = values[2]
            if int_branch is not None:
                network_points_1.append(values[3][:2])
                branch_start = start_value[int_branch]
                branch_end = end_value[int_branch]
                branch_length = magnitude(sub(branch_end, branch_start))
                int_length = magnitude(sub(int_location, branch_start))
                network_points[int_branch] = network_points.get(int_branch, [(0.0, end_point_data[int_branch][0][0]), (1.0, end_point_data[int_branch][0][1])])
                network_points[int_branch].append((int_length / branch_length, values[3][:2]))

    numbers = []
    points = []
    for i, vv in network_points.items():
        for v in vv:
            numbers.extend(v[1])
            points.append(v[1])

    key_tolerance = 1 / _calculate_tolerance(numbers)

    begin_hash = {}
    for index, pt in enumerate(points):
        key = _create_key(pt, key_tolerance)
        begin_hash[key] = begin_hash.get(key, index)

    network_points_2 = []
    index_map = {}
    for pt in points:
        key = _create_key(pt, key_tolerance)
        index = begin_hash[key]
        if index not in index_map:
            index_map[index] = len(network_points_2)
            network_points_2.append(pt)

    final_network_points = network_points_2
    size_of_digits = len(f'{len(final_network_points)}')
    final_network = {}
    for group_name, values in network_points.items():
        final_network[group_name] = []
        sorted_values = sorted(values, key=lambda tup: tup[0])
        for value in sorted_values:
            key = _create_key(value[1], key_tolerance)
            index = begin_hash[key]
            mapped_name = _define_point_title(index_map[index], size_of_digits)
            if mapped_name not in final_network[group_name]:
                final_network[group_name].append(mapped_name)

    return final_network, final_network_points


def _collate_end_points(connected_segments, svg_id_group_map):
    end_point_data = {}
    for group_name, connected_segment in connected_segments.items():
        end_points = []
        for c in connected_segment:
            end_points.append((c[0][0], c[-1][3]))
        svg_id = _group_svg_id(group_name)
        end_point_data[svg_id_group_map.get(svg_id, "ungrouped")] = end_points
    return end_point_data


def _create_plan(label, plan_data, group_svg_id_map, annotations_map):
    plan = {
        "id": group_svg_id_map.get(label, "ungrouped"),
        "label": label,
        "connects": plan_data,
    }
    if annotations_map is not None and _label_has_annotations(label, annotations_map):
        plan["models"] = annotations_map[label]

    return plan


def _create_network_centrelines(network_plan, group_svg_id_map, annotations_map):
    return [_create_plan(label, data, group_svg_id_map, annotations_map) for label, data in network_plan.items()]


def _create_vagus_network(network_plan, group_svg_id_map, annotations_map):
    return {
        "id": "vagus",
        "type": "nerve",
        "centrelines": _create_network_centrelines(network_plan, group_svg_id_map, annotations_map)
    }


def _evaluate_field_data(element, xi, data_field):
    mesh = element.getMesh()
    fm = mesh.getFieldmodule()
    fc = fm.createFieldcache()

    components_count = data_field.getNumberOfComponents()

    fc.setMeshLocation(element, xi)
    result, values = data_field.evaluateReal(fc, components_count)
    if result == RESULT_OK:
        return values

    return None


def _calculate_bezier_curve(pt_1, pt_2):
    h0 = pt_1[0][:2]
    v0 = pt_1[1][:2]
    h1 = pt_2[0][:2]
    v1 = pt_2[1][:2]

    b0 = h0
    b1 = add(h0, div(v0, 3))
    b2 = sub(h1, div(v1, 3))
    b3 = h1

    return b0, b1, b2, b3


def _calculate_bezier_control_points(point_data):
    bezier = {}

    for point_group in point_data:
        if point_data[point_group]:
            bezier[point_group] = []
            for curve_pts in point_data[point_group]:
                bezier[point_group].append(_calculate_bezier_curve(curve_pts[0], curve_pts[1]))

    return bezier


class UnionFind:
    def __init__(self, v):
        self.parent = [-1 for _ in range(v)]

    def find(self, i):
        if self.parent[i] == -1:
            return i
        self.parent[i] = self.find(self.parent[i])  # Path compression
        return self.parent[i]

    def union(self, i, j):
        root_i = self.find(i)
        root_j = self.find(j)
        if root_i != root_j:
            self.parent[root_i] = root_j
            return root_j
        return root_i

    def __repr__(self):
        return f"{self.parent}"


def _count_significant_figs(num_str):
    return len(Decimal(num_str).normalize().as_tuple().digits)


def _create_key(pt, tolerance=1e8):
    return tuple(int(p * tolerance) for p in pt)


def _calculate_tolerance(numbers):
    min_sig_figs = math.inf
    max_sig_digit = -math.inf
    for n in numbers:
        min_sig_figs = min([min_sig_figs, _count_significant_figs(f"{n}")])
        # max_sig_digit = max([max_sig_digit, float(f'{float(f"{n:.1g}"):g}')])
        abs_n = math.fabs(n)
        max_sig_digit = max([max_sig_digit, math.ceil(math.log10(abs_n if abs_n > 1e-08 else 1.0))])

    min_sig_figs = max(14, min_sig_figs)
    tolerance_power = min_sig_figs - max_sig_digit - 2
    return 10 ** (-tolerance_power if tolerance_power > 0 else -8)


def _connected_segments(curve):
    # Determine a tolerance for the curve to use in defining keys
    numbers = []
    for c in curve:
        for i in [0, 3]:
            for j in [0, 1]:
                numbers.append(c[i][j])

    key_tolerance = 1 / _calculate_tolerance(numbers)

    begin_hash = {}
    for index, c in enumerate(curve):
        key = _create_key(c[0], key_tolerance)
        if key in begin_hash:
            logger.warning(f"Problem repeated key found while trying to connect segments! {index} - {c}")
        begin_hash[key] = index

    curve_size = len(curve)
    uf = UnionFind(len(curve))
    for index, c in enumerate(curve):
        y_cur = _create_key(c[3], key_tolerance)
        if y_cur in begin_hash:
            uf.union(begin_hash[y_cur], index)

    sets = {}
    for i in range(curve_size):
        root = uf.find(i)
        if root not in sets:
            sets[root] = []

        sets[root].append(i)

    segments = []
    for s in sets:
        seg = [curve[s]]
        key = _create_key(curve[s][3], key_tolerance)
        while key in begin_hash:
            s = begin_hash[key]
            seg.append(curve[s])
            old_key = key
            key = _create_key(curve[s][3], key_tolerance)
            if old_key == key:
                logger.warning("Breaking out of loop in determining segments.")
                break

        segments.append(seg)

    return segments


def _collect_curves_into_segments(bezier_data):
    collection_of_paths = {}
    for group_name in bezier_data:
        connected_paths = _connected_segments(bezier_data[group_name])

        if len(connected_paths) > 1:
            logger.warning("Two (or more) of the following points should have been detected as the same point.")
            for connected_path in connected_paths:
                logger.warning(f"{connected_path[0][0]} - {connected_path[-1][-1]}")

        collection_of_paths[group_name] = connected_paths

    return collection_of_paths


def _write_connected_svg_bezier_path(bezier_path, group_name):
    stroke = "grey" if group_name is None else "#01136e"

    svg = '<path d="'
    for i, bezier_section in enumerate(bezier_path):
        m_space = '' if i == 0 else ' '
        for j, b in enumerate(bezier_section):
            if j == 0:
                svg += f'{m_space}M {b[0][0]} {-b[0][1]}'

            svg += f' C {b[1][0]} {-b[1][1]}, {b[2][0]} {-b[2][1]}, {b[3][0]} {-b[3][1]}'
    svg += f'" stroke="{stroke}" fill="none"'
    svg += '/>' if group_name is None else f'><title>.id({_group_svg_id(group_name)})</title></path>'

    return svg


def _write_svg_circle(point, identifier):
    return f'<circle style="fill: rgb(216, 216, 216);" cx="{point[0]}" cy="{-point[1]}" r="0.9054"><title>.id({identifier})</title></circle>'


def _write_into_svg_format(connected_paths, markers, network_points):
    svg = '<svg width="1000" height="1000" viewBox="WWW XXX YYY ZZZ" xmlns="http://www.w3.org/2000/svg">'
    size_of_digits = len(f'{len(network_points)}')
    for index, network_point in enumerate(network_points):
        svg += _write_svg_circle(network_point, _define_point_title(index, size_of_digits))

    for group_name, connected_path in connected_paths.items():
        svg += _write_connected_svg_bezier_path(connected_path, group_name=group_name if group_name != "ungrouped" else None)

    # for i in range(len(bezier_path)):
    #     b = bezier_path[i]
    #     svg += f'<circle cx="{b[0][0]}" cy="{b[0][1]}" r="2" fill="green"/>\n'
    #     svg += f'<circle cx="{b[1][0]}" cy="{b[1][1]}" r="1" fill="yellow"/>\n'
    #     svg += f'<circle cx="{b[2][0]}" cy="{b[2][1]}" r="1" fill="purple"/>\n'
    #     svg += f'<circle cx="{b[3][0]}" cy="{b[3][1]}" r="2" fill="brown"/>\n'
    #     svg += f'<path d="M {b[0][0]} {b[0][1]} L {b[1][0]} {b[1][1]}" stroke="pink"/>\n'
    #     svg += f'<path d="M {b[3][0]} {b[3][1]} L {b[2][0]} {b[2][1]}" stroke="orange"/>\n'

    for marker in markers:
        try:
            svg += f'<circle cx="{marker[1][0]}" cy="{-marker[1][1]}" r="1" fill="none">'
            svg += f'<title>.id({marker[0]})</title>'
            svg += '</circle>'
        except IndexError:
            logger.warning(f"Invalid marker for export: {marker}")

    svg += '</svg>'

    return svg


def _reverse_map_annotations(csv_reader):
    reverse_map = {}
    if csv_reader:
        first = True

        for row in csv_reader:
            if first:
                first = False
            else:
                reverse_map[row[1]] = row[0]

    return reverse_map


def _label_has_annotations(entry, annotation_map):
    return entry in annotation_map and annotation_map[entry] and annotation_map[entry] != "None"


def _is_annotation_csv_file(csv_reader):
    """
    Check if the given CSV reader represents an annotation CSV file.

    Args:
        csv_reader (csv.reader): The CSV reader to check.

    Returns:
        bool: True if it represents an annotation CSV file, False otherwise.
    """
    if csv_reader:
        first = True

        for row in csv_reader:
            if first:
                if len(row) == 2 and row[0] == "Term ID" and row[1] == "Group name":
                    first = False
                else:
                    return False
            elif len(row) != 2:
                return False

        return True

    return False
