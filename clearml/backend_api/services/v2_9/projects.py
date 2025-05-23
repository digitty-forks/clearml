"""
projects service

Provides support for defining Projects containing Tasks, Models and Dataset Versions.
"""
from typing import List, Optional, Any
from datetime import datetime
import six
from dateutil.parser import parse as parse_datetime
from ....backend_api.session import (
    NonStrictDataModel,
    Request,
    Response,
    schema_property,
)


class MultiFieldPatternData(NonStrictDataModel):
    """
    :param pattern: Pattern string (regex)
    :type pattern: str
    :param fields: List of field names
    :type fields: Sequence[str]
    """

    _schema = {
        "properties": {
            "fields": {
                "description": "List of field names",
                "items": {"type": "string"},
                "type": ["array", "null"],
            },
            "pattern": {
                "description": "Pattern string (regex)",
                "type": ["string", "null"],
            },
        },
        "type": "object",
    }

    def __init__(self, pattern: Optional[str] = None, fields: Optional[List[str]] = None, **kwargs: Any) -> None:
        super(MultiFieldPatternData, self).__init__(**kwargs)
        self.pattern = pattern
        self.fields = fields

    @schema_property("pattern")
    def pattern(self) -> Optional[str]:
        return self._property_pattern

    @pattern.setter
    def pattern(self, value: Optional[str]) -> None:
        if value is None:
            self._property_pattern = None
            return
        self.assert_isinstance(value, "pattern", six.string_types)
        self._property_pattern = value

    @schema_property("fields")
    def fields(self) -> Optional[List[str]]:
        return self._property_fields

    @fields.setter
    def fields(self, value: Optional[List[str]]) -> None:
        if value is None:
            self._property_fields = None
            return
        self.assert_isinstance(value, "fields", (list, tuple))
        self.assert_isinstance(value, "fields", six.string_types, is_array=True)
        self._property_fields = value


class Project(NonStrictDataModel):
    """
    :param id: Project id
    :type id: str
    :param name: Project name
    :type name: str
    :param description: Project description
    :type description: str
    :param user: Associated user id
    :type user: str
    :param company: Company id
    :type company: str
    :param created: Creation time
    :type created: datetime.datetime
    :param tags: User-defined tags
    :type tags: Sequence[str]
    :param system_tags: System tags. This field is reserved for system use, please
        don't use it.
    :type system_tags: Sequence[str]
    :param default_output_destination: The default output destination URL for new
        tasks under this project
    :type default_output_destination: str
    :param last_update: Last project update time. Reflects the last time the
        project metadata was changed or a task in this project has changed status
    :type last_update: datetime.datetime
    """

    _schema = {
        "properties": {
            "company": {"description": "Company id", "type": ["string", "null"]},
            "created": {
                "description": "Creation time",
                "format": "date-time",
                "type": ["string", "null"],
            },
            "default_output_destination": {
                "description": "The default output destination URL for new tasks under this project",
                "type": ["string", "null"],
            },
            "description": {
                "description": "Project description",
                "type": ["string", "null"],
            },
            "id": {"description": "Project id", "type": ["string", "null"]},
            "last_update": {
                "description": "Last project update time. Reflects the last time the project metadata was changed or a task in this project has changed status",
                "format": "date-time",
                "type": ["string", "null"],
            },
            "name": {"description": "Project name", "type": ["string", "null"]},
            "system_tags": {
                "description": "System tags. This field is reserved for system use, please don't use it.",
                "items": {"type": "string"},
                "type": ["array", "null"],
            },
            "tags": {
                "description": "User-defined tags",
                "items": {"type": "string"},
                "type": ["array", "null"],
            },
            "user": {"description": "Associated user id", "type": ["string", "null"]},
        },
        "type": "object",
    }

    def __init__(
        self,
        id: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        user: Optional[str] = None,
        company: Optional[str] = None,
        created: Optional[str] = None,
        tags: Optional[List[str]] = None,
        system_tags: Optional[List[str]] = None,
        default_output_destination: Optional[str] = None,
        last_update: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        super(Project, self).__init__(**kwargs)
        self.id = id
        self.name = name
        self.description = description
        self.user = user
        self.company = company
        self.created = created
        self.tags = tags
        self.system_tags = system_tags
        self.default_output_destination = default_output_destination
        self.last_update = last_update

    @schema_property("id")
    def id(self) -> Optional[str]:
        return self._property_id

    @id.setter
    def id(self, value: Optional[str]) -> None:
        if value is None:
            self._property_id = None
            return
        self.assert_isinstance(value, "id", six.string_types)
        self._property_id = value

    @schema_property("name")
    def name(self) -> Optional[str]:
        return self._property_name

    @name.setter
    def name(self, value: Optional[str]) -> None:
        if value is None:
            self._property_name = None
            return
        self.assert_isinstance(value, "name", six.string_types)
        self._property_name = value

    @schema_property("description")
    def description(self) -> Optional[str]:
        return self._property_description

    @description.setter
    def description(self, value: Optional[str]) -> None:
        if value is None:
            self._property_description = None
            return
        self.assert_isinstance(value, "description", six.string_types)
        self._property_description = value

    @schema_property("user")
    def user(self) -> Optional[str]:
        return self._property_user

    @user.setter
    def user(self, value: Optional[str]) -> None:
        if value is None:
            self._property_user = None
            return
        self.assert_isinstance(value, "user", six.string_types)
        self._property_user = value

    @schema_property("company")
    def company(self) -> Optional[str]:
        return self._property_company

    @company.setter
    def company(self, value: Optional[str]) -> None:
        if value is None:
            self._property_company = None
            return
        self.assert_isinstance(value, "company", six.string_types)
        self._property_company = value

    @schema_property("created")
    def created(self) -> Optional[str]:
        return self._property_created

    @created.setter
    def created(self, value: Optional[str]) -> None:
        if value is None:
            self._property_created = None
            return
        self.assert_isinstance(value, "created", six.string_types + (datetime,))
        if not isinstance(value, datetime):
            value = parse_datetime(value)
        self._property_created = value

    @schema_property("tags")
    def tags(self) -> Optional[List[str]]:
        return self._property_tags

    @tags.setter
    def tags(self, value: Optional[List[str]]) -> None:
        if value is None:
            self._property_tags = None
            return
        self.assert_isinstance(value, "tags", (list, tuple))
        self.assert_isinstance(value, "tags", six.string_types, is_array=True)
        self._property_tags = value

    @schema_property("system_tags")
    def system_tags(self) -> Optional[List[str]]:
        return self._property_system_tags

    @system_tags.setter
    def system_tags(self, value: Optional[List[str]]) -> None:
        if value is None:
            self._property_system_tags = None
            return
        self.assert_isinstance(value, "system_tags", (list, tuple))
        self.assert_isinstance(value, "system_tags", six.string_types, is_array=True)
        self._property_system_tags = value

    @schema_property("default_output_destination")
    def default_output_destination(self) -> Optional[str]:
        return self._property_default_output_destination

    @default_output_destination.setter
    def default_output_destination(self, value: Optional[str]) -> None:
        if value is None:
            self._property_default_output_destination = None
            return
        self.assert_isinstance(value, "default_output_destination", six.string_types)
        self._property_default_output_destination = value

    @schema_property("last_update")
    def last_update(self) -> Optional[str]:
        return self._property_last_update

    @last_update.setter
    def last_update(self, value: Optional[str]) -> None:
        if value is None:
            self._property_last_update = None
            return
        self.assert_isinstance(value, "last_update", six.string_types + (datetime,))
        if not isinstance(value, datetime):
            value = parse_datetime(value)
        self._property_last_update = value


class StatsStatusCount(NonStrictDataModel):
    """
    :param total_runtime: Total run time of all tasks in project (in seconds)
    :type total_runtime: int
    :param status_count: Status counts
    :type status_count: dict
    """

    _schema = {
        "properties": {
            "status_count": {
                "description": "Status counts",
                "properties": {
                    "closed": {
                        "description": "Number of 'closed' tasks in project",
                        "type": "integer",
                    },
                    "created": {
                        "description": "Number of 'created' tasks in project",
                        "type": "integer",
                    },
                    "failed": {
                        "description": "Number of 'failed' tasks in project",
                        "type": "integer",
                    },
                    "in_progress": {
                        "description": "Number of 'in_progress' tasks in project",
                        "type": "integer",
                    },
                    "published": {
                        "description": "Number of 'published' tasks in project",
                        "type": "integer",
                    },
                    "queued": {
                        "description": "Number of 'queued' tasks in project",
                        "type": "integer",
                    },
                    "stopped": {
                        "description": "Number of 'stopped' tasks in project",
                        "type": "integer",
                    },
                    "unknown": {
                        "description": "Number of 'unknown' tasks in project",
                        "type": "integer",
                    },
                },
                "type": ["object", "null"],
            },
            "total_runtime": {
                "description": "Total run time of all tasks in project (in seconds)",
                "type": ["integer", "null"],
            },
        },
        "type": "object",
    }

    def __init__(self, total_runtime: Optional[int] = None, status_count: Optional[dict] = None, **kwargs: Any) -> None:
        super(StatsStatusCount, self).__init__(**kwargs)
        self.total_runtime = total_runtime
        self.status_count = status_count

    @schema_property("total_runtime")
    def total_runtime(self) -> Optional[int]:
        return self._property_total_runtime

    @total_runtime.setter
    def total_runtime(self, value: Optional[int]) -> None:
        if value is None:
            self._property_total_runtime = None
            return
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        self.assert_isinstance(value, "total_runtime", six.integer_types)
        self._property_total_runtime = value

    @schema_property("status_count")
    def status_count(self) -> Optional[dict]:
        return self._property_status_count

    @status_count.setter
    def status_count(self, value: Optional[dict]) -> None:
        if value is None:
            self._property_status_count = None
            return
        self.assert_isinstance(value, "status_count", (dict,))
        self._property_status_count = value


class Stats(NonStrictDataModel):
    """
    :param active: Stats for active tasks
    :type active: StatsStatusCount
    :param archived: Stats for archived tasks
    :type archived: StatsStatusCount
    """

    _schema = {
        "properties": {
            "active": {
                "description": "Stats for active tasks",
                "oneOf": [
                    {"$ref": "#/definitions/stats_status_count"},
                    {"type": "null"},
                ],
            },
            "archived": {
                "description": "Stats for archived tasks",
                "oneOf": [
                    {"$ref": "#/definitions/stats_status_count"},
                    {"type": "null"},
                ],
            },
        },
        "type": "object",
    }

    def __init__(self, active: Any = None, archived: Any = None, **kwargs: Any) -> None:
        super(Stats, self).__init__(**kwargs)
        self.active = active
        self.archived = archived

    @schema_property("active")
    def active(self) -> Any:
        return self._property_active

    @active.setter
    def active(self, value: Any) -> None:
        if value is None:
            self._property_active = None
            return
        if isinstance(value, dict):
            value = StatsStatusCount.from_dict(value)
        else:
            self.assert_isinstance(value, "active", StatsStatusCount)
        self._property_active = value

    @schema_property("archived")
    def archived(self) -> Any:
        return self._property_archived

    @archived.setter
    def archived(self, value: Any) -> None:
        if value is None:
            self._property_archived = None
            return
        if isinstance(value, dict):
            value = StatsStatusCount.from_dict(value)
        else:
            self.assert_isinstance(value, "archived", StatsStatusCount)
        self._property_archived = value


class ProjectsGetAllResponseSingle(NonStrictDataModel):
    """
    :param id: Project id
    :type id: str
    :param name: Project name
    :type name: str
    :param description: Project description
    :type description: str
    :param user: Associated user id
    :type user: str
    :param company: Company id
    :type company: str
    :param created: Creation time
    :type created: datetime.datetime
    :param tags: User-defined tags
    :type tags: Sequence[str]
    :param system_tags: System tags. This field is reserved for system use, please
        don't use it.
    :type system_tags: Sequence[str]
    :param default_output_destination: The default output destination URL for new
        tasks under this project
    :type default_output_destination: str
    :param stats: Additional project stats
    :type stats: Stats
    """

    _schema = {
        "properties": {
            "company": {"description": "Company id", "type": ["string", "null"]},
            "created": {
                "description": "Creation time",
                "format": "date-time",
                "type": ["string", "null"],
            },
            "default_output_destination": {
                "description": "The default output destination URL for new tasks under this project",
                "type": ["string", "null"],
            },
            "description": {
                "description": "Project description",
                "type": ["string", "null"],
            },
            "id": {"description": "Project id", "type": ["string", "null"]},
            "name": {"description": "Project name", "type": ["string", "null"]},
            "stats": {
                "description": "Additional project stats",
                "oneOf": [{"$ref": "#/definitions/stats"}, {"type": "null"}],
            },
            "system_tags": {
                "description": "System tags. This field is reserved for system use, please don't use it.",
                "items": {"type": "string"},
                "type": ["array", "null"],
            },
            "tags": {
                "description": "User-defined tags",
                "items": {"type": "string"},
                "type": ["array", "null"],
            },
            "user": {"description": "Associated user id", "type": ["string", "null"]},
        },
        "type": "object",
    }

    def __init__(
        self,
        id: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        user: Optional[str] = None,
        company: Optional[str] = None,
        created: Optional[str] = None,
        tags: Optional[List[str]] = None,
        system_tags: Optional[List[str]] = None,
        default_output_destination: Optional[str] = None,
        stats: Any = None,
        **kwargs: Any
    ) -> None:
        super(ProjectsGetAllResponseSingle, self).__init__(**kwargs)
        self.id = id
        self.name = name
        self.description = description
        self.user = user
        self.company = company
        self.created = created
        self.tags = tags
        self.system_tags = system_tags
        self.default_output_destination = default_output_destination
        self.stats = stats

    @schema_property("id")
    def id(self) -> Optional[str]:
        return self._property_id

    @id.setter
    def id(self, value: Optional[str]) -> None:
        if value is None:
            self._property_id = None
            return
        self.assert_isinstance(value, "id", six.string_types)
        self._property_id = value

    @schema_property("name")
    def name(self) -> Optional[str]:
        return self._property_name

    @name.setter
    def name(self, value: Optional[str]) -> None:
        if value is None:
            self._property_name = None
            return
        self.assert_isinstance(value, "name", six.string_types)
        self._property_name = value

    @schema_property("description")
    def description(self) -> Optional[str]:
        return self._property_description

    @description.setter
    def description(self, value: Optional[str]) -> None:
        if value is None:
            self._property_description = None
            return
        self.assert_isinstance(value, "description", six.string_types)
        self._property_description = value

    @schema_property("user")
    def user(self) -> Optional[str]:
        return self._property_user

    @user.setter
    def user(self, value: Optional[str]) -> None:
        if value is None:
            self._property_user = None
            return
        self.assert_isinstance(value, "user", six.string_types)
        self._property_user = value

    @schema_property("company")
    def company(self) -> Optional[str]:
        return self._property_company

    @company.setter
    def company(self, value: Optional[str]) -> None:
        if value is None:
            self._property_company = None
            return
        self.assert_isinstance(value, "company", six.string_types)
        self._property_company = value

    @schema_property("created")
    def created(self) -> Optional[str]:
        return self._property_created

    @created.setter
    def created(self, value: Optional[str]) -> None:
        if value is None:
            self._property_created = None
            return
        self.assert_isinstance(value, "created", six.string_types + (datetime,))
        if not isinstance(value, datetime):
            value = parse_datetime(value)
        self._property_created = value

    @schema_property("tags")
    def tags(self) -> Optional[List[str]]:
        return self._property_tags

    @tags.setter
    def tags(self, value: Optional[List[str]]) -> None:
        if value is None:
            self._property_tags = None
            return
        self.assert_isinstance(value, "tags", (list, tuple))
        self.assert_isinstance(value, "tags", six.string_types, is_array=True)
        self._property_tags = value

    @schema_property("system_tags")
    def system_tags(self) -> Optional[List[str]]:
        return self._property_system_tags

    @system_tags.setter
    def system_tags(self, value: Optional[List[str]]) -> None:
        if value is None:
            self._property_system_tags = None
            return
        self.assert_isinstance(value, "system_tags", (list, tuple))
        self.assert_isinstance(value, "system_tags", six.string_types, is_array=True)
        self._property_system_tags = value

    @schema_property("default_output_destination")
    def default_output_destination(self) -> Optional[str]:
        return self._property_default_output_destination

    @default_output_destination.setter
    def default_output_destination(self, value: Optional[str]) -> None:
        if value is None:
            self._property_default_output_destination = None
            return
        self.assert_isinstance(value, "default_output_destination", six.string_types)
        self._property_default_output_destination = value

    @schema_property("stats")
    def stats(self) -> Any:
        return self._property_stats

    @stats.setter
    def stats(self, value: Any) -> None:
        if value is None:
            self._property_stats = None
            return
        if isinstance(value, dict):
            value = Stats.from_dict(value)
        else:
            self.assert_isinstance(value, "stats", Stats)
        self._property_stats = value


class MetricVariantResult(NonStrictDataModel):
    """
    :param metric: Metric name
    :type metric: str
    :param metric_hash: Metric name hash. Used instead of the metric name when
        categorizing last metrics events in task objects.
    :type metric_hash: str
    :param variant: Variant name
    :type variant: str
    :param variant_hash: Variant name hash. Used instead of the variant name when
        categorizing last metrics events in task objects.
    :type variant_hash: str
    """

    _schema = {
        "properties": {
            "metric": {"description": "Metric name", "type": ["string", "null"]},
            "metric_hash": {
                "description": "Metric name hash. Used instead of the metric name when categorizing\n                last metrics events in task objects.",
                "type": ["string", "null"],
            },
            "variant": {"description": "Variant name", "type": ["string", "null"]},
            "variant_hash": {
                "description": "Variant name hash. Used instead of the variant name when categorizing\n                last metrics events in task objects.",
                "type": ["string", "null"],
            },
        },
        "type": "object",
    }

    def __init__(
        self,
        metric: Optional[str] = None,
        metric_hash: Optional[str] = None,
        variant: Optional[str] = None,
        variant_hash: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        super(MetricVariantResult, self).__init__(**kwargs)
        self.metric = metric
        self.metric_hash = metric_hash
        self.variant = variant
        self.variant_hash = variant_hash

    @schema_property("metric")
    def metric(self) -> Optional[str]:
        return self._property_metric

    @metric.setter
    def metric(self, value: Optional[str]) -> None:
        if value is None:
            self._property_metric = None
            return
        self.assert_isinstance(value, "metric", six.string_types)
        self._property_metric = value

    @schema_property("metric_hash")
    def metric_hash(self) -> Optional[str]:
        return self._property_metric_hash

    @metric_hash.setter
    def metric_hash(self, value: Optional[str]) -> None:
        if value is None:
            self._property_metric_hash = None
            return
        self.assert_isinstance(value, "metric_hash", six.string_types)
        self._property_metric_hash = value

    @schema_property("variant")
    def variant(self) -> Optional[str]:
        return self._property_variant

    @variant.setter
    def variant(self, value: Optional[str]) -> None:
        if value is None:
            self._property_variant = None
            return
        self.assert_isinstance(value, "variant", six.string_types)
        self._property_variant = value

    @schema_property("variant_hash")
    def variant_hash(self) -> Optional[str]:
        return self._property_variant_hash

    @variant_hash.setter
    def variant_hash(self, value: Optional[str]) -> None:
        if value is None:
            self._property_variant_hash = None
            return
        self.assert_isinstance(value, "variant_hash", six.string_types)
        self._property_variant_hash = value


class CreateRequest(Request):
    """
    Create a new project

    :param name: Project name Unique within the company.
    :type name: str
    :param description: Project description.
    :type description: str
    :param tags: User-defined tags
    :type tags: Sequence[str]
    :param system_tags: System tags. This field is reserved for system use, please
        don't use it.
    :type system_tags: Sequence[str]
    :param default_output_destination: The default output destination URL for new
        tasks under this project
    :type default_output_destination: str
    """

    _service = "projects"
    _action = "create"
    _version = "2.9"
    _schema = {
        "definitions": {},
        "properties": {
            "default_output_destination": {
                "description": "The default output destination URL for new tasks under this project",
                "type": "string",
            },
            "description": {"description": "Project description. ", "type": "string"},
            "name": {
                "description": "Project name Unique within the company.",
                "type": "string",
            },
            "system_tags": {
                "description": "System tags. This field is reserved for system use, please don't use it.",
                "items": {"type": "string"},
                "type": "array",
            },
            "tags": {
                "description": "User-defined tags",
                "items": {"type": "string"},
                "type": "array",
            },
        },
        "required": ["name", "description"],
        "type": "object",
    }

    def __init__(
        self,
        name: str,
        description: str,
        tags: Optional[List[str]] = None,
        system_tags: Optional[List[str]] = None,
        default_output_destination: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        super(CreateRequest, self).__init__(**kwargs)
        self.name = name
        self.description = description
        self.tags = tags
        self.system_tags = system_tags
        self.default_output_destination = default_output_destination

    @schema_property("name")
    def name(self) -> str:
        return self._property_name

    @name.setter
    def name(self, value: str) -> None:
        if value is None:
            self._property_name = None
            return
        self.assert_isinstance(value, "name", six.string_types)
        self._property_name = value

    @schema_property("description")
    def description(self) -> str:
        return self._property_description

    @description.setter
    def description(self, value: str) -> None:
        if value is None:
            self._property_description = None
            return
        self.assert_isinstance(value, "description", six.string_types)
        self._property_description = value

    @schema_property("tags")
    def tags(self) -> Optional[List[str]]:
        return self._property_tags

    @tags.setter
    def tags(self, value: Optional[List[str]]) -> None:
        if value is None:
            self._property_tags = None
            return
        self.assert_isinstance(value, "tags", (list, tuple))
        self.assert_isinstance(value, "tags", six.string_types, is_array=True)
        self._property_tags = value

    @schema_property("system_tags")
    def system_tags(self) -> Optional[List[str]]:
        return self._property_system_tags

    @system_tags.setter
    def system_tags(self, value: Optional[List[str]]) -> None:
        if value is None:
            self._property_system_tags = None
            return
        self.assert_isinstance(value, "system_tags", (list, tuple))
        self.assert_isinstance(value, "system_tags", six.string_types, is_array=True)
        self._property_system_tags = value

    @schema_property("default_output_destination")
    def default_output_destination(self) -> Optional[str]:
        return self._property_default_output_destination

    @default_output_destination.setter
    def default_output_destination(self, value: Optional[str]) -> None:
        if value is None:
            self._property_default_output_destination = None
            return
        self.assert_isinstance(value, "default_output_destination", six.string_types)
        self._property_default_output_destination = value


class CreateResponse(Response):
    """
    Response of projects.create endpoint.

    :param id: Project id
    :type id: str
    """

    _service = "projects"
    _action = "create"
    _version = "2.9"
    _schema = {
        "definitions": {},
        "properties": {"id": {"description": "Project id", "type": ["string", "null"]}},
        "type": "object",
    }

    def __init__(self, id: Optional[str] = None, **kwargs: Any) -> None:
        super(CreateResponse, self).__init__(**kwargs)
        self.id = id

    @schema_property("id")
    def id(self) -> Optional[str]:
        return self._property_id

    @id.setter
    def id(self, value: Optional[str]) -> None:
        if value is None:
            self._property_id = None
            return
        self.assert_isinstance(value, "id", six.string_types)
        self._property_id = value


class DeleteRequest(Request):
    """
    Deletes a project

    :param project: Project id
    :type project: str
    :param force: If not true, fails if project has tasks. If true, and project has
        tasks, they will be unassigned
    :type force: bool
    """

    _service = "projects"
    _action = "delete"
    _version = "2.9"
    _schema = {
        "definitions": {},
        "properties": {
            "force": {
                "default": False,
                "description": "If not true, fails if project has tasks.\n                    If true, and project has tasks, they will be unassigned",
                "type": "boolean",
            },
            "project": {"description": "Project id", "type": "string"},
        },
        "required": ["project"],
        "type": "object",
    }

    def __init__(self, project: str, force: Optional[bool] = False, **kwargs: Any) -> None:
        super(DeleteRequest, self).__init__(**kwargs)
        self.project = project
        self.force = force

    @schema_property("project")
    def project(self) -> str:
        return self._property_project

    @project.setter
    def project(self, value: str) -> None:
        if value is None:
            self._property_project = None
            return
        self.assert_isinstance(value, "project", six.string_types)
        self._property_project = value

    @schema_property("force")
    def force(self) -> Optional[bool]:
        return self._property_force

    @force.setter
    def force(self, value: Optional[bool]) -> None:
        if value is None:
            self._property_force = None
            return
        self.assert_isinstance(value, "force", (bool,))
        self._property_force = value


class DeleteResponse(Response):
    """
    Response of projects.delete endpoint.

    :param deleted: Number of projects deleted (0 or 1)
    :type deleted: int
    :param disassociated_tasks: Number of tasks disassociated from the deleted
        project
    :type disassociated_tasks: int
    """

    _service = "projects"
    _action = "delete"
    _version = "2.9"
    _schema = {
        "definitions": {},
        "properties": {
            "deleted": {
                "description": "Number of projects deleted (0 or 1)",
                "type": ["integer", "null"],
            },
            "disassociated_tasks": {
                "description": "Number of tasks disassociated from the deleted project",
                "type": ["integer", "null"],
            },
        },
        "type": "object",
    }

    def __init__(self, deleted: Optional[int] = None, disassociated_tasks: Optional[int] = None, **kwargs: Any) -> None:
        super(DeleteResponse, self).__init__(**kwargs)
        self.deleted = deleted
        self.disassociated_tasks = disassociated_tasks

    @schema_property("deleted")
    def deleted(self) -> Optional[int]:
        return self._property_deleted

    @deleted.setter
    def deleted(self, value: Optional[int]) -> None:
        if value is None:
            self._property_deleted = None
            return
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        self.assert_isinstance(value, "deleted", six.integer_types)
        self._property_deleted = value

    @schema_property("disassociated_tasks")
    def disassociated_tasks(self) -> Optional[int]:
        return self._property_disassociated_tasks

    @disassociated_tasks.setter
    def disassociated_tasks(self, value: Optional[int]) -> None:
        if value is None:
            self._property_disassociated_tasks = None
            return
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        self.assert_isinstance(value, "disassociated_tasks", six.integer_types)
        self._property_disassociated_tasks = value


class GetAllRequest(Request):
    """
    Get all the company's projects and all public projects

    :param id: List of IDs to filter by
    :type id: Sequence[str]
    :param name: Get only projects whose name matches this pattern (python regular
        expression syntax)
    :type name: str
    :param description: Get only projects whose description matches this pattern
        (python regular expression syntax)
    :type description: str
    :param tags: User-defined tags list used to filter results. Prepend '-' to tag
        name to indicate exclusion
    :type tags: Sequence[str]
    :param system_tags: System tags list used to filter results. Prepend '-' to
        system tag name to indicate exclusion
    :type system_tags: Sequence[str]
    :param order_by: List of field names to order by. When search_text is used,
        '@text_score' can be used as a field representing the text score of returned
        documents. Use '-' prefix to specify descending order. Optional, recommended
        when using page
    :type order_by: Sequence[str]
    :param page: Page number, returns a specific page out of the resulting list of
        dataviews
    :type page: int
    :param page_size: Page size, specifies the number of results returned in each
        page (last page may contain fewer results)
    :type page_size: int
    :param search_text: Free text search query
    :type search_text: str
    :param only_fields: List of document's field names (nesting is supported using
        '.', e.g. execution.model_labels). If provided, this list defines the query's
        projection (only these fields will be returned for each result entry)
    :type only_fields: Sequence[str]
    :param _all_: Multi-field pattern condition (all fields match pattern)
    :type _all_: MultiFieldPatternData
    :param _any_: Multi-field pattern condition (any field matches pattern)
    :type _any_: MultiFieldPatternData
    """

    _service = "projects"
    _action = "get_all"
    _version = "2.9"
    _schema = {
        "definitions": {
            "multi_field_pattern_data": {
                "properties": {
                    "fields": {
                        "description": "List of field names",
                        "items": {"type": "string"},
                        "type": ["array", "null"],
                    },
                    "pattern": {
                        "description": "Pattern string (regex)",
                        "type": ["string", "null"],
                    },
                },
                "type": "object",
            }
        },
        "properties": {
            "_all_": {
                "description": "Multi-field pattern condition (all fields match pattern)",
                "oneOf": [
                    {"$ref": "#/definitions/multi_field_pattern_data"},
                    {"type": "null"},
                ],
            },
            "_any_": {
                "description": "Multi-field pattern condition (any field matches pattern)",
                "oneOf": [
                    {"$ref": "#/definitions/multi_field_pattern_data"},
                    {"type": "null"},
                ],
            },
            "description": {
                "description": "Get only projects whose description matches this pattern (python regular expression syntax)",
                "type": ["string", "null"],
            },
            "id": {
                "description": "List of IDs to filter by",
                "items": {"type": "string"},
                "type": ["array", "null"],
            },
            "name": {
                "description": "Get only projects whose name matches this pattern (python regular expression syntax)",
                "type": ["string", "null"],
            },
            "only_fields": {
                "description": "List of document's field names (nesting is supported using '.', e.g. execution.model_labels). If provided, this list defines the query's projection (only these fields will be returned for each result entry)",
                "items": {"type": "string"},
                "type": ["array", "null"],
            },
            "order_by": {
                "description": "List of field names to order by. When search_text is used, '@text_score' can be used as a field representing the text score of returned documents. Use '-' prefix to specify descending order. Optional, recommended when using page",
                "items": {"type": "string"},
                "type": ["array", "null"],
            },
            "page": {
                "description": "Page number, returns a specific page out of the resulting list of dataviews",
                "minimum": 0,
                "type": ["integer", "null"],
            },
            "page_size": {
                "description": "Page size, specifies the number of results returned in each page (last page may contain fewer results)",
                "minimum": 1,
                "type": ["integer", "null"],
            },
            "search_text": {
                "description": "Free text search query",
                "type": ["string", "null"],
            },
            "system_tags": {
                "description": "System tags list used to filter results. Prepend '-' to system tag name to indicate exclusion",
                "items": {"type": "string"},
                "type": ["array", "null"],
            },
            "tags": {
                "description": "User-defined tags list used to filter results. Prepend '-' to tag name to indicate exclusion",
                "items": {"type": "string"},
                "type": ["array", "null"],
            },
        },
        "type": "object",
    }

    def __init__(
        self,
        id: Optional[List[str]] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        system_tags: Optional[List[str]] = None,
        order_by: Optional[List[str]] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        search_text: Optional[str] = None,
        only_fields: Optional[List[str]] = None,
        _all_: Any = None,
        _any_: Any = None,
        **kwargs: Any
    ) -> None:
        super(GetAllRequest, self).__init__(**kwargs)
        self.id = id
        self.name = name
        self.description = description
        self.tags = tags
        self.system_tags = system_tags
        self.order_by = order_by
        self.page = page
        self.page_size = page_size
        self.search_text = search_text
        self.only_fields = only_fields
        self._all_ = _all_
        self._any_ = _any_

    @schema_property("id")
    def id(self) -> Optional[List[str]]:
        return self._property_id

    @id.setter
    def id(self, value: Optional[List[str]]) -> None:
        if value is None:
            self._property_id = None
            return
        self.assert_isinstance(value, "id", (list, tuple))
        self.assert_isinstance(value, "id", six.string_types, is_array=True)
        self._property_id = value

    @schema_property("name")
    def name(self) -> Optional[str]:
        return self._property_name

    @name.setter
    def name(self, value: Optional[str]) -> None:
        if value is None:
            self._property_name = None
            return
        self.assert_isinstance(value, "name", six.string_types)
        self._property_name = value

    @schema_property("description")
    def description(self) -> Optional[str]:
        return self._property_description

    @description.setter
    def description(self, value: Optional[str]) -> None:
        if value is None:
            self._property_description = None
            return
        self.assert_isinstance(value, "description", six.string_types)
        self._property_description = value

    @schema_property("tags")
    def tags(self) -> Optional[List[str]]:
        return self._property_tags

    @tags.setter
    def tags(self, value: Optional[List[str]]) -> None:
        if value is None:
            self._property_tags = None
            return
        self.assert_isinstance(value, "tags", (list, tuple))
        self.assert_isinstance(value, "tags", six.string_types, is_array=True)
        self._property_tags = value

    @schema_property("system_tags")
    def system_tags(self) -> Optional[List[str]]:
        return self._property_system_tags

    @system_tags.setter
    def system_tags(self, value: Optional[List[str]]) -> None:
        if value is None:
            self._property_system_tags = None
            return
        self.assert_isinstance(value, "system_tags", (list, tuple))
        self.assert_isinstance(value, "system_tags", six.string_types, is_array=True)
        self._property_system_tags = value

    @schema_property("order_by")
    def order_by(self) -> Optional[List[str]]:
        return self._property_order_by

    @order_by.setter
    def order_by(self, value: Optional[List[str]]) -> None:
        if value is None:
            self._property_order_by = None
            return
        self.assert_isinstance(value, "order_by", (list, tuple))
        self.assert_isinstance(value, "order_by", six.string_types, is_array=True)
        self._property_order_by = value

    @schema_property("page")
    def page(self) -> Optional[int]:
        return self._property_page

    @page.setter
    def page(self, value: Optional[int]) -> None:
        if value is None:
            self._property_page = None
            return
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        self.assert_isinstance(value, "page", six.integer_types)
        self._property_page = value

    @schema_property("page_size")
    def page_size(self) -> Optional[int]:
        return self._property_page_size

    @page_size.setter
    def page_size(self, value: Optional[int]) -> None:
        if value is None:
            self._property_page_size = None
            return
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        self.assert_isinstance(value, "page_size", six.integer_types)
        self._property_page_size = value

    @schema_property("search_text")
    def search_text(self) -> Optional[str]:
        return self._property_search_text

    @search_text.setter
    def search_text(self, value: Optional[str]) -> None:
        if value is None:
            self._property_search_text = None
            return
        self.assert_isinstance(value, "search_text", six.string_types)
        self._property_search_text = value

    @schema_property("only_fields")
    def only_fields(self) -> Optional[List[str]]:
        return self._property_only_fields

    @only_fields.setter
    def only_fields(self, value: Optional[List[str]]) -> None:
        if value is None:
            self._property_only_fields = None
            return
        self.assert_isinstance(value, "only_fields", (list, tuple))
        self.assert_isinstance(value, "only_fields", six.string_types, is_array=True)
        self._property_only_fields = value

    @schema_property("_all_")
    def _all_(self) -> Any:
        return self._property__all_

    @_all_.setter
    def _all_(self, value: Any) -> None:
        if value is None:
            self._property__all_ = None
            return
        if isinstance(value, dict):
            value = MultiFieldPatternData.from_dict(value)
        else:
            self.assert_isinstance(value, "_all_", MultiFieldPatternData)
        self._property__all_ = value

    @schema_property("_any_")
    def _any_(self) -> Any:
        return self._property__any_

    @_any_.setter
    def _any_(self, value: Any) -> None:
        if value is None:
            self._property__any_ = None
            return
        if isinstance(value, dict):
            value = MultiFieldPatternData.from_dict(value)
        else:
            self.assert_isinstance(value, "_any_", MultiFieldPatternData)
        self._property__any_ = value


class GetAllResponse(Response):
    """
    Response of projects.get_all endpoint.

    :param projects: Projects list
    :type projects: Sequence[ProjectsGetAllResponseSingle]
    """

    _service = "projects"
    _action = "get_all"
    _version = "2.9"
    _schema = {
        "definitions": {
            "projects_get_all_response_single": {
                "properties": {
                    "company": {
                        "description": "Company id",
                        "type": ["string", "null"],
                    },
                    "created": {
                        "description": "Creation time",
                        "format": "date-time",
                        "type": ["string", "null"],
                    },
                    "default_output_destination": {
                        "description": "The default output destination URL for new tasks under this project",
                        "type": ["string", "null"],
                    },
                    "description": {
                        "description": "Project description",
                        "type": ["string", "null"],
                    },
                    "id": {"description": "Project id", "type": ["string", "null"]},
                    "name": {"description": "Project name", "type": ["string", "null"]},
                    "stats": {
                        "description": "Additional project stats",
                        "oneOf": [{"$ref": "#/definitions/stats"}, {"type": "null"}],
                    },
                    "system_tags": {
                        "description": "System tags. This field is reserved for system use, please don't use it.",
                        "items": {"type": "string"},
                        "type": ["array", "null"],
                    },
                    "tags": {
                        "description": "User-defined tags",
                        "items": {"type": "string"},
                        "type": ["array", "null"],
                    },
                    "user": {
                        "description": "Associated user id",
                        "type": ["string", "null"],
                    },
                },
                "type": "object",
            },
            "stats": {
                "properties": {
                    "active": {
                        "description": "Stats for active tasks",
                        "oneOf": [
                            {"$ref": "#/definitions/stats_status_count"},
                            {"type": "null"},
                        ],
                    },
                    "archived": {
                        "description": "Stats for archived tasks",
                        "oneOf": [
                            {"$ref": "#/definitions/stats_status_count"},
                            {"type": "null"},
                        ],
                    },
                },
                "type": "object",
            },
            "stats_status_count": {
                "properties": {
                    "status_count": {
                        "description": "Status counts",
                        "properties": {
                            "closed": {
                                "description": "Number of 'closed' tasks in project",
                                "type": "integer",
                            },
                            "created": {
                                "description": "Number of 'created' tasks in project",
                                "type": "integer",
                            },
                            "failed": {
                                "description": "Number of 'failed' tasks in project",
                                "type": "integer",
                            },
                            "in_progress": {
                                "description": "Number of 'in_progress' tasks in project",
                                "type": "integer",
                            },
                            "published": {
                                "description": "Number of 'published' tasks in project",
                                "type": "integer",
                            },
                            "queued": {
                                "description": "Number of 'queued' tasks in project",
                                "type": "integer",
                            },
                            "stopped": {
                                "description": "Number of 'stopped' tasks in project",
                                "type": "integer",
                            },
                            "unknown": {
                                "description": "Number of 'unknown' tasks in project",
                                "type": "integer",
                            },
                        },
                        "type": ["object", "null"],
                    },
                    "total_runtime": {
                        "description": "Total run time of all tasks in project (in seconds)",
                        "type": ["integer", "null"],
                    },
                },
                "type": "object",
            },
        },
        "properties": {
            "projects": {
                "description": "Projects list",
                "items": {"$ref": "#/definitions/projects_get_all_response_single"},
                "type": ["array", "null"],
            }
        },
        "type": "object",
    }

    def __init__(self, projects: Optional[List[Any]] = None, **kwargs: Any) -> None:
        super(GetAllResponse, self).__init__(**kwargs)
        self.projects = projects

    @schema_property("projects")
    def projects(self) -> Optional[List[Any]]:
        return self._property_projects

    @projects.setter
    def projects(self, value: Optional[List[Any]]) -> None:
        if value is None:
            self._property_projects = None
            return
        self.assert_isinstance(value, "projects", (list, tuple))
        if any((isinstance(v, dict) for v in value)):
            value = [ProjectsGetAllResponseSingle.from_dict(v) if isinstance(v, dict) else v for v in value]
        else:
            self.assert_isinstance(value, "projects", ProjectsGetAllResponseSingle, is_array=True)
        self._property_projects = value


class GetByIdRequest(Request):
    """
    :param project: Project id
    :type project: str
    """

    _service = "projects"
    _action = "get_by_id"
    _version = "2.9"
    _schema = {
        "definitions": {},
        "properties": {"project": {"description": "Project id", "type": "string"}},
        "required": ["project"],
        "type": "object",
    }

    def __init__(self, project: str, **kwargs: Any) -> None:
        super(GetByIdRequest, self).__init__(**kwargs)
        self.project = project

    @schema_property("project")
    def project(self) -> str:
        return self._property_project

    @project.setter
    def project(self, value: str) -> None:
        if value is None:
            self._property_project = None
            return
        self.assert_isinstance(value, "project", six.string_types)
        self._property_project = value


class GetByIdResponse(Response):
    """
    Response of projects.get_by_id endpoint.

    :param project: Project info
    :type project: Project
    """

    _service = "projects"
    _action = "get_by_id"
    _version = "2.9"
    _schema = {
        "definitions": {
            "project": {
                "properties": {
                    "company": {
                        "description": "Company id",
                        "type": ["string", "null"],
                    },
                    "created": {
                        "description": "Creation time",
                        "format": "date-time",
                        "type": ["string", "null"],
                    },
                    "default_output_destination": {
                        "description": "The default output destination URL for new tasks under this project",
                        "type": ["string", "null"],
                    },
                    "description": {
                        "description": "Project description",
                        "type": ["string", "null"],
                    },
                    "id": {"description": "Project id", "type": ["string", "null"]},
                    "last_update": {
                        "description": "Last project update time. Reflects the last time the project metadata was changed or a task in this project has changed status",
                        "format": "date-time",
                        "type": ["string", "null"],
                    },
                    "name": {"description": "Project name", "type": ["string", "null"]},
                    "system_tags": {
                        "description": "System tags. This field is reserved for system use, please don't use it.",
                        "items": {"type": "string"},
                        "type": ["array", "null"],
                    },
                    "tags": {
                        "description": "User-defined tags",
                        "items": {"type": "string"},
                        "type": ["array", "null"],
                    },
                    "user": {
                        "description": "Associated user id",
                        "type": ["string", "null"],
                    },
                },
                "type": "object",
            }
        },
        "properties": {
            "project": {
                "description": "Project info",
                "oneOf": [{"$ref": "#/definitions/project"}, {"type": "null"}],
            }
        },
        "type": "object",
    }

    def __init__(self, project: Any = None, **kwargs: Any) -> None:
        super(GetByIdResponse, self).__init__(**kwargs)
        self.project = project

    @schema_property("project")
    def project(self) -> Any:
        return self._property_project

    @project.setter
    def project(self, value: Any) -> None:
        if value is None:
            self._property_project = None
            return
        if isinstance(value, dict):
            value = Project.from_dict(value)
        else:
            self.assert_isinstance(value, "project", Project)
        self._property_project = value


class GetHyperParametersRequest(Request):
    """
    Get a list of all hyper parameter sections and names used in tasks within the given project.

    :param project: Project ID
    :type project: str
    :param page: Page number
    :type page: int
    :param page_size: Page size
    :type page_size: int
    """

    _service = "projects"
    _action = "get_hyper_parameters"
    _version = "2.9"
    _schema = {
        "definitions": {},
        "properties": {
            "page": {
                "default": 0,
                "description": "Page number",
                "type": ["integer", "null"],
            },
            "page_size": {
                "default": 500,
                "description": "Page size",
                "type": ["integer", "null"],
            },
            "project": {"description": "Project ID", "type": ["string", "null"]},
        },
        "type": "object",
    }

    def __init__(
        self, project: Optional[str] = None, page: Optional[int] = 0, page_size: Optional[int] = 500, **kwargs: Any
    ) -> None:
        super(GetHyperParametersRequest, self).__init__(**kwargs)
        self.project = project
        self.page = page
        self.page_size = page_size

    @schema_property("project")
    def project(self) -> Optional[str]:
        return self._property_project

    @project.setter
    def project(self, value: Optional[str]) -> None:
        if value is None:
            self._property_project = None
            return
        self.assert_isinstance(value, "project", six.string_types)
        self._property_project = value

    @schema_property("page")
    def page(self) -> Optional[int]:
        return self._property_page

    @page.setter
    def page(self, value: Optional[int]) -> None:
        if value is None:
            self._property_page = None
            return
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        self.assert_isinstance(value, "page", six.integer_types)
        self._property_page = value

    @schema_property("page_size")
    def page_size(self) -> Optional[int]:
        return self._property_page_size

    @page_size.setter
    def page_size(self, value: Optional[int]) -> None:
        if value is None:
            self._property_page_size = None
            return
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        self.assert_isinstance(value, "page_size", six.integer_types)
        self._property_page_size = value


class GetHyperParametersResponse(Response):
    """
    Response of projects.get_hyper_parameters endpoint.

    :param parameters: A list of parameter sections and names
    :type parameters: Sequence[dict]
    :param remaining: Remaining results
    :type remaining: int
    :param total: Total number of results
    :type total: int
    """

    _service = "projects"
    _action = "get_hyper_parameters"
    _version = "2.9"
    _schema = {
        "definitions": {},
        "properties": {
            "parameters": {
                "description": "A list of parameter sections and names",
                "items": {"type": "object"},
                "type": ["array", "null"],
            },
            "remaining": {
                "description": "Remaining results",
                "type": ["integer", "null"],
            },
            "total": {
                "description": "Total number of results",
                "type": ["integer", "null"],
            },
        },
        "type": "object",
    }

    def __init__(
        self,
        parameters: Optional[List[dict]] = None,
        remaining: Optional[int] = None,
        total: Optional[int] = None,
        **kwargs: Any
    ) -> None:
        super(GetHyperParametersResponse, self).__init__(**kwargs)
        self.parameters = parameters
        self.remaining = remaining
        self.total = total

    @schema_property("parameters")
    def parameters(self) -> Optional[List[dict]]:
        return self._property_parameters

    @parameters.setter
    def parameters(self, value: Optional[List[dict]]) -> None:
        if value is None:
            self._property_parameters = None
            return
        self.assert_isinstance(value, "parameters", (list, tuple))
        self.assert_isinstance(value, "parameters", (dict,), is_array=True)
        self._property_parameters = value

    @schema_property("remaining")
    def remaining(self) -> Optional[int]:
        return self._property_remaining

    @remaining.setter
    def remaining(self, value: Optional[int]) -> None:
        if value is None:
            self._property_remaining = None
            return
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        self.assert_isinstance(value, "remaining", six.integer_types)
        self._property_remaining = value

    @schema_property("total")
    def total(self) -> Optional[int]:
        return self._property_total

    @total.setter
    def total(self, value: Optional[int]) -> None:
        if value is None:
            self._property_total = None
            return
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        self.assert_isinstance(value, "total", six.integer_types)
        self._property_total = value


class GetModelTagsRequest(Request):
    """
    Get user and system tags used for the models under the specified projects

    :param include_system: If set to 'true' then the list of the system tags is
        also returned. The default value is 'false'
    :type include_system: bool
    :param projects: The list of projects under which the tags are searched. If not
        passed or empty then all the projects are searched
    :type projects: Sequence[str]
    :param filter: Filter on entities to collect tags from
    :type filter: dict
    """

    _service = "projects"
    _action = "get_model_tags"
    _version = "2.9"
    _schema = {
        "definitions": {},
        "properties": {
            "filter": {
                "description": "Filter on entities to collect tags from",
                "properties": {
                    "system_tags": {
                        "description": "The list of system tag values to filter by. Use 'null' value to specify empty system tags. Use '__Snot' value to specify that the following value should be excluded",
                        "items": {"type": "string"},
                        "type": "array",
                    },
                    "tags": {
                        "description": "The list of tag values to filter by. Use 'null' value to specify empty tags. Use '__Snot' value to specify that the following value should be excluded",
                        "items": {"type": "string"},
                        "type": "array",
                    },
                },
                "type": ["object", "null"],
            },
            "include_system": {
                "default": False,
                "description": "If set to 'true' then the list of the system tags is also returned. The default value is 'false'",
                "type": ["boolean", "null"],
            },
            "projects": {
                "description": "The list of projects under which the tags are searched. If not passed or empty then all the projects are searched",
                "items": {"type": "string"},
                "type": ["array", "null"],
            },
        },
        "type": "object",
    }

    def __init__(
        self,
        include_system: Optional[bool] = False,
        projects: Optional[List[str]] = None,
        filter: Optional[dict] = None,
        **kwargs: Any
    ) -> None:
        super(GetModelTagsRequest, self).__init__(**kwargs)
        self.include_system = include_system
        self.projects = projects
        self.filter = filter

    @schema_property("include_system")
    def include_system(self) -> Optional[bool]:
        return self._property_include_system

    @include_system.setter
    def include_system(self, value: Optional[bool]) -> None:
        if value is None:
            self._property_include_system = None
            return
        self.assert_isinstance(value, "include_system", (bool,))
        self._property_include_system = value

    @schema_property("projects")
    def projects(self) -> Optional[List[str]]:
        return self._property_projects

    @projects.setter
    def projects(self, value: Optional[List[str]]) -> None:
        if value is None:
            self._property_projects = None
            return
        self.assert_isinstance(value, "projects", (list, tuple))
        self.assert_isinstance(value, "projects", six.string_types, is_array=True)
        self._property_projects = value

    @schema_property("filter")
    def filter(self) -> Optional[dict]:
        return self._property_filter

    @filter.setter
    def filter(self, value: Optional[dict]) -> None:
        if value is None:
            self._property_filter = None
            return
        self.assert_isinstance(value, "filter", (dict,))
        self._property_filter = value


class GetModelTagsResponse(Response):
    """
    Response of projects.get_model_tags endpoint.

    :param tags: The list of unique tag values
    :type tags: Sequence[str]
    :param system_tags: The list of unique system tag values. Returned only if
        'include_system' is set to 'true' in the request
    :type system_tags: Sequence[str]
    """

    _service = "projects"
    _action = "get_model_tags"
    _version = "2.9"
    _schema = {
        "definitions": {},
        "properties": {
            "system_tags": {
                "description": "The list of unique system tag values. Returned only if 'include_system' is set to 'true' in the request",
                "items": {"type": "string"},
                "type": ["array", "null"],
            },
            "tags": {
                "description": "The list of unique tag values",
                "items": {"type": "string"},
                "type": ["array", "null"],
            },
        },
        "type": "object",
    }

    def __init__(
        self, tags: Optional[List[str]] = None, system_tags: Optional[List[str]] = None, **kwargs: Any
    ) -> None:
        super(GetModelTagsResponse, self).__init__(**kwargs)
        self.tags = tags
        self.system_tags = system_tags

    @schema_property("tags")
    def tags(self) -> Optional[List[str]]:
        return self._property_tags

    @tags.setter
    def tags(self, value: Optional[List[str]]) -> None:
        if value is None:
            self._property_tags = None
            return
        self.assert_isinstance(value, "tags", (list, tuple))
        self.assert_isinstance(value, "tags", six.string_types, is_array=True)
        self._property_tags = value

    @schema_property("system_tags")
    def system_tags(self) -> Optional[List[str]]:
        return self._property_system_tags

    @system_tags.setter
    def system_tags(self, value: Optional[List[str]]) -> None:
        if value is None:
            self._property_system_tags = None
            return
        self.assert_isinstance(value, "system_tags", (list, tuple))
        self.assert_isinstance(value, "system_tags", six.string_types, is_array=True)
        self._property_system_tags = value


class GetTaskTagsRequest(Request):
    """
    Get user and system tags used for the tasks under the specified projects

    :param include_system: If set to 'true' then the list of the system tags is
        also returned. The default value is 'false'
    :type include_system: bool
    :param projects: The list of projects under which the tags are searched. If not
        passed or empty then all the projects are searched
    :type projects: Sequence[str]
    :param filter: Filter on entities to collect tags from
    :type filter: dict
    """

    _service = "projects"
    _action = "get_task_tags"
    _version = "2.9"
    _schema = {
        "definitions": {},
        "properties": {
            "filter": {
                "description": "Filter on entities to collect tags from",
                "properties": {
                    "system_tags": {
                        "description": "The list of system tag values to filter by. Use 'null' value to specify empty system tags. Use '__Snot' value to specify that the following value should be excluded",
                        "items": {"type": "string"},
                        "type": "array",
                    },
                    "tags": {
                        "description": "The list of tag values to filter by. Use 'null' value to specify empty tags. Use '__Snot' value to specify that the following value should be excluded",
                        "items": {"type": "string"},
                        "type": "array",
                    },
                },
                "type": ["object", "null"],
            },
            "include_system": {
                "default": False,
                "description": "If set to 'true' then the list of the system tags is also returned. The default value is 'false'",
                "type": ["boolean", "null"],
            },
            "projects": {
                "description": "The list of projects under which the tags are searched. If not passed or empty then all the projects are searched",
                "items": {"type": "string"},
                "type": ["array", "null"],
            },
        },
        "type": "object",
    }

    def __init__(
        self,
        include_system: Optional[bool] = False,
        projects: Optional[List[str]] = None,
        filter: Optional[dict] = None,
        **kwargs: Any
    ) -> None:
        super(GetTaskTagsRequest, self).__init__(**kwargs)
        self.include_system = include_system
        self.projects = projects
        self.filter = filter

    @schema_property("include_system")
    def include_system(self) -> Optional[bool]:
        return self._property_include_system

    @include_system.setter
    def include_system(self, value: Optional[bool]) -> None:
        if value is None:
            self._property_include_system = None
            return
        self.assert_isinstance(value, "include_system", (bool,))
        self._property_include_system = value

    @schema_property("projects")
    def projects(self) -> Optional[List[str]]:
        return self._property_projects

    @projects.setter
    def projects(self, value: Optional[List[str]]) -> None:
        if value is None:
            self._property_projects = None
            return
        self.assert_isinstance(value, "projects", (list, tuple))
        self.assert_isinstance(value, "projects", six.string_types, is_array=True)
        self._property_projects = value

    @schema_property("filter")
    def filter(self) -> Optional[dict]:
        return self._property_filter

    @filter.setter
    def filter(self, value: Optional[dict]) -> None:
        if value is None:
            self._property_filter = None
            return
        self.assert_isinstance(value, "filter", (dict,))
        self._property_filter = value


class GetTaskTagsResponse(Response):
    """
    Response of projects.get_task_tags endpoint.

    :param tags: The list of unique tag values
    :type tags: Sequence[str]
    :param system_tags: The list of unique system tag values. Returned only if
        'include_system' is set to 'true' in the request
    :type system_tags: Sequence[str]
    """

    _service = "projects"
    _action = "get_task_tags"
    _version = "2.9"
    _schema = {
        "definitions": {},
        "properties": {
            "system_tags": {
                "description": "The list of unique system tag values. Returned only if 'include_system' is set to 'true' in the request",
                "items": {"type": "string"},
                "type": ["array", "null"],
            },
            "tags": {
                "description": "The list of unique tag values",
                "items": {"type": "string"},
                "type": ["array", "null"],
            },
        },
        "type": "object",
    }

    def __init__(
        self, tags: Optional[List[str]] = None, system_tags: Optional[List[str]] = None, **kwargs: Any
    ) -> None:
        super(GetTaskTagsResponse, self).__init__(**kwargs)
        self.tags = tags
        self.system_tags = system_tags

    @schema_property("tags")
    def tags(self) -> Optional[List[str]]:
        return self._property_tags

    @tags.setter
    def tags(self, value: Optional[List[str]]) -> None:
        if value is None:
            self._property_tags = None
            return
        self.assert_isinstance(value, "tags", (list, tuple))
        self.assert_isinstance(value, "tags", six.string_types, is_array=True)
        self._property_tags = value

    @schema_property("system_tags")
    def system_tags(self) -> Optional[List[str]]:
        return self._property_system_tags

    @system_tags.setter
    def system_tags(self, value: Optional[List[str]]) -> None:
        if value is None:
            self._property_system_tags = None
            return
        self.assert_isinstance(value, "system_tags", (list, tuple))
        self.assert_isinstance(value, "system_tags", six.string_types, is_array=True)
        self._property_system_tags = value


class GetUniqueMetricVariantsRequest(Request):
    """
    Get all metric/variant pairs reported for tasks in a specific project.
            If no project is specified, metrics/variant paris reported for all tasks will be returned.
            If the project does not exist, an empty list will be returned.

    :param project: Project ID
    :type project: str
    """

    _service = "projects"
    _action = "get_unique_metric_variants"
    _version = "2.9"
    _schema = {
        "definitions": {},
        "properties": {"project": {"description": "Project ID", "type": ["string", "null"]}},
        "type": "object",
    }

    def __init__(self, project: Optional[str] = None, **kwargs: Any) -> None:
        super(GetUniqueMetricVariantsRequest, self).__init__(**kwargs)
        self.project = project

    @schema_property("project")
    def project(self) -> Optional[str]:
        return self._property_project

    @project.setter
    def project(self, value: Optional[str]) -> None:
        if value is None:
            self._property_project = None
            return
        self.assert_isinstance(value, "project", six.string_types)
        self._property_project = value


class GetUniqueMetricVariantsResponse(Response):
    """
    Response of projects.get_unique_metric_variants endpoint.

    :param metrics: A list of metric variants reported for tasks in this project
    :type metrics: Sequence[MetricVariantResult]
    """

    _service = "projects"
    _action = "get_unique_metric_variants"
    _version = "2.9"
    _schema = {
        "definitions": {
            "metric_variant_result": {
                "properties": {
                    "metric": {
                        "description": "Metric name",
                        "type": ["string", "null"],
                    },
                    "metric_hash": {
                        "description": "Metric name hash. Used instead of the metric name when categorizing\n                last metrics events in task objects.",
                        "type": ["string", "null"],
                    },
                    "variant": {
                        "description": "Variant name",
                        "type": ["string", "null"],
                    },
                    "variant_hash": {
                        "description": "Variant name hash. Used instead of the variant name when categorizing\n                last metrics events in task objects.",
                        "type": ["string", "null"],
                    },
                },
                "type": "object",
            }
        },
        "properties": {
            "metrics": {
                "description": "A list of metric variants reported for tasks in this project",
                "items": {"$ref": "#/definitions/metric_variant_result"},
                "type": ["array", "null"],
            }
        },
        "type": "object",
    }

    def __init__(self, metrics: Optional[List[Any]] = None, **kwargs: Any) -> None:
        super(GetUniqueMetricVariantsResponse, self).__init__(**kwargs)
        self.metrics = metrics

    @schema_property("metrics")
    def metrics(self) -> Optional[List[Any]]:
        return self._property_metrics

    @metrics.setter
    def metrics(self, value: Optional[List[Any]]) -> None:
        if value is None:
            self._property_metrics = None
            return
        self.assert_isinstance(value, "metrics", (list, tuple))
        if any((isinstance(v, dict) for v in value)):
            value = [MetricVariantResult.from_dict(v) if isinstance(v, dict) else v for v in value]
        else:
            self.assert_isinstance(value, "metrics", MetricVariantResult, is_array=True)
        self._property_metrics = value


class MakePrivateRequest(Request):
    """
    Convert public projects to private

    :param ids: Ids of the projects to convert. Only the projects originated by the
        company can be converted
    :type ids: Sequence[str]
    """

    _service = "projects"
    _action = "make_private"
    _version = "2.9"
    _schema = {
        "definitions": {},
        "properties": {
            "ids": {
                "description": "Ids of the projects to convert. Only the projects originated by the company can be converted",
                "items": {"type": "string"},
                "type": ["array", "null"],
            }
        },
        "type": "object",
    }

    def __init__(self, ids: Optional[List[str]] = None, **kwargs: Any) -> None:
        super(MakePrivateRequest, self).__init__(**kwargs)
        self.ids = ids

    @schema_property("ids")
    def ids(self) -> Optional[List[str]]:
        return self._property_ids

    @ids.setter
    def ids(self, value: Optional[List[str]]) -> None:
        if value is None:
            self._property_ids = None
            return
        self.assert_isinstance(value, "ids", (list, tuple))
        self.assert_isinstance(value, "ids", six.string_types, is_array=True)
        self._property_ids = value


class MakePrivateResponse(Response):
    """
    Response of projects.make_private endpoint.

    :param updated: Number of projects updated
    :type updated: int
    """

    _service = "projects"
    _action = "make_private"
    _version = "2.9"
    _schema = {
        "definitions": {},
        "properties": {
            "updated": {
                "description": "Number of projects updated",
                "type": ["integer", "null"],
            }
        },
        "type": "object",
    }

    def __init__(self, updated: Optional[int] = None, **kwargs: Any) -> None:
        super(MakePrivateResponse, self).__init__(**kwargs)
        self.updated = updated

    @schema_property("updated")
    def updated(self) -> Optional[int]:
        return self._property_updated

    @updated.setter
    def updated(self, value: Optional[int]) -> None:
        if value is None:
            self._property_updated = None
            return
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        self.assert_isinstance(value, "updated", six.integer_types)
        self._property_updated = value


class MakePublicRequest(Request):
    """
    Convert company projects to public

    :param ids: Ids of the projects to convert
    :type ids: Sequence[str]
    """

    _service = "projects"
    _action = "make_public"
    _version = "2.9"
    _schema = {
        "definitions": {},
        "properties": {
            "ids": {
                "description": "Ids of the projects to convert",
                "items": {"type": "string"},
                "type": ["array", "null"],
            }
        },
        "type": "object",
    }

    def __init__(self, ids: Optional[List[str]] = None, **kwargs: Any) -> None:
        super(MakePublicRequest, self).__init__(**kwargs)
        self.ids = ids

    @schema_property("ids")
    def ids(self) -> Optional[List[str]]:
        return self._property_ids

    @ids.setter
    def ids(self, value: Optional[List[str]]) -> None:
        if value is None:
            self._property_ids = None
            return
        self.assert_isinstance(value, "ids", (list, tuple))
        self.assert_isinstance(value, "ids", six.string_types, is_array=True)
        self._property_ids = value


class MakePublicResponse(Response):
    """
    Response of projects.make_public endpoint.

    :param updated: Number of projects updated
    :type updated: int
    """

    _service = "projects"
    _action = "make_public"
    _version = "2.9"
    _schema = {
        "definitions": {},
        "properties": {
            "updated": {
                "description": "Number of projects updated",
                "type": ["integer", "null"],
            }
        },
        "type": "object",
    }

    def __init__(self, updated: Optional[int] = None, **kwargs: Any) -> None:
        super(MakePublicResponse, self).__init__(**kwargs)
        self.updated = updated

    @schema_property("updated")
    def updated(self) -> Optional[int]:
        return self._property_updated

    @updated.setter
    def updated(self, value: Optional[int]) -> None:
        if value is None:
            self._property_updated = None
            return
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        self.assert_isinstance(value, "updated", six.integer_types)
        self._property_updated = value


class UpdateRequest(Request):
    """
    Update project information

    :param project: Project id
    :type project: str
    :param name: Project name. Unique within the company.
    :type name: str
    :param description: Project description
    :type description: str
    :param tags: User-defined tags list
    :type tags: Sequence[str]
    :param system_tags: System tags list. This field is reserved for system use,
        please don't use it.
    :type system_tags: Sequence[str]
    :param default_output_destination: The default output destination URL for new
        tasks under this project
    :type default_output_destination: str
    """

    _service = "projects"
    _action = "update"
    _version = "2.9"
    _schema = {
        "definitions": {},
        "properties": {
            "default_output_destination": {
                "description": "The default output destination URL for new tasks under this project",
                "type": "string",
            },
            "description": {"description": "Project description", "type": "string"},
            "name": {
                "description": "Project name. Unique within the company.",
                "type": "string",
            },
            "project": {"description": "Project id", "type": "string"},
            "system_tags": {
                "description": "System tags list. This field is reserved for system use, please don't use it.",
                "items": {"type": "string"},
                "type": "array",
            },
            "tags": {
                "description": "User-defined tags list",
                "items": {"type": "string"},
                "type": "array",
            },
        },
        "required": ["project"],
        "type": "object",
    }

    def __init__(
        self,
        project: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        system_tags: Optional[List[str]] = None,
        default_output_destination: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        super(UpdateRequest, self).__init__(**kwargs)
        self.project = project
        self.name = name
        self.description = description
        self.tags = tags
        self.system_tags = system_tags
        self.default_output_destination = default_output_destination

    @schema_property("project")
    def project(self) -> str:
        return self._property_project

    @project.setter
    def project(self, value: str) -> None:
        if value is None:
            self._property_project = None
            return
        self.assert_isinstance(value, "project", six.string_types)
        self._property_project = value

    @schema_property("name")
    def name(self) -> Optional[str]:
        return self._property_name

    @name.setter
    def name(self, value: Optional[str]) -> None:
        if value is None:
            self._property_name = None
            return
        self.assert_isinstance(value, "name", six.string_types)
        self._property_name = value

    @schema_property("description")
    def description(self) -> Optional[str]:
        return self._property_description

    @description.setter
    def description(self, value: Optional[str]) -> None:
        if value is None:
            self._property_description = None
            return
        self.assert_isinstance(value, "description", six.string_types)
        self._property_description = value

    @schema_property("tags")
    def tags(self) -> Optional[List[str]]:
        return self._property_tags

    @tags.setter
    def tags(self, value: Optional[List[str]]) -> None:
        if value is None:
            self._property_tags = None
            return
        self.assert_isinstance(value, "tags", (list, tuple))
        self.assert_isinstance(value, "tags", six.string_types, is_array=True)
        self._property_tags = value

    @schema_property("system_tags")
    def system_tags(self) -> Optional[List[str]]:
        return self._property_system_tags

    @system_tags.setter
    def system_tags(self, value: Optional[List[str]]) -> None:
        if value is None:
            self._property_system_tags = None
            return
        self.assert_isinstance(value, "system_tags", (list, tuple))
        self.assert_isinstance(value, "system_tags", six.string_types, is_array=True)
        self._property_system_tags = value

    @schema_property("default_output_destination")
    def default_output_destination(self) -> Optional[str]:
        return self._property_default_output_destination

    @default_output_destination.setter
    def default_output_destination(self, value: Optional[str]) -> None:
        if value is None:
            self._property_default_output_destination = None
            return
        self.assert_isinstance(value, "default_output_destination", six.string_types)
        self._property_default_output_destination = value


class UpdateResponse(Response):
    """
    Response of projects.update endpoint.

    :param updated: Number of projects updated (0 or 1)
    :type updated: int
    :param fields: Updated fields names and values
    :type fields: dict
    """

    _service = "projects"
    _action = "update"
    _version = "2.9"
    _schema = {
        "definitions": {},
        "properties": {
            "fields": {
                "additionalProperties": True,
                "description": "Updated fields names and values",
                "type": ["object", "null"],
            },
            "updated": {
                "description": "Number of projects updated (0 or 1)",
                "enum": [0, 1],
                "type": ["integer", "null"],
            },
        },
        "type": "object",
    }

    def __init__(self, updated: Optional[int] = None, fields: Optional[dict] = None, **kwargs: Any) -> None:
        super(UpdateResponse, self).__init__(**kwargs)
        self.updated = updated
        self.fields = fields

    @schema_property("updated")
    def updated(self) -> Optional[int]:
        return self._property_updated

    @updated.setter
    def updated(self, value: Optional[int]) -> None:
        if value is None:
            self._property_updated = None
            return
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        self.assert_isinstance(value, "updated", six.integer_types)
        self._property_updated = value

    @schema_property("fields")
    def fields(self) -> Optional[dict]:
        return self._property_fields

    @fields.setter
    def fields(self, value: Optional[dict]) -> None:
        if value is None:
            self._property_fields = None
            return
        self.assert_isinstance(value, "fields", (dict,))
        self._property_fields = value


response_mapping = {
    CreateRequest: CreateResponse,
    GetByIdRequest: GetByIdResponse,
    GetAllRequest: GetAllResponse,
    UpdateRequest: UpdateResponse,
    DeleteRequest: DeleteResponse,
    GetUniqueMetricVariantsRequest: GetUniqueMetricVariantsResponse,
    GetHyperParametersRequest: GetHyperParametersResponse,
    GetTaskTagsRequest: GetTaskTagsResponse,
    GetModelTagsRequest: GetModelTagsResponse,
    MakePublicRequest: MakePublicResponse,
    MakePrivateRequest: MakePrivateResponse,
}
