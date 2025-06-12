from importlib import metadata


def get_version(package_name: str, fallback: str = "X.Y.Z") -> str:
    try:
        return metadata.version(package_name)
    except metadata.PackageNotFoundError:
        try:
            return metadata.version(package_name.replace(".", "_"))
        except metadata.PackageNotFoundError:
            return fallback


__version__ = get_version("cmlibs.exporter")
