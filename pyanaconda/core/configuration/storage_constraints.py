#
# Copyright (C) 2020 Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# the GNU General Public License v.2, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the
# GNU General Public License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.  Any Red Hat trademarks that are incorporated in the
# source code or documentation are not subject to the GNU General Public
# License and may only be used or replicated with the express permission of
# Red Hat, Inc.
#
#
from enum import Enum

from pyanaconda.core.configuration.base import Section
from pyanaconda.core.storage import DEVICE_TYPE_LVM, DEVICE_TYPE_MD, DEVICE_TYPE_PARTITION, \
    DEVICE_TYPE_BTRFS, DEVICE_TYPE_DISK, DEVICE_TYPE_LVM_THINP, Size


class DeviceType(Enum):
    """Type of a device."""
    LVM = DEVICE_TYPE_LVM
    MD = DEVICE_TYPE_MD
    PARTITION = DEVICE_TYPE_PARTITION
    BTRFS = DEVICE_TYPE_BTRFS
    DISK = DEVICE_TYPE_DISK
    LVM_THINP = DEVICE_TYPE_LVM_THINP

    @classmethod
    def from_name(cls, value):
        """Convert the given value into a device type."""
        try:
            member = cls.__members__[value]  # pylint: disable=unsubscriptable-object
            return member.value
        except KeyError:
            pass

        raise ValueError("'{}' is not a valid device typ".format(value))


class StorageConstraints(Section):
    """The Storage Constraints section."""

    @property
    def min_ram(self):
        """Minimal size of the total memory."""
        return self._get_option("min_ram", Size)

    @property
    def luks2_min_ram(self):
        """Minimal size of the available memory for LUKS2."""
        return self._get_option("luks2_min_ram", Size)

    @property
    def swap_is_recommended(self):
        """Should we recommend to specify a swap partition?"""
        return self._get_option("swap_is_recommended", bool)

    @property
    def min_partition_sizes(self):
        """Recommended minimal sizes of partitions.

        :return: a dictionary of partition sizes
        """
        return self._get_option("min_partition_sizes", self._convert_partition_sizes)

    @property
    def req_partition_sizes(self):
        """Required minimal sizes of partitions.

        :return: a dictionary of partition sizes
        """
        return self._get_option("req_partition_sizes", self._convert_partition_sizes)

    def _convert_partition_sizes(self, value):
        """Convert the given value into a dictionary of partition sizes."""
        lines = value.split("\n")
        sizes = {}

        for line in lines:
            if line:
                mount_point, size = line.split(maxsplit=1)
                sizes[mount_point] = Size(size)

        return sizes

    @property
    def root_device_types(self):
        """Allowed device types of the / partition if any.

        Valid values:

          0  LVM        Allow LVM.
          1  MD         Allow RAID.
          2  PARTITION  Allow standard partitions.
          3  BTRFS      Allow Btrfs.
          4  DISK       Allow disks.
          5  LVM_THINP  Allow LVM Thin Provisioning.

        :return: a set of device types
        """
        return self._get_option("root_device_types", self._convert_device_types)

    def _convert_device_types(self, value):
        """Convert the given value into a set of device types."""
        return set(map(DeviceType.from_name, value.split()))

    @property
    def must_be_on_linuxfs(self):
        """Mount points that must be on a linux file system.

        :return: a set of mount points
        """
        return set(self._get_option("must_be_on_linuxfs").split())

    @property
    def must_be_on_root(self):
        """Paths that must be directories on the / file system.

        :return: a set of paths
        """
        return set(self._get_option("must_be_on_root").split())

    @property
    def must_not_be_on_root(self):
        """Paths that must NOT be directories on the / file system.

        :return: a set of paths
        """
        return set(self._get_option("must_not_be_on_root").split())

    @property
    def reformat_allowlist(self):
        """Mount point prefixes that are recommended to be reformatted.

        It will be recommended to create a new file system on a mount point
        that has an allowed prefix, but doesn't have a blocked one.

        :return: a set of mount point prefixes
        """
        return set(self._get_option("reformat_allowlist").split())

    @property
    def reformat_blocklist(self):
        """Mount point prefixes that are NOT recommended to be reformatted.

        It will be recommended to create a new file system on a mount point
        that has an allowed prefix, but doesn't have a blocked one.

        :return: a set of mount point prefixes
        """
        return set(self._get_option("reformat_blocklist").split())
