"""
Export an Argon document to an STL document.
"""
from cmlibs.argon.argondocument import ArgonDocument
from cmlibs.exporter.base import BaseExporter
from cmlibs.exporter.errors import ExportSTLError

from cmlibs.zinc.status import OK as ZINC_OK


class ArgonSceneExporter(BaseExporter):
    """
    Export a visualisation described by an Argon document to STL.
    """

    def __init__(self, output_target=None, output_prefix=None):
        """
        :param output_target: The target directory to export the visualisation to.
        :param output_prefix: The prefix for the exported file(s).
        """
        super(ArgonSceneExporter, self).__init__("ArgonSceneExporterSTL" if output_prefix is None else output_prefix)
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

        self.export_stl()

    def export_stl(self):
        """
        Export surface and line graphics into STL format.
        """
        scene = self._document.getRootRegion().getZincRegion().getScene()
        self.export_stl_from_scene(scene)

    def export_stl_from_scene(self, scene, scene_filter=None):
        """
        Export graphics from a Zinc Scene into STL format.

        :param scene: The Zinc Scene object to be exported.
        :param scene_filter: Optional; A Zinc Scenefilter object associated with the Zinc scene, allowing the user to filter which
            graphics are included in the export.
        """
        sceneSR = scene.createStreaminformationScene()
        sceneSR.setIOFormat(sceneSR.IO_FORMAT_ASCII_STL)

        # Optionally filter the scene.
        if scene_filter:
            sceneSR.setScenefilter(scene_filter)

        number = sceneSR.getNumberOfResourcesRequired()
        if number == 0:
            raise ExportSTLError("No resources available for export.")

        memory_resource = sceneSR.createStreamresourceMemory()

        scene.write(sceneSR)

        result, buffer = memory_resource.getBuffer()
        if result != ZINC_OK:
            raise ExportSTLError("Experienced an error exporting STL from Zinc.")

        buffer = buffer.decode()
        stl_file = self._form_full_filename(self._stl_filename(scene.getRegion()))
        try:
            with open(stl_file, 'w') as f:
                f.write(buffer)
        except IOError:
            raise ExportSTLError(f"Failed to write STL file: {stl_file}")

    def _stl_filename(self, region):
        name = "zinc_graphics"
        if region:
            region_name = region.getName()
            if region_name and region_name != "/":
                name = region_name

        return f"{self._prefix}_{name}.stl"
