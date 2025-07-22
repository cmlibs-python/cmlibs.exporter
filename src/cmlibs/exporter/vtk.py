"""
Export an Argon document to VTK.
"""
import io
import os.path

from cmlibs.exporter.base import BaseExporter
from cmlibs.exporter.errors import ExportVTKError
from cmlibs.utils.zinc.field import find_coordinate_fields
from cmlibs.utils.zinc.finiteelement import getElementNodeIdentifiersBasisOrder
from cmlibs.zinc.field import Field
from cmlibs.zinc.result import RESULT_OK


def _write_points_with_labels(out_stream, points_data):
    out_stream.write("# vtk DataFile Version 3.0\n")
    out_stream.write("Point data with labels\n")
    out_stream.write("ASCII\n")
    out_stream.write("DATASET POLYDATA\n")
    out_stream.write(f"POINTS {len(points_data)} float\n")
    for x, y, z, _ in points_data:
        out_stream.write(f"{x} {y} {z}\n")

    out_stream.write(f"VERTICES {len(points_data)} {len(points_data) * 2}\n")
    for i in range(len(points_data)):
        out_stream.write(f"1 {i}\n")

    out_stream.write(f"POINT_DATA {len(points_data)}\n")
    out_stream.write("SCALARS label string\n")
    out_stream.write("LOOKUP_TABLE default\n")
    for _, _, _, label in points_data:
        out_stream.write(f"{label}\n")


def _write_markers(out_stream, region, coordinate_field):
    field_module = region.getFieldmodule()
    markers_group = field_module.findFieldByName("marker").castGroup()

    marker_data = []
    if markers_group.isValid():
        marker_node_set = field_module.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        marker_points = markers_group.getNodesetGroup(marker_node_set)
        marker_iterator = marker_points.createNodeiterator()
        marker_mesh_location_field = field_module.findFieldByName("marker_location").castStoredMeshLocation()
        marker_name_field = field_module.findFieldByName("marker_name").castStoredString()
        mesh = marker_mesh_location_field.getMesh()

        marker = marker_iterator.next()
        field_cache = field_module.createFieldcache()

        i = 0
        while marker.isValid():
            field_cache.setNode(marker)
            if marker_name_field.isValid():
                name = marker_name_field.evaluateString(field_cache)
            else:
                name = f"Unnamed marker {i + 1}"
            element, values = marker_mesh_location_field.evaluateMeshLocation(field_cache, mesh.getDimension())
            field_cache.setMeshLocation(element, values)
            result, values = coordinate_field.evaluateReal(field_cache, mesh.getDimension())

            marker_data.append((*values, name))

            marker = marker_iterator.next()
            i += 1

        if marker_data:
            with open(out_stream.name[:-4] + "_marker" + out_stream.name[-4:], "w") as marker_out_stream:
                _write_points_with_labels(marker_out_stream, marker_data)


def _write_mesh(out_stream, mesh):
    field_module = mesh.getFieldmodule()
    region = field_module.getRegion()

    potential_coordinates = find_coordinate_fields(region)
    if len(potential_coordinates) == 0:
        return

    coordinates = potential_coordinates[0]

    nodeIdentifierToIndex = {}  # map needed since vtk points are zero index based, i.e. have no identifier
    nodes = field_module.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)

    coordinatesCount = coordinates.getNumberOfComponents()
    cache = field_module.createFieldcache()

    # exclude marker nodes from output
    node_buffer = io.StringIO()

    # following assumes all hex (3-D) or all quad (2-D) elements
    if mesh.getDimension() == 3:
        localNodeCount = 8
        vtkIndexing = [0, 1, 3, 2, 4, 5, 7, 6]
        cellTypeString = '12'
    elif mesh.getDimension() == 2:
        localNodeCount = 4
        vtkIndexing = [0, 1, 3, 2]
        cellTypeString = '9'
    elif mesh.getDimension() == 1:
        localNodeCount = 2
        vtkIndexing = [0, 1]
        cellTypeString = '3'
    else:
        raise ExportVTKError("Mesh dimension not supported. d =", mesh.getDimension())

    element_buffer = io.StringIO()

    cellCount = mesh.getSize()
    cellListSize = (1 + localNodeCount) * cellCount
    element_buffer.write('CELLS ' + str(cellCount) + ' ' + str(cellListSize) + '\n')
    elementIter = mesh.createElementiterator()
    element = elementIter.next()
    node_count = 0
    while element.isValid():
        eft = element.getElementfieldtemplate(coordinates, -1)  # assumes all components same
        node_identifiers = getElementNodeIdentifiersBasisOrder(element, eft)
        if node_identifiers:
            element_buffer.write(f'{localNodeCount}')
            for localIndex in vtkIndexing:

                node_identifier = node_identifiers[localIndex]
                if node_identifier not in nodeIdentifierToIndex:
                    nodeIdentifierToIndex[node_identifier] = node_count
                    node_count += 1
                index = nodeIdentifierToIndex[node_identifier]
                element_buffer.write(f' {index}')
            element_buffer.write('\n')
        element = elementIter.next()
    element_buffer.write('CELL_TYPES ' + str(cellCount) + '\n')
    for i in range(cellCount - 1):
        element_buffer.write(cellTypeString + ' ')
    element_buffer.write(cellTypeString + '\n')

    node_buffer.write(f'POINTS {node_count} double\n')

    for node_id in nodeIdentifierToIndex.keys():
        node = nodes.findNodeByIdentifier(node_id)
        cache.setNode(node)
        result, x = coordinates.evaluateReal(cache, coordinatesCount)
        if result != RESULT_OK:
            print("Coordinates not found for node", node.getIdentifier())
            x = [0.0] * coordinatesCount
        if coordinatesCount < 3:
            for c in range(coordinatesCount - 1, 3):
                x.append(0.0)
        node_buffer.write(" ".join(str(s) for s in x) + "\n")

    out_stream.write('# vtk DataFile Version 2.0\n')
    out_stream.write('Export of CMLibs Zinc region.\n')
    out_stream.write('ASCII\n')
    out_stream.write('DATASET UNSTRUCTURED_GRID\n')
    node_buffer.seek(0)
    out_stream.write(node_buffer.read())
    node_buffer.close()
    element_buffer.seek(0)
    out_stream.write(element_buffer.read())
    element_buffer.close()

    _write_markers(out_stream, region, coordinates)


def _write(out_stream, region):

    field_module = region.getFieldmodule()

    out_mesh = None
    for dimension in range(3, 0, -1):
        mesh = field_module.findMeshByDimension(dimension)
        if mesh.getSize() > 0:
            out_mesh = mesh
            break

    if out_mesh is not None:
        _write_mesh(out_stream, out_mesh)

    # Add group information to export?
    # for group in get_group_list(field_module):
    #     print(group.getName())


class ArgonSceneExporter(BaseExporter):
    """
    Export a visualisation described by an Argon document to VTK.
    """

    def __init__(self, output_target=None, output_prefix=None):
        """
        :param output_target: The target directory to export the visualisation to.
        :param output_prefix: The prefix for the exported file(s).
        """
        super(ArgonSceneExporter, self).__init__("ArgonSceneExporterVTK" if output_prefix is None else output_prefix)
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

        self.export_vtk()

    def export_vtk(self):
        """
        Export surface and line graphics into VTK format.
        """
        scene = self._document.getRootRegion().getZincRegion().getScene()
        self.export_from_scene(scene)

    def export_from_scene(self, scene, scene_filter=None):
        """
        Export graphics from a Zinc Scene into VTK format.

        :param scene: The Zinc Scene object to be exported.
        :param scene_filter: Optional; A Zinc Scenefilter object associated with the Zinc scene, allowing the user to filter which
            graphics are included in the export.
        """
        region = scene.getRegion()
        try:
            self._export_regions(region)
        except IOError:
            raise ExportVTKError(f"Failed to write VTK file.")

    def _export_regions(self, region):
        vtk_file = self._form_full_filename(self._vtk_filename(region))
        with open(vtk_file, 'w') as out_stream:
            _write(out_stream, region)

        if not os.path.getsize(vtk_file):
            os.remove(vtk_file)

        child = region.getFirstChild()
        while child.isValid():
            self._export_regions(child)
            child = child.getNextSibling()

    def _vtk_filename(self, region):
        region_name = region.getPath() if region and region.getPath() not in [None, "/", ""] else "root"
        prefix = f"{self._prefix}_" if self._prefix else ""
        return f"{prefix}{region_name.replace(' ', '_')}.vtk"
