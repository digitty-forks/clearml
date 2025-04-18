from time import sleep
from typing import Optional, Sequence, Any

from ..optimization import Objective, SearchStrategy
from ..parameters import (
    DiscreteParameterRange,
    Parameter,
    UniformIntegerParameterRange,
    UniformParameterRange,
    LogUniformParameterRange,
)
from ...task import Task

try:
    # noinspection PyPackageRequirements
    import optuna

    Task.add_requirements("optuna")
except ImportError:
    raise ImportError("OptimizerOptuna requires 'optuna' package, it was not found\n install with: pip install optuna")


class OptunaObjective(object):
    def __init__(
        self,
        base_task_id: str,
        queue_name: str,
        optimizer: "OptimizerOptuna",
        max_iteration_per_job: int,
        min_iteration_per_job: Optional[int],
        sleep_interval: float,
        config_space: dict,
    ) -> None:
        self.base_task_id = base_task_id
        self.optimizer = optimizer
        self.queue_name = queue_name
        self.sleep_interval = sleep_interval
        self.max_iteration_per_job = max_iteration_per_job
        self.min_iteration_per_job = min_iteration_per_job
        self._config_space = config_space

    def objective(self, trial: optuna.Trial) -> Optional[float]:
        """
        return metric value for a specified set of parameter, pulled from the trail object

        :param optuna.Trial trial: optuna.Trial object
        :return: metric value float
        """
        parameter_override = {}
        for name, (func_name, params) in self._config_space.items():
            suggest = getattr(trial, func_name)
            parameter_override[name] = suggest(name=name, **params)

        # fixes https://github.com/optuna/optuna/issues/2021
        if parameter_override in self.optimizer.parameter_override_history:
            print("Pruning trial with duplicate parameters")
            raise optuna.exceptions.TrialPruned()

        self.optimizer.parameter_override_history.append(parameter_override)
        current_job = self.optimizer.helper_create_job(self.base_task_id, parameter_override=parameter_override)
        # noinspection PyProtectedMember
        self.optimizer._current_jobs.append(current_job)
        if not current_job.launch(self.queue_name):
            # failed launching the job
            return None
        iteration_value = None
        is_pending = True
        while True:
            if is_pending and not current_job.is_pending():
                is_pending = False
                self.optimizer.budget.jobs.update(current_job.task_id(), 1.0)
            if not is_pending:
                # noinspection PyProtectedMember
                iteration_value = self.optimizer._objective_metric.get_current_raw_objective(current_job)
                if not iteration_value:
                    if not self.optimizer.monitor_job(current_job):
                        break
                    continue

                # make sure we skip None objective values
                if not any(val is None or val[1] is None for val in iteration_value):
                    iteration = max(iv[0] for iv in iteration_value)
                    # trial pruning based on intermediate values not supported when using multi-objective
                    # noinspection PyProtectedMember
                    if self.optimizer._objective_metric.len == 1:
                        # update budget
                        trial.report(value=iteration_value[0][1], step=iteration)

                        # Handle pruning based on the intermediate value.
                        if trial.should_prune() and (
                            not self.min_iteration_per_job or iteration >= self.min_iteration_per_job
                        ):
                            current_job.abort()
                            raise optuna.TrialPruned()

                    # check if we exceeded this job budget
                    if self.max_iteration_per_job and iteration >= self.max_iteration_per_job:
                        current_job.abort()
                        break

            if not self.optimizer.monitor_job(current_job):
                break
            sleep(self.sleep_interval)

        # noinspection PyProtectedMember
        objective_metric = self.optimizer._objective_metric.get_objective(current_job)
        # noinspection PyProtectedMember
        if self.optimizer._objective_metric.len == 1:
            objective_metric = objective_metric[0]
            iteration_value = iteration_value[0]
        print("OptunaObjective result metric={}, iteration {}".format(objective_metric, iteration_value))
        # noinspection PyProtectedMember
        self.optimizer._current_jobs.remove(current_job)
        return objective_metric


class OptimizerOptuna(SearchStrategy):
    def __init__(
        self,
        base_task_id: str,
        hyper_parameters: Sequence[Parameter],
        objective_metric: Objective,
        execution_queue: str,
        num_concurrent_workers: int,
        max_iteration_per_job: Optional[int],
        total_max_jobs: Optional[int],
        pool_period_min: float = 2.0,
        min_iteration_per_job: Optional[int] = None,
        time_limit_per_job: Optional[float] = None,
        compute_time_limit: Optional[float] = None,
        optuna_sampler: Optional[Any] = None,
        optuna_pruner: Optional[Any] = None,
        continue_previous_study: Optional[optuna.Study] = None,
        **optuna_kwargs: Any
    ) -> None:
        """
        Initialize an Optuna search strategy optimizer
        Optuna performs robust and efficient hyperparameter optimization at scale by combining.
        Specific hyperparameter pruning strategy can be selected via `sampler` and `pruner` arguments

        :param str base_task_id: Task ID (str)
        :param list hyper_parameters: list of Parameter objects to optimize over
        :param Objective objective_metric: Objective metric to maximize / minimize
        :param str execution_queue: execution queue to use for launching Tasks (experiments).
        :param int num_concurrent_workers: Limit number of concurrent running Tasks (machines)
        :param int max_iteration_per_job: number of iteration per job
            'iterations' are the reported iterations for the specified objective,
            not the maximum reported iteration of the Task.
        :param int total_max_jobs: total maximum job for the optimization process.
            Must be provided in order to calculate the total budget for the optimization process.
            The total budget is measured by "iterations" (see above)
            and will be set to `max_iteration_per_job * total_max_jobs`
            This means more than total_max_jobs could be created, as long as the cumulative iterations
            (summed over all created jobs) will not exceed `max_iteration_per_job * total_max_jobs`
        :param float pool_period_min: time in minutes between two consecutive pools
        :param int min_iteration_per_job: The minimum number of iterations (of the Objective metric) per single job,
            before early stopping the Job. (Optional)
        :param float time_limit_per_job: Optional, maximum execution time per single job in minutes,
            when time limit is exceeded job is aborted
        :param float compute_time_limit: The maximum compute time in minutes. When time limit is exceeded,
            all jobs aborted. (Optional)
        :param optuna_kwargs: arguments passed directly to the Optuna object
        """
        super(OptimizerOptuna, self).__init__(
            base_task_id=base_task_id,
            hyper_parameters=hyper_parameters,
            objective_metric=objective_metric,
            execution_queue=execution_queue,
            num_concurrent_workers=num_concurrent_workers,
            pool_period_min=pool_period_min,
            time_limit_per_job=time_limit_per_job,
            compute_time_limit=compute_time_limit,
            max_iteration_per_job=max_iteration_per_job,
            min_iteration_per_job=min_iteration_per_job,
            total_max_jobs=total_max_jobs,
        )
        self._optuna_sampler = optuna_sampler
        self._optuna_pruner = optuna_pruner
        verified_optuna_kwargs = []
        self._optuna_kwargs = dict((k, v) for k, v in optuna_kwargs.items() if k in verified_optuna_kwargs)
        self._param_iterator = None
        self._objective = None
        self._study = continue_previous_study if continue_previous_study else None
        self.parameter_override_history = []

    def start(self) -> ():
        """
        Start the Optimizer controller function loop()
        If the calling process is stopped, the controller will stop as well.

        .. important::
            This function returns only after optimization is completed or :meth:`stop` was called.

        """
        if self._objective_metric.len != 1:
            self._study = optuna.create_study(
                directions=[
                    "minimize" if sign_ < 0 else "maximize" for sign_ in self._objective_metric.get_objective_sign()
                ],
                load_if_exists=False,
                sampler=self._optuna_sampler,
                pruner=self._optuna_pruner,
                study_name=self._optimizer_task.id if self._optimizer_task else None,
            )
        else:
            self._study = optuna.create_study(
                direction="minimize" if self._objective_metric.get_objective_sign()[0] < 0 else "maximize",
                load_if_exists=False,
                sampler=self._optuna_sampler,
                pruner=self._optuna_pruner,
                study_name=self._optimizer_task.id if self._optimizer_task else None,
            )
        config_space = self._convert_hyper_parameters_to_optuna()
        self._objective = OptunaObjective(
            base_task_id=self._base_task_id,
            queue_name=self._execution_queue,
            optimizer=self,
            max_iteration_per_job=self.max_iteration_per_job,
            min_iteration_per_job=self.min_iteration_per_job,
            sleep_interval=int(self.pool_period_minutes * 60),
            config_space=config_space,
        )
        self._study.optimize(
            self._objective.objective,
            n_trials=self.total_max_jobs,
            n_jobs=self._num_concurrent_workers,
        )

    def stop(self) -> ():
        """
        Stop the current running optimization loop,
        Called from a different thread than the :meth:`start`.
        """
        if self._study:
            try:
                self._study.stop()
            except Exception as ex:
                print(ex)
        self._stop_event.set()

    def _convert_hyper_parameters_to_optuna(self) -> dict:
        cs = {}
        for p in self._hyper_parameters:
            if isinstance(p, LogUniformParameterRange):
                hp_type = "suggest_float"
                hp_params = dict(
                    low=p.base**p.min_value,
                    high=p.base**p.max_value,
                    log=True,
                    step=None,
                )
            elif isinstance(p, UniformParameterRange):
                if p.include_max and p.step_size:
                    hp_type = "suggest_discrete_uniform"
                    hp_params = dict(low=p.min_value, high=p.max_value, q=p.step_size)
                else:
                    hp_type = "suggest_float"
                    hp_params = dict(low=p.min_value, high=p.max_value, log=False, step=p.step_size)
            elif isinstance(p, UniformIntegerParameterRange):
                hp_type = "suggest_int"
                hp_params = dict(
                    low=p.min_value,
                    high=p.max_value if p.include_max else p.max_value - p.step_size,
                    log=False,
                    step=p.step_size,
                )
            elif isinstance(p, DiscreteParameterRange):
                hp_type = "suggest_categorical"
                hp_params = dict(choices=p.values)
            else:
                raise ValueError("HyperParameter type {} not supported yet with OptimizerBOHB".format(type(p)))
            cs[p.name] = (hp_type, hp_params)

        return cs
