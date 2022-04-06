
==================
OpenCMISS Exporter
==================

OpenCMISS exporter classes.  This software can be found on PyPi and installed with the following command::

  pip install opencmiss.exporter

When using the thumbnail exporter there are additional requirements for hardware or software rendering.
To install the thumbnail exporter with support for hardware rendering install *opencmiss.exporter* with::

  pip install 'opencmiss.exporter[thumbnail_hardware]'

To install the thumbnail exporter with support for software rendering install *opencmiss.exporter* with::

  pip install 'opencmiss.exporter[thumbnail_software]'

To force the use of the software renderer even when hardware rendering is available, set an environment variable like so::

  OC_EXPORTER_RENDERER=osmesa

either in the environment the exporter is run in or before calling the export thumbnail method.

Distribution
============

This software uses regex to extract the version number information from the package. The version number for this package is stored in 'src/opencmiss/exporter/__init__.py'
