import os
import unittest

from cmlibs.exporter import vtk
from cmlibs.zinc.context import Context

here = os.path.abspath(os.path.dirname(__file__))


def _resource_path(resource_name):
    return os.path.join(here, "resources", resource_name)


class VTKExporter(unittest.TestCase):

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

    def test_vtk_from_scene(self):
        source_model = _resource_path("fitted_uterus.exf")
        output_target = _resource_path("")

        exporter = vtk.ArgonSceneExporter(output_target=output_target, output_prefix="fitted_uterus")

        c = Context('generate_vtk')
        root_region = c.getDefaultRegion()
        root_region.readFile(source_model)

        exporter.export_from_scene(root_region.getScene())

        vtk_file = _resource_path("fitted_uterus_root.vtk")
        self.assertTrue(os.path.isfile(vtk_file))

        os.remove(vtk_file)

    def test_embedded_data_vtk(self):
        argon_document = _resource_path("embedded_model/neon-document.json")
        output_target = _resource_path("embedded_model")

        exporter = vtk.ArgonSceneExporter(output_target=output_target)
        exporter.load(argon_document)
        exporter.export_vtk()

        cube_file = _resource_path("embedded_model/ArgonSceneExporterVTK_root.vtk")
        self.assertTrue(os.path.isfile(cube_file))
        sphere_file = _resource_path("embedded_model/ArgonSceneExporterVTK_root_marker.vtk")
        self.assertTrue(os.path.isfile(sphere_file))
        vasculature_file = _resource_path("embedded_model/ArgonSceneExporterVTK_vasculature_data.vtk")
        self.assertTrue(os.path.isfile(vasculature_file))

        os.remove(cube_file)
        os.remove(sphere_file)
        os.remove(vasculature_file)


