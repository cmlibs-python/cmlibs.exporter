import json
import os.path
import unittest
import xml.etree.ElementTree as ET

from cmlibs.zinc.context import Context

from cmlibs.exporter import flatmapsvg
from cmlibs.exporter.flatmapsvg import _connected_segments, _write_into_svg_format, _calculate_view_box
from cmlibs.exporter.utils.continuity import find_continuous_segments

here = os.path.abspath(os.path.dirname(__file__))


def _resource_path(resource_name):
    return os.path.join(here, "resources", resource_name)


NULL = [0, 0]


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

        self.assertEqual(8, len(root))

        with open(properties_file) as f:
            content = json.load(f)

        self.assertIn("networks", content)
        self.assertEqual(1, len(content["networks"]))
        self.assertEqual(3, len(content["networks"][0]))

        os.remove(flatmap_svg_file)
        os.remove(properties_file)

    def test_write_svg_outline(self):
        values = {'wave': [
            [([-10.0, 0.0], [-7.5, 2.5], [-2.5, 2.5], [0.0, 0.0]),
             ([0.0, 0.0], [2.5, -2.5], [7.5, -2.5], [10.0, 0.0])]]
        }
        svg_string = _write_into_svg_format(values, {}, [], {})
        self.assertTrue(len(svg_string) > 0)

        view_box = _calculate_view_box(svg_string)

        svg_string = svg_string.replace('viewBox="WWW XXX YYY ZZZ"', f'viewBox="{view_box[0]} {view_box[1]} {view_box[2]} {view_box[3]}"')

        simple_svg_file = _resource_path("simple.svg")
        with open(simple_svg_file, "w") as fh:
            fh.write(svg_string)

        os.remove(simple_svg_file)

    def test_flatmap_svg_user_mesh(self):
        source_model = _resource_path("user-projected-mesh.exf")
        source_annotations = _resource_path("user-projected-annotations.json")
        output_target = _resource_path("")

        exporter = flatmapsvg.ArgonSceneExporter(output_target=output_target, output_prefix="vagus")
        exporter.set_annotations_json_file(source_annotations)

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

        self.assertEqual(89, len(root))

        with open(properties_file) as f:
            content = json.load(f)

        self.assertTrue('features' in content)
        self.assertTrue('nerve_feature_02' in content['features'])
        self.assertTrue('label' in content['features']['nerve_feature_02'])
        self.assertIn('Right spinal accessory nerve', content['features']['nerve_feature_02']['label'])
        self.assertIn('ILX:345678', content['features']['nerve_feature_02']['label'])

        os.remove(flatmap_svg_file)
        os.remove(properties_file)


def _define_test_points():
    p1 = [-38.76407990290047, 136.95711038948954]
    p2 = [-38.66539406842078, 135.33885440116572]
    p3 = [-38.66539406842079, 135.3388544011657]
    p4 = [-38.57638526850839, 133.76842178271903]
    p5 = [-38.57638526850839, 133.768421782719]
    p6 = [-38.50103491179091, 132.19996302635846]
    p7 = [-38.5010349117909, 132.1999630263585]
    return p1, p2, p3, p4, p5, p6, p7


class FindConnectedSet(unittest.TestCase):

    def test_simple(self):

        p1 = [1, 1]
        p2 = [2, 2]
        p3 = [3, 3]
        p4 = [4, 4]
        p5 = [5, 5]
        p6 = [6, 6]
        p7 = [7, 7]

        c3 = self._setup_data(p1, p2, p3, p4, p5, p6, p7)
        segmented_c3 = _connected_segments(c3)
        self.assertEqual(1, len(segmented_c3))
        self.assertEqual(p1, segmented_c3[0][0][0])

    def _setup_data(self, p1, p2, p3, p4, p5, p6, p7, alt_c3=False):
        c1 = [[p1, NULL, NULL, p2], [p2, NULL, NULL, p3], [p3, NULL, NULL, p4], [p4, NULL, NULL, p5]]
        c2 = [[p1, NULL, NULL, p2], [p2, NULL, NULL, p3], [p5, NULL, NULL, p6], [p6, NULL, NULL, p7]]
        if alt_c3:
            c3 = [[p3, NULL, NULL, p4], [p2, NULL, NULL, p3], [p4, NULL, NULL, p5], [p1, NULL, NULL, p2]]
        else:
            c3 = [[p2, NULL, NULL, p3], [p3, NULL, NULL, p4], [p1, NULL, NULL, p2], [p4, NULL, NULL, p5]]

        self.assertEqual(1, len(_connected_segments(c1)))
        self.assertEqual(2, len(_connected_segments(c2)))
        return c3

    def test_real_data(self):
        p1 = [-38.76407990290047, 136.95711038948954]
        p2 = [-38.66539406842079, 135.3388544011657]
        p3 = [-38.66539406842079, 135.3388544011657]
        p4 = [-38.57638526850839, 133.768421782719]
        p5 = [-38.57638526850839, 133.768421782719]
        p6 = [-38.50103491179091, 132.19996302635846]
        p7 = [-38.5010349117909, 132.1999630263585]

        c3 = self._setup_data(p1, p2, p3, p4, p5, p6, p7, alt_c3=True)
        segmented_c3 = _connected_segments(c3)
        self.assertEqual(2, len(segmented_c3))
        self.assertEqual(p2, segmented_c3[0][0][0])

    def test_real_data_single_section(self):
        p1, p2, p3, p4, p5, p6, p7 = _define_test_points()

        c1 = [[p1, NULL, NULL, p2], [p2, NULL, NULL, p3], [p3, NULL, NULL, p4], [p4, NULL, NULL, p5], [p6, NULL, NULL, p7]]

        self.assertEqual(2, len(_connected_segments(c1)))

    def test_real_data_fork(self):
        p1, p2, p3, p4, p5, p6, p7 = _define_test_points()

        c1 = [[p1, NULL, NULL, p2], [p2, NULL, NULL, p3], [p3, NULL, NULL, p4], [p4, NULL, NULL, p5], [p3, NULL, NULL, p6], [p6, NULL, NULL, p7]]

        self.assertEqual(2, len(_connected_segments(c1)))


class ContinuityTests(unittest.TestCase):

    def test_continuous_segments(self):
        partition_info = {'r1': [0, 1, 2, 3], 'r2': [4, 5, 6, 7], 'r3': [8, 9, 5, 6]}
        connected_segments_index = [[0, 1, 2, 3], [4, 5, 6, 7]]
        continuous_segments = find_continuous_segments(partition_info, connected_segments_index)

        self.assertEqual(2, len(continuous_segments))
        self.assertEqual(partition_info['r1'], continuous_segments['r1'])
        self.assertEqual(partition_info['r2'], continuous_segments['r2'])
