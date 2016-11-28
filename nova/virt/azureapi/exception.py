from nova.i18n import _
from nova import exception
from azure.common import AzureMissingResourceHttpError
from msrestazure.azure_exceptions import CloudError


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
