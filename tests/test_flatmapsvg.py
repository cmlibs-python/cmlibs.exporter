import json
import os.path
import unittest
import xml.etree.ElementTree as ET

from cmlibs.zinc.context import Context

from cmlibs.exporter import flatmapsvg
from cmlibs.exporter.flatmapsvg import _connected_segments

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
        properties_file = _resource_path("properties.json")
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


class FindConnectedSet(unittest.TestCase):

    def test_simple(self):
        null = [0, 0]
        p1 = [1, 1]
        p2 = [2, 2]
        p3 = [3, 3]
        p4 = [4, 4]
        p5 = [5, 5]
        p6 = [6, 6]
        p7 = [7, 7]

        c1 = [[p1, null, null, p2], [p2, null, null, p3], [p3, null, null, p4], [p4, null, null, p5]]
        c2 = [[p1, null, null, p2], [p2, null, null, p3], [p5, null, null, p6], [p6, null, null, p7]]
        c3 = [[p2, null, null, p3], [p3, null, null, p4], [p1, null, null, p2], [p4, null, null, p5]]

        self.assertEqual(1, len(_connected_segments(c1)))
        self.assertEqual(2, len(_connected_segments(c2)))
        segmented_c3 = _connected_segments(c3)
        self.assertEqual(1, len(segmented_c3))
        self.assertEqual(p1, segmented_c3[0][0][0])

    def test_real_data(self):
        null = [0, 0]
        p1 = [-38.76407990290047, 136.95711038948954]
        p2 = [-38.66539406842079, 135.3388544011657]
        p3 = [-38.66539406842079, 135.3388544011657]
        p4 = [-38.57638526850839, 133.768421782719]
        p5 = [-38.57638526850839, 133.768421782719]
        p6 = [-38.50103491179091, 132.19996302635846]
        p7 = [-38.5010349117909, 132.1999630263585]

        c1 = [[p1, null, null, p2], [p2, null, null, p3], [p3, null, null, p4], [p4, null, null, p5]]
        c2 = [[p1, null, null, p2], [p2, null, null, p3], [p5, null, null, p6], [p6, null, null, p7]]
        c3 = [[p3, null, null, p4], [p2, null, null, p3], [p4, null, null, p5], [p1, null, null, p2]]

        self.assertEqual(1, len(_connected_segments(c1)))
        self.assertEqual(2, len(_connected_segments(c2)))
        segmented_c3 = _connected_segments(c3)
        self.assertEqual(2, len(segmented_c3))
        print(segmented_c3)
        self.assertEqual(p2, segmented_c3[0][0][0])

    def test_real_data_single_section(self):
        null = [0, 0]
        p1 = [-38.76407990290047, 136.95711038948954]
        p2 = [-38.66539406842078, 135.33885440116572]
        p3 = [-38.66539406842079, 135.3388544011657]
        p4 = [-38.57638526850839, 133.76842178271903]
        p5 = [-38.57638526850839, 133.768421782719]
        p6 = [-38.50103491179091, 132.19996302635846]
        p7 = [-38.5010349117909, 132.1999630263585]

        c1 = [[p1, null, null, p2], [p2, null, null, p3], [p3, null, null, p4], [p4, null, null, p5], [p6, null, null, p7]]

        self.assertEqual(2, len(_connected_segments(c1)))

    def test_real_data_fork(self):
        null = [0, 0]
        p1 = [-38.76407990290047, 136.95711038948954]
        p2 = [-38.66539406842078, 135.33885440116572]
        p3 = [-38.66539406842079, 135.3388544011657]
        p4 = [-38.57638526850839, 133.76842178271903]
        p5 = [-38.57638526850839, 133.768421782719]
        p6 = [-38.50103491179091, 132.19996302635846]
        p7 = [-38.5010349117909, 132.1999630263585]

        c1 = [[p1, null, null, p2], [p2, null, null, p3], [p3, null, null, p4], [p4, null, null, p5], [p3, null, null, p6], [p6, null, null, p7]]

        self.assertEqual(2, len(_connected_segments(c1)))
