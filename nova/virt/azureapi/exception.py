#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from azure.common import AzureMissingResourceHttpError
from msrestazure.azure_exceptions import CloudError
from nova import exception
from nova.i18n import _


AzureMissingResourceHttpError = AzureMissingResourceHttpError
CloudError = CloudError


class ImageAzureMappingNotFound(exception.NotFound):
    msg_fmt = _("Image %(image_name)s could not be found in Azure Mapping.")


class FlavorAzureMappingNotFound(exception.NotFound):
    msg_fmt = _("Flavor %(flavor_name)s could not be found in Azure Mapping.")


class FlavorInvalid(exception.Invalid):
    msg_fmt = _("Flavor %(flavor_name)s are Invalid for Instance "
                "%(instance_uuid)s in Azure.")


class PasswordInvalid(exception.Invalid):
    msg_fmt = _("Password are Invalid for Instance "
                "%(instance_uuid)s in Azure.")


class OSTypeNotFound(exception.NotFound):
    msg_fmt = _("Unabled to decide OS type %(os_type)s of instance.")


class NetworkCreateFailure(exception.NovaException):
    msg_fmt = _("Unabled to create network in Azure"
                " because %(reason)s")


class SubnetCreateFailure(exception.NovaException):
    msg_fmt = _("Unabled to create subnet in Azure"
                " because %(reason)s")


class ProviderRegisterFailure(exception.NovaException):
    msg_fmt = _("Unabled to register provider in Azure"
                " because %(reason)s")


class ResourceGroupCreateFailure(exception.NovaException):
    msg_fmt = _("Unabled to create resource group in Azure"
                " because %(reason)s")


class StorageAccountCreateFailure(exception.NovaException):
    msg_fmt = _("Unabled to create storage account in Azure"
                " because %(reason)s")


class StorageContainerCreateFailure(exception.NovaException):
    msg_fmt = _("Unabled to create storage container in Azure"
                " because %(reason)s")


class InstanceGetFailure(exception.NovaException):
    msg_fmt = _("Unabled to query instance %(instance_uuid)s in Azure"
                " because %(reason)s")


class InstanceListFailure(exception.NovaException):
    msg_fmt = _("Unabled to list instances in Azure"
                " because %(reason)s")


class InstanceDeleteFailure(exception.NovaException):
    msg_fmt = _("Unabled to delete instance %(instance_uuid)s in Azure"
                " because %(reason)s")


class InstanceResizeFailure(exception.NovaException):
    msg_fmt = _("Unabled to resize instance %(instance_uuid)s in Azure"
                " because %(reason)s")


class InstanceCreateUpdateFailure(exception.NovaException):
    msg_fmt = _("Unabled to create/update instance %(instance_uuid)s in Azure"
                " because %(reason)s")


class InstancePasswordSetFailure(exception.NovaException):
    msg_fmt = _("Unabled to set password for instance %(instance_uuid)s"
                " in Azure because %(reason)s")


class ComputeUsageListFailure(exception.NovaException):
    msg_fmt = _("Unabled to list compute usage in Azure"
                " because %(reason)s")


class NetworkInterfaceCreateFailure(exception.NovaException):
    msg_fmt = _("Unabled to create network interface for instance"
                " %(instance_uuid)s in Azure because %(reason)s")


class NetworkInterfaceListFailure(exception.NovaException):
    msg_fmt = _("Unabled to list network interface"
                " in Azure because %(reason)s")


class NetworkInterfaceDeleteFailure(exception.NovaException):
    msg_fmt = _("Unabled to delete network interface for instance"
                " %(instance_uuid)s in Azure because %(reason)s")


class BlobCopyFailure(exception.NovaException):
    msg_fmt = _("Unabled to copy blob %(blob_name)s from %(source_blob)s"
                " in Azure because %(reason)s")


class BlobDeleteFailure(exception.NovaException):
    msg_fmt = _("Unabled to delete blob %(blob_name)s"
                " in Azure because %(reason)s")


class BlobNotFound(exception.NotFound):
    msg_fmt = _("blob %(blob_name)s not found in Azure.")


class CleanUpFilure(exception.NovaException):
    msg_fmt = _("Unabled to clean up in Azure"
                " because %(reason)s")
