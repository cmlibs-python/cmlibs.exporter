"""
Export an Argon document to source document(s) suitable for the generating
flatmaps from.
"""
import os

from cmlibs.zinc.field import Field
from cmlibs.zinc.node import Node
from cmlibs.zinc.result import RESULT_OK

from cmlibs.exporter.base import BaseExporter
from cmlibs.maths.vectorops import sub, div, add
from cmlibs.utils.zinc.general import ChangeManager


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

    def export_flatmapsvg(self):
        """
        Export graphics into JSON format, one json export represents one Zinc graphics.
        """
        scene = self._document.getRootRegion().getZincRegion().getScene()
        self.export_flatmapsvg_from_scene(scene)

    def export_flatmapsvg_from_scene(self, scene, scene_filter=None):
        """
        Export graphics from a Zinc Scene into WebGL JSON format.

        :param scene: The Zinc Scene object to be exported.
        :param scene_filter: Optional; A Zinc Scenefilter object associated with the Zinc scene, allowing the user to filter which
            graphics are included in the export.
        """
        region = scene.getRegion()
        data = _calculate_node_derivative(region, "coordinates")
        bezier = _calculate_bezier_control_points(data)
        svg_string = _write_into_svg_format(bezier)

        with open(f'{os.path.join(self._output_target, self._prefix)}.svg', 'w') as f:
            f.write(svg_string)


def _calculate_node_derivative(region, coordinate_field_name):
    fm = region.getFieldmodule()
    fc = fm.createFieldcache()
    node_derivatives = [Node.VALUE_LABEL_D_DS1, Node.VALUE_LABEL_D_DS2]
    derivatives_count = len(node_derivatives)

    nodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
    node_iter = nodes.createNodeiterator()

    coordinates = fm.findFieldByName(coordinate_field_name).castFiniteElement()
    components_count = coordinates.getNumberOfComponents()

    data = []
    with ChangeManager(fm):

        node = node_iter.next()
        while node.isValid():
            fc.setNode(node)
            result, x = coordinates.evaluateReal(fc, coordinates.getNumberOfComponents())
            if result == RESULT_OK:
                # print(f"values: {x}")
                # proj_x = _node_values_fcn(x)
                # coordinates.assignReal(fc, proj_x)
                parameter_data = {}
                for d in range(derivatives_count):
                    result, values = coordinates.getNodeParameters(fc, -1, node_derivatives[d], 1, components_count)
                    if result == RESULT_OK:
                        parameter_data[node_derivatives[d]] = values
                        # proj_param = _node_parameters_fcn(values)
                        # coordinates.setNodeParameters(fc, -1, node_derivatives[d], 1, proj_param)

                derivative = [parameter_data[Node.VALUE_LABEL_D_DS1][i] for i in range(components_count)]
                # print("derivative:", derivative)
                data.append((x, derivative))
            node = node_iter.next()

    return data


def _calculate_bezier_control_points(data):
    bezier = []

    for i in range(len(data)):
        if i == len(data) - 1:
            continue

        h0 = data[i][0][:2]
        v0 = data[i][1][:2]
        h1 = data[i+1][0][:2]
        v1 = data[i+1][1][:2]

        b0 = h0
        b1 = sub(h0, div(v0, 3))
        b2 = add(h1, div(v1, 3))
        b3 = h1

        bezier.append((b0, b1, b2, b3))

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
