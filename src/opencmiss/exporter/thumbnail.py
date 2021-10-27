"""
Export an Argon document to a PNG file.
"""
import os
import json

from opencmiss.argon.argondocument import ArgonDocument
from opencmiss.argon.argonlogger import ArgonLogger
from opencmiss.argon.argonerror import ArgonError
from opencmiss.exporter.errors import OpenCMISSExportThumbnailError


class ArgonSceneExporter(object):
    """
    Export a visualisation described by an Argon document to webGL.
    """

    def __init__(self, output_target=None, output_prefix=None):
        """
        :param output_target: The target directory to export the visualisation to.
        :param output_prefix: The prefix to apply to the output.
        """
        self._output_target = '.' if output_target is None else output_target
        self._prefix = "ArgonSceneExporterThumbnail" if output_prefix is None else output_prefix
        self._document = None
        self._filename = None
        self._initialTime = None
        self._finishTime = None
        self._numberOfTimeSteps = 10

    def set_document(self, document):
        self._document = document

    def set_filename(self, filename):
        self._filename = filename

    def load(self, filename):
        """
        Loads the named Argon file and on success sets filename as the current location.
        Emits documentChange separately if new document loaded, including if existing document cleared due to load failure.
        :return  True on success, otherwise False.
        """
        if filename is None:
            return False

        try:
            with open(filename, 'r') as f:
                state = f.read()

            current_wd = os.getcwd()
            # set current directory to path from file, to support scripts and FieldML with external resources
            if not os.path.isabs(filename):
                filename = os.path.abspath(filename)
            path = os.path.dirname(filename)
            os.chdir(path)
            self._document = ArgonDocument()
            self._document.initialiseVisualisationContents()
            self._document.deserialize(state)
            os.chdir(current_wd)
            return True
        except (ArgonError, IOError, ValueError) as e:
            ArgonLogger.getLogger().error("Failed to load Argon visualisation " + filename + ": " + str(e))
        except Exception as e:
            ArgonLogger.getLogger().error("Failed to load Argon visualisation " + filename + ": Unknown error " + str(e))

        return False

    def set_parameters(self, parameters):
        self._numberOfTimeSteps = parameters["numberOfTimeSteps"]
        self._initialTime = parameters["initialTime"]
        self._finishTime = parameters["finishTime"]
        self._prefix = parameters["prefix"]

    def _form_full_filename(self, filename):
        return filename if self._output_target is None else os.path.join(self._output_target, filename)

    def export(self, output_target=None):
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

        self.export_thumbnail()

    def export_thumbnail(self):
        """
        Export graphics into an image format.
        """
        try:
            from PySide2 import QtWidgets
            from PySide2 import QtGui
            from PySide2 import QtOpenGL

            from opencmiss.zinc.sceneviewer import Sceneviewer

            if QtGui.QGuiApplication.instance() is None:
                QtGui.QGuiApplication([])

            off_screen = QtGui.QOffscreenSurface()
            off_screen.create()
            if off_screen.isValid():
                context = QtGui.QOpenGLContext()
                if context.create():
                    context.makeCurrent(off_screen)

                    fbo_format = QtGui.QOpenGLFramebufferObjectFormat()
                    fbo_format.setAttachment(QtGui.QOpenGLFramebufferObject.CombinedDepthStencil)
                    fbo_format.setSamples(4)
                    fbo = QtGui.QOpenGLFramebufferObject(512, 512, fbo_format)
                    fbo.bind()

                    zinc_context = self._document.getZincContext()
                    sceneviewermodule = zinc_context.getSceneviewermodule()
                    sceneviewer = sceneviewermodule.createSceneviewer(Sceneviewer.BUFFERING_MODE_DOUBLE, Sceneviewer.STEREO_MODE_DEFAULT)
                    sceneviewer.setViewportSize(512, 512)

                    if not (self._initialTime is None or self._finishTime is None):
                        raise NotImplementedError('Time varying image export is not implemented.')

                    viewDataRaw = self._document.getSceneviewer().get_view_parameters()

                    sceneviewer.setLookatParametersNonSkew(viewDataRaw['eyePosition'], viewDataRaw['lookAtPosition'], viewDataRaw['upVector'])
                    sceneviewer.setFarClippingPlane(viewDataRaw['farClippingPlane'])
                    sceneviewer.setNearClippingPlane(viewDataRaw['nearClippingPlane'])
                    sceneviewer.setViewAngle(viewDataRaw['viewAngle'])
                    scene = self._document.getRootRegion().getZincRegion().getScene()
                    sceneviewer.setScene(scene)
                    sceneviewer.renderScene()

                    image = fbo.toImage()
                    image.save(os.path.join(self._output_target, f'{self._prefix}_thumbnail.jpeg'))
                    fbo.release()

        except ImportError:
            raise OpenCMISSExportThumbnailError('Thumbnail export not supported without optional requirement PySide2')
