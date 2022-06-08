import os
import json
from datetime import datetime
import subprocess

def extract_stats(path):
    stats = list()
    for file in os.listdir(path):
        if file.endswith(".stats.json"):
            with open(f"{path}/{file}", 'r') as f:
                content = json.load(f)
                stats.append(content)
    return stats  


"""This file contains functions from flatpak-rebuilder, which are also
usefull for analysis. Ideally these should not be copy/paseted here,
but taken from flatpak-rebuilder directly, if this one was available
easily as a python package (which is not the case). """

class FlatpakCmdException(Exception):
    def __init__(self, cmd, msg = ""):
        super().__init__(f"Failed to run {cmd}, with the following error: {msg}")
        
class GitNotFoundException(Exception):
    pass

def cmd_output_to_dict(output: str) -> dict[str, str]:
    """Format commands with output of the form 'key : value' into a dictionary"""
    result = [
        list(map(str.strip, line.split(":", 1)))
        for line in output.split("\n")
        if ":" in line
    ]
    resultDict: dict[str, str] = dict(result)
    return resultDict

def flatpak_date_to_datetime(date: str) -> datetime:
    format = "%Y-%m-%d %H:%M:%S %z"
    return datetime.strptime(date, format)

def run_flatpak_command(
    cmd,
    installation,
    may_need_root=False,
    capture_output=False,
    cwd = None,
    interactive=True,
    arch = None,
    check_returncode=True,
    include_stderr=False,
):
    """Runs a flatpak shell command.
    Parameters
    ----------
    cmd
        The command to execute.
    installation
        The flatpak installation to use (i.e user, system).
    may_need_root : bool, optional
        If true will use sudo if it runs with a system install.
    capture_output : bool, optional
        If true, will capture and return the output
    cwd: str, optional
        Run the command in this directory (if set).
    interactive : bool, optional
        Run the command in interactive mode.
    arch: str, optional
        Add the --arch=<arch> flag to the command.
    check_returncode : bool, optional
        If true, will check return code and throw exception if not 0.
    include_stderr: bool, optional
        If true, will pipe stderr in stdout and return it (regardless of capture_output).
    Returns
    -------
    str
        Empty if no capture flag set, the command output (either stdout or stderr) otherwise.
    Raises
    ------
    Exception
        If check_returncode = True and the command returns a non zero code.
    """
    if may_need_root and installation != "user":
        cmd.insert(0, "sudo")

    if installation == "user":
        cmd.append("--user")
    elif installation == "system":
        cmd.append("--system")
    else:
        cmd.append("--installation=" + installation)

    if arch:
        cmd.append("--arch=" + arch)

    if not interactive:
        cmd.append("--noninteractive")

    if include_stderr:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=cwd)
    elif capture_output:
        result = subprocess.run(cmd, capture_output=True, cwd=cwd)
    else:
        result = subprocess.run(cmd, cwd=cwd)

    if result.returncode != 0 and check_returncode:
        if include_stderr:
            raise FlatpakCmdException(cmd, result.stdout.decode("UTF-8"))
        elif capture_output:
            raise FlatpakCmdException(cmd, result.stderr.decode("UTF-8"))
        else:
            raise FlatpakCmdException(cmd)
    else:
        if capture_output or include_stderr:
            return result.stdout.decode("UTF-8")
        else:
            return ""

def find_flatpak_commit_for_date(
    remote, installation, package, date
):
    """Find the latest commit of a flatpak, at a certain date. This is used to estimate
    the commit used for certain dependencies where it is not dirrectly provided.
    Parameters
    ----------
    remote : str
        Name of the remote (i.e flathub)
    installation : str
        Installation in which the package is installed.
    package : str
        Name of the package.
    date : datetime
        Date at which the commit was the latest.
    """
    cmd = ["flatpak", "remote-info", remote, package, "--log"]
    output = run_flatpak_command(cmd, installation, capture_output=True)
    commits = output.split("\n\n")[1:]
    # We use the fact that --log return commits from the most recent to the oldest
    for commit in commits:
        commit = cmd_output_to_dict(commit)
        commit_date = flatpak_date_to_datetime(commit["Date"])
        if commit_date <= date:
            return commit["Commit"]

    raise Exception("No commit matching the date has been found.")
    
def get_additional_deps(remote: str, package: str) -> str:
    """Get the link to the github repo, containing the manifest and some additional
    dependencies used for the build.

    Raises
    ------
    Exception if the remote is not supported.
    CalledProcessError if the repo does not exists.
    """
    if remote == "flathub":
        link = "github.com/flathub/" + package
    elif remote == "flathub-beta":
        link = "github.com/flathub/" + package
    else:
        raise Exception(f"Remote {remote} is not supported.")

    # Verify that repo exists
    cmd = ["git", "ls-remote", "https://null:null@" + link]
    if subprocess.run(cmd, capture_output=True).returncode != 0:
        raise GitNotFoundException(f"No git repository found for package: {package}")

    return "https://" + link

def find_pacman_name(pkg):
    cmd = ['pkgfile', '-i', pkg, '-l']
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        return None
    output = result.stdout.decode('UTF-8')
    name = output.split('/')[1]
    print(name)
    cmd = f"rebuildctl -H https://reproducible.archlinux.org pkgs ls --json --name {name}"
    result = subprocess.run(cmd, capture_output=True, shell=True)
    output = result.stderr.decode('UTF-8')
    if result.returncode != 0:
        return None
    output = result.stdout.decode('UTF-8')
    return json.loads(output)

def find_build_manifest(files: list[str], package: str) -> str | None:
    """Find the manifest file, it is always of the form package.yml/json/yaml.
    This is the format in whcih we find the manifest when it comes from the github repo.
    """
    manifests = [
        file
        for file in files
        if file == package + ".json"
        or file == package + ".yml"
        or file == package + ".yaml"
    ]
    if len(manifests) > 1:
        return None
    return manifests[0]
