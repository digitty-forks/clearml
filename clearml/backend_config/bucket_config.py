import abc
import logging
import warnings
from copy import copy
from operator import itemgetter
from os import getenv
from typing import Tuple, Dict, List, Union, Optional, Any

import furl
import six
from attr import attrib, attrs


def _none_to_empty_string(maybe_string: str) -> str:
    return maybe_string if maybe_string is not None else ""


def _url_stripper(bucket: str) -> str:
    bucket = _none_to_empty_string(bucket)
    bucket = bucket.strip("\"'").rstrip("/")
    return bucket


@attrs
class S3BucketConfig(object):
    bucket = attrib(type=str, converter=_url_stripper, default="")
    subdir = attrib(type=str, converter=_url_stripper, default="")
    host = attrib(type=str, converter=_none_to_empty_string, default="")
    key = attrib(type=str, converter=_none_to_empty_string, default="")
    secret = attrib(type=str, converter=_none_to_empty_string, default="")
    token = attrib(type=str, converter=_none_to_empty_string, default="")
    multipart = attrib(type=bool, default=True)
    acl = attrib(type=str, converter=_none_to_empty_string, default="")
    secure = attrib(type=bool, default=True)
    region = attrib(type=str, converter=_none_to_empty_string, default="")
    verify = attrib(type=bool, default=None)
    use_credentials_chain = attrib(type=bool, default=False)
    extra_args = attrib(type=dict, default=None)
    profile = attrib(type=str, default="")

    def update(
        self,
        key: str = "",
        secret: str = "",
        multipart: bool = True,
        region: str = None,
        use_credentials_chain: bool = False,
        token: str = "",
        extra_args: dict = None,
        secure: bool = True,
        profile: str = "",
    ) -> None:
        self.key = key
        self.secret = secret
        self.token = token
        self.multipart = multipart
        self.region = region
        self.use_credentials_chain = use_credentials_chain
        self.extra_args = extra_args
        self.secure = secure
        self.profile = profile

    def is_valid(self) -> bool:
        return (self.key and self.secret) or self.use_credentials_chain

    def get_bucket_host(self) -> Tuple[str, str]:
        return self.bucket, self.host

    @classmethod
    def from_list(
        cls,
        dict_list: Union[Tuple[Dict], List[Dict]],
        log: Optional[logging.Logger] = None,
    ) -> List["S3BucketConfig"]:
        if not isinstance(dict_list, (tuple, list)) or not all(isinstance(x, dict) for x in dict_list):
            raise ValueError("Expecting a list of configurations dictionaries")
        configs = [cls(**entry) for entry in dict_list]
        valid_configs = [conf for conf in configs if conf.is_valid()]
        if log and len(valid_configs) < len(configs):
            log.warning(
                "Invalid bucket configurations detected for {}".format(
                    ", ".join(
                        "/".join((config.host, config.bucket)) for config in configs if config not in valid_configs
                    )
                )
            )
        return valid_configs


BucketConfig = S3BucketConfig


@six.add_metaclass(abc.ABCMeta)
class BaseBucketConfigurations(object):
    def __init__(self, buckets: Optional[List[Any]] = None, *_: Any, **__: Any) -> None:
        self._buckets = buckets or []
        self._prefixes = None

    def _update_prefixes(self, refresh: bool = True) -> None:
        if self._prefixes and not refresh:
            return
        prefixes = ((config, self._get_prefix_from_bucket_config(config)) for config in self._buckets)
        self._prefixes = sorted(prefixes, key=itemgetter(1), reverse=True)

    @abc.abstractmethod
    def _get_prefix_from_bucket_config(self, config: "GSBucketConfig") -> str:
        pass


class S3BucketConfigurations(BaseBucketConfigurations):
    def __init__(
        self,
        buckets: Optional[List[S3BucketConfig]] = None,
        default_key: str = "",
        default_secret: str = "",
        default_region: str = "",
        default_use_credentials_chain: bool = False,
        default_token: str = "",
        default_extra_args: Optional[dict] = None,
        default_verify: Optional[bool] = None,
        default_profile: str = "",
        default_secure: bool = True,
    ) -> None:
        super(S3BucketConfigurations, self).__init__()
        self._buckets = buckets if buckets else list()
        self._default_key = default_key
        self._default_secret = default_secret
        self._default_token = default_token
        self._default_region = default_region
        self._default_multipart = True
        self._default_use_credentials_chain = default_use_credentials_chain
        self._default_extra_args = default_extra_args
        self._default_verify = default_verify
        self._default_profile = default_profile
        self._default_secure = default_secure

    @classmethod
    def from_config(cls, s3_configuration: dict) -> "S3BucketConfigurations":
        config_list = S3BucketConfig.from_list(s3_configuration.get("credentials", []))

        default_key = s3_configuration.get("key", "") or getenv("AWS_ACCESS_KEY_ID", "")
        default_secret = s3_configuration.get("secret", "") or getenv("AWS_SECRET_ACCESS_KEY", "")
        default_token = s3_configuration.get("token", "") or getenv("AWS_SESSION_TOKEN", "")
        default_region = s3_configuration.get("region", "") or getenv("AWS_DEFAULT_REGION", "")
        default_use_credentials_chain = s3_configuration.get("use_credentials_chain") or False
        default_extra_args = s3_configuration.get("extra_args")
        default_verify = s3_configuration.get("verify", None)
        default_profile = s3_configuration.get("profile", "") or getenv("AWS_PROFILE", "")
        default_secure = s3_configuration.get("secure", True)

        default_key = _none_to_empty_string(default_key).strip()
        default_secret = _none_to_empty_string(default_secret).strip()
        default_token = _none_to_empty_string(default_token).strip()
        default_region = _none_to_empty_string(default_region).strip()
        default_profile = _none_to_empty_string(default_profile).strip()

        return cls(
            config_list,
            default_key,
            default_secret,
            default_region,
            default_use_credentials_chain,
            default_token,
            default_extra_args,
            default_verify,
            default_profile,
            default_secure,
        )

    def add_config(self, bucket_config: S3BucketConfig) -> None:
        self._buckets.insert(0, bucket_config)
        self._prefixes = None

    def remove_config(self, bucket_config: S3BucketConfig) -> None:
        self._buckets.remove(bucket_config)
        self._prefixes = None

    def get_config_by_bucket(self, bucket: str, host: str = None) -> S3BucketConfig:
        try:
            return next(
                bucket_config for bucket_config in self._buckets if (bucket, host) == bucket_config.get_bucket_host()
            )
        except StopIteration:
            pass

        return None

    def update_config_with_defaults(self, bucket_config: S3BucketConfig) -> None:
        bucket_config.update(
            key=self._default_key,
            secret=self._default_secret,
            region=bucket_config.region or self._default_region,
            multipart=bucket_config.multipart or self._default_multipart,
            use_credentials_chain=self._default_use_credentials_chain,
            token=self._default_token,
            extra_args=self._default_extra_args,
            profile=self._default_profile,
            secure=self._default_secure,
        )

    def _get_prefix_from_bucket_config(self, config: S3BucketConfig) -> str:
        scheme = "s3"
        prefix = furl.furl()

        if config.host:
            prefix.set(
                scheme=scheme,
                netloc=config.host.lower(),
                path=config.bucket.lower() if config.bucket else "",
            )
        else:
            prefix.set(scheme=scheme, path=config.bucket.lower())
            bucket = prefix.path.segments[0]
            prefix.path.segments.pop(0)
            prefix.set(netloc=bucket)

        return str(prefix)

    def get_config_by_uri(self, uri: str) -> S3BucketConfig:
        """
        Get the credentials for an AWS S3 bucket from the config
        :param uri: URI of bucket, directory or file
        :return: S3BucketConfig: bucket config
        """

        def find_match(uri: str) -> Optional[S3BucketConfig]:
            self._update_prefixes(refresh=False)
            uri = uri.lower()
            res = (config for config, prefix in self._prefixes if prefix is not None and uri.startswith(prefix))

            try:
                return next(res)
            except StopIteration:
                return None

        match = find_match(uri)

        if match:
            return match

        parsed = furl.furl(uri)

        if parsed.port:
            host = parsed.netloc
            parts = parsed.path.segments
            bucket = parts[0] if parts else None
        else:
            host = None
            bucket = parsed.netloc

        return S3BucketConfig(
            key=self._default_key,
            secret=self._default_secret,
            region=self._default_region,
            multipart=True,
            use_credentials_chain=self._default_use_credentials_chain,
            bucket=bucket,
            host=host,
            token=self._default_token,
            extra_args=self._default_extra_args,
            profile=self._default_profile,
            secure=self._default_secure,
        )


BucketConfigurations = S3BucketConfigurations


@attrs
class GSBucketConfig(object):
    bucket = attrib(type=str)
    subdir = attrib(type=str, converter=_url_stripper, default="")
    project = attrib(type=str, default=None)
    credentials_json = attrib(type=str, default=None)
    pool_connections = attrib(type=int, default=None)
    pool_maxsize = attrib(type=int, default=None)

    def update(self, **kwargs: Any) -> None:
        for item in kwargs:
            if not hasattr(self, item):
                warnings.warn("Unexpected argument {} for update. Ignored".format(item))
            else:
                setattr(self, item, kwargs[item])

    def is_valid(self) -> bool:
        return self.bucket


class GSBucketConfigurations(BaseBucketConfigurations):
    def __init__(
        self,
        buckets: Optional[List[GSBucketConfig]] = None,
        default_project: Optional[str] = None,
        default_credentials: Optional[str] = None,
        default_pool_connections: Optional[int] = None,
        default_pool_maxsize: Optional[int] = None,
    ) -> None:
        super(GSBucketConfigurations, self).__init__(buckets)
        self._default_project = default_project
        self._default_credentials = default_credentials
        self._default_pool_connections = default_pool_connections
        self._default_pool_maxsize = default_pool_maxsize

        self._update_prefixes()

    @classmethod
    def from_config(cls, gs_configuration: dict) -> "GSBucketConfigurations":
        default_credentials = getenv("GOOGLE_APPLICATION_CREDENTIALS") or {}

        if not gs_configuration:
            return cls(default_credentials=default_credentials)

        config_list = gs_configuration.get("credentials", [])
        buckets_configs = [GSBucketConfig(**entry) for entry in config_list]

        default_project = gs_configuration.get("project", "default") or {}
        default_credentials = gs_configuration.get("credentials_json", None) or default_credentials
        default_pool_connections = gs_configuration.get("pool_connections", None)
        default_pool_maxsize = gs_configuration.get("pool_maxsize", None)

        return cls(
            buckets_configs,
            default_project,
            default_credentials,
            default_pool_connections,
            default_pool_maxsize,
        )

    def add_config(self, bucket_config: S3BucketConfig) -> None:
        self._buckets.insert(0, bucket_config)
        self._update_prefixes()

    def remove_config(self, bucket_config: S3BucketConfig) -> None:
        self._buckets.remove(bucket_config)
        self._update_prefixes()

    def update_config_with_defaults(self, bucket_config: GSBucketConfig) -> None:
        bucket_config.update(
            project=bucket_config.project or self._default_project,
            credentials_json=bucket_config.credentials_json or self._default_credentials,
            pool_connections=bucket_config.pool_connections or self._default_pool_connections,
            pool_maxsize=bucket_config.pool_maxsize or self._default_pool_maxsize,
        )

    def get_config_by_uri(self, uri: str, create_if_not_found: bool = True) -> GSBucketConfig:
        """
        Get the credentials for a Google Storage bucket from the config
        :param uri: URI of bucket, directory or file
        :param create_if_not_found: If True and the config is not found in the current configurations, create a new one.
            Else, don't create a new one and return None
        :return: GSBucketConfig: bucket config
        """

        res = (config for config, prefix in self._prefixes if prefix is not None and uri.lower().startswith(prefix))

        try:
            return next(res)
        except StopIteration:
            if not create_if_not_found:
                return None

        parsed = furl.furl(uri)

        return GSBucketConfig(
            bucket=parsed.netloc,
            subdir=str(parsed.path),
            project=self._default_project,
            credentials_json=self._default_credentials,
            pool_connections=self._default_pool_connections,
            pool_maxsize=self._default_pool_maxsize,
        )

    def _get_prefix_from_bucket_config(self, config: GSBucketConfig) -> str:
        prefix = furl.furl(scheme="gs", netloc=config.bucket, path=config.subdir)
        return str(prefix)


@attrs
class AzureContainerConfig(object):
    account_name = attrib(type=str)
    account_key = attrib(type=str)
    container_name = attrib(type=str, default=None)

    def update(self, **kwargs: Any) -> None:
        for item in kwargs:
            if not hasattr(self, item):
                warnings.warn("Unexpected argument {} for update. Ignored".format(item))
            else:
                setattr(self, item, kwargs[item])

    def is_valid(self) -> bool:
        return self.account_name and self.container_name


class AzureContainerConfigurations(object):
    def __init__(
        self,
        container_configs: List[AzureContainerConfig] = None,
        default_account: str = None,
        default_key: str = None,
    ) -> None:
        super(AzureContainerConfigurations, self).__init__()
        self._container_configs = container_configs or []
        self._default_account = default_account
        self._default_key = default_key

    @classmethod
    def from_config(cls, configuration: dict) -> "AzureContainerConfigurations":
        default_account = getenv("AZURE_STORAGE_ACCOUNT")
        default_key = getenv("AZURE_STORAGE_KEY")

        default_container_configs = []
        if default_account and default_key:
            default_container_configs.append(
                AzureContainerConfig(account_name=default_account, account_key=default_key)
            )

        if configuration is None:
            return cls(
                default_container_configs,
                default_account=default_account,
                default_key=default_key,
            )

        containers = configuration.get("containers", list())
        container_configs = [AzureContainerConfig(**entry) for entry in containers] + default_container_configs

        return cls(container_configs, default_account=default_account, default_key=default_key)

    def get_config_by_uri(self, uri: str) -> AzureContainerConfig:
        """
        Get the credentials for an Azure Blob Storage container from the config
        :param uri: URI of container or blob
        :return: AzureContainerConfig: container config
        """
        f = furl.furl(uri)
        account_name = f.host.partition(".")[0]

        if not f.path.segments:
            raise ValueError(
                "URI {} is missing a container name (expected "
                "[https/azure]://<account-name>.../<container-name>)".format(uri)
            )

        container = f.path.segments[0]

        config = copy(self.get_config(account_name, container))

        if config and not config.container_name:
            config.container_name = container

        return config

    def get_config(self, account_name: str, container: str) -> AzureContainerConfig:
        return next(
            (
                config
                for config in self._container_configs
                if config.account_name == account_name
                and (not config.container_name or config.container_name == container)
            ),
            None,
        )

    def update_config_with_defaults(self, bucket_config: AzureContainerConfig) -> None:
        bucket_config.update(
            account_name=bucket_config.account_name or self._default_account,
            account_key=bucket_config.account_key or self._default_key,
        )

    def add_config(self, bucket_config: AzureContainerConfig) -> None:
        self._container_configs.append(bucket_config)

    def remove_config(self, bucket_config: AzureContainerConfig) -> None:
        self._container_configs.remove(bucket_config)
