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

        self._document.checkVersion("0.3.0")

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

                            sceneviewer = sceneviewermodule.createSceneviewer(Sceneviewer.BUFFERING_MODE_DOUBLE, Sceneviewer.STEREO_MODE_DEFAULT)
                            sceneviewer.setViewportSize(512, 512)

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

                            # Workaround for partial scene rendering.  We will call renderScene one more time than
                            # we have regions in the region tree.
                            region_count = 1
                            region_count += count_regions(root_region)

                            sceneviewer.setScene(scene)
                            for _index in range(region_count):
                                sceneviewer.renderScene()

                            image = fbo.toImage()
                            image.save(os.path.join(self._output_target, f'{self._prefix}_{name}_thumbnail.jpeg'))

                            fbo.release()

        except ImportError:
            raise OpenCMISSExportThumbnailError('Thumbnail export not supported without optional requirement PySide2')

    # def _generate_thumbnail(self, ):
def count_regions(region):
    count = 1
    first_child = region.getFirstChild()
    if first_child.isValid():
        count += count_regions(first_child)
        next_sibling = first_child.getNextSibling()
        while next_sibling.isValid():
            count += count_regions(next_sibling)
            next_sibling = next_sibling.getNextSibling()

    return count
