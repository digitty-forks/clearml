import base64
from typing import Dict, Optional

import attr
from attr.validators import instance_of

from .. import Task
from ..utilities.pyhocon import ConfigFactory, ConfigTree
from .auto_scaler import CloudDriver
from .cloud_driver import parse_tags

try:
    # noinspection PyPackageRequirements
    import boto3
    from botocore.exceptions import ClientError

    Task.add_requirements("boto3")
except ImportError as err:
    raise ImportError(
        "AwsAutoScaler requires 'boto3' package, it was not found\ninstall with: pip install boto3"
    ) from err


@attr.s
class AWSDriver(CloudDriver):
    """AWS Driver"""

    aws_access_key_id = attr.ib(validator=instance_of(str), default="")
    aws_secret_access_key = attr.ib(validator=instance_of(str), default="")
    aws_session_token = attr.ib(validator=instance_of(str), default="")
    aws_region = attr.ib(validator=instance_of(str), default="")
    use_credentials_chain = attr.ib(validator=instance_of(bool), default=False)
    use_iam_instance_profile = attr.ib(validator=instance_of(bool), default=False)
    iam_arn = attr.ib(validator=instance_of(str), default="")
    iam_name = attr.ib(validator=instance_of(str), default="")

    @classmethod
    def from_config(cls, config: ConfigTree) -> "AWSDriver":
        obj = super().from_config(config)
        obj.aws_access_key_id = config["hyper_params"].get("cloud_credentials_key")
        obj.aws_secret_access_key = config["hyper_params"].get("cloud_credentials_secret")
        obj.aws_session_token = config["hyper_params"].get("cloud_credentials_token")
        obj.aws_region = config["hyper_params"].get("cloud_credentials_region")
        obj.use_credentials_chain = config["hyper_params"].get("use_credentials_chain", False)
        obj.use_iam_instance_profile = config["hyper_params"].get("use_iam_instance_profile", False)
        obj.iam_arn = config["hyper_params"].get("iam_arn")
        obj.iam_name = config["hyper_params"].get("iam_name")
        return obj

    def __attrs_post_init__(self) -> None:
        super().__attrs_post_init__()
        self.tags = parse_tags(self.tags)

    def spin_up_worker(
        self,
        resource_conf: dict,
        worker_prefix: str,
        queue_name: str,
        task_id: str,
    ) -> str:
        # user_data script will automatically run when the instance is started. it will install the required packages
        # for clearml-agent, configure it using environment variables and run clearml-agent on the required queue
        # Config reference: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2/client/run_instances.html
        user_data = self.gen_user_data(worker_prefix, queue_name, task_id, resource_conf.get("cpu_only", False))

        ec2 = boto3.client("ec2", **self.creds())
        launch_specification = ConfigFactory.from_dict(
            {
                "ImageId": resource_conf["ami_id"],
                "Monitoring": {"Enabled": bool(resource_conf.get("enable_monitoring", False))},
                "InstanceType": resource_conf["instance_type"],
            }
        )
        # handle EBS volumes (existing or new)
        # Ref: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/block-device-mapping-concepts.html
        if resource_conf.get("ebs_snapshot_id") and resource_conf.get("ebs_device_name"):
            launch_specification["BlockDeviceMappings"] = [
                {
                    "DeviceName": resource_conf["ebs_device_name"],
                    "Ebs": {"SnapshotId": resource_conf["ebs_snapshot_id"]},
                }
            ]
        elif resource_conf.get("ebs_device_name"):
            launch_specification["BlockDeviceMappings"] = [
                {
                    "DeviceName": resource_conf["ebs_device_name"],
                    "Ebs": {
                        "VolumeSize": resource_conf.get("ebs_volume_size", 80),
                        "VolumeType": resource_conf.get("ebs_volume_type", "gp3"),
                    },
                }
            ]

        if resource_conf.get("subnet_id", None):
            launch_specification["SubnetId"] = resource_conf["subnet_id"]
        elif resource_conf.get("availability_zone", None):
            launch_specification["Placement"] = {"AvailabilityZone": resource_conf["availability_zone"]}
        else:
            raise Exception("subnet_id or availability_zone must to be specified in the config")
        if resource_conf.get("key_name", None):
            launch_specification["KeyName"] = resource_conf["key_name"]
        if resource_conf.get("security_group_ids", None):
            launch_specification["SecurityGroupIds"] = resource_conf["security_group_ids"]
        # Adding iam role - you can have Arn OR Name, not both, Arn getting priority
        if self.iam_arn:
            launch_specification["IamInstanceProfile"] = {
                "Arn": self.iam_arn,
            }
        elif self.iam_name:
            launch_specification["IamInstanceProfile"] = {"Name": self.iam_name}

        if resource_conf["is_spot"]:
            # Create a request for a spot instance in AWS
            encoded_user_data = base64.b64encode(user_data.encode("ascii")).decode("ascii")
            launch_specification["UserData"] = encoded_user_data
            ConfigTree.merge_configs(launch_specification, resource_conf.get("extra_configurations", {}))

            instances = ec2.request_spot_instances(LaunchSpecification=launch_specification)

            # Wait until spot request is fulfilled
            request_id = instances["SpotInstanceRequests"][0]["SpotInstanceRequestId"]
            waiter = ec2.get_waiter("spot_instance_request_fulfilled")
            waiter.wait(SpotInstanceRequestIds=[request_id])
            # Get the instance object for later use
            response = ec2.describe_spot_instance_requests(SpotInstanceRequestIds=[request_id])
            instance_id = response["SpotInstanceRequests"][0]["InstanceId"]

        else:
            # Create a new EC2 instance
            launch_specification.update(
                MinCount=1,
                MaxCount=1,
                UserData=user_data,
                InstanceInitiatedShutdownBehavior="terminate",
            )
            ConfigTree.merge_configs(launch_specification, resource_conf.get("extra_configurations", {}))

            instances = ec2.run_instances(**launch_specification)

            # Get the instance object for later use
            instance_id = instances["Instances"][0]["InstanceId"]

        instance = boto3.resource("ec2", **self.creds()).Instance(instance_id)
        if resource_conf.get("tags"):
            instance.create_tags(
                Resources=[instance_id],
                Tags=[{"Key": key, "Value": val} for key, val in parse_tags(resource_conf.get("tags"))],
            )
        # Wait until instance is in running state
        instance.wait_until_running()
        return instance_id

    def spin_down_worker(self, instance_id: str) -> None:
        instance = boto3.resource("ec2", **self.creds()).Instance(instance_id)
        instance.terminate()

    def creds(self) -> Dict[str, Optional[str]]:
        creds = {
            "region_name": self.aws_region or None,
        }

        if not self.use_credentials_chain:
            creds.update(
                {
                    "aws_secret_access_key": self.aws_secret_access_key or None,
                    "aws_access_key_id": self.aws_access_key_id or None,
                    "aws_session_token": self.aws_session_token or None,
                }
            )
        return creds

    def instance_id_command(self) -> str:
        return "curl http://169.254.169.254/latest/meta-data/instance-id"

    def instance_type_key(self) -> str:
        return "instance_type"

    def kind(self) -> str:
        return "AWS"

    def console_log(self, instance_id: str) -> str:
        ec2 = boto3.client("ec2", **self.creds())
        try:
            out = ec2.get_console_output(InstanceId=instance_id)
            return out.get("Output", "")
        except ClientError as err:
            return "error: cannot get logs for {}:\n{}".format(instance_id, err)
