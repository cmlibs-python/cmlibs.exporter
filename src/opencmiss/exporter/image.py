"""
Export an Argon document to a JPEG file of size Width x Height.
"""
from opencmiss.exporter.baseimage import BaseImageExporter


class ArgonSceneExporter(BaseImageExporter):
    """
    Export a visualisation described by an Argon document to JPEG image.
    See the BaseImageExporter for rendering options.
    """

    def __init__(self, width, height, output_target=None, output_prefix=None):
        """
        :param output_target: The target directory to export the visualisation to.
        :param output_prefix: The prefix to apply to the output.
        """
        local_output_target = '.' if output_target is None else output_target
        local_output_prefix = "ArgonSceneExporterImage" if output_prefix is None else output_prefix
        super(ArgonSceneExporter, self).__init__(width, height, "image", output_target=local_output_target, output_prefix=local_output_prefix)
