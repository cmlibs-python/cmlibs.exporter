"""
Export an Argon document to WebGL documents suitable for scaffoldvuer.
"""
import math
import json

from cmlibs.argon.argondocument import ArgonDocument
from cmlibs.exporter.base import BaseExporter
from cmlibs.exporter.errors import ExportWebGLError

from cmlibs.zinc.status import OK as ZINC_OK


class ArgonSceneExporter(BaseExporter):
    """
    Export a visualisation described by an Argon document to webGL.
    """

    def __init__(self, output_target=None, output_prefix=None):
        """
        :param output_target: The target directory to export the visualisation to.
        :param output_prefix: The prefix for the exported file(s).
        """
        super(ArgonSceneExporter, self).__init__("ArgonSceneExporterWebGL" if output_prefix is None else output_prefix)
        self._output_target = output_target
        self._output_multiple_detail_levels = False
        self._tessellation_level = None

    def export(self, output_target=None):
        """
        Export the current document to *output_target*. If no *output_target* is given then
        the *output_target* set at initialisation is used.

        If there is no current document then one will be loaded from the current filename.

        :param output_target: Output directory location.
        """
        super().export()

        if output_target is not None:
            self._output_target = output_target

        if self._output_multiple_detail_levels:
            initial_state = self._document.serialize()

            self._set_tessellation("high")
            self.export_webgl()
            self._document.deserialize(initial_state)

            self._set_tessellation("medium")
            self.export_webgl()
            self._document.deserialize(initial_state)

            # For LOD the default URL level is low.
            self._set_tessellation("low")
            self.export_webgl()

            # Set the document back to its initial state.
            self._document.deserialize(initial_state)
        else:
            self.export_webgl()

        self.export_view()

    def export_view(self):
        """Export sceneviewer parameters to JSON format"""
        view_manager = self._document.getViewManager()
        views = view_manager.getViews()
        for view in views:
            name = view.getName()
            scenes = view.getScenes()
            if len(scenes) == 1:
                scene_description = scenes[0]["Sceneviewer"].serialize()
                viewData = {'farPlane': scene_description['FarClippingPlane'],
                            'nearPlane': scene_description['NearClippingPlane'],
                            'eyePosition': scene_description['EyePosition'],
                            'targetPosition': scene_description['LookatPosition'],
                            'upVector': scene_description['UpVector'], 'viewAngle': scene_description['ViewAngle']}

                view_file = self._form_full_filename(self._view_filename(name))
                with open(view_file, 'w') as f:
                    json.dump(viewData, f)

    def _view_filename(self, name):
        return f"{self._prefix}_{name}_view.json"

    def setLoD(self, state):
        self._output_multiple_detail_levels = state

    def _set_tessellation(self, tessellation_level):
        """
        Set tessellation based on the current tessellation level.
        """
        self._tessellation_level = tessellation_level
        state = self._document.serialize()
        document_content = json.loads(state)

        used_tessellations = _tessellations_in_use(document_content["RootRegion"])
        for used_tessellation in used_tessellations:
            matched_tessellations = [t for t in document_content["Tessellations"]["Tessellations"] if t["Name"] == used_tessellation]
            if len(matched_tessellations) == 1:
                _re_level_tessellation(tessellation_level, matched_tessellations[0])

        self._document.deserialize(json.dumps(document_content))

    def _define_default_LOD_obj(self, url):
        index = url.split("_")[-1]
        LOD_obj = {
            "Preload": False,
            "Levels": {
                "medium": {
                    "URL": f"{self._prefix}_medium_{index}"
                },
                "close": {
                    "URL": f"{self._prefix}_high_{index}"
                }
            }
        }
        return LOD_obj

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

    def _define_settings_obj(self):
        settings_obj = None

        if self._initialTime is not None and self._finishTime is not None:
            # /P(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)W)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$/;
            time_diff = int(self._finishTime - self._initialTime)
            duration = f"PT{time_diff}S"
            settings_obj = {
                "Type": "Settings",
                "Duration": duration,
                "OriginalDuration": duration,
            }

        return settings_obj

    def export_webgl(self):
        """
        Export graphics into JSON format, one json export represents one Zinc graphics.
        """
        scene = self._document.getRootRegion().getZincRegion().getScene()
        self.export_webgl_from_scene(scene)

    def export_webgl_from_scene(self, scene, scene_filter=None):
        """
        Export graphics from a Zinc Scene into WebGL JSON format.

        :param scene: The Zinc Scene object to be exported.
        :param scene_filter: Optional; A Zinc Scenefilter object associated with the Zinc scene, allowing the user to filter which
            graphics are included in the export.
        """
        sceneSR = scene.createStreaminformationScene()
        sceneSR.setIOFormat(sceneSR.IO_FORMAT_THREEJS)

        # Set time-related parameters if specified
        if not (self._initialTime is None or self._finishTime is None):
            sceneSR.setNumberOfTimeSteps(self._numberOfTimeSteps)
            sceneSR.setInitialTime(self._initialTime)
            sceneSR.setFinishTime(self._finishTime)
            """ We want the geometries and colours change overtime """
            sceneSR.setOutputTimeDependentVertices(1)
            sceneSR.setOutputTimeDependentColours(1)

        # Optionally filter the scene.
        if scene_filter:
            sceneSR.setScenefilter(scene_filter)

        # Check if any resources are required
        number = sceneSR.getNumberOfResourcesRequired()
        if number == 0:
            return

        resources = []
        """Write out each graphics into a json file which can be rendered with ZincJS"""
        for i in range(number):
            resources.append(sceneSR.createStreamresourceMemory())

        scene.write(sceneSR)

        # Calculate number of digits for resource filenames
        number_of_digits = math.floor(math.log10(number)) + 1

        # Define resource filename based on prefix and index
        def _resource_filename(prefix, i_, tessellation_level=None):
            if self._output_multiple_detail_levels and tessellation_level != "low":
                return f'{prefix}_{tessellation_level}_{str(i_).zfill(number_of_digits)}.json'
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
                # Replace memory_resource_# with corresponding filenames
                for j in range(number - 1):
                    """
                    IMPORTANT: the replace name here is relative to your html page, so adjust it
                    accordingly.
                    """
                    replaceName = f'"{_resource_filename(self._prefix, j + 1, self._tessellation_level)}"'
                    old_name = '"memory_resource_' + str(j + 2) + '"'
                    buffer = buffer.replace(old_name, replaceName, 1)

                # Add default view object and settings object
                view_obj = self._define_default_view_obj() if self._document else None
                settings_obj = self._define_settings_obj()

                obj = json.loads(buffer)
                if obj is None:
                    raise ExportWebGLError('There is nothing to export')

                for o in obj:
                    # Add Level of Detail (LOD) object if necessary
                    LOD_obj = self._define_default_LOD_obj(
                        o["URL"]) if self._document and self._output_multiple_detail_levels else None
                    if LOD_obj:
                        o['LOD'] = LOD_obj

                obj.append(view_obj)
                if settings_obj is not None:
                    obj.append(settings_obj)

                buffer = json.dumps(obj)

            # Write buffer content to metadata file
            if i == 0:
                current_file = self.metadata_file()
            else:
                current_file = self._form_full_filename(
                    _resource_filename(self._prefix, resource_count, self._tessellation_level))

            with open(current_file, 'w') as f:
                f.write(buffer)

            resource_count += 1

    def metadata_file(self):
        return self._form_full_filename(self._prefix + '_metadata.json')


def _reduce_to_level(level, value):
    divisor = 4
    if level == "high":
        divisor = 1
    elif level == "medium":
        divisor = 2

    return max(math.floor(value / divisor), 1)


def _re_level_tessellation(level, tessellation):
    tessellation["CircleDivisions"] = _reduce_to_level(level, tessellation["CircleDivisions"])
    tessellation["RefinementFactors"] = [_reduce_to_level(level, v) for v in tessellation["RefinementFactors"]]


def _tessellations_in_use(region):
    used_tessellations = set()
    if "Scene" in region:
        if region["Scene"].get("Graphics", []):
            for g in region["Scene"]["Graphics"]:
                used_tessellations.add(g["Tessellation"])

    for child_region in region.get("ChildRegions", []):
        used_tessellations.update(_tessellations_in_use(child_region))

    return used_tessellations
