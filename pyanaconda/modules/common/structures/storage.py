#
# DBus structures for the storage data.
#
# Copyright (C) 2019  Red Hat, Inc.  All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from dasbus.structure import DBusData
from dasbus.typing import *  # pylint: disable=wildcard-import

__all__ = ["DeviceData", "DeviceFormatData", "DeviceActionData", "OSData"]


class DeviceData(DBusData):
    """Device data."""

    def __init__(self):
        self._type = ""
        self._name = ""
        self._path = ""
        self._size = 0
        self._parents = []
        self._children = []
        self._is_disk = False
        self._protected = False
        self._removable = False
        self._attrs = {}
        self._description = ""

    @property
    def type(self) -> Str:
        """A type of the device.

        :return: a device type
        """
        return self._type

    @type.setter
    def type(self, value: Str):
        self._type = value

    @property
    def name(self) -> Str:
        """A name of the device

        :return: a device name
        """
        return self._name

    @name.setter
    def name(self, name: Str):
        self._name = name

    @property
    def path(self) -> Str:
        """A device node representing the device.

        :return: a path
        """
        return self._path

    @path.setter
    def path(self, value: Str):
        self._path = value

    @property
    def size(self) -> UInt64:
        """A size of the device

        :return: a size in bytes
        """
        return UInt64(self._size)

    @size.setter
    def size(self, size: UInt64):
        self._size = size

    @property
    def is_disk(self) -> Bool:
        """Is this device a disk?

        :return: True or False
        """
        return self._is_disk

    @is_disk.setter
    def is_disk(self, is_disk: Bool):
        self._is_disk = is_disk

    @property
    def protected(self) -> Bool:
        """Is this device protected?"""
        return self._protected

    @protected.setter
    def protected(self, value):
        self._protected = value

    @property
    def removable(self) -> Bool:
        """Is this device removable?"""
        return self._removable

    @removable.setter
    def removable(self, value: Bool):
        self._removable = value

    @property
    def parents(self) -> List[Str]:
        """Parents of the device.

        :return: a list of device names
        """
        return self._parents

    @parents.setter
    def parents(self, names):
        self._parents = names

    @property
    def children(self) -> List[Str]:
        """Children of the device.

        :return: a list of device names
        """
        return self._children

    @children.setter
    def children(self, value):
        self._children = value

    @property
    def attrs(self) -> Dict[Str, Str]:
        """Additional attributes.

        The supported attributes are defined by
        the lists below.

        Attributes for all types:
            serial
            vendor
            model
            bus
            wwn
            uuid

        Attributes for DASD:
            bus-id

        Attributes for FCoE:
            path-id

        Attributes for iSCSI:
            port
            initiator
            lun
            target
            path-id

        Attributes for NVDIMM:
            mode
            namespace
            path-id

        Attributes for ZFCP:
            fcp-lun
            wwpn
            hba-id

        :return: a dictionary of attributes
        """
        return self._attrs

    @attrs.setter
    def attrs(self, attrs: Dict[Str, Str]):
        self._attrs = attrs

    @property
    def description(self) -> Str:
        """Description of the device.

        FIXME: This is a temporary property.

        :return: a string with description
        """
        return self._description

    @description.setter
    def description(self, text):
        self._description = text


class DeviceFormatData(DBusData):
    """Device format data."""

    def __init__(self):
        self._type = ""
        self._mountable = False
        self._attrs = {}
        self._description = ""

    @property
    def type(self) -> Str:
        """A type of the format.

        :return: a format type
        """
        return self._type

    @type.setter
    def type(self, value):
        self._type = value

    @property
    def mountable(self) -> Bool:
        """Is this something we can mount?"""
        return self._mountable

    @mountable.setter
    def mountable(self, value: Bool):
        self._mountable = value

    @property
    def attrs(self) -> Dict[Str, Str]:
        """Additional attributes.

        The supported attributes are defined by
        the list below.

        Attributes for all types:
            uuid
            label

        Attributes for file systems:
            mount-point

        :return: a dictionary of attributes
        """
        return self._attrs

    @attrs.setter
    def attrs(self, attrs: Dict[Str, Str]):
        self._attrs = attrs

    @property
    def description(self) -> Str:
        """Description of the format.

        FIXME: This is a temporary property.

        :return: a string with description
        """
        return self._description

    @description.setter
    def description(self, text):
        self._description = text


class DeviceActionData(DBusData):
    """Device action data."""

    def __init__(self):
        self._action_type = ""
        self._action_description = ""

        self._object_type = ""
        self._object_description = ""

        self._device_name = ""
        self._device_description = ""

        self._attrs = {}

    @property
    def action_type(self) -> Str:
        """A type of the action.

        For example:
            destroy, resize, create,
            add, remove, configure

        :return: a string with the type
        """
        return self._action_type

    @action_type.setter
    def action_type(self, name: Str):
        self._action_type = name

    @property
    def action_description(self) -> Str:
        """Description of the action.

        :return: a string with description
        """
        return self._action_description

    @action_description.setter
    def action_description(self, value):
        self._action_description = value

    @property
    def object_type(self) -> Str:
        """A type of the action object.

        For example:
            format, device, container

        :return: a string with the type
        """
        return self._object_type

    @object_type.setter
    def object_type(self, name: Str):
        self._object_type = name

    @property
    def object_description(self) -> Str:
        """Description of the action object.

        :return: a string with description
        """
        return self._object_description

    @object_description.setter
    def object_description(self, value):
        self._object_description = value

    @property
    def device_name(self) -> Str:
        """A name of the device.

        :return: a device name
        """
        return self._device_name

    @device_name.setter
    def device_name(self, name: Str):
        self._device_name = name

    @property
    def device_description(self) -> Str:
        """Description of the device.

        :return: a string with description
        """
        return self._device_description

    @device_description.setter
    def device_description(self, value):
        self._device_description = value

    @property
    def attrs(self) -> Dict[Str, Str]:
        """Additional attributes.

        The supported attributes are defined by
        the lists below.

        Attributes for all types:
            serial

        Attributes for file systems:
            mount-point

        :return: a dictionary of attributes
        """
        return self._attrs

    @attrs.setter
    def attrs(self, attrs: Dict[Str, Str]):
        self._attrs = attrs


class OSData(DBusData):
    """Data of an existing OS installation."""

    def __init__(self):
        self._os_name = ""
        self._mount_points = {}
        self._swap_devices = []

    @property
    def os_name(self) -> Str:
        """Name of the OS.

        :return: a string with name
        """
        return self._os_name

    @os_name.setter
    def os_name(self, name: Str):
        self._os_name = name

    @property
    def mount_points(self) -> Dict[Str, Str]:
        """Mount points.

        :return: a dictionary of mount points and device names
        """
        return self._mount_points

    @mount_points.setter
    def mount_points(self, mount_points: Dict[Str, Str]):
        self._mount_points = mount_points

    @property
    def swap_devices(self) -> List[Str]:
        """Swap devices.

        :return: a list of device names
        """
        return self._swap_devices

    @swap_devices.setter
    def swap_devices(self, devices: List[Str]):
        self._swap_devices = devices

    def get_root_device(self):
        """Get the root device.

        :return: a device name or None
        """
        return self.mount_points.get("/")

    def get_devices(self):
        """Get all devices.

        :return: a list of device names
        """
        devices = []
        devices.extend(self.swap_devices)
        devices.extend(self.mount_points.values())
        return devices
