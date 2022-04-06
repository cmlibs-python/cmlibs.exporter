"""
Export an Argon document to WebGL documents suitable for scaffoldvuer.
"""
import math
import os
import json

from opencmiss.argon.argondocument import ArgonDocument
from opencmiss.argon.argonlogger import ArgonLogger
from opencmiss.argon.argonerror import ArgonError
from opencmiss.exporter.errors import OpenCMISSExportWebGLError

from opencmiss.zinc.status import OK as ZINC_OK


class ArgonSceneExporter(object):
    """
    Export a visualisation described by an Argon document to webGL.
    """

    def __init__(self, output_target=None, output_prefix=None):
        """
        :param output_target: The target directory to export the visualisation to.
        :param output_prefix: The prefix for the exported file(s).
        """
        self._output_target = output_target
        self._document = None
        self._filename = None
        self._prefix = "ArgonSceneExporterWebGL" if output_prefix is None else output_prefix
        self._numberOfTimeSteps = 10
        self._initialTime = None
        self._finishTime = None

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

        self._document.checkVersion("0.3.0")

        self.export_view()
        self.export_webgl()

    def export_view(self):
        """Export sceneviewer parameters to JSON format"""
        view_manager = self._document.getViewManager()
        views = view_manager.getViews()
        for view in views:
            name = view.getName()
            scenes = view.getScenes()
            if len(scenes) == 1:
                scene_description = scenes[0]["Sceneviewer"].serialize()
                viewData = {'farPlane': scene_description['FarClippingPlane'], 'nearPlane': scene_description['NearClippingPlane'],
                            'eyePosition': scene_description['EyePosition'], 'targetPosition': scene_description['LookatPosition'],
                            'upVector': scene_description['UpVector'], 'viewAngle': scene_description['ViewAngle']}

                view_file = self._form_full_filename(self._view_filename(name))
                with open(view_file, 'w') as f:
                    json.dump(viewData, f)

    def _view_filename(self, name):
        return f"{self._prefix}_{name}_view.json"

    def _define_default_view_obj(self):
        view_obj = {}
        view_manager = self._document.getViewManager()
        view_name = view_manager.getActiveView()
        if view_name is not None:
            view_obj = {
                "Type": "View",
                "URL": self._view_filename(view_name)
            }

        return view_obj

    def export_webgl(self):
        """
        Export graphics into JSON format, one json export represents one
        surface graphics.
        """
        scene = self._document.getRootRegion().getZincRegion().getScene()
        sceneSR = scene.createStreaminformationScene()
        sceneSR.setIOFormat(sceneSR.IO_FORMAT_THREEJS)
        """
        Output frames of the deforming heart between time 0 to 1,
        this matches the number of frame we have read in previously
        """
        if not (self._initialTime is None or self._finishTime is None):
            sceneSR.setNumberOfTimeSteps(self._numberOfTimeSteps)
            sceneSR.setInitialTime(self._initialTime)
            sceneSR.setFinishTime(self._finishTime)
            """ We want the geometries and colours change overtime """
            sceneSR.setOutputTimeDependentVertices(1)
            sceneSR.setOutputTimeDependentColours(1)

        number = sceneSR.getNumberOfResourcesRequired()
        if number == 0:
            return

        resources = []
        """Write out each graphics into a json file which can be rendered with ZincJS"""
        for i in range(number):
            resources.append(sceneSR.createStreamresourceMemory())

        scene.write(sceneSR)

        number_of_digits = math.floor(math.log10(number)) + 1

        def _resource_filename(prefix, i_):
            return f'{prefix}_{str(i_).zfill(number_of_digits)}.json'

        """Write out each resource into their own file"""
        resource_count = 0
        for i in range(number):
            result, buffer = resources[i].getBuffer()
            if result != ZINC_OK:
                print('some sort of error')
                continue

            if buffer is None:
                # Maybe this is a bug in the resource counting.
                continue

            buffer = buffer.decode()

            if i == 0:
                for j in range(number - 1):
                    """
                    IMPORTANT: the replace name here is relative to your html page, so adjust it
                    accordingly.
                    """
                    replaceName = f'"{_resource_filename(self._prefix, j + 1)}"'
                    old_name = '"memory_resource_' + str(j + 2) + '"'
                    buffer = buffer.replace(old_name, replaceName, 1)

                viewObj = self._define_default_view_obj()

                obj = json.loads(buffer)
                if obj is None:
                    raise OpenCMISSExportWebGLError('There is nothing to export')

                obj.append(viewObj)
                buffer = json.dumps(obj)

            if i == 0:
                current_file = self._form_full_filename(self._prefix + '_metadata.json')
            else:
                current_file = self._form_full_filename(_resource_filename(self._prefix, resource_count))

            with open(current_file, 'w') as f:
                f.write(buffer)

            resource_count += 1
