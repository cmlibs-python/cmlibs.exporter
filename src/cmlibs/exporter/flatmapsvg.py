"""
Export an Argon document to source document(s) suitable for the generating
flatmaps from.
"""
import os

from cmlibs.zinc.node import Node
from cmlibs.zinc.result import RESULT_OK

from cmlibs.exporter.base import BaseExporter
from cmlibs.maths.vectorops import sub, div, add


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
        svg_string = _write_into_svg_format(bezier)

        with open(f'{os.path.join(self._output_target, self._prefix)}.svg', 'w') as f:
            f.write(svg_string)


def _analyze_elements(region, coordinate_field_name):
    fm = region.getFieldmodule()
    mesh = fm.findMeshByDimension(1)
    coordinates = fm.findFieldByName(coordinate_field_name).castFiniteElement()

    if mesh is None:
        return []

    if mesh.getSize() == 0:
        return []

    el_iterator = mesh.createElementiterator()

    element = el_iterator.next()
    element_data = []
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

            element_data.append([(values_1, derivatives_1), (values_2, derivatives_2)])
        element = el_iterator.next()

    return element_data


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
    bezier = []

    for curve_pts in point_data:
        bezier.append(_calculate_bezier_curve(curve_pts[0], curve_pts[1]))

    return bezier


def _write_into_svg_format(bezier_path):
    svg = '<svg width="1000" height="1000" xmlns="http://www.w3.org/2000/svg">\n'
    for i in range(len(bezier_path)):
        b = bezier_path[i]
        colour = 'blue' if i % 2 == 0 else 'red'
        svg += f'<path d="M {b[0][0]} {b[0][1]} C {b[1][0]} {b[1][1]}, {b[2][0]} {b[2][1]}, {b[3][0]} {b[3][1]}" stroke="{colour}" fill-opacity="0.0"/>\n'

    # for i in range(len(bezier_path)):
    #     b = bezier_path[i]
    #     svg += f'<circle cx="{b[0][0]}" cy="{b[0][1]}" r="2" fill="green"/>\n'
    #     svg += f'<circle cx="{b[1][0]}" cy="{b[1][1]}" r="1" fill="yellow"/>\n'
    #     svg += f'<circle cx="{b[2][0]}" cy="{b[2][1]}" r="1" fill="purple"/>\n'
    #     svg += f'<circle cx="{b[3][0]}" cy="{b[3][1]}" r="2" fill="brown"/>\n'
    #     svg += f'<path d="M {b[0][0]} {b[0][1]} L {b[1][0]} {b[1][1]}" stroke="pink"/>\n'
    #     svg += f'<path d="M {b[3][0]} {b[3][1]} L {b[2][0]} {b[2][1]}" stroke="orange"/>\n'

    svg += '</svg>'

    return svg
