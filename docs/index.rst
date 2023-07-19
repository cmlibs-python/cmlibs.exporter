CMLibs Exporter
===============

**CMLibs Exporter** is a Python package for exporting Argon documents to different formats.
The exporter can export an Argon document to the following formats:

* webGL
* VTK
* Wavefront
* STL
* Thumbnail
* Image

webGL
-----

The webGL export takes scenes described in an Argon document and produces a JSON description of the scenes.
The JSON description is exported to a format `@abi-software/scaffoldvuer <https://github.com/ABI-Software/scaffoldvuer>`_ can read and create a visualisation in the browser.

Usage::

 from cmlibs.exporter import webgl

 argon_document = "argon-document.json"
 output_directory = "."

 exporter = webgl.ArgonSceneExporter(output_target=output_directory)
 exporter.load(argon_document)
 exporter.export()


It is also possible to use the WebGL exporter to produce a JSON description of a Zinc scene without embedding it in an Argon document.
This can be achieved with the :code:`export_webgl_from_scene` method. This method has one required parameter (:code:`scene`) and one
optional parameter (:code:`scene_filter`). The :code:`scene` parameter is the Zinc Scene object to be exported. The :code:`scene_filter`
parameter is a Zinc Scenefilter object associated with the Zinc scene and gives the user the option to filter which graphics are included
in the export.

Usage::

 exporter = webgl.ArgonSceneExporter(output_target=output_directory)
 exporter.export_webgl_from_scene(scene)

VTK
---

The VTK export takes scenes described in an Argon document and produces a VTK document for each of the scenes.
The VTK export does not currently support time varying scenes.
If an Argon document describes a time varying scene then VTK document(s) will be created only at the default time.

Usage::

 from cmlibs.exporter import vtk

 argon_document = "argon-document.json"
 output_directory = "."

 exporter = vtk.ArgonSceneExporter(output_target=output_directory)
 exporter.load(argon_document)
 exporter.export()

Wavefront
---------

The wavefront export takes scenes described in an Argon document and produces a main wavefront file that references wavefront files for each of the scenes.
The wavefront export does not currently support time varying scenes.
If an Argon document describes a time varying scene then wavefront file(s) will only be created at the default time.

Usage::

 from cmlibs.exporter import wavefront

 argon_document = "argon-document.json"
 output_directory = "."

 exporter = wavefront.ArgonSceneExporter(output_target=output_directory)
 exporter.load(argon_document)
 exporter.export()

STL
---

The STL export takes scenes described in an Argon document and produces an STL document for the scene.
The STL export does not currently support time varying scenes.
If an Argon document describes a time varying scene then an STL file will only be created at the default time.

Usage::

 from cmlibs.exporter import stl

 argon_document = "argon-document.json"
 output_directory = "."

 exporter = stl.ArgonSceneExporter(output_target=output_directory)
 exporter.load(argon_document)
 exporter.export()

Thumbnail
---------

The thumbnail export takes scenes described in an Argon document and produces a JPEG thumbnail for each of the scenes.
The thumbnail export does not currently support time varying scenes.
If an Argon document describes a time varying scene then only one thumbnail will be created and that will be done at the default time.

Usage::

 from cmlibs.exporter import thumbnail

 argon_document = "argon-document.json"
 output_directory = "."

 exporter = thumbnail.ArgonSceneExporter(output_target=output_directory)
 exporter.load(argon_document)
 exporter.export()

Image
-----

The image export takes scenes described in an Argon document and produces a JPEG image of width x height for each of the scenes.
The image export does not currently support time varying scenes.
If an Argon document describes a time varying scene then only one image will be created and that will be done at the default time.

Usage::

 from cmlibs.exporter import image

 argon_document = "argon-document.json"
 output_directory = "."

 exporter = image.ArgonSceneExporter(2000, 3000, output_target=output_directory)
 exporter.load(argon_document)
 exporter.export()

Package API
-----------

webGL Module
************

.. automodule:: cmlibs.exporter.webgl

.. autoclass:: cmlibs.exporter.webgl.ArgonSceneExporter
   :members:

VTK Module
**********

.. automodule:: cmlibs.exporter.vtk

.. autoclass:: cmlibs.exporter.vtk.ArgonSceneExporter
   :members:

Wavefront Module
****************

.. automodule:: cmlibs.exporter.wavefront

.. autoclass:: cmlibs.exporter.wavefront.ArgonSceneExporter
   :members:

STL Module
**********

.. automodule:: cmlibs.exporter.stl

.. autoclass:: cmlibs.exporter.stl.ArgonSceneExporter
   :members:

Thumbnail Module
****************

.. automodule:: cmlibs.exporter.thumbnail

.. autoclass:: cmlibs.exporter.thumbnail.ArgonSceneExporter
   :members:

Image Module
************

.. automodule:: cmlibs.exporter.image

.. autoclass:: cmlibs.exporter.image.ArgonSceneExporter
   :members:

Base Module
***********

.. automodule:: cmlibs.exporter.base

.. autoclass:: cmlibs.exporter.base.BaseExporter
   :members:

Base Image Module
*****************

.. automodule:: cmlibs.exporter.baseimage

.. autoclass:: cmlibs.exporter.baseimage.BaseImageExporter
   :members:

