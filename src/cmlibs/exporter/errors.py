
class ExportError(Exception):
    pass


class ExportWebGLError(ExportError):
    pass


class ExportVTKError(ExportError):
    pass


class ExportSTLError(ExportError):
    pass


class ExportWavefrontError(ExportError):
    pass


class ExportImageError(ExportError):
    pass
