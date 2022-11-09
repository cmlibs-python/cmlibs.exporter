OpenCMISS Exporter
==================

**OpenCMISS Exporter** is a Python package for exporting Argon documents to different formats.
The exporter can export an Argon document to the following formats:

* webGL
* Thumbnail
* Image

webGL
-----

The webGL export takes scenes described in an Argon document and produces a JSON description of the scenes.
The JSON description is exported to a format `@abi-software/scaffoldvuer <https://github.com/ABI-Software/scaffoldvuer>`_ can read and create a visualisation in the browser.

Usage::

 from opencmiss.exporter import webgl

 argon_document = "argon-document.json"
 output_directory = "."

 exporter = webgl.ArgonSceneExporter(output_target=output_directory)
 exporter.load(argon_document)
 exporter.export()


Thumbnail
---------

The thumbnail export takes scenes described in an Argon document and produces a JPEG thumbnail for each of the scenes.
The thumbnail export does not currently support time varying scenes.
If an Argon document describes a time varying scene then only one thumbnail will be created and that will be done at the default time.

Usage::

 from opencmiss.exporter import thumbnail

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

 from opencmiss.exporter import image

 argon_document = "argon-document.json"
 output_directory = "."

 exporter = image.ArgonSceneExporter(2000, 3000, output_target=output_directory)
 exporter.load(argon_document)
 exporter.export()

Package API
-----------

webGL Module
************

.. automodule:: opencmiss.exporter.webgl

.. autoclass:: opencmiss.exporter.webgl.ArgonSceneExporter
   :members:

Thumbnail Module
****************

.. automodule:: opencmiss.exporter.thumbnail

.. autoclass:: opencmiss.exporter.thumbnail.ArgonSceneExporter
   :members:

Image Module
************

.. automodule:: opencmiss.exporter.image

.. autoclass:: opencmiss.exporter.image.ArgonSceneExporter
   :members:

Base Module
***********

.. automodule:: opencmiss.exporter.base

.. autoclass:: opencmiss.exporter.base.BaseExporter
   :members:

Base Image Module
*****************

.. automodule:: opencmiss.exporter.baseimage

.. autoclass:: opencmiss.exporter.baseimage.BaseImageExporter
   :members:

