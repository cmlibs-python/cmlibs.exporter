"""
Export an Argon document to source document(s) suitable for the generating
flatmaps from.
"""
import json
import os
import random

from svgpathtools import svg2paths
from xml.dom.minidom import parseString

from cmlibs.zinc.field import Field
from cmlibs.zinc.node import Node
from cmlibs.zinc.result import RESULT_OK

from cmlibs.exporter.base import BaseExporter
from cmlibs.maths.vectorops import sub, div, add
from cmlibs.utils.zinc.field import get_group_list


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
        path_points = _analyze_elements(region, "coordinates")
        bezier = _calculate_bezier_control_points(path_points)
        markers = _calculate_markers(region, "coordinates")
        svg_string = _write_into_svg_format(bezier, markers)
        paths, attributes = svg2paths(svg_string)
        bbox = [999999999, -999999999, 999999999, -999999999]
        for p in paths:
            path_bbox = p.bbox()
            bbox[0] = min(path_bbox[0], bbox[0])
            bbox[1] = max(path_bbox[1], bbox[1])
            bbox[2] = min(path_bbox[2], bbox[2])
            bbox[3] = max(path_bbox[3], bbox[3])

        view_margin = 10
        view_box = (int(bbox[0] + 0.5) - view_margin,
                    int(bbox[2] + 0.5) - view_margin,
                    int(bbox[1] - bbox[0] + 0.5) + 2 * view_margin,
                    int(bbox[3] - bbox[2] + 0.5) + 2 * view_margin)

        svg_string = svg_string.replace('viewBox="WWW XXX YYY ZZZ"', f'viewBox="{view_box[0]} {view_box[1]} {view_box[2]} {view_box[3]}"')

        svg_string = parseString(svg_string).toprettyxml()

        features = {}
        for path_key in path_points:
            if path_key.endswith('_name'):
                features[path_key] = {
                    "name": path_points[path_key],
                    "type": "nerve",
                }

        for marker in markers:
            feature = {
                "name": marker[2],
                "models": marker[3],
                "colour": "orange"
            }
            features[marker[0]] = feature

        properties = {"features": features}

        with open(f'{os.path.join(self._output_target, self._prefix)}.svg', 'w') as f:
            f.write(svg_string)

        with open(f'{os.path.join(self._output_target, f"{self._prefix}_properties")}.json', 'w') as f:
            json.dump(properties, f, default=lambda o: o.__dict__, sort_keys=True, indent=2)


def _calculate_markers(region, coordinate_field_name):
    probable_group_names = ['marker', 'markers']
    fm = region.getFieldmodule()
    coordinate_field = fm.findFieldByName('marker_data_coordinates').castFiniteElement()
    name_field = fm.findFieldByName('marker_data_name')
    id_field = fm.findFieldByName('marker_data_id')

    markers_group = Field()
    for probable_group_name in probable_group_names:
        markers_group = fm.findFieldByName(probable_group_name)
        if markers_group.isValid():
            break

    marker_data = []
    if markers_group.isValid():
        markers_group = markers_group.castGroup()
        marker_node_set = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
        marker_datapoints = markers_group.getNodesetGroup(marker_node_set)
        marker_iterator = marker_datapoints.createNodeiterator()
        components_count = coordinate_field.getNumberOfComponents()

        marker = marker_iterator.next()
        fc = fm.createFieldcache()

        i = 0
        while marker.isValid():
            fc.setNode(marker)
            result, values = coordinate_field.evaluateReal(fc, components_count)
            if name_field.isValid():
                name = name_field.evaluateString(fc)
            else:
                name = f"Unnamed marker {i + 1}"

            if id_field.isValid():
                onto_id = id_field.evaluateString(fc)
            else:
                rand_num = random.randint(1, 99999)
                onto_id = f"UBERON:99{rand_num:0=5}"
            marker_data.append((f"marker_{marker.getIdentifier()}", values[:2], name, onto_id))
            marker = marker_iterator.next()
            i += 1

    return marker_data


def _analyze_elements(region, coordinate_field_name):
    fm = region.getFieldmodule()
    mesh = fm.findMeshByDimension(1)
    coordinates = fm.findFieldByName(coordinate_field_name).castFiniteElement()

    if mesh is None:
        return []

    if mesh.getSize() == 0:
        return []

    group_list = get_group_list(fm)
    group_index = 0
    groups = {
        "ungrouped": []
    }
    for group in group_list:
        group_name = group.getName()
        if group_name != "marker":
            group_label = f"group_{group_index + 1}"
            groups[group_label] = []
            groups[f"{group_label}_name"] = group_name
        group_index += 1
    el_iterator = mesh.createElementiterator()

    element = el_iterator.next()
    while element.isValid():
        eft = element.getElementfieldtemplate(coordinates, -1)
        function_count = eft.getNumberOfFunctions()
        status = [function_count == 4]
        for f in range(1, function_count + 1):
            term_count = eft.getFunctionNumberOfTerms(f)
            status.append(term_count == 1)

        if all(status):
            values_1, derivatives_1 = _get_parameters_from_eft(element, eft, coordinates)
            values_2, derivatives_2 = _get_parameters_from_eft(element, eft, coordinates, False)

            group_index = 0
            in_group = False
            for group in group_list:
                mesh_group = group.getMeshGroup(mesh)
                if mesh_group.containsElement(element):
                    group_label = f"group_{group_index + 1}"
                    groups[group_label].append([(values_1, derivatives_1), (values_2, derivatives_2)])
                    in_group = True

                group_index += 1

            if not in_group:
                groups["ungrouped"].append([(values_1, derivatives_1), (values_2, derivatives_2)])

        element = el_iterator.next()

    return groups


def _get_parameters_from_eft(element, eft, coordinates, first=True):
    start_fn = 0 if first else 2
    ln = eft.getTermLocalNodeIndex(start_fn + 1, 1)
    node_1 = element.getNode(eft, ln)
    version = eft.getTermNodeVersion(start_fn + 1, 1)
    values = _get_node_data(node_1, coordinates, Node.VALUE_LABEL_VALUE, version)
    version = eft.getTermNodeVersion(start_fn + 2, 1)
    derivatives = _get_node_data(node_1, coordinates, Node.VALUE_LABEL_D_DS1, version)

    return values, derivatives


def _get_node_data(node, coordinate_field, node_parameter, version):
    fm = coordinate_field.getFieldmodule()
    fc = fm.createFieldcache()

    components_count = coordinate_field.getNumberOfComponents()

    if node.isValid():
        fc.setNode(node)
        result, values = coordinate_field.getNodeParameters(fc, -1, node_parameter, version, components_count)
        if result == RESULT_OK:
            return values

    return None


def _calculate_bezier_curve(pt_1, pt_2):
    h0 = pt_1[0][:2]
    v0 = pt_1[1][:2]
    h1 = pt_2[0][:2]
    v1 = pt_2[1][:2]

    b0 = h0
    b1 = sub(h0, div(v0, 3))
    b2 = add(h1, div(v1, 3))
    b3 = h1

    return b0, b1, b2, b3


def _calculate_bezier_control_points(point_data):
    bezier = {}

    for point_group in point_data:
        if point_data[point_group] and not point_group.endswith("_name"):
            bezier[point_group] = []
            for curve_pts in point_data[point_group]:
                bezier[point_group].append(_calculate_bezier_curve(curve_pts[0], curve_pts[1]))

    return bezier


def _write_svg_bezier_path(bezier_path, ungrouped=False):
    svg = ''
    for i in range(len(bezier_path)):
        b = bezier_path[i]
        stroke_attr = 'stroke="blue" ' if ungrouped else ''  # if i % 2 == 0 else 'red'
        svg += f'<path d="M {b[0][0]} {b[0][1]} C {b[1][0]} {b[1][1]}, {b[2][0]} {b[2][1]}, {b[3][0]} {b[3][1]}" {stroke_attr} fill-opacity="0.0"/>'

    return svg


def _write_into_svg_format(bezier_data, markers):
    title_count = 0
    svg = '<svg width="1000" height="1000" viewBox="WWW XXX YYY ZZZ" xmlns="http://www.w3.org/2000/svg">'
    for group_name in bezier_data:
        if group_name == "ungrouped":
            svg += _write_svg_bezier_path(bezier_data[group_name], True)
        else:
            title_count += 1
            svg += f'<g><title id="title{title_count}">.id({group_name}_name)</title>'
            svg += _write_svg_bezier_path(bezier_data[group_name])
            svg += f'</g>'

    # for i in range(len(bezier_path)):
    #     b = bezier_path[i]
    #     svg += f'<circle cx="{b[0][0]}" cy="{b[0][1]}" r="2" fill="green"/>\n'
    #     svg += f'<circle cx="{b[1][0]}" cy="{b[1][1]}" r="1" fill="yellow"/>\n'
    #     svg += f'<circle cx="{b[2][0]}" cy="{b[2][1]}" r="1" fill="purple"/>\n'
    #     svg += f'<circle cx="{b[3][0]}" cy="{b[3][1]}" r="2" fill="brown"/>\n'
    #     svg += f'<path d="M {b[0][0]} {b[0][1]} L {b[1][0]} {b[1][1]}" stroke="pink"/>\n'
    #     svg += f'<path d="M {b[3][0]} {b[3][1]} L {b[2][0]} {b[2][1]}" stroke="orange"/>\n'

    for marker in markers:
        title_count += 1
        svg += f'<circle cx="{marker[1][0]}" cy="{marker[1][1]}" r="3" fill-opacity="0.0">'
        svg += f'<title id="title{title_count}">.id({marker[0]})</title>'
        svg += '</circle>'

    svg += '</svg>'



    return svg
