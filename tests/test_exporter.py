import os.path
import unittest

from opencmiss.exporter import thumbnail


here = os.path.abspath(os.path.dirname(__file__))


def _resource_path(resource_name):
    return os.path.join(here, "resources", resource_name)


class Exporter(unittest.TestCase):

    def test_thumbnail(self):
        argon_document = _resource_path("argon-document.json")
        output_target = _resource_path("")

        exporter = thumbnail.ArgonSceneExporter(output_target=output_target)
        exporter.load(argon_document)
        exporter.export_thumbnail()
        thumbnail_file = _resource_path("ArgonSceneExporterThumbnail_Layout1_thumbnail.jpeg")
        self.assertTrue(os.path.isfile(thumbnail_file))

        os.remove(thumbnail_file)
