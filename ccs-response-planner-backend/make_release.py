import io
import shutil
import subprocess
import sys

LIB_NAME = "ccs-response-planner-backend"
PACKAGE_NAME = LIB_NAME.replace("-", "_")
VERSION_FILE = f"src/{PACKAGE_NAME}/__version__.py"


def read_current_version():
    with io.open(VERSION_FILE, "r", encoding="utf-8") as f:
        return f.read().split("=")[-1].strip().strip("'\"")


def write_version(new_version):
    with io.open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(f"__version__ = '{new_version}'\n")


def replace_version_in_file(path, old_version, new_version):
    with io.open(path, "r", encoding="utf-8") as f:
        contents = f.read()
    updated = contents.replace(old_version, new_version)
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(updated)


def run(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = p.communicate()
    return p.returncode, stdout.decode(), stderr.decode()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <new_version>")
        print(f"Example: python {sys.argv[0]} 0.0.2")
        sys.exit(1)

    new_version = sys.argv[1]
    old_version = read_current_version()

    if old_version == new_version:
        print(f"Releasing {LIB_NAME}: {old_version} (current version)")
    else:
        print(f"Releasing {LIB_NAME}: {old_version} -> {new_version}")

        # Update version in all config files
        print("Updating __version__.py")
        write_version(new_version)

        print("Updating requirements.txt")
        replace_version_in_file("requirements.txt", old_version, new_version)

        print("Updating setup.cfg")
        replace_version_in_file("setup.cfg", old_version, new_version)

        print("Updating pyproject.toml")
        replace_version_in_file("pyproject.toml", old_version, new_version)

    # Delete old build artifacts
    print("Deleting old dist/")
    shutil.rmtree("dist", ignore_errors=True)

    # Build
    print("Building package")
    code, out, err = run("python -m build")
    if code != 0:
        print(f"Build failed (exit code {code})")
        print(out)
        print(err)
        sys.exit(1)
    print("Build succeeded")

    # Upload to PyPI
    print("Uploading to PyPI")
    code, out, err = run("python -m twine upload --config-file ~/.pypirc dist/*")
    if code != 0:
        print(f"Upload failed (exit code {code})")
        print(out)
        print(err)
        sys.exit(1)
    print("Upload succeeded")
