import importlib
import sys
import threading
from typing import Callable, Optional, Any

import six
from pathlib2 import Path

from ..frameworks import (
    _patched_call,
    _patched_call_no_recursion_guard,
    WeightsFileHandler,
    _Empty,
)
from ..import_bind import PostImportHookPatching
from ...binding.frameworks.base_bind import PatchBaseModelIO
from ...config import running_remotely
from ...model import Framework


class PatchPyTorchModelIO(PatchBaseModelIO):
    _current_task = None
    _checkpoint_filename = {}
    __patched = None
    __patched_lightning = None
    __patched_pytorch_lightning = None
    __patched_mmcv = None

    @staticmethod
    def update_current_task(task: Any, **_: Any) -> None:
        PatchPyTorchModelIO._current_task = task
        if not task:
            return
        PatchPyTorchModelIO._patch_model_io()
        PatchPyTorchModelIO._patch_lightning_io()
        PatchPyTorchModelIO._patch_pytorch_lightning_io()
        PatchPyTorchModelIO._patch_mmcv()
        PostImportHookPatching.add_on_import("torch", PatchPyTorchModelIO._patch_model_io)
        PostImportHookPatching.add_on_import("lightning", PatchPyTorchModelIO._patch_lightning_io)
        PostImportHookPatching.add_on_import("pytorch_lightning", PatchPyTorchModelIO._patch_pytorch_lightning_io)

    @staticmethod
    def _patch_model_io() -> None:
        if PatchPyTorchModelIO.__patched:
            return

        if "torch" not in sys.modules:
            return

        PatchPyTorchModelIO.__patched = True

        # noinspection PyBroadException
        try:
            import torch  # noqa

            torch.save = _patched_call(torch.save, PatchPyTorchModelIO._save)
            torch.load = _patched_call(torch.load, PatchPyTorchModelIO._load)
            # noinspection PyBroadException
            try:
                # noinspection PyProtectedMember
                torch.jit._script.RecursiveScriptModule.save = _patched_call(
                    torch.jit._script.RecursiveScriptModule.save,
                    PatchPyTorchModelIO._save,
                )
            except BaseException:
                pass

            # no need to worry about recursive calls, _patched_call takes care of that
            if hasattr(torch, "serialization") and hasattr(torch.serialization, "_save"):
                torch.serialization._save = _patched_call(torch.serialization._save, PatchPyTorchModelIO._save)  # noqa
            if hasattr(torch, "serialization") and hasattr(torch.serialization, "_load"):
                torch.serialization._load = _patched_call(torch.serialization._load, PatchPyTorchModelIO._load)  # noqa
            if hasattr(torch, "serialization") and hasattr(torch.serialization, "_legacy_save"):
                torch.serialization._legacy_save = _patched_call(
                    torch.serialization._legacy_save, PatchPyTorchModelIO._save
                )  # noqa
            if hasattr(torch, "serialization") and hasattr(torch.serialization, "_legacy_load"):
                torch.serialization._legacy_load = _patched_call(
                    torch.serialization._legacy_load, PatchPyTorchModelIO._load
                )  # noqa
        except ImportError:
            pass
        except Exception:
            pass  # print('Failed patching pytorch')

    @staticmethod
    def _patch_mmcv() -> None:
        if PatchPyTorchModelIO.__patched_mmcv:
            return
        if "mmcv" not in sys.modules:
            return
        PatchPyTorchModelIO.__patched_mmcv = True

        # noinspection PyBroadException
        try:
            from mmcv.runner import epoch_based_runner, iter_based_runner

            # we don't want the recursion check here because it guards pytorch's patched save functions
            # which we need in order to log the saved model/checkpoint
            epoch_based_runner.save_checkpoint = _patched_call_no_recursion_guard(
                epoch_based_runner.save_checkpoint,
                PatchPyTorchModelIO._mmcv_save_checkpoint,
            )
            iter_based_runner.save_checkpoint = _patched_call_no_recursion_guard(
                iter_based_runner.save_checkpoint,
                PatchPyTorchModelIO._mmcv_save_checkpoint,
            )
        except Exception:
            pass

    @staticmethod
    def _mmcv_save_checkpoint(original_fn: Callable, model: Any, filename: str, *args: Any, **kwargs: Any) -> Any:
        # note that mmcv.runner.save_checkpoint doesn't return anything, hence the need for this
        # patch function, but we return from it just in case this changes in the future
        if not PatchPyTorchModelIO._current_task:
            return original_fn(model, filename, *args, **kwargs)
        tid = threading.current_thread().ident
        PatchPyTorchModelIO._checkpoint_filename[tid] = filename
        ret = original_fn(model, filename, *args, **kwargs)
        del PatchPyTorchModelIO._checkpoint_filename[tid]
        return ret

    @staticmethod
    def _patch_lightning_io_internal(lightning_name: str) -> None:
        """
        :param lightning_name: lightning module name, use "lightning" or "pytorch_lightning"
        """
        try:
            pytorch_lightning = importlib.import_module(lightning_name)
        except ImportError:
            # lightning is not installed
            # Nothing to do
            return
        if lightning_name == "lightning":
            pytorch_lightning = pytorch_lightning.pytorch

        def patch_method(cls, method_name: str, patched_method: Callable) -> None:
            """
            Patch a method of a class if it exists.

            Otherwise, no effect.
            """
            try:
                method = getattr(cls, method_name)
            except AttributeError:
                # the method is not defined on the given class
                pass
            else:
                setattr(cls, method_name, _patched_call(method, patched_method))

        patch_method(
            pytorch_lightning.trainer.Trainer,
            "save_checkpoint",
            PatchPyTorchModelIO._save,
        )

        patch_method(
            pytorch_lightning.trainer.Trainer,
            "restore",
            PatchPyTorchModelIO._load_from_obj,
        )

        try:
            checkpoint_connector = pytorch_lightning.trainer.connectors.checkpoint_connector
        except AttributeError:
            # checkpoint_connector does not yet exist; lightning version is < 0.10.0
            # Nothing left to do
            return

        try:
            CheckpointConnector = checkpoint_connector._CheckpointConnector
        except AttributeError:
            # CheckpointConnector has not yet been made protected
            # lighting version is < 2.0.0
            try:
                CheckpointConnector = checkpoint_connector.CheckpointConnector
            except AttributeError:
                # Unexpected future breaking change in lightning
                # No way to automatically handle
                return

        patch_method(CheckpointConnector, "save_checkpoint", PatchPyTorchModelIO._save)

        patch_method(CheckpointConnector, "restore", PatchPyTorchModelIO._load_from_obj)

    @staticmethod
    def _patch_lightning_io() -> None:
        if PatchPyTorchModelIO.__patched_lightning:
            return

        if "lightning" not in sys.modules:
            return

        PatchPyTorchModelIO.__patched_lightning = True

        PatchPyTorchModelIO._patch_lightning_io_internal("lightning")

    @staticmethod
    def _patch_pytorch_lightning_io() -> None:
        if PatchPyTorchModelIO.__patched_pytorch_lightning:
            return

        if "pytorch_lightning" not in sys.modules:
            return

        PatchPyTorchModelIO.__patched_pytorch_lightning = True

        PatchPyTorchModelIO._patch_lightning_io_internal("pytorch_lightning")

    @staticmethod
    def _save(original_fn: Callable, obj: Any, f: Any, *args: Any, **kwargs: Any) -> Any:
        ret = original_fn(obj, f, *args, **kwargs)

        # if there is no main task or this is a nested call
        if not PatchPyTorchModelIO._current_task:
            return ret

        # pytorch-lightning check if rank is zero
        if hasattr(obj, "is_global_zero"):
            if not obj.is_global_zero:
                return ret
        elif hasattr(obj, "trainer") and hasattr(obj.trainer, "is_global_zero"):
            if not obj.trainer.is_global_zero:
                return ret

        # noinspection PyBroadException
        try:
            if isinstance(f, six.string_types):
                filename = f
            elif hasattr(f, "as_posix"):
                filename = f.as_posix()
            elif hasattr(f, "name"):
                # noinspection PyBroadException
                try:
                    f.flush()
                except Exception:
                    pass

                if not isinstance(f.name, six.string_types):
                    # Probably a BufferedRandom object that has no meaningful name (still no harm flushing)
                    return ret

                filename = f.name
            else:
                filename = PatchPyTorchModelIO.__get_cached_checkpoint_filename()
        except Exception:
            filename = PatchPyTorchModelIO.__get_cached_checkpoint_filename()

        # give the model a descriptive name based on the file name
        # noinspection PyBroadException
        try:
            model_name = Path(filename).stem if filename is not None else None
        except Exception:
            model_name = None
        WeightsFileHandler.create_output_model(
            obj,
            filename,
            Framework.pytorch,
            PatchPyTorchModelIO._current_task,
            singlefile=True,
            model_name=model_name,
        )

        return ret

    @staticmethod
    def _load(original_fn: Callable, f: Any, *args: Any, **kwargs: Any) -> Any:
        # if there is no main task or this is a nested call
        if not PatchPyTorchModelIO._current_task:
            return original_fn(f, *args, **kwargs)

        # noinspection PyBroadException
        try:
            if isinstance(f, six.string_types):
                filename = f
            elif hasattr(f, "as_posix"):
                filename = f.as_posix()
            elif hasattr(f, "name"):
                filename = f.name
            else:
                filename = None
        except Exception:
            filename = None

        # register input model
        empty = _Empty()
        # Hack: disabled
        if False and running_remotely():
            filename = WeightsFileHandler.restore_weights_file(
                empty, filename, Framework.pytorch, PatchPyTorchModelIO._current_task
            )
            model = original_fn(filename or f, *args, **kwargs)
        else:
            # try to load model before registering, in case we fail
            model = original_fn(f, *args, **kwargs)
            WeightsFileHandler.restore_weights_file(
                empty, filename, Framework.pytorch, PatchPyTorchModelIO._current_task
            )

        if empty.trains_in_model:
            # noinspection PyBroadException
            try:
                model.trains_in_model = empty.trains_in_model
            except Exception:
                pass

        return model

    @staticmethod
    def _load_from_obj(original_fn: Callable, obj: Any, f: Any, *args: Any, **kwargs: Any) -> Any:
        # if there is no main task or this is a nested call
        if not PatchPyTorchModelIO._current_task:
            return original_fn(obj, f, *args, **kwargs)

        # noinspection PyBroadException
        try:
            if isinstance(f, six.string_types):
                filename = f
            elif hasattr(f, "as_posix"):
                filename = f.as_posix()
            elif hasattr(f, "name"):
                filename = f.name
            else:
                filename = None
        except Exception:
            filename = None

        # register input model
        empty = _Empty()
        # Hack: disabled
        if False and running_remotely():
            filename = WeightsFileHandler.restore_weights_file(
                empty, filename, Framework.pytorch, PatchPyTorchModelIO._current_task
            )
            model = original_fn(obj, filename or f, *args, **kwargs)
        else:
            # try to load model before registering, in case we fail
            model = original_fn(obj, f, *args, **kwargs)
            WeightsFileHandler.restore_weights_file(
                empty, filename, Framework.pytorch, PatchPyTorchModelIO._current_task
            )

        if empty.trains_in_model:
            # noinspection PyBroadException
            try:
                model.trains_in_model = empty.trains_in_model
            except Exception:
                pass

        return model

    @staticmethod
    def __get_cached_checkpoint_filename() -> Optional[str]:
        tid = threading.current_thread().ident
        checkpoint_filename = PatchPyTorchModelIO._checkpoint_filename.get(tid)
        return checkpoint_filename or None
