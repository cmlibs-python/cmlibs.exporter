import json
import os.path
import unittest

from cmlibs.exporter import webgl


here = os.path.abspath(os.path.dirname(__file__))


def _resource_path(resource_name):
    return os.path.join(here, "resources", resource_name)


class WebGL(unittest.TestCase):

    def test_webgl(self):
        argon_document = _resource_path("two-cubes-lines.neon")
        output_target = _resource_path("")

        exporter = webgl.ArgonSceneExporter(output_target=output_target)
        exporter.load(argon_document)
        exporter.export_view()
        exporter.export_webgl()

        metadata_file = _resource_path("ArgonSceneExporterWebGL_metadata.json")
        view_file = _resource_path("ArgonSceneExporterWebGL_default_view.json")
        data_file = _resource_path("ArgonSceneExporterWebGL_1.json")

        self.assertTrue(os.path.isfile(metadata_file))
        self.assertTrue(os.path.isfile(view_file))
        self.assertTrue(os.path.isfile(data_file))

        with open(data_file) as fh:
            content = json.load(fh)

        self.assertEqual(720, len(content["vertices"]))

        os.remove(metadata_file)
        os.remove(view_file)
        os.remove(data_file)
