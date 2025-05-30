import sys
from argparse import ArgumentParser

from pathlib2 import Path

import clearml.backend_api.session
from clearml import Task, PipelineController
from clearml.backend_interface.task.populate import CreateAndPopulate
from clearml.version import __version__

clearml.backend_api.session.Session.add_client("clearml-task", __version__)


def setup_parser(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--version",
        action="store_true",
        default=None,
        help="Display the clearml-task utility version",
    )
    parser.add_argument(
        "--project",
        type=str,
        default=None,
        help="Required: set the project name for the task. If --base-task-id is used, this arguments is optional.",
    )
    parser.add_argument(
        "--name",
        type=str,
        default=None,
        help="Required: select a name for the remote task",
    )
    parser.add_argument(
        "--tags",
        default=None,
        nargs="*",
        help='Optional: add tags to the newly created Task. \'Example: --tags "base" "job"\'',
    )
    parser.add_argument(
        "--repo",
        type=str,
        default=None,
        help="remote URL for the repository to use. Example: --repo https://github.com/allegroai/clearml.git",
    )
    parser.add_argument(
        "--branch",
        type=str,
        default=None,
        help="Select specific repository branch/tag (implies the latest commit from the branch)",
    )
    parser.add_argument(
        "--commit",
        type=str,
        default=None,
        help="Select specific commit id to use (default: latest commit, "
        "or when used with local repository matching the local commit id)",
    )
    parser.add_argument(
        "--folder",
        type=str,
        default=None,
        help="Remotely execute the code in the local folder. "
        "Notice! It assumes a git repository already exists. "
        "Current state of the repo (commit id and uncommitted changes) is logged "
        "and will be replicated on the remote machine",
    )
    parser.add_argument(
        "--script",
        type=str,
        default=None,
        help="Specify the entry point script for the remote execution. "
        "Currently supports .py .ipynb and .sh scripts (python, jupyter notebook, bash) "
        "When used in tandem with --repo the script should be a relative path inside "
        "the repository, for example: --script source/train.py."
        "When used with --folder it supports a direct path to a file inside the local "
        "repository itself, for example: --script ~/project/source/train.py. "
        "To run a bash script, simply specify the path of that script; the script should "
        "have the .sh extension, for example: --script init.sh",
    )
    parser.add_argument(
        "--binary",
        type=str,
        default=None,
        help="Binary used to launch the entry point. For example: '--binary python3', '--binary /bin/bash'."
        "By default, the binary will be auto-detected.",
    )
    parser.add_argument(
        "--module",
        type=str,
        default=None,
        help="Instead of a script entry point, specify a python module to be remotely executed. "
        "Notice: It cannot be used with --script at the same time. "
        'for example: --module "torch.distributed.launch train_script.py"',
    )
    parser.add_argument(
        "--cwd",
        type=str,
        default=None,
        help="Working directory to launch the script from. Default: repository root folder. "
        "Relative to repo root or local folder",
    )
    parser.add_argument(
        "--args",
        default=None,
        nargs="*",
        help="Arguments to pass to the remote execution, list of <argument>=<value> strings."
        "Currently only argparse arguments are supported. "
        "Example: --args lr=0.003 batch_size=64",
    )
    parser.add_argument(
        "--queue",
        type=str,
        default=None,
        help="Select the queue to launch the task. "
        "If not provided a Task will be created but it will not be launched.",
    )
    parser.add_argument(
        "--requirements",
        type=str,
        default=None,
        help="Specify requirements.txt file to install when setting the session. "
        "If not provided, the requirements.txt from the repository will be used.",
    )
    parser.add_argument(
        "--packages",
        default=None,
        nargs="*",
        help="Manually specify a list of required packages. 'Example: --packages \"tqdm>=2.1 scikit-learn\"'",
    )
    parser.add_argument(
        "--docker",
        type=str,
        default=None,
        help="Select the docker image to use in the remote session",
    )
    parser.add_argument(
        "--docker_args",
        type=str,
        default=None,
        help="Add docker arguments, pass a single string",
    )
    parser.add_argument(
        "--docker_bash_setup_script",
        type=str,
        default=None,
        help="Add bash script to be executed inside the docker before setting up the Task's environment",
    )
    parser.add_argument(
        "--output-uri",
        type=str,
        default=None,
        required=False,
        help="Optional: set the Task `output_uri` (automatically upload model destination)",
    )
    parser.add_argument(
        "--task-type",
        type=str,
        default=None,
        help="Set the Task type, optional values: "
        "training, testing, inference, data_processing, application, monitor, "
        "optimizer, service, qc, custom. Will be ignored if '--pipeline' is used.",
    )
    parser.add_argument(
        "--skip-task-init",
        action="store_true",
        default=None,
        help="If set, Task.init() call is not added to the entry point, and is assumed "
        "to be called in within the script. Default: add Task.init() call entry point script",
    )
    parser.add_argument(
        "--base-task-id",
        type=str,
        default=None,
        help="Use a pre-existing task in the system, instead of a local repo/script. "
        "Essentially clones an existing task and overrides arguments/requirements.",
    )
    parser.add_argument(
        "--import-offline-session",
        type=str,
        default=None,
        help="Specify the path to the offline session you want to import.",
    )
    parser.add_argument(
        "--force-no-requirements",
        action="store_true",
        help="If specified, no requirements will be installed, nor do they need to be specified"
    )
    parser.add_argument(
        "--skip-repo-detection",
        action="store_true",
        help="If specified, skip repository detection when no repository is specified. "
        "No repository will be set in remote execution"
    )
    parser.add_argument(
        "--skip-python-env-install",
        action="store_true",
        help="If specified, the agent will not install any required Python packages when running the task. "
        "Instead, it will use the preexisting Python environment to run the task. "
        "Only relevant when the agent is running in Docker mode or is running the task in Kubernetes"
    )
    parser.add_argument(
        "--pipeline",
        action="store_true",
        help="If specified, indicate that the created object is a pipeline instead of a regular task",
    )
    parser.add_argument(
        "--pipeline-version",
        type=str,
        default=None,
        help="Specify the pipeline version. Will be ignored if '--pipeline' is not specified",
    )
    parser.add_argument(
        "--pipeline-dont-add-run-number",
        action="store_true",
        help="If specified, don't add the run number to the pipeline. Will be ignored if '--pipeline' is not specified",
    )


def cli() -> None:
    title = "ClearML launch - launch any codebase on remote machine running clearml-agent"
    print(title)
    parser = ArgumentParser(description=title)
    setup_parser(parser)

    # get the args
    args = parser.parse_args()

    if len(sys.argv) < 2:
        parser.print_help()
        exit(0)

    if args.version:
        print("Version {}".format(__version__))
        exit(0)

    if not args.name and not args.import_offline_session:
        raise ValueError("Task name must be provided, use `--name <task-name>`")

    if args.docker_bash_setup_script and Path(args.docker_bash_setup_script).is_file():
        with open(args.docker_bash_setup_script, "r") as bash_setup_script_file:
            bash_setup_script = bash_setup_script_file.readlines()
            # remove Bash Shebang
            if bash_setup_script and bash_setup_script[0].strip().startswith("#!"):
                bash_setup_script = bash_setup_script[1:]
    else:
        bash_setup_script = args.docker_bash_setup_script or None

    if args.import_offline_session:
        print("Importing offline session: {}".format(args.import_offline_session))
        Task.import_offline_session(args.import_offline_session)
    else:
        docker_args = args.docker_args
        if args.skip_python_env_install:
            docker_args = ((docker_args or "") + " -e CLEARML_AGENT_SKIP_PYTHON_ENV_INSTALL=1").lstrip(" ")
        packages = "" if args.force_no_requirements else args.packages
        requirements = "" if args.force_no_requirements else args.requirements
        if args.script and args.script.endswith(".sh") and not args.binary:
            print("Detected shell script. Binary will be set to '/bin/bash'")
        if args.pipeline:
            argparse_args = []
            for arg in (args.args or []):
                arg_split = arg.split("=")
                if len(arg_split) != 2:
                    raise ValueError("Invalid argument: {}. Format should be key=value".format(arg))
                argparse_args.append(arg_split)
            pipeline = PipelineController.create(
                project_name=args.project,
                task_name=args.name,
                repo=args.repo or args.folder,
                branch=args.branch,
                commit=args.commit,
                script=args.script,
                module=args.module,
                working_directory=args.cwd,
                packages=packages,
                requirements_file=requirements,
                docker=args.docker,
                docker_args=docker_args,
                docker_bash_setup_script=bash_setup_script,
                version=args.pipeline_version,
                add_run_number=False if args.pipeline_dont_add_run_number else True,
                binary=args.binary,
                argparse_args=argparse_args or None,
                detect_repository=not args.skip_repo_detection
            )
            created_task = pipeline._task
        else:
            create_and_populate = CreateAndPopulate(
                project_name=args.project,
                task_name=args.name,
                task_type=args.task_type,
                repo=args.repo or args.folder,
                branch=args.branch,
                commit=args.commit,
                script=args.script,
                module=args.module,
                working_directory=args.cwd,
                packages=packages,
                requirements_file=requirements,
                docker=args.docker,
                docker_args=docker_args,
                docker_bash_setup_script=bash_setup_script,
                output_uri=args.output_uri,
                base_task_id=args.base_task_id,
                add_task_init_call=not args.skip_task_init,
                raise_on_missing_entries=True,
                verbose=True,
                binary=args.binary,
                detect_repository=not args.skip_repo_detection
            )
            # verify args before creating the Task
            create_and_populate.update_task_args(args.args)
            print("Creating new task")
            create_and_populate.create_task()
            # update Task args
            create_and_populate.update_task_args(args.args)
            created_task = create_and_populate.task
        # set tags
        if args.tags:
            created_task.add_tags(args.tags)

        # noinspection PyProtectedMember
        created_task._set_runtime_properties({"_CLEARML_TASK": True})

        print("New {} created id={}".format("pipeline" if args.pipeline else "task", created_task.id))
        if not args.queue:
            print(
                "Warning: No queue was provided, leaving {} in draft-mode.".format(
                    "pipeline" if args.pipeline else "task"
                )
            )
            exit(0)

        Task.enqueue(created_task, queue_name=args.queue)
        print(
            "{} id={} sent for execution on queue {}".format(
                "Pipeline" if args.pipeline else "task", created_task.id, args.queue
            )
        )
        print("Execution log at: {}".format(created_task.get_output_log_web_page()))


def main() -> None:
    try:
        cli()
    except KeyboardInterrupt:
        print("\nUser aborted")
    except Exception as ex:
        print("\nError: {}".format(ex))
        exit(1)


if __name__ == "__main__":
    main()
