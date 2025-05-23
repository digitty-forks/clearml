import inspect
import json
import os
import re
import tempfile
from functools import reduce
from logging import getLogger
from sys import platform
from typing import Optional, Sequence, Union, Tuple, List, Callable, Dict, Any

from pathlib2 import Path
from six.moves.urllib.parse import urlparse

from .args import _Arguments
from .repo import ScriptInfo
from ...task import Task


class CreateAndPopulate(object):
    _VCS_SSH_REGEX = (
        "^"
        "(?:(?P<user>{regular}*?)@)?"
        "(?P<host>{regular}*?)"
        ":"
        "(?P<path>{regular}.*)?"
        "$".format(regular=r"[^/@:#]")
    )

    def __init__(
        self,
        project_name: Optional[str] = None,
        task_name: Optional[str] = None,
        task_type: Optional[str] = None,
        repo: Optional[str] = None,
        branch: Optional[str] = None,
        commit: Optional[str] = None,
        script: Optional[str] = None,
        working_directory: Optional[str] = None,
        module: Optional[str] = None,
        packages: Optional[Union[bool, Sequence[str]]] = None,
        requirements_file: Optional[Union[str, Path]] = None,
        docker: Optional[str] = None,
        docker_args: Optional[str] = None,
        docker_bash_setup_script: Optional[str] = None,
        output_uri: Optional[str] = None,
        base_task_id: Optional[str] = None,
        add_task_init_call: bool = True,
        force_single_script_file: bool = False,
        raise_on_missing_entries: bool = False,
        verbose: bool = False,
        binary: Optional[str] = None,
        detect_repository: bool = True
    ) -> None:
        """
        Create a new Task from an existing code base.
        If the code does not already contain a call to Task.init, pass add_task_init_call=True,
        and the code will be patched in remote execution (i.e. when executed by `clearml-agent`

        :param project_name: Set the project name for the task. Required if base_task_id is None.
        :param task_name: Set the name of the remote task. Required if base_task_id is None.
        :param task_type: Optional, The task type to be created. Supported values: 'training', 'testing', 'inference',
            'data_processing', 'application', 'monitor', 'controller', 'optimizer', 'service', 'qc', 'custom'
        :param repo: Remote URL for the repository to use, OR path to local copy of the git repository
            Example: 'https://github.com/allegroai/clearml.git' or '~/project/repo'
        :param branch: Select specific repository branch/tag (implies the latest commit from the branch)
        :param commit: Select specific commit id to use (default: latest commit,
            or when used with local repository matching the local commit id)
        :param script: Specify the entry point script for the remote execution. When used in tandem with
            remote git repository the script should be a relative path inside the repository,
            for example: './source/train.py' . When used with local repository path it supports a
            direct path to a file inside the local repository itself, for example: '~/project/source/train.py'
        :param module: If specified instead of executing `script`, a module named `module` is executed.
            Implies script is empty. Module can contain multiple argument for execution,
            for example: module="my.module arg1 arg2"
        :param working_directory: Working directory to launch the script from. Default: repository root folder.
            Relative to repo root or local folder.
        :param packages: Manually specify a list of required packages. Example: ["tqdm>=2.1", "scikit-learn"]
            or `True` to automatically create requirements
            based on locally installed packages (repository must be local).
            Pass an empty string to not install any packages (not even from the repository)
        :param requirements_file: Specify requirements.txt file to install when setting the session.
            If not provided, the requirements.txt from the repository will be used.
        :param docker: Select the docker image to be executed in by the remote session
        :param docker_args: Add docker arguments, pass a single string
        :param docker_bash_setup_script: Add bash script to be executed
            inside the docker before setting up the Task's environment
        :param output_uri: Optional, set the Tasks's output_uri (Storage destination).
            examples: 's3://bucket/folder', 'https://server/' , 'gs://bucket/folder', 'azure://bucket', '/folder/'
        :param base_task_id: Use a pre-existing task in the system, instead of a local repo/script.
            Essentially clones an existing task and overrides arguments/requirements.
        :param add_task_init_call: If True, a 'Task.init()' call is added to the script entry point in remote execution.
        :param force_single_script_file: If True, do not auto-detect local repository
        :param raise_on_missing_entries: If True, raise ValueError on missing entries when populating
        :param verbose: If True, print verbose logging
        :param binary: Binary used to launch the entry point
        :param detect_repository: If True, detect the repository if no repository has been specified.
            If False, don't detect repository under any circumstance. Ignored if `repo` is specified
        """
        if repo and len(urlparse(repo).scheme) <= 1 and not re.compile(self._VCS_SSH_REGEX).match(repo):
            folder = repo
            repo = None
        else:
            folder = None

        if script and module:
            raise ValueError("Entry point script or module need to be specified not both")

        if raise_on_missing_entries and not base_task_id:
            if not script and not module:
                raise ValueError("Entry point script not provided")
            if not repo and not folder and (script and not Path(script).is_file()):
                raise ValueError("Script file '{}' could not be found".format(script))
        if raise_on_missing_entries and commit and branch:
            raise ValueError(
                "Specify either a branch/tag or specific commit id, not both (either --commit or --branch)"
            )
        if raise_on_missing_entries and not folder and working_directory and working_directory.startswith("/"):
            raise ValueError("working directory '{}', must be relative to repository root")

        if requirements_file and not Path(requirements_file).is_file():
            raise ValueError("requirements file could not be found '{}'")

        self.folder = folder
        self.commit = commit
        self.branch = branch
        self.repo = repo
        self.script = script
        self.module = module
        self.cwd = working_directory
        assert not packages or isinstance(packages, (tuple, list, bool))
        if isinstance(packages, bool):
            self.packages = True if packages else None
        elif packages:
            self.packages = list(packages)
        else:
            self.packages = packages
        self.requirements_file = Path(requirements_file) if requirements_file else None
        self.base_task_id = base_task_id
        self.docker = dict(image=docker, args=docker_args, bash_script=docker_bash_setup_script)
        self.add_task_init_call = add_task_init_call
        self.project_name = project_name
        self.task_name = task_name
        self.task_type = task_type
        self.output_uri = output_uri
        self.task = None
        self.force_single_script_file = bool(force_single_script_file)
        self.raise_on_missing_entries = raise_on_missing_entries
        self.verbose = verbose
        self.binary = binary
        self.detect_repository = detect_repository

    def create_task(self, dry_run: bool = False) -> Union[Task, Dict]:
        """
        Create the new populated Task

        :param dry_run: Optional, If True, do not create an actual Task, instead return the Task definition as dict
        :return: newly created Task object
        """
        local_entry_file = None
        repo_info = None
        stand_alone_script_outside_repo = False
        entry_point = ""
        # populate from local repository / script
        if self.folder or (self.script and Path(self.script).is_file() and not self.repo):
            self.folder = os.path.expandvars(os.path.expanduser(self.folder)) if self.folder else None
            self.script = os.path.expandvars(os.path.expanduser(self.script)) if self.script else None
            self.cwd = os.path.expandvars(os.path.expanduser(self.cwd)) if self.cwd else None

            if self.module:
                entry_point = "-m {}".format(self.module)
                # we must have a folder if we are here
                local_entry_file = self.folder.rstrip("/") + "/."
            else:
                if Path(self.script).is_file():
                    entry_point = self.script
                else:
                    entry_point = (Path(self.folder) / self.script).as_posix()

                entry_point = os.path.abspath(entry_point)

                try:
                    if entry_point and Path(entry_point).is_file() and self.folder and Path(self.folder).is_dir():
                        # make sure we raise exception if this is outside the local repo folder
                        entry_point = (Path(entry_point) / (Path(entry_point).relative_to(self.folder))).as_posix()
                except ValueError:
                    entry_point = self.folder
                    stand_alone_script_outside_repo = True

                if not os.path.isfile(entry_point) and not stand_alone_script_outside_repo:
                    if (
                        not Path(self.script).is_absolute()
                        and not Path(self.cwd).is_absolute()
                        and (Path(self.folder) / self.cwd / self.script).is_file()
                    ):
                        entry_point = (Path(self.folder) / self.cwd / self.script).as_posix()
                    elif (
                        Path(self.cwd).is_absolute()
                        and not Path(self.script).is_absolute()
                        and (Path(self.cwd) / self.script).is_file()
                    ):
                        entry_point = (Path(self.cwd) / self.script).as_posix()
                    else:
                        raise ValueError("Script entrypoint file '{}' could not be found".format(entry_point))

                local_entry_file = entry_point

            if self.detect_repository:
                repo_info, requirements = ScriptInfo.get(
                    filepaths=[local_entry_file],
                    log=getLogger(),
                    create_requirements=self.packages is True,
                    uncommitted_from_remote=True,
                    detect_jupyter_notebook=False,
                    add_missing_installed_packages=True,
                    detailed_req_report=False,
                    force_single_script=self.force_single_script_file,
                )
            else:
                repo_info, requirements = None, None

            if stand_alone_script_outside_repo:
                # if we have a standalone script and a local repo we skip[ the local diff and store it
                local_entry_file = Path(self.script).as_posix()
                if self.detect_repository:
                    a_create_requirements = self.packages is True
                    a_repo_info, a_requirements = ScriptInfo.get(
                        filepaths=[Path(self.script).as_posix()],
                        log=getLogger(),
                        create_requirements=a_create_requirements,
                        uncommitted_from_remote=True,
                        detect_jupyter_notebook=False,
                        add_missing_installed_packages=True,
                        detailed_req_report=False,
                        force_single_script=True,
                    )
                    if repo_info.script["diff"]:
                        print(
                            "Warning: local git repo diff is ignored, "
                            "storing only the standalone script form {}".format(self.script)
                        )
                        repo_info.script["diff"] = a_repo_info.script["diff"] or ""
                    repo_info.script["entry_point"] = a_repo_info.script["entry_point"]
                    if a_create_requirements:
                        repo_info.script["requirements"] = a_repo_info.script.get("requirements") or {}

        # check if we have no repository and no requirements raise error
        if (
            self.raise_on_missing_entries
            and (self.requirements_file is None and self.packages is None)
            and not self.repo
            and (not repo_info or not repo_info.script or not repo_info.script.get("repository"))
            and (not entry_point or not entry_point.endswith(".sh"))
        ):
            raise ValueError("Standalone script detected '{}', but no requirements provided".format(self.script))
        if dry_run:
            task = None
            task_state: dict = dict(
                name=self.task_name,
                project=Task.get_project_id(self.project_name),
                type=str(self.task_type or Task.TaskTypes.training),
            )
            if self.output_uri is not None:
                task_state["output"] = dict(destination=self.output_uri)
        else:
            task_state = dict(script={})

            if self.base_task_id:
                if self.verbose:
                    print("Cloning task {}".format(self.base_task_id))
                task = Task.clone(
                    source_task=self.base_task_id,
                    project=Task.get_project_id(self.project_name),
                )

                self._set_output_uri(task)
            else:
                # noinspection PyProtectedMember
                task = Task._create(
                    task_name=self.task_name,
                    project_name=self.project_name,
                    task_type=self.task_type or Task.TaskTypes.training,
                )

                self._set_output_uri(task)

                # if there is nothing to populate, return
                if not any(
                    [
                        self.folder,
                        self.commit,
                        self.branch,
                        self.repo,
                        self.script,
                        self.module,
                        self.cwd,
                        self.packages,
                        self.requirements_file,
                        self.base_task_id,
                    ]
                    + (list(self.docker.values()))
                ):
                    return task

        # clear the script section
        task_state["script"] = {}
        if repo_info:
            task_state["script"]["repository"] = repo_info.script["repository"]
            task_state["script"]["version_num"] = repo_info.script["version_num"]
            task_state["script"]["branch"] = repo_info.script["branch"]
            task_state["script"]["diff"] = repo_info.script["diff"] or ""
            task_state["script"]["working_dir"] = repo_info.script["working_dir"]
            task_state["script"]["entry_point"] = repo_info.script["entry_point"]
            task_state["script"]["binary"] = self.binary or (
                "/bin/bash"
                if (
                    (repo_info.script["entry_point"] or "").lower().strip().endswith(".sh")
                    and not (repo_info.script["entry_point"] or "").lower().strip().startswith("-m ")
                )
                else repo_info.script["binary"]
            )
            task_state["script"]["requirements"] = repo_info.script.get("requirements") or {}
            if self.cwd:
                cwd = self.cwd
                if not Path(cwd).is_absolute():
                    # cwd should be relative to the repo_root, but we need the full path
                    # (repo_root + cwd) in order to resolve the entry point
                    cwd = os.path.normpath((Path(repo_info.script["repo_root"]) / self.cwd).as_posix())
                    if not Path(cwd).is_dir():
                        # we need to leave it as is, we have no idea, and this is a repo
                        cwd = self.cwd

                elif not Path(cwd).is_dir():
                    # we were passed an absolute dir and it does not exist
                    raise ValueError("Working directory '{}' could not be found".format(cwd))

                if self.module:
                    entry_point = "-m {}".format(self.module)
                elif stand_alone_script_outside_repo:
                    # this should be relative and the temp file we generated
                    entry_point = repo_info.script["entry_point"]
                else:
                    entry_point = os.path.normpath(
                        Path(repo_info.script["repo_root"])
                        / repo_info.script["working_dir"]
                        / repo_info.script["entry_point"]
                    )
                    # resolve entry_point relative to the current working directory
                    if Path(cwd).is_absolute():
                        entry_point = Path(entry_point).relative_to(cwd).as_posix()
                    else:
                        entry_point = repo_info.script["entry_point"]

                # restore cwd - make it relative to the repo_root again
                if Path(cwd).is_absolute():
                    # now cwd is relative again
                    cwd = Path(cwd).relative_to(repo_info.script["repo_root"]).as_posix()

                # make sure we always have / (never \\)
                if platform == "win32":
                    entry_point = entry_point.replace("\\", "/") if entry_point else ""
                    cwd = cwd.replace("\\", "/") if cwd else ""

                task_state["script"]["entry_point"] = entry_point or ""
                task_state["script"]["working_dir"] = cwd or "."
        elif self.repo:
            cwd = "/".join([p for p in (self.cwd or ".").split("/") if p and p != "."])
            # normalize backslashes and remove first one
            if self.module:
                entry_point = "-m {}".format(self.module)
            else:
                entry_point = "/".join([p for p in self.script.split("/") if p and p != "."])
                if cwd and entry_point.startswith(cwd + "/"):
                    entry_point = entry_point[len(cwd) + 1 :]

            task_state["script"]["repository"] = self.repo
            task_state["script"]["version_num"] = self.commit or None
            task_state["script"]["branch"] = self.branch or None
            task_state["script"]["diff"] = ""
            task_state["script"]["working_dir"] = cwd or "."
            task_state["script"]["entry_point"] = entry_point or ""

            if (
                self.script
                and Path(self.script).is_file()
                and (self.force_single_script_file or Path(self.script).is_absolute())
            ):
                self.force_single_script_file = True
                create_requirements = self.packages is True
                repo_info, requirements = ScriptInfo.get(
                    filepaths=[Path(self.script).as_posix()],
                    log=getLogger(),
                    create_requirements=create_requirements,
                    uncommitted_from_remote=True,
                    detect_jupyter_notebook=False,
                    add_missing_installed_packages=True,
                    detailed_req_report=False,
                    force_single_script=True,
                )
                task_state["script"]["binary"] = self.binary or (
                    "/bin/bash"
                    if (
                        (repo_info.script["entry_point"] or "").lower().strip().endswith(".sh")
                        and not (repo_info.script["entry_point"] or "").lower().strip().startswith("-m ")
                    )
                    else repo_info.script["binary"]
                )
                task_state["script"]["diff"] = repo_info.script["diff"] or ""
                task_state["script"]["entry_point"] = repo_info.script["entry_point"]
                if create_requirements:
                    task_state["script"]["requirements"] = repo_info.script.get("requirements") or {}
            else:
                if self.binary:
                    task_state["script"]["binary"] = self.binary
                elif (
                    entry_point
                    and entry_point.lower().strip().endswith(".sh")
                    and not entry_point.lower().strip().startswith("-m")
                ):
                    task_state["script"]["binary"] = "/bin/bash"
        else:
            # standalone task
            task_state["script"]["entry_point"] = (
                self.script if self.script else ("-m {}".format(self.module) if self.module else "")
            )
            task_state["script"]["working_dir"] = "."
        # update requirements
        reqs = []
        if self.requirements_file:
            with open(self.requirements_file.as_posix(), "rt") as f:
                reqs = [line.strip() for line in f.readlines()]
        if self.packages and self.packages is not True:
            reqs += self.packages
        if self.packages == "" and len(reqs) == 0:
            reqs = [""]
        if reqs:
            # make sure we have clearml.
            clearml_found = False
            for line in reqs:
                if line.strip().startswith("#"):
                    continue
                package = reduce(lambda a, b: a.split(b)[0], "#;@=~<>[", line).strip()
                if package == "clearml":
                    clearml_found = True
                    break
            if not clearml_found and reqs != [""]:
                reqs.append("clearml")
            task_state["script"]["requirements"] = {"pip": "\n".join(reqs)}
        elif not self.repo and repo_info and not repo_info.script.get("requirements"):
            # we are in local mode, make sure we have "requirements.txt" it is a must
            reqs_txt_file = Path(repo_info.script["repo_root"]) / "requirements.txt"
            poetry_toml_file = Path(repo_info.script["repo_root"]) / "pyproject.toml"
            if self.raise_on_missing_entries and not reqs_txt_file.is_file() and not poetry_toml_file.is_file():
                raise ValueError(
                    "requirements.txt not found [{}] "
                    "Use --requirements or --packages".format(reqs_txt_file.as_posix())
                )

        if self.add_task_init_call:
            script_entry = (
                "/" + task_state["script"].get("working_dir", ".") + "/" + task_state["script"]["entry_point"]
            )
            if platform == "win32":
                script_entry = os.path.normpath(script_entry).replace("\\", "/")
            else:
                script_entry = os.path.abspath(script_entry)
            idx_a = 0
            lines = None
            # find the right entry for the patch if we have a local file (basically after __future__
            if (
                local_entry_file
                and not stand_alone_script_outside_repo
                and not self.module
                and str(local_entry_file).lower().endswith(".py")
            ):
                with open(local_entry_file, "rt") as f:
                    lines = f.readlines()
                future_found = self._locate_future_import(lines)
                if future_found >= 0:
                    idx_a = future_found + 1

            task_init_patch = ""
            if (
                (self.repo or task_state.get("script", {}).get("repository"))
                and not self.force_single_script_file
                and not stand_alone_script_outside_repo
            ):
                # if we do not have requirements, add clearml to the requirements.txt
                if not reqs:
                    task_init_patch += (
                        "diff --git a/requirements.txt b/requirements.txt\n"
                        "--- a/requirements.txt\n"
                        "+++ b/requirements.txt\n"
                        "@@ -0,0 +1,1 @@\n"
                        "+clearml\n"
                    )

                # Add Task.init call
                if not self.module and script_entry and str(script_entry).lower().endswith(".py"):
                    task_init_patch += (
                        "diff --git a{script_entry} b{script_entry}\n"
                        "--- a{script_entry}\n"
                        "+++ b{script_entry}\n"
                        "@@ -{idx_a},0 +{idx_b},4 @@\n"
                        "+try: from allegroai import Task\n"
                        "+except ImportError: from clearml import Task\n"
                        '+(__name__ != "__main__") or Task.init()\n'
                        "+\n".format(script_entry=script_entry, idx_a=idx_a, idx_b=idx_a + 1)
                    )
            elif self.module:
                # if we are here, do nothing
                pass
            elif local_entry_file and lines:
                # if we are here it means we do not have a git diff, but a single script file
                init_lines = [
                    "try: from allegroai import Task\n",
                    "except ImportError: from clearml import Task\n",
                    '(__name__ != "__main__") or Task.init()\n\n',
                ]
                task_state["script"]["diff"] = "".join(lines[:idx_a] + init_lines + lines[idx_a:])
                # no need to add anything, we patched it.
                task_init_patch = ""
            elif str(script_entry or "").lower().endswith(".py"):
                # Add Task.init call
                # if we are here it means we do not have a git diff, but a single script file
                task_init_patch += (
                    "try: from allegroai import Task\n"
                    "except ImportError: from clearml import Task\n"
                    '(__name__ != "__main__") or Task.init()\n\n'
                )
                task_state["script"]["diff"] = task_init_patch + task_state["script"].get("diff", "")
                task_init_patch = ""

            # make sure we add the diff at the end of the current diff
            task_state["script"]["diff"] = task_state["script"].get("diff", "")
            if task_state["script"]["diff"] and not task_state["script"]["diff"].endswith("\n"):
                task_state["script"]["diff"] += "\n"
            task_state["script"]["diff"] += task_init_patch
        # set base docker image if provided
        if self.docker:
            if dry_run:
                task_state["container"] = dict(
                    image=self.docker.get("image") or "",
                    arguments=self.docker.get("args") or "",
                    setup_shell_script=self.docker.get("bash_script") or "",
                )
            else:
                task.set_base_docker(
                    docker_image=self.docker.get("image"),
                    docker_arguments=self.docker.get("args"),
                    docker_setup_bash_script=self.docker.get("bash_script"),
                )

        if self.verbose:
            if task_state["script"].get("repository"):
                repo_details = {
                    k: v for k, v in task_state["script"].items() if v and k not in ("diff", "requirements", "binary")
                }
                print("Repository Detected\n{}".format(json.dumps(repo_details, indent=2)))
            else:
                print("Standalone script detected\n  Script: {}".format(self.script))

            if task_state["script"].get("requirements") and task_state["script"]["requirements"].get("pip"):
                print(
                    "Requirements:{}{}".format(
                        "\n  Using requirements.txt: {}".format(self.requirements_file.as_posix())
                        if self.requirements_file
                        else "",
                        "\n  {}Packages: {}".format(
                            "Additional " if self.requirements_file else "",
                            self.packages,
                        )
                        if self.packages
                        else "",
                    )
                )
            if self.docker:
                print("Base docker image: {}".format(self.docker))

        if dry_run:
            return task_state

        # update the Task
        task.update_task(task_state)
        self.task = task
        return task

    def _set_output_uri(self, task: Task) -> None:
        if self.output_uri is not None:
            try:
                task.output_uri = self.output_uri
            except ValueError:
                getLogger().warning('Could not verify permission for output_uri: "{}"'.format(self.output_uri))
                # do not verify the output uri (it might not be valid when we are creating the Task)
                task.storage_uri = self.output_uri

    def update_task_args(
        self,
        args: Optional[Union[Sequence[str], Sequence[Tuple[str, str]]]] = None,
    ) -> ():
        """
        Update the newly created Task argparse Arguments
        If called before Task created, used for argument verification

        :param args: Arguments to pass to the remote execution, list of string pairs (argument, value) or
            list of strings '<argument>=<value>'. Example: ['lr=0.003', (batch_size, 64)]
        """
        if not args:
            return

        # check args are in format <key>=<value>
        args_list = []
        for a in args:
            if isinstance(a, (list, tuple)):
                assert len(a) == 2
                args_list.append(a)
                continue
            try:
                parts = a.split("=", 1)
                assert len(parts) == 2
                args_list.append(parts)
            except Exception:
                raise ValueError("Failed parsing argument '{}', arguments must be in '<key>=<value>' format")

        if not self.task:
            return

        task_params = self.task.get_parameters()
        args_list = {"Args/{}".format(k): v for k, v in args_list}
        task_params.update(args_list)
        self.task.set_parameters(task_params)

    def get_id(self) -> Optional[str]:
        """
        :return: Return the created Task id (str)
        """
        return self.task.id if self.task else None

    @staticmethod
    def _locate_future_import(lines: List[str]) -> int:
        """
        :param lines: string lines of a python file
        :return: line index of the last __future_ import. return -1 if no __future__ was found
        """
        # skip over the first two lines, they are ours
        # then skip over empty or comment lines
        lines = [
            (i, line.split("#", 1)[0].rstrip())
            for i, line in enumerate(lines)
            if line.strip("\r\n\t ") and not line.strip().startswith("#")
        ]

        # remove triple quotes ' """ '
        nested_c = -1
        skip_lines = []
        for i, line_pair in enumerate(lines):
            for _ in line_pair[1].split('"""')[1:]:
                if nested_c >= 0:
                    skip_lines.extend(list(range(nested_c, i + 1)))
                    nested_c = -1
                else:
                    nested_c = i
        # now select all the
        lines = [pair for i, pair in enumerate(lines) if i not in skip_lines]

        from_future = re.compile(r"^from[\s]*__future__[\s]*")
        import_future = re.compile(r"^import[\s]*__future__[\s]*")
        # test if we have __future__ import
        found_index = -1
        for a_i, (_, a_line) in enumerate(lines):
            if found_index >= a_i:
                continue
            if from_future.match(a_line) or import_future.match(a_line):
                found_index = a_i
                # check the last import block
                i, line = lines[found_index]
                # wither we have \\ character at the end of the line or the line is indented
                parenthesized_lines = "(" in line and ")" not in line
                while line.endswith("\\") or parenthesized_lines:
                    found_index += 1
                    i, line = lines[found_index]
                    if ")" in line:
                        break

            else:
                break

        return found_index if found_index < 0 else lines[found_index][0]


class CreateFromFunction(object):
    kwargs_section = "kwargs"
    return_section = "return"
    input_artifact_section = "kwargs_artifacts"
    default_task_template_header = """from clearml import Task
from clearml import TaskTypes
from clearml.automation.controller import PipelineDecorator
import inspect
"""
    task_template = """{header}
from clearml.utilities.proxy_object import get_basic_type

{artifact_serialization_function_source}

{artifact_deserialization_function_source}

{function_source}

if __name__ == '__main__':
    task = Task.init(
        auto_connect_frameworks={auto_connect_frameworks},
        auto_connect_arg_parser={auto_connect_arg_parser},
    )
    kwargs = {function_kwargs}
    task.connect(kwargs, name='{kwargs_section}')
    function_input_artifacts = {function_input_artifacts}
    params = task.get_parameters(cast=True) or dict()
    argspec = inspect.getfullargspec({function_name})
    if argspec.varkw is not None or argspec.varargs is not None:
        for k, v in params.items():
            if k.startswith('{kwargs_section}/'):
                kwargs[k.replace('{kwargs_section}/', '', 1)] = v
    return_section = '{return_section}'
    for k, v in params.items():
        if not v or not k.startswith('{input_artifact_section}/'):
            continue
        k = k.replace('{input_artifact_section}/', '', 1)
        task_id, artifact_name = v.split('.', 1)
        parent_task = Task.get_task(task_id=task_id)
        if artifact_name in parent_task.artifacts:
            kwargs[k] = parent_task.artifacts[artifact_name].get(deserialization_function={artifact_deserialization_function_name})
        else:
            kwargs[k] = parent_task.get_parameters(cast=True).get(return_section + '/' + artifact_name)
    if '0' in kwargs:  # *args arguments are present
        pos_args = [kwargs.pop(arg, None) for arg in (argspec.args or [])]
        other_pos_args_index = 0
        while str(other_pos_args_index) in kwargs:
            pos_args.append(kwargs.pop(str(other_pos_args_index)))
            other_pos_args_index += 1
        results = {function_name}(*pos_args, **kwargs)
    else:
        results = {function_name}(**kwargs)
    result_names = {function_return}
    if result_names:
        if not isinstance(results, (tuple, list)) or len(result_names) == 1:
            results = [results]
        parameters = dict()
        parameters_types = dict()
        for name, artifact in zip(result_names, results):
            if type(artifact) in (float, int, bool, str):
                parameters[return_section + '/' + name] = artifact
                parameters_types[return_section + '/' + name] = get_basic_type(artifact)
            else:
                task.upload_artifact(
                    name=name,
                    artifact_object=artifact,
                    extension_name='.pkl' if isinstance(artifact, dict) else None,
                    serialization_function={artifact_serialization_function_name}
                )
        if parameters:
            task._set_parameters(parameters, __parameters_types=parameters_types, __update=True)
"""

    @classmethod
    def create_task_from_function(
        cls,
        a_function: Callable,
        function_kwargs: Optional[Dict[str, Any]] = None,
        function_input_artifacts: Optional[Dict[str, str]] = None,
        function_return: Optional[List[str]] = None,
        project_name: Optional[str] = None,
        task_name: Optional[str] = None,
        task_type: Optional[str] = None,
        auto_connect_frameworks: Optional[dict] = None,
        auto_connect_arg_parser: Optional[dict] = None,
        repo: Optional[str] = None,
        branch: Optional[str] = None,
        commit: Optional[str] = None,
        packages: Optional[Union[str, Sequence[str]]] = None,
        docker: Optional[str] = None,
        docker_args: Optional[str] = None,
        docker_bash_setup_script: Optional[str] = None,
        output_uri: Optional[str] = None,
        helper_functions: Optional[Sequence[Callable]] = None,
        dry_run: bool = False,
        task_template_header: Optional[str] = None,
        artifact_serialization_function: Optional[Callable[[Any], Union[bytes, bytearray]]] = None,
        artifact_deserialization_function: Optional[Callable[[bytes], Any]] = None,
        _sanitize_function: Optional[Callable[[str], str]] = None,
        _sanitize_helper_functions: Optional[Callable[[str], str]] = None,
        skip_global_imports: bool = False,
        working_dir: Optional[str] = None,
    ) -> Optional[Union[Dict, "Task"]]:
        """
        Create a Task from a function, including wrapping the function input arguments
        into the hyper-parameter section as kwargs, and storing function results as named artifacts

        Example:
            def mock_func(a=6, b=9):
                c = a*b
                print(a, b, c)
                return c, c**2

            create_task_from_function(mock_func, function_return=['mul', 'square'])

        Example arguments from other Tasks (artifact):
            def mock_func(matrix_np):
                c = matrix_np*matrix_np
                print(matrix_np, c)
                return c

            create_task_from_function(
                mock_func,
                function_input_artifacts={'matrix_np': 'aabb1122.previous_matrix'},
                function_return=['square_matrix']
            )

        :param a_function: A global function to convert into a standalone Task
        :param function_kwargs: Optional, provide subset of function arguments and default values to expose.
            If not provided automatically take all function arguments & defaults
        :param function_input_artifacts: Optional, pass input arguments to the function from
            other Tasks's output artifact.
            Example argument named `numpy_matrix` from Task ID `aabbcc` artifact name `answer`:
            {'numpy_matrix': 'aabbcc.answer'}
        :param function_return: Provide a list of names for all the results.
            If not provided no results will be stored as artifacts.
        :param project_name: Set the project name for the task. Required if base_task_id is None.
        :param task_name: Set the name of the remote task. Required if base_task_id is None.
        :param task_type: Optional, The task type to be created. Supported values: 'training', 'testing', 'inference',
            'data_processing', 'application', 'monitor', 'controller', 'optimizer', 'service', 'qc', 'custom'
        :param auto_connect_frameworks: Control the frameworks auto connect, see `Task.init` auto_connect_frameworks
        :param auto_connect_arg_parser: Control the ArgParser auto connect, see `Task.init` auto_connect_arg_parser
        :param repo: Remote URL for the repository to use, OR path to local copy of the git repository
            Example: 'https://github.com/allegroai/clearml.git' or '~/project/repo'
        :param branch: Select specific repository branch/tag (implies the latest commit from the branch)
        :param commit: Select specific commit id to use (default: latest commit,
            or when used with local repository matching the local commit id)
        :param packages: Manually specify a list of required packages or a local requirements.txt file.
            Example: ["tqdm>=2.1", "scikit-learn"] or "./requirements.txt"
            If not provided, packages are automatically added based on the imports used in the function.
        :param docker: Select the docker image to be executed in by the remote session
        :param docker_args: Add docker arguments, pass a single string
        :param docker_bash_setup_script: Add bash script to be executed
            inside the docker before setting up the Task's environment
        :param output_uri: Optional, set the Tasks's output_uri (Storage destination).
            examples: 's3://bucket/folder', 'https://server/' , 'gs://bucket/folder', 'azure://bucket', '/folder/'
        :param helper_functions: Optional, a list of helper functions to make available
            for the standalone function Task.
        :param dry_run: If True, do not create the Task, but return a dict of the Task's definitions
        :param task_template_header: A string placed at the top of the task's code
        :param artifact_serialization_function: A serialization function that takes one
            parameter of any type which is the object to be serialized. The function should return
            a `bytes` or `bytearray` object, which represents the serialized object. All parameter/return
            artifacts uploaded by the pipeline will be serialized using this function.
            All relevant imports must be done in this function. For example:

            .. code-block:: py

                def serialize(obj):
                    import dill
                    return dill.dumps(obj)
        :param artifact_deserialization_function: A deserialization function that takes one parameter of type `bytes`,
            which represents the serialized object. This function should return the deserialized object.
            All parameter/return artifacts fetched by the pipeline will be deserialized using this function.
            All relevant imports must be done in this function. For example:

            .. code-block:: py

                def deserialize(bytes_):
                    import dill
                    return dill.loads(bytes_)
        :param _sanitize_function: Sanitization function for the function string.
        :param _sanitize_helper_functions: Sanitization function for the helper function string.
        :param skip_global_imports: If True, the global imports will not be fetched from the function's file, otherwise
            all global imports will be automatically imported in a safe manner at the beginning of the function's
            execution. Default is False
        :param working_dir: Optional, Working directory to launch the script from.

        :return: Newly created Task object
        """
        # not set -> equals True
        if auto_connect_frameworks is None:
            auto_connect_frameworks = True
        if auto_connect_arg_parser is None:
            auto_connect_arg_parser = True

        assert not auto_connect_frameworks or isinstance(auto_connect_frameworks, (bool, dict))
        assert not auto_connect_arg_parser or isinstance(auto_connect_arg_parser, (bool, dict))

        (
            function_source,
            function_name,
        ) = CreateFromFunction.__extract_function_information(
            a_function,
            sanitize_function=_sanitize_function,
            skip_global_imports=skip_global_imports,
        )
        # add helper functions on top.
        for f in helper_functions or []:
            (
                helper_function_source,
                _,
            ) = CreateFromFunction.__extract_function_information(f, sanitize_function=_sanitize_helper_functions)
            function_source = helper_function_source + "\n\n" + function_source

        artifact_serialization_function_source, artifact_serialization_function_name = (
            CreateFromFunction.__extract_function_information(artifact_serialization_function)
            if artifact_serialization_function
            else ("", "None")
        )
        (
            artifact_deserialization_function_source,
            artifact_deserialization_function_name,
        ) = (
            CreateFromFunction.__extract_function_information(artifact_deserialization_function)
            if artifact_deserialization_function
            else ("", "None")
        )

        function_input_artifacts = function_input_artifacts or dict()
        # verify artifact kwargs:
        if not all(len(v.split(".", 1)) == 2 for v in function_input_artifacts.values()):
            raise ValueError(
                "function_input_artifacts={}, it must in the format: "
                '{{"argument": "task_id.artifact_name"}}'.format(function_input_artifacts)
            )
        inspect_args = None
        function_kwargs_types = dict()
        if function_kwargs is None:
            function_kwargs = dict()
            inspect_args = inspect.getfullargspec(a_function)
            if inspect_args and inspect_args.args:
                inspect_defaults_vals = inspect_args.defaults
                inspect_defaults_args = inspect_args.args

                # adjust the defaults so they match the args (match from the end)
                if inspect_defaults_vals and len(inspect_defaults_vals) != len(inspect_defaults_args):
                    inspect_defaults_args = inspect_defaults_args[-len(inspect_defaults_vals) :]

                if inspect_defaults_vals and len(inspect_defaults_vals) != len(inspect_defaults_args):
                    getLogger().warning(
                        "Ignoring default argument values: "
                        "could not find all default valued for: '{}'".format(function_name)
                    )
                    inspect_defaults_vals = []

                function_kwargs = (
                    {str(k): v for k, v in zip(inspect_defaults_args, inspect_defaults_vals)}
                    if inspect_defaults_vals
                    else {str(k): None for k in inspect_defaults_args}
                )

        if function_kwargs:
            if not inspect_args:
                inspect_args = inspect.getfullargspec(a_function)
            # inspect_func.annotations[k]
            if inspect_args.annotations:
                supported_types = _Arguments.get_supported_types()
                function_kwargs_types = {
                    str(k): str(inspect_args.annotations[k].__name__)
                    for k in inspect_args.annotations
                    if inspect_args.annotations[k] in supported_types
                }

        task_template = cls.task_template.format(
            header=task_template_header or cls.default_task_template_header,
            auto_connect_frameworks=auto_connect_frameworks,
            auto_connect_arg_parser=auto_connect_arg_parser,
            kwargs_section=cls.kwargs_section,
            input_artifact_section=cls.input_artifact_section,
            function_source=function_source,
            function_kwargs=function_kwargs,
            function_input_artifacts=function_input_artifacts,
            function_name=function_name,
            function_return=function_return,
            return_section=cls.return_section,
            artifact_serialization_function_source=artifact_serialization_function_source,
            artifact_serialization_function_name=artifact_serialization_function_name,
            artifact_deserialization_function_source=artifact_deserialization_function_source,
            artifact_deserialization_function_name=artifact_deserialization_function_name,
        )

        temp_dir = repo if repo and os.path.isdir(repo) else None
        with tempfile.NamedTemporaryFile("w", suffix=".py", dir=temp_dir) as temp_file:
            temp_file.write(task_template)
            temp_file.flush()

            requirements_file = None
            if packages and not isinstance(packages, (list, tuple)) and Path(packages).is_file():
                requirements_file = packages
                packages = False

            populate = CreateAndPopulate(
                project_name=project_name,
                task_name=task_name or str(function_name),
                task_type=task_type,
                script=temp_file.name,
                packages=packages if packages is not None else True,
                requirements_file=requirements_file,
                repo=repo,
                branch=branch,
                commit=commit,
                docker=docker,
                docker_args=docker_args,
                docker_bash_setup_script=docker_bash_setup_script,
                output_uri=output_uri,
                add_task_init_call=False,
                working_directory=working_dir,
            )
            entry_point = "{}.py".format(function_name)
            task = populate.create_task(dry_run=dry_run)

            if dry_run:
                task["script"]["diff"] = task_template
                task["script"]["entry_point"] = entry_point
                task["script"]["working_dir"] = working_dir or "."
                task["hyperparams"] = {
                    cls.kwargs_section: {
                        k: dict(
                            section=cls.kwargs_section,
                            name=k,
                            value=str(v) if v is not None else "",
                            type=function_kwargs_types.get(k, None),
                        )
                        for k, v in (function_kwargs or {}).items()
                    },
                    cls.input_artifact_section: {
                        k: dict(
                            section=cls.input_artifact_section,
                            name=k,
                            value=str(v) if v is not None else "",
                        )
                        for k, v in (function_input_artifacts or {}).items()
                    },
                }
            else:
                task.update_task(
                    task_data={
                        "script": task.data.script.to_dict().update(
                            {
                                "entry_point": entry_point,
                                "working_dir": ".",
                                "diff": task_template,
                            }
                        )
                    }
                )
                hyper_parameters = (
                    {"{}/{}".format(cls.kwargs_section, k): str(v) for k, v in function_kwargs}
                    if function_kwargs
                    else {}
                )
                hyper_parameters.update(
                    {"{}/{}".format(cls.input_artifact_section, k): str(v) for k, v in function_input_artifacts}
                    if function_input_artifacts
                    else {}
                )
                __function_kwargs_types = (
                    {"{}/{}".format(cls.kwargs_section, k): v for k, v in function_kwargs_types}
                    if function_kwargs_types
                    else None
                )
                task.set_parameters(hyper_parameters, __parameters_types=__function_kwargs_types)

            return task

    @staticmethod
    def __sanitize_remove_type_hints(function_source: str) -> str:
        try:
            import ast

            try:
                # available in Python3.9+
                from ast import unparse
            except ImportError:
                from ...utilities.lowlevel.astor_unparse import unparse
        except ImportError:
            return function_source

        # noinspection PyBroadException
        try:

            class TypeHintRemover(ast.NodeTransformer):
                def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
                    # remove the return type definition
                    node.returns = None
                    # remove all argument annotations
                    if node.args.args:
                        for arg in node.args.args:
                            arg.annotation = None
                    return node

            # parse the source code into an AST
            parsed_source = ast.parse(function_source)
            # remove all type annotations, function return type definitions
            # and import statements from 'typing'
            transformed = TypeHintRemover().visit(parsed_source)
            # convert the AST back to source code
            return unparse(transformed).lstrip("\n")
        except Exception:
            # just in case we failed parsing.
            return function_source

    @staticmethod
    def __extract_imports(func: Callable) -> str:
        def add_import_guard(import_: str) -> str:
            return (
                "try:\n    "
                + import_.replace("\n", "\n    ", import_.count("\n") - 1)
                + "\nexcept Exception as e:\n    print('Import error: ' + str(e))\n"
            )

        # noinspection PyBroadException
        try:
            import ast

            func_module = inspect.getmodule(func)
            source = inspect.getsource(func_module)
            parsed_source = ast.parse(source)
            imports = []
            for parsed_source_entry in parsed_source.body:
                # we only include global imports (i.e. at col_offset 0)
                if parsed_source_entry.col_offset != 0:
                    continue
                if isinstance(parsed_source_entry, ast.ImportFrom):
                    for sub_entry in parsed_source_entry.names:
                        import_str = "from {} import {}".format(parsed_source_entry.module, sub_entry.name)
                        if sub_entry.asname:
                            import_str += " as {}".format(sub_entry.asname)
                        imports.append(import_str)
                elif isinstance(parsed_source_entry, ast.Import):
                    for sub_entry in parsed_source_entry.names:
                        import_str = "import {}".format(sub_entry.name)
                        if sub_entry.asname:
                            import_str += " as {}".format(sub_entry.asname)
                        imports.append(import_str)
            imports = [add_import_guard(import_) for import_ in imports]
            return "\n".join(imports)
        except Exception as e:
            getLogger().warning("Could not fetch function imports: {}".format(e))
            return ""

    @staticmethod
    def _extract_wrapped(decorated: Callable) -> Optional[Callable]:
        if not decorated.__closure__:
            return None
        closure = (c.cell_contents for c in decorated.__closure__)
        if not closure:
            return None
        return next((c for c in closure if inspect.isfunction(c)), None)

    @staticmethod
    def _deep_extract_wrapped(decorated: Callable) -> Callable:
        while True:
            # noinspection PyProtectedMember
            func = CreateFromFunction._extract_wrapped(decorated)
            if not func:
                return decorated
            decorated = func

    @staticmethod
    def __sanitize(func_source: str, sanitize_function: Optional[Callable[[str], str]] = None) -> str:
        if sanitize_function:
            func_source = sanitize_function(func_source)
        return CreateFromFunction.__sanitize_remove_type_hints(func_source)

    @staticmethod
    def __get_func_members(module: Any) -> List[str]:
        result = []
        try:
            import ast

            source = inspect.getsource(module)
            parsed = ast.parse(source)
            for f in parsed.body:
                if isinstance(f, ast.FunctionDef):
                    result.append(f.name)
        except Exception as e:
            name = getattr(module, "__name__", module)
            getLogger().warning("Could not fetch function declared in {}: {}".format(name, e))
        return result

    @staticmethod
    def __get_source_with_decorators(
        func: Callable,
        original_module: Optional[Any] = None,
        sanitize_function: Optional[Callable] = None,
    ) -> str:
        if original_module is None:
            original_module = inspect.getmodule(func)
        func_members = CreateFromFunction.__get_func_members(original_module)
        try:
            func_members_dict = dict(inspect.getmembers(original_module, inspect.isfunction))
        except Exception as e:
            name = getattr(original_module, "__name__", original_module)
            getLogger().warning("Could not fetch functions from {}: {}".format(name, e))
            func_members_dict = {}
        decorated_func = CreateFromFunction._deep_extract_wrapped(func)
        decorated_func_source = CreateFromFunction.__sanitize(
            inspect.getsource(decorated_func), sanitize_function=sanitize_function
        )
        try:
            import ast

            parsed_decorated = ast.parse(decorated_func_source)
            for body_elem in parsed_decorated.body:
                if not isinstance(body_elem, ast.FunctionDef):
                    continue
                for decorator in body_elem.decorator_list:
                    name = None
                    if isinstance(decorator, ast.Name):
                        name = decorator.id
                    elif isinstance(decorator, ast.Call):
                        name = decorator.func.id
                    if not name:
                        continue
                    decorator_func = func_members_dict.get(name)
                    if name not in func_members or not decorator_func:
                        continue
                    decorated_func_source = (
                        CreateFromFunction.__get_source_with_decorators(
                            decorator_func,
                            original_module=original_module,
                            sanitize_function=sanitize_function,
                        )
                        + "\n\n"
                        + decorated_func_source
                    )
                break
        except Exception as e:
            getLogger().warning("Could not fetch full definition of function {}: {}".format(func.__name__, e))
        return decorated_func_source

    @staticmethod
    def __extract_function_information(
        function: Callable,
        sanitize_function: Optional[Callable] = None,
        skip_global_imports: bool = False,
    ) -> (str, str):
        function = CreateFromFunction._deep_extract_wrapped(function)
        function_source = CreateFromFunction.__get_source_with_decorators(function, sanitize_function=sanitize_function)
        if not skip_global_imports:
            imports = CreateFromFunction.__extract_imports(function)
        else:
            imports = ""
        return imports + "\n" + function_source, function.__name__
