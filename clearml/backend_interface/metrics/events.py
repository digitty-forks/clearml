import abc
import hashlib
import time
from functools import reduce
from logging import getLevelName
from typing import Optional, List, Dict, Union, Tuple, Any

import io
import attr
import numpy as np
import pathlib2
import six
from PIL import Image
from six.moves.urllib.parse import urlparse, urlunparse

from ...backend_api.services import events
from ...config import deferred_config
from ...debugging.log import LoggerRoot
from ...storage.util import quote_url
from ...utilities.attrs import attrs
from ...utilities.process.mp import SingletonLock


@six.add_metaclass(abc.ABCMeta)
class MetricsEventAdapter(object):
    """
    Adapter providing all the base attributes required by a metrics event and defining an interface used by the
    metrics manager when batching and writing events.
    """

    default_nan_value = 0.0
    default_inf_value = 0.0
    """ Default value used when a np.nan or np.inf value is encountered """
    report_nan_warning_period = 1000
    report_inf_warning_period = 1000
    _report_nan_warning_iteration = float("inf")
    _report_inf_warning_iteration = float("inf")

    @attrs(cmp=False, slots=True)
    class FileEntry(object):
        """File entry used to report on file data that needs to be uploaded prior to sending the event"""

        event = attr.attrib()

        name = attr.attrib()
        """ File name """

        stream = attr.attrib()
        """ File-like object containing the file's data """

        url_prop = attr.attrib()
        """ Property name that should be updated with the uploaded url """

        key_prop = attr.attrib()

        upload_uri = attr.attrib()

        url = attr.attrib(default=None)

        exception = attr.attrib(default=None)
        retries = attr.attrib(default=None)

        delete_local_file = attr.attrib(default=True)
        """ Local file path, if exists, delete the file after upload completed """

        def set_exception(self, exp: Exception) -> None:
            self.exception = exp
            self.event.upload_exception = exp

    @property
    def metric(self) -> Any:
        return self._metric

    @metric.setter
    def metric(self, value: Any) -> None:
        self._metric = value

    @property
    def variant(self) -> Any:
        return self._variant

    def __init__(
        self,
        metric: str,
        variant: str,
        iter: Optional[int] = None,
        timestamp: Optional[int] = None,
        task: Optional[str] = None,
        gen_timestamp_if_none: bool = True,
        model_event: Optional[dict] = None,
    ) -> None:
        if not timestamp and gen_timestamp_if_none:
            timestamp = int(time.time() * 1000)
        self._metric = metric
        self._variant = variant
        self._iter = iter
        self._timestamp = timestamp
        self._task = task
        self._model_event = model_event

        # Try creating an event just to trigger validation
        _ = self.get_api_event()
        self.upload_exception = None

    @abc.abstractmethod
    def get_api_event(self) -> None:
        """Get an API event instance"""
        pass

    def get_file_entry(self) -> None:
        """Get information for a file that should be uploaded before this event is sent"""
        pass

    def get_iteration(self) -> Optional[int]:
        return self._iter

    def update(self, task: Optional[str] = None, iter_offset: Optional[int] = None, **kwargs: Any) -> None:
        """Update event properties"""
        if task:
            self._task = task
        if iter_offset is not None and self._iter is not None:
            self._iter += iter_offset

    def _get_base_dict(self) -> Dict[str, Any]:
        """Get a dict with the base attributes"""
        res = dict(
            task=self._task,
            timestamp=self._timestamp,
            metric=self._metric,
            variant=self._variant,
        )
        if self._iter is not None:
            res.update(iter=self._iter)
        if self._model_event is not None:
            res.update(model_event=self._model_event)
        return res

    @classmethod
    def _convert_np_nan_inf(cls, val: float) -> float:
        if np.isnan(val):
            cls._report_nan_warning_iteration += 1
            if cls._report_nan_warning_iteration >= cls.report_nan_warning_period:
                LoggerRoot.get_base_logger().info(
                    "NaN value encountered. Reporting it as '{}'. Use clearml.Logger.set_reporting_nan_value to assign another value".format(
                        cls.default_nan_value
                    )
                )
                cls._report_nan_warning_iteration = 0
            return cls.default_nan_value
        if np.isinf(val):
            cls._report_inf_warning_iteration += 1
            if cls._report_inf_warning_iteration >= cls.report_inf_warning_period:
                LoggerRoot.get_base_logger().info(
                    "inf value encountered. Reporting it as '{}'. Use clearml.Logger.set_reporting_inf_value to assign another value".format(
                        cls.default_inf_value
                    )
                )
                cls._report_inf_warning_iteration = 0
            return cls.default_inf_value
        return val


class ScalarEvent(MetricsEventAdapter):
    """Scalar event adapter"""

    def __init__(self, metric: str, variant: str, value: float, iter: int, **kwargs: Any) -> None:
        self._value = self._convert_np_nan_inf(value)
        super(ScalarEvent, self).__init__(metric=metric, variant=variant, iter=iter, **kwargs)

    def get_api_event(self) -> "events.MetricsScalarEvent":
        return events.MetricsScalarEvent(value=self._value, **self._get_base_dict())


class ConsoleEvent(MetricsEventAdapter):
    """Console log event adapter"""

    def __init__(self, message: str, level: int, worker: str, **kwargs: Any) -> None:
        self._value = str(message)
        self._level = getLevelName(level) if isinstance(level, int) else str(level)
        self._worker = worker
        super(ConsoleEvent, self).__init__(metric=None, variant=None, iter=0, **kwargs)

    def get_api_event(self) -> "events.TaskLogEvent":
        return events.TaskLogEvent(
            task=self._task,
            timestamp=self._timestamp,
            level=self._level,
            worker=self._worker,
            msg=self._value,
        )


class VectorEvent(MetricsEventAdapter):
    """Vector event adapter"""

    def __init__(self, metric: str, variant: str, values: List[float], iter: int, **kwargs: Any) -> None:
        self._values = [self._convert_np_nan_inf(v) for v in values]
        super(VectorEvent, self).__init__(metric=metric, variant=variant, iter=iter, **kwargs)

    def get_api_event(self) -> "events.MetricsVectorEvent":
        return events.MetricsVectorEvent(values=self._values, **self._get_base_dict())


class PlotEvent(MetricsEventAdapter):
    """Plot event adapter"""

    def __init__(self, metric: str, variant: str, plot_str: str, iter: Optional[int] = None, **kwargs: Any) -> None:
        self._plot_str = plot_str
        super(PlotEvent, self).__init__(metric=metric, variant=variant, iter=iter, **kwargs)

    def get_api_event(self) -> "events.MetricsPlotEvent":
        return events.MetricsPlotEvent(plot_str=self._plot_str, **self._get_base_dict())


class ImageEventNoUpload(MetricsEventAdapter):
    def __init__(self, metric: str, variant: str, src: str, iter: int = 0, **kwargs: Any) -> None:
        self._url = src
        parts = urlparse(src)
        self._key = urlunparse(("", "", parts.path, parts.params, parts.query, parts.fragment))
        super(ImageEventNoUpload, self).__init__(metric, variant, iter=iter, **kwargs)

    def get_api_event(self) -> "events.MetricsImageEvent":
        return events.MetricsImageEvent(url=self._url, key=self._key, **self._get_base_dict())


class UploadEvent(MetricsEventAdapter):
    """Image event adapter"""

    _format = deferred_config(
        "metrics.images.format",
        "JPEG",
        transform=lambda x: "." + str(x).upper().lstrip("."),
    )
    _quality = deferred_config("metrics.images.quality", 87, transform=int)
    _subsampling = deferred_config("metrics.images.subsampling", 0, transform=int)
    _file_history_size = deferred_config("metrics.file_history_size", 5, transform=int)
    _upload_retries = 3

    _metric_counters = {}
    _metric_counters_lock = SingletonLock()

    @staticmethod
    def _replace_slash(part: str) -> str:
        # replace the three quote symbols we cannot have,
        # notice % will be converted to %25 when the link is quoted, so we should not use it
        # Replace quote safe characters: ";" | "/" | "?" | ":" | "@" | "&" | "=" | "+" | "$" | "," | "\n" | "\r"
        return reduce(
            lambda a, b: a.replace(b, "0x{:02x}".format(ord(b))),
            "#\"';?:@&=+$,%!\r\n",
            part.replace("\\", "/").strip("/").replace("/", ".slash."),
        )

    def __init__(
        self,
        metric: str,
        variant: str,
        image_data: Union[np.ndarray, six.StringIO, six.BytesIO, None],
        local_image_path: Optional[str] = None,
        iter: int = 0,
        upload_uri: Optional[str] = None,
        file_history_size: Optional[int] = None,
        delete_after_upload: bool = False,
        **kwargs: Any
    ) -> None:
        # param override_filename: override uploaded file name (notice extension will be added from local path
        # param override_filename_ext: override uploaded file extension
        if image_data is not None and (
            not hasattr(image_data, "shape") and not isinstance(image_data, (six.StringIO, six.BytesIO))
        ):
            raise ValueError("Image must have a shape attribute")
        self._image_data = image_data
        self._local_image_path = local_image_path
        self._url = None
        self._key = None
        self._count = None
        self._filename = None
        self.file_history_size = file_history_size or int(self._file_history_size)
        self._override_filename = kwargs.pop("override_filename", None)
        self._upload_uri = upload_uri
        self._delete_after_upload = delete_after_upload
        # get upload uri upfront, either predefined image format or local file extension
        # e.g.: image.png -> .png or image.raw.gz -> .raw.gz
        self._override_filename_ext = kwargs.pop("override_filename_ext", None)
        self._upload_filename = None

        self._override_storage_key_prefix = kwargs.pop("override_storage_key_prefix", None)
        self.retries = self._upload_retries
        super(UploadEvent, self).__init__(metric, variant, iter=iter, **kwargs)

    def _generate_file_name(self, force_pid_suffix: int = None) -> None:
        if force_pid_suffix is None and self._filename is not None:
            return

        self._count = self._get_metric_count(self._metric, self._variant)

        self._filename = self._override_filename
        if not self._filename:
            self._filename = "{}_{}".format(self._metric, self._variant)
            cnt = self._count if self.file_history_size < 1 else (self._count % self.file_history_size)
            self._filename += (
                "_{:05x}{:03d}".format(force_pid_suffix, cnt) if force_pid_suffix else "_{:08d}".format(cnt)
            )

        # make sure we have to '/' in the filename because it might access other folders,
        # and we don't want that to occur
        self._filename = self._replace_slash(self._filename)

        # get upload uri upfront, either predefined image format or local file extension
        # e.g.: image.png -> .png or image.raw.gz -> .raw.gz
        filename_ext = self._override_filename_ext
        if filename_ext is None:
            filename_ext = (
                str(self._format).lower()
                if self._image_data is not None
                else "." + ".".join(pathlib2.Path(self._local_image_path).parts[-1].split(".")[1:])
            )
        # always add file extension to the uploaded target file
        if filename_ext and filename_ext[0] != ".":
            filename_ext = "." + filename_ext
        self._upload_filename = pathlib2.Path(self._filename).as_posix()
        if self._filename.rpartition(".")[2] != filename_ext.rpartition(".")[2]:
            self._upload_filename += filename_ext

    @classmethod
    def _get_metric_count(cls, metric: str, variant: str, next: bool = True) -> int:
        """Returns the next count number for the given metric/variant (rotates every few calls)"""
        counters = cls._metric_counters
        key = "%s_%s" % (metric, variant)
        try:
            cls._metric_counters_lock.acquire()
            value = counters.get(key, -1)
            if next:
                value = counters[key] = value + 1
            return value
        finally:
            cls._metric_counters_lock.release()

    # return No event (just the upload)
    def get_api_event(self) -> None:
        return None

    def update(self, url: str = None, key: str = None, **kwargs: Any) -> None:
        super(UploadEvent, self).update(**kwargs)
        if url is not None:
            self._url = url
        if key is not None:
            self._key = key

    def get_file_entry(self) -> Optional[MetricsEventAdapter.FileEntry]:
        self._generate_file_name()

        local_file = None

        # Notice that in case we are running with reporter in subprocess,
        # when we are here, the cls._metric_counters is actually empty,
        # since it was updated on the main process and this function is running from the subprocess.
        #
        # In the future, if we want to support multi processes reporting images with the same title/series,
        # we should move the _count & _filename selection into the subprocess, not the main process.
        # For the time being, this will remain a limitation of the Image reporting mechanism.

        if isinstance(self._image_data, (six.StringIO, six.BytesIO)):
            output = self._image_data
        elif self._image_data is not None:
            image_data = self._image_data
            if not isinstance(image_data, np.ndarray):
                # try conversion, if it fails we'll leave it to the user.
                image_data = np.ndarray(image_data, dtype=np.uint8)
            image_data = np.atleast_3d(image_data)
            if image_data.dtype != np.uint8:
                if np.issubdtype(image_data.dtype, np.floating) and image_data.max() <= 1.0:
                    image_data = (image_data * 255).astype(np.uint8)
                else:
                    image_data = image_data.astype(np.uint8)
            shape = image_data.shape
            height, width, channel = shape[:3]
            if channel == 1:
                image_data = np.reshape(image_data, (height, width))

            # serialize image
            image = Image.fromarray(image_data)
            output = six.BytesIO()
            image_format = Image.registered_extensions().get(str(self._format).lower(), "JPEG")
            image.save(output, format=image_format, quality=int(self._quality))
            output.seek(0)
        else:
            # noinspection PyBroadException
            try:
                output = pathlib2.Path(self._local_image_path)
                if output.is_file():
                    local_file = output
                else:
                    output = None
            except Exception:
                output = None

            if output is None:
                LoggerRoot.get_base_logger().warning(
                    "Skipping upload, could not find object file '{}'".format(self._local_image_path)
                )
                return None

        return self.FileEntry(
            event=self,
            name=self._upload_filename,
            stream=output,
            url_prop="url",
            key_prop="key",
            upload_uri=self._upload_uri,
            delete_local_file=local_file if self._delete_after_upload else None,
            retries=self.retries,
        )

    def get_target_full_upload_uri(
        self,
        storage_uri: str,
        storage_key_prefix: str = None,
        quote_uri: bool = True,
    ) -> Tuple[str, str]:
        def limit_path_folder_length(folder_path: str) -> str:
            if not folder_path or len(folder_path) <= 250:
                return folder_path
            parts = folder_path.split(".")
            if len(parts) > 1:
                prefix = hashlib.md5(str(".".join(parts[:-1])).encode("utf-8")).hexdigest()
                new_path = "{}.{}".format(prefix, parts[-1])
                if len(new_path) <= 250:
                    return new_path
            return hashlib.md5(str(folder_path).encode("utf-8")).hexdigest()

        self._generate_file_name()
        e_storage_uri = self._upload_uri or storage_uri
        # if we have an entry (with or without a stream), we'll generate the URL and store it in the event
        filename = self._upload_filename
        if self._override_storage_key_prefix or not storage_key_prefix:
            storage_key_prefix = self._override_storage_key_prefix
        key = "/".join(
            x
            for x in (
                storage_key_prefix,
                self._replace_slash(self.metric),
                self._replace_slash(self.variant),
                self._replace_slash(filename),
            )
            if x
        )
        key = "/".join(limit_path_folder_length(x) for x in key.split("/"))
        url = "/".join(x.strip("/") for x in (e_storage_uri, key))
        # make sure we preserve local path root
        if e_storage_uri.startswith("/"):
            url = "/" + url

        if quote_uri:
            url = quote_url(url)

        return key, url


class ImageEvent(UploadEvent):
    def __init__(
        self,
        metric: str,
        variant: str,
        image_data: Union[np.ndarray, six.StringIO, six.BytesIO],
        local_image_path: Optional[str] = None,
        iter: int = 0,
        upload_uri: Optional[str] = None,
        file_history_size: Optional[int] = None,
        delete_after_upload: bool = False,
        **kwargs: Any
    ) -> None:
        super(ImageEvent, self).__init__(
            metric,
            variant,
            image_data=image_data,
            local_image_path=local_image_path,
            iter=iter,
            upload_uri=upload_uri,
            file_history_size=file_history_size,
            delete_after_upload=delete_after_upload,
            **kwargs
        )

    def get_api_event(self) -> "events.MetricsImageEvent":
        return events.MetricsImageEvent(url=self._url, key=self._key, **self._get_base_dict())


class MediaEvent(UploadEvent):
    def __init__(
        self,
        metric: str,
        variant: str,
        stream: Union[io.StringIO, io.BytesIO],
        local_image_path: Optional[str] = None,
        iter: int = 0,
        upload_uri: Optional[str] = None,
        file_history_size: Optional[int] = None,
        delete_after_upload: bool = False,
        **kwargs: Any
    ) -> None:
        super(MediaEvent, self).__init__(
            metric,
            variant,
            image_data=stream,
            local_image_path=local_image_path,
            iter=iter,
            upload_uri=upload_uri,
            file_history_size=file_history_size,
            delete_after_upload=delete_after_upload,
            **kwargs
        )

    def get_api_event(self) -> "events.MetricsImageEvent":
        return events.MetricsImageEvent(url=self._url, key=self._key, **self._get_base_dict())
