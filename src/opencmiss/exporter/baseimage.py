"""
Base class for exporting an Argon document to a JPEG image.
"""
import os
import json

from opencmiss.argon.argondocument import ArgonDocument
from opencmiss.exporter.base import BaseExporter
from opencmiss.exporter.errors import OpenCMISSExportImageError
from opencmiss.zinc.sceneviewer import Sceneviewer


class BaseImageExporter(BaseExporter):
    """
    A base class for exporting visualisation described by an Argon document to JPEG.
    By default the export will be use PySide2 to render the scene.
    An alternative is to use OSMesa for software rendering.
    To use OSMesa as the renderer either set the environment variable
    OC_EXPORTER_RENDERER to 'osmesa' or not have PySide2 available in the
    calling environment.
    """

    def __init__(self, width, height, name_postfix, output_target=None, output_prefix=None):
        """
        :param output_target: The target directory to export the visualisation to.
        :param output_prefix: The prefix to apply to the output.
        """
        super(BaseImageExporter, self).__init__(output_prefix)
        self._output_target = '.' if output_target is None else output_target
        self._width = width
        self._height = height
        self._name_postfix = name_postfix

    def _form_full_filename(self, filename):
        return filename if self._output_target is None else os.path.join(self._output_target, filename)

    def export(self, output_target=None):
        """
        Export the current document to *output_target*. If no *output_target* is given then
        the *output_target* set at initialisation is used.

        If there is no current document then one will be loaded from the current filename.

        :param output_target: Output directory location.
        """
        if output_target is not None:
            self._output_target = output_target

        if self._document is None:
            self._document = ArgonDocument()
            self._document.initialiseVisualisationContents()
            self.load(self._filename)
        else:
            state = self._document.serialize()
            self._document.freeVisualisationContents()
            self._document.initialiseVisualisationContents()
            self._document.deserialize(state)

        self._document.checkVersion("0.3.0")

        self.export_image()

    def export_image(self):
        """
        Export graphics into an image format.
        """
        pyside2_opengl_failed = True
        if "OC_EXPORTER_RENDERER" not in os.environ or os.environ["OC_EXPORTER_RENDERER"] != "osmesa":
            try:
                from PySide2 import QtGui

                if QtGui.QGuiApplication.instance() is None:
                    QtGui.QGuiApplication([])

                off_screen = QtGui.QOffscreenSurface()
                off_screen.create()
                if off_screen.isValid():
                    context = QtGui.QOpenGLContext()
                    if context.create():
                        context.makeCurrent(off_screen)
                        pyside2_opengl_failed = False

            except ImportError:
                pyside2_opengl_failed = True

        mesa_context = None
        mesa_opengl_failed = True
        if pyside2_opengl_failed:
            try:
                from OpenGL import GL
                from OpenGL import arrays
                from OpenGL.osmesa import (
                    OSMesaCreateContextAttribs, OSMesaMakeCurrent, OSMESA_FORMAT,
                    OSMESA_RGBA, OSMESA_PROFILE, OSMESA_COMPAT_PROFILE,
                    OSMESA_CONTEXT_MAJOR_VERSION, OSMESA_CONTEXT_MINOR_VERSION,
                    OSMESA_DEPTH_BITS
                )

                attrs = arrays.GLintArray.asArray([
                    OSMESA_FORMAT, OSMESA_RGBA,
                    OSMESA_DEPTH_BITS, 24,
                    OSMESA_PROFILE, OSMESA_COMPAT_PROFILE,
                    OSMESA_CONTEXT_MAJOR_VERSION, 2,
                    OSMESA_CONTEXT_MINOR_VERSION, 1,
                    0
                ])
                mesa_context = OSMesaCreateContextAttribs(attrs, None)
                mesa_buffer = arrays.GLubyteArray.zeros((self._width, self._height, 4))
                result = OSMesaMakeCurrent(mesa_context, mesa_buffer, GL.GL_UNSIGNED_BYTE, self._width, self._height)
                if result:
                    mesa_opengl_failed = False
            except ImportError:
                mesa_opengl_failed = True

        if pyside2_opengl_failed and mesa_opengl_failed:
            raise OpenCMISSExportImageError('Image export not supported without optional requirements PySide2 for hardware rendering or OSMesa for software rendering.')

        zinc_context = self._document.getZincContext()
        view_manager = self._document.getViewManager()

        root_region = zinc_context.getDefaultRegion()
        sceneviewermodule = zinc_context.getSceneviewermodule()

        views = view_manager.getViews()

        for view in views:
            name = view.getName()
            scenes = view.getScenes()
            if len(scenes) == 1:
                scene_description = scenes[0]["Sceneviewer"].serialize()

                sceneviewer = sceneviewermodule.createSceneviewer(Sceneviewer.BUFFERING_MODE_DOUBLE, Sceneviewer.STEREO_MODE_DEFAULT)
                sceneviewer.setViewportSize(self._width, self._height)

                if not (self._initialTime is None or self._finishTime is None):
                    raise NotImplementedError('Time varying image export is not implemented.')

                sceneviewer.readDescription(json.dumps(scene_description))
                # Workaround for order independent transparency producing a white output
                # and in any case, sceneviewer transparency layers were not being serialised by Zinc.
                if sceneviewer.getTransparencyMode() == Sceneviewer.TRANSPARENCY_MODE_ORDER_INDEPENDENT:
                    sceneviewer.setTransparencyMode(Sceneviewer.TRANSPARENCY_MODE_SLOW)

                scene_path = scene_description["Scene"]
                scene = root_region.getScene()
                if scene_path is not None:
                    scene_region = root_region.findChildByName(scene_path)
                    if scene_region.isValid():
                        scene = scene_region.getScene()

                sceneviewer.setScene(scene)

                sceneviewer.writeImageToFile(os.path.join(self._output_target, f'{self._prefix}_{name}_{self._name_postfix}.jpeg'), False, self._width, self._height, 4, 0)

        if mesa_context is not None:
            from OpenGL.osmesa import OSMesaDestroyContext
            OSMesaDestroyContext(mesa_context)
