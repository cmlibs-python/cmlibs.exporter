"""
Export an Argon document to Wavefront documents.
"""
import math
import re

from cmlibs.argon.argondocument import ArgonDocument
from cmlibs.exporter.base import BaseExporter
from cmlibs.exporter.errors import ExportWavefrontError

from cmlibs.zinc.status import OK as ZINC_OK


def _parse_meta_buffer(buffer):
    call_line_re = re.compile("^call (.*)$")
    filenames = []
    for line in buffer.split("\n"):
        result = call_line_re.match(line)
        if result:
            filenames.append(result.group(1))

    return filenames


class ArgonSceneExporter(BaseExporter):
    """
    Export a visualisation described by an Argon document to Wavefront.
    """

    def __init__(self, output_target=None, output_prefix=None):
        """
        :param output_target: The target directory to export the visualisation to.
        :param output_prefix: The prefix for the exported file(s).
        """
        super(ArgonSceneExporter, self).__init__("ArgonSceneExporterWavefront" if output_prefix is None else output_prefix)
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

        self.export_wavefront()

    def export_wavefront(self):
        """
        Export graphics into Wavefront format, one Wavefront export represents one Zinc graphics.
        """
        scene = self._document.getRootRegion().getZincRegion().getScene()
        self.export_wavefront_from_scene(scene)

    def export_wavefront_from_scene(self, scene, scene_filter=None):
        """
        Export graphics from a Zinc Scene into Wavefront format.

        :param scene: The Zinc Scene object to be exported.
        :param scene_filter: Optional; A Zinc Scenefilter object associated with the Zinc scene, allowing the user to filter which
            graphics are included in the export.
        """
        sceneSR = scene.createStreaminformationScene()
        sceneSR.setIOFormat(sceneSR.IO_FORMAT_WAVEFRONT)

        # Optionally filter the scene.
        if scene_filter:
            sceneSR.setScenefilter(scene_filter)

        number = sceneSR.getNumberOfResourcesRequired()
        if number == 0:
            raise ExportWavefrontError("No resources available for export.")

        resources = []
        """Write out each graphics into a json file which can be rendered with ZincJS"""
        for i in range(number):
            resources.append(sceneSR.createStreamresourceMemory())

        scene.write(sceneSR)

        number_of_digits = math.floor(math.log10(number)) + 1

        def _resource_filename(prefix, i_):
            return f'{prefix}_{str(i_).zfill(number_of_digits)}.obj'

        """Write out each resource into their own file"""
        resource_count = 0
        obj_filenames = []
        for i in range(number):
            result, buffer = resources[i].getBuffer()
            if result != ZINC_OK:
                raise ExportWavefrontError("Experienced an error exporting Wavefront from Zinc.")

            if buffer is None:
                # Maybe this is a bug in the resource counting.
                continue

            buffer = buffer.decode()

            if resource_count == 0:
                obj_filenames = _parse_meta_buffer(buffer)
                current_file = self._form_full_filename(self ._metadata_file())
            else:
                current_file = self._form_full_filename(obj_filenames[resource_count - 1])

            with open(current_file, 'w') as f:
                f.write(buffer)

            resource_count += 1

    def _metadata_file(self):
        return self._form_full_filename(self._prefix + '_base.obj')
