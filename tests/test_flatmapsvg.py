import json
import os.path
import unittest
import xml.etree.ElementTree as ET

from cmlibs.zinc.context import Context

from cmlibs.exporter import flatmapsvg


here = os.path.abspath(os.path.dirname(__file__))


def _resource_path(resource_name):
    return os.path.join(here, "resources", resource_name)


class Exporter(unittest.TestCase):

    def test_flatmap_svg(self):
        source_model = _resource_path("flattened_vagus.exf")
        output_target = _resource_path("")

        exporter = flatmapsvg.ArgonSceneExporter(output_target=output_target, output_prefix="vagus")

        c = Context('generate_flatmap_svg')
        root_region = c.getDefaultRegion()
        root_region.readFile(source_model)

        exporter.export_from_scene(root_region.getScene())
        flatmap_svg_file = _resource_path("vagus.svg")
        self.assertTrue(os.path.isfile(flatmap_svg_file))
        properties_file = _resource_path("vagus_properties.json")
        self.assertTrue(os.path.isfile(properties_file))

        tree = ET.parse(flatmap_svg_file)
        root = tree.getroot()

        self.assertEqual(18, len(root))

        with open(properties_file) as f:
            content = json.load(f)

        self.assertIn("features", content)
        self.assertEqual(18, len(content["features"]))

        os.remove(flatmap_svg_file)
        os.remove(properties_file)
