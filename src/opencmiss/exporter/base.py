import os

from opencmiss.argon.argondocument import ArgonDocument
from opencmiss.argon.argonerror import ArgonError
from opencmiss.argon.argonlogger import ArgonLogger


class BaseExporter(object):

    def __init__(self, output_prefix):
        self._prefix = output_prefix
        self._document = None
        self._filename = None
        self._initialTime = None
        self._finishTime = None
        self._numberOfTimeSteps = 10

    def set_document(self, document):
        """
        Set the document to export.

        :param document: Set the document to export.
        """
        self._document = document

    def set_filename(self, filename):
        """
        Set filename.

        :param filename: The filename for the Argon document.
        """
        self._filename = filename

    def set_parameters(self, parameters):
        """
        Set the parameters for this exporter.
        The parameters must have values for:

        * numberOfTimeSteps
        * initialTime
        * finishTime
        * prefix

        :param parameters: A *dict* of parameters.
        """
        self._numberOfTimeSteps = parameters["numberOfTimeSteps"]
        self._initialTime = parameters["initialTime"]
        self._finishTime = parameters["finishTime"]
        self._prefix = parameters["prefix"]

    def export(self):
        raise NotImplementedError("export() not implemented")

    def load(self, filename):
        """
        Loads the named Argon file and on success sets filename as the current location.
        Emits documentChange separately if new document loaded, including if existing document cleared due to load failure.

        :return:  True on success, otherwise False.
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

    def _form_full_filename(self, filename):
        return filename if self._output_target is None else os.path.join(self._output_target, filename)
