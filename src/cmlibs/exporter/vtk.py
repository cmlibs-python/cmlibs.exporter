"""
Export an Argon document to VTK.
"""
import os.path

from cmlibs.argon.argondocument import ArgonDocument
from cmlibs.exporter.base import BaseExporter
from cmlibs.exporter.errors import ExportVTKError
from cmlibs.utils.zinc.finiteelement import getElementNodeIdentifiersBasisOrder
from cmlibs.zinc.field import Field
from cmlibs.zinc.result import RESULT_OK


def _write(out_stream, region):
    field_module = region.getFieldmodule()
    coordinates = field_module.findFieldByName('coordinates').castFiniteElement()
    nodes = field_module.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
    mesh = None
    for dimension in range(3, 1, -1):
        mesh = field_module.findMeshByDimension(dimension)
        if mesh.getSize() > 0:
            break

    if mesh is None:
        return

    if mesh.getSize() == 0:
        return

    out_stream.write('# vtk DataFile Version 2.0\n')
    out_stream.write('Export of CMLibs Zinc region.\n')
    out_stream.write('ASCII\n')
    out_stream.write('DATASET UNSTRUCTURED_GRID\n')
    nodeIdentifierToIndex = {}  # map needed since vtk points are zero index based, i.e. have no identifier
    coordinatesCount = coordinates.getNumberOfComponents()
    cache = field_module.createFieldcache()

    # exclude marker nodes from output
    pointCount = nodes.getSize()
    out_stream.write('POINTS ' + str(pointCount) + ' double\n')
    nodeIter = nodes.createNodeiterator()
    node = nodeIter.next()
    index = 0
    while node.isValid():
        nodeIdentifierToIndex[node.getIdentifier()] = index
        cache.setNode(node)
        result, x = coordinates.evaluateReal(cache, coordinatesCount)
        if result != RESULT_OK:
            print("Coordinates not found for node", node.getIdentifier())
            x = [0.0] * coordinatesCount
        if coordinatesCount < 3:
            for c in range(coordinatesCount - 1, 3):
                x.append(0.0)
        out_stream.write(" ".join(str(s) for s in x) + "\n")
        index += 1
        node = nodeIter.next()

    if mesh is None:
        raise ExportVTKError("No mesh found in scene.")
    # following assumes all hex (3-D) or all quad (2-D) elements
    if mesh.getDimension() == 2:
        localNodeCount = 4
        vtkIndexing = [0, 1, 3, 2]
        cellTypeString = '9'
    else:
        localNodeCount = 8
        vtkIndexing = [0, 1, 3, 2, 4, 5, 7, 6]
        cellTypeString = '12'
    localNodeCountStr = str(localNodeCount)
    cellCount = mesh.getSize()
    cellListSize = (1 + localNodeCount) * cellCount
    out_stream.write('CELLS ' + str(cellCount) + ' ' + str(cellListSize) + '\n')
    elementIter = mesh.createElementiterator()
    element = elementIter.next()
    while element.isValid():
        eft = element.getElementfieldtemplate(coordinates, -1)  # assumes all components same
        nodeIdentifiers = getElementNodeIdentifiersBasisOrder(element, eft)
        out_stream.write(localNodeCountStr)
        for localIndex in vtkIndexing:
            index = nodeIdentifierToIndex[nodeIdentifiers[localIndex]]
            out_stream.write(' ' + str(index))
        out_stream.write('\n')
        element = elementIter.next()
    out_stream.write('CELL_TYPES ' + str(cellCount) + '\n')
    for i in range(cellCount - 1):
        out_stream.write(cellTypeString + ' ')
    out_stream.write(cellTypeString + '\n')


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
        self.export_vtk_from_scene(scene)

    def export_vtk_from_scene(self, scene, scene_filter=None):
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
        name = "root"
        if region:
            region_name = region.getName()
            if region_name and region_name != "/":
                name = region_name

        return f"{self._prefix}_{name}.vtk"
