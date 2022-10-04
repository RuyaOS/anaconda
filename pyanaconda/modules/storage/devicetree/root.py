#
# Copyright (C) 2019  Red Hat, Inc.
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
import os
import shlex

from blivet import util as blivet_util
from blivet.errors import StorageError
from blivet.storage_log import log_exception_info

from pyanaconda.core.configuration.anaconda import conf
from pyanaconda.core.i18n import _
from pyanaconda.core.path import set_system_root
from pyanaconda.modules.storage.devicetree.fsset import BlkidTab, CryptTab

from pyanaconda.anaconda_loggers import get_module_logger
log = get_module_logger(__name__)

__all__ = ["mount_existing_system", "find_existing_installations", "Root"]


def mount_existing_system(storage, root_device, read_only=None):
    """Mount filesystems specified in root_device's /etc/fstab file."""
    root_path = conf.target.physical_root
    read_only = "ro" if read_only else ""

    # Mount the root device.
    if root_device.protected and os.path.ismount("/mnt/install/isodir"):
        blivet_util.mount("/mnt/install/isodir",
                          root_path,
                          fstype=root_device.format.type,
                          options="bind")
    else:
        root_device.setup()
        root_device.format.mount(chroot=root_path,
                                 mountpoint="/",
                                 options="%s,%s" % (root_device.format.options, read_only))

    # Set up the sysroot.
    set_system_root(root_path)

    # Mount the filesystems.
    storage.fsset.parse_fstab(chroot=root_path)
    storage.fsset.mount_filesystems(root_path=root_path, read_only=read_only, skip_root=True)

    # Turn on swap.
    if not conf.target.is_image or not read_only:
        try:
            storage.fsset.turn_on_swap(root_path=root_path)
        except StorageError as e:
            log.error("Error enabling swap: %s", str(e))

    # Generate mtab.
    if not read_only:
        storage.make_mtab(chroot=root_path)


def find_existing_installations(devicetree, teardown_all=True):
    """Find existing GNU/Linux installations on devices from the device tree.

    :param devicetree: a device tree to find existing installations in
    :param bool teardown_all: whether to tear down all devices in the end
    :return: roots of all found installations
    """
    try:
        roots = _find_existing_installations(devicetree)
        return roots
    except Exception:  # pylint: disable=broad-except
        log_exception_info(log.info, "failure detecting existing installations")
    finally:
        if teardown_all:
            devicetree.teardown_all()

    return []


def _find_existing_installations(devicetree):
    """Find existing GNU/Linux installations on devices from the device tree.

    :param devicetree: a device tree to find existing installations in
    :return: roots of all found installations
    """
    if not os.path.exists(conf.target.physical_root):
        blivet_util.makedirs(conf.target.physical_root)

    sysroot = conf.target.physical_root
    roots = []
    direct_devices = (dev for dev in devicetree.devices if dev.direct)
    for device in direct_devices:
        if not device.format.linux_native or not device.format.mountable or \
           not device.controllable or not device.format.exists:
            continue

        try:
            device.setup()
        except Exception:  # pylint: disable=broad-except
            log_exception_info(log.warning, "setup of %s failed", [device.name])
            continue

        options = device.format.options + ",ro"
        try:
            device.format.mount(options=options, mountpoint=sysroot)
        except Exception:  # pylint: disable=broad-except
            log_exception_info(log.warning, "mount of %s as %s failed", [device.name, device.format.type])
            blivet_util.umount(mountpoint=sysroot)
            continue

        if not os.access(sysroot + "/etc/fstab", os.R_OK):
            blivet_util.umount(mountpoint=sysroot)
            device.teardown()
            continue

        architecture, product, version = get_release_string(chroot=sysroot)
        (mounts, swaps) = _parse_fstab(devicetree, chroot=sysroot)
        blivet_util.umount(mountpoint=sysroot)

        if not mounts and not swaps:
            # empty /etc/fstab. weird, but I've seen it happen.
            continue

        roots.append(Root(
            product=product,
            version=version,
            arch=architecture,
            mounts=mounts,
            swaps=swaps
        ))

    return roots


def get_release_string(chroot):
    """Identify the installation of a Linux distribution.

    Attempt to identify the installation of a Linux distribution by checking
    a previously mounted filesystem for several files.  The filesystem must
    be mounted under the target physical root.

    :returns: The machine's arch, distribution name, and distribution version
    or None for any parts that cannot be determined
    :rtype: (string, string, string)
    """
    rel_name = None
    rel_ver = None
    sysroot = chroot

    try:
        rel_arch = blivet_util.capture_output(["arch"], root=sysroot).strip()
    except OSError:
        rel_arch = None

    try:
        filename = "%s/etc/redhat-release" % sysroot
        if os.access(filename, os.R_OK):
            (rel_name, rel_ver) = _release_from_redhat_release(filename)
        else:
            filename = "%s/etc/os-release" % sysroot
            if os.access(filename, os.R_OK):
                (rel_name, rel_ver) = _release_from_os_release(filename)
    except ValueError:
        pass

    return rel_arch, rel_name, rel_ver


def _release_from_redhat_release(fn):
    """Identify the installation of a Linux distribution via /etc/redhat-release.

    Attempt to identify the installation of a Linux distribution via
    /etc/redhat-release.  This file must already have been verified to exist
    and be readable.

    :param fn: an open filehandle on /etc/redhat-release
    :type fn: filehandle
    :returns: The distribution's name and version, or None for either or both
    if they cannot be determined
    :rtype: (string, string)
    """
    rel_name = None
    rel_ver = None

    with open(fn) as f:
        try:
            relstr = f.readline().strip()
        except (OSError, AttributeError):
            relstr = ""

    # get the release name and version
    # assumes that form is something
    # like "Red Hat Linux release 6.2 (Zoot)"
    (product, sep, version) = relstr.partition(" release ")
    if sep:
        rel_name = product
        rel_ver = version.split()[0]

    return rel_name, rel_ver


def _release_from_os_release(fn):
    """Identify the installation of a Linux distribution via /etc/os-release.

    Attempt to identify the installation of a Linux distribution via
    /etc/os-release.  This file must already have been verified to exist
    and be readable.

    :param fn: an open filehandle on /etc/os-release
    :type fn: filehandle
    :returns: The distribution's name and version, or None for either or both
    if they cannot be determined
    :rtype: (string, string)
    """
    rel_name = None
    rel_ver = None

    with open(fn, "r") as f:
        parser = shlex.shlex(f)

        while True:
            key = parser.get_token()
            if key == parser.eof:
                break
            elif key == "NAME":
                # Throw away the "=".
                parser.get_token()
                rel_name = parser.get_token().strip("'\"")
            elif key == "VERSION_ID":
                # Throw away the "=".
                parser.get_token()
                rel_ver = parser.get_token().strip("'\"")

    return rel_name, rel_ver


def _parse_fstab(devicetree, chroot):
    """Parse /etc/fstab.

    :param devicetree: a device tree
    :param chroot: a path to the target OS installation
    :return: a tuple of a mount dict and swap list
    """
    mounts = {}
    swaps = []
    path = "%s/etc/fstab" % chroot
    if not os.access(path, os.R_OK):
        # XXX should we raise an exception instead?
        log.info("cannot open %s for read", path)
        return mounts, swaps

    blkid_tab = BlkidTab(chroot=chroot)
    try:
        blkid_tab.parse()
        log.debug("blkid.tab devs: %s", list(blkid_tab.devices.keys()))
    except Exception:  # pylint: disable=broad-except
        log_exception_info(log.info, "error parsing blkid.tab")
        blkid_tab = None

    crypt_tab = CryptTab(devicetree, blkid_tab=blkid_tab, chroot=chroot)
    try:
        crypt_tab.parse(chroot=chroot)
        log.debug("crypttab maps: %s", list(crypt_tab.mappings.keys()))
    except Exception:  # pylint: disable=broad-except
        log_exception_info(log.info, "error parsing crypttab")
        crypt_tab = None

    with open(path) as f:
        log.debug("parsing %s", path)
        for line in f.readlines():

            (line, _pound, _comment) = line.partition("#")
            fields = line.split(None, 4)

            if len(fields) < 5:
                continue

            (devspec, mountpoint, fstype, options, _rest) = fields

            # find device in the tree
            device = devicetree.resolve_device(devspec,
                                               crypt_tab=crypt_tab,
                                               blkid_tab=blkid_tab,
                                               options=options)

            if device is None:
                continue

            if fstype != "swap":
                mounts[mountpoint] = device
            else:
                swaps.append(device)

    return mounts, swaps


class Root(object):
    """A root represents an existing OS installation."""

    def __init__(self, name=None, product=None, version=None, arch=None, mounts=None, swaps=None):
        """Create a new OS representation.

        :param name: a name of the OS or None
        :param product: a distribution name or None
        :param version: a distribution version or None
        :param arch: a machine's architecture or None
        :param mounts: a dictionary of mount points and devices
        :param swaps: a list of swap devices
        """
        self._name = name
        self._product = product
        self._version = version
        self._arch = arch

        # Blivet needs to be able to set these attributes.
        self.mounts = mounts or {}
        self.swaps = swaps or []

    @property
    def name(self):
        """The name of the OS."""
        # Use the specified name.
        if self._name:
            return self._name

        # Or generate a translated name.
        if not self._product or not self._version or not self._arch:
            return _("Unknown Linux")

        if "linux" in self._product.lower():
            template = _("{product} {version} for {arch}")
        else:
            template = _("{product} Linux {version} for {arch}")

        return template.format(
            product=self._product,
            version=self._version,
            arch=self._arch
        )

    @property
    def device(self):
        """The root device or None."""
        return self.mounts.get("/")
