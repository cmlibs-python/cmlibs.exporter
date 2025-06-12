import os.path
import unittest

from cmlibs.exporter import thumbnail
from cmlibs.exporter import vtk
from cmlibs.exporter import stl
from cmlibs.exporter import wavefront
from cmlibs.exporter import mbfxml


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

    def test_vtk(self):
        argon_document = _resource_path("argon-document.json")
        output_target = _resource_path("")

        exporter = vtk.ArgonSceneExporter(output_target=output_target)
        exporter.load(argon_document)
        exporter.export_vtk()

        cube_file = _resource_path("ArgonSceneExporterVTK_cube.vtk")
        self.assertTrue(os.path.isfile(cube_file))
        sphere_file = _resource_path("ArgonSceneExporterVTK_sphere.vtk")
        self.assertTrue(os.path.isfile(sphere_file))

        os.remove(cube_file)
        os.remove(sphere_file)

    def test_stl(self):
        argon_document = _resource_path("argon-document.json")
        output_target = _resource_path("")

        exporter = stl.ArgonSceneExporter(output_target=output_target)
        exporter.load(argon_document)
        exporter.export_stl()

        stl_file = _resource_path("ArgonSceneExporterSTL_zinc_graphics.stl")
        self.assertTrue(os.path.isfile(stl_file))

        os.remove(stl_file)

    def test_wavefront(self):
        argon_document = _resource_path("argon-document.json")
        output_target = _resource_path("")

        exporter = wavefront.ArgonSceneExporter(output_target=output_target)
        exporter.load(argon_document)
        exporter.export_wavefront()

        wavefront_file = _resource_path("ArgonSceneExporterWavefront_base.obj")
        self.assertTrue(os.path.isfile(wavefront_file))
        cube_file = _resource_path("cube.1.obj")
        self.assertTrue(os.path.isfile(cube_file))
        sphere_file = _resource_path("sphere.1.obj")
        self.assertTrue(os.path.isfile(sphere_file))

        os.remove(wavefront_file)
        os.remove(cube_file)
        os.remove(sphere_file)

    def test_mbfxml(self):
        argon_document = _resource_path("simple-vessel-structure.neon")
        output_target = _resource_path("")

        exporter = mbfxml.ArgonSceneExporter(output_target=output_target)
        exporter.load(argon_document)
        exporter.export_mbfxml()
        mbfxml_file = _resource_path("ArgonSceneExporterMBFXML.xml")
        self.assertTrue(os.path.isfile(mbfxml_file))

        os.remove(mbfxml_file)

    def test_mbfxml_two_element_cube(self):
        argon_document = _resource_path("two-cubes-lines.neon")

        exporter = mbfxml.ArgonSceneExporter()
        exporter.load(argon_document)
        self.assertFalse(exporter.is_valid())
