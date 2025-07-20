"""
Export an Argon document to MBF XML file specification format.
"""

from cmlibs.exporter.base import BaseExporter

from exf2mbfxml.reader import extract_mesh_info
from exf2mbfxml.writer import write_mbfxml
from exf2mbfxml.analysis import is_suitable_mesh


class ArgonSceneExporter(BaseExporter):
    """
    Export a visualisation described by an Argon document to webGL.
    """

    def __init__(self, output_target=None, output_prefix=None):
        """
        :param output_target: The target directory to export the visualisation to.
        :param output_prefix: The prefix for the exported file(s).
        """
        super(ArgonSceneExporter, self).__init__("ArgonSceneExporterMBFXML" if output_prefix is None else output_prefix)
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

        self.export_mbfxml()

    def export_mbfxml(self):
        """
        Export graphics into MBF XML format.
        Supports 1D meshes where the elements all have the same element template with two nodes.
        """
        scene = self._document.getRootRegion().getZincRegion().getScene()
        self.export_from_scene(scene)

    def export_from_scene(self, scene, scene_filter=None):
        """
        Export graphics from a Zinc Scene into MBF XML format.

        :param scene: The Zinc Scene object to be exported.
        :param scene_filter: Optional; A Zinc Scenefilter object associated with the Zinc scene, allowing the user to filter which
            graphics are included in the export.
        """
        region = scene.getRegion()
        self._export_region(region)
        
    def _export_region(self, region):
        content = extract_mesh_info(region)
        output_file = self._form_full_filename(self._prefix + ".xml")
        write_mbfxml(output_file, content)

    def is_valid(self, document=None):
        if document is None:
            document = self._document

        if document is None:
            return False

        region = document.getRootRegion().getZincRegion()
        return is_suitable_mesh(region)
