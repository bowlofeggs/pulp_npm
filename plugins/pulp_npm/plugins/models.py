from gettext import gettext as _
import hashlib
import json
import os
import re
import tarfile


from pulp_npm.common import constants

DEFAULT_CHECKSUM_TYPE = 'sha1'
asciidot = re.compile('\.')
unidot = re.compile(u'\uff0e')


class Package(object):
    """
    This class represents an Npm package.
    """

    TYPE = constants.PACKAGE_TYPE_ID
    # The full list of supported attributes.
    metadata = {}
    attrs = {}

    @classmethod
    def from_archive(cls, archive_path):
        """
        Instantiate a Package using the metadata found inside the Python package found at
        archive_path. This tarball should be the build result of running setup.py sdist on the
        package, and should contain a PKG-INFO file. This method will read the PKG-INFO to determine
        the package's metadata and unit key.

        :param archive_path: A filesystem path to the Python source distribution that this Package
                             will represent.
        :type  archive_path: basestring
        :return:             An instance of Package that represents the package found at
                             archive_path.
        :rtype:              pulp.common.models.Package
        :raises:             ValueError if archive_path does not point to a valid Python tarball
                             created with setup.py sdist.
        :raises:             IOError if the archive_path does not exist.
        """
        try:
            filename = os.path.basename(archive_path)
            checksum = cls.checksum(archive_path)
            package_archive = tarfile.open(archive_path)
            package_file = None
            for member in package_archive.getmembers():
                if re.match('.*/package\.json$', member.name):
                    if package_file:
                        if len(member.name) < len(package_file.name):
                            package_file = member
                    else:
                        package_file = member
            if not package_file:
                msg = _('The archive at %(path)s does not contain a package.json file.')
                msg = msg % {'path': archive_path}
                raise ValueError(msg)

            package_file = package_archive.extractfile(package_file)
            try:
                package_json = json.load(package_file)

                # Check for Name and Version fields in package.json file
                if not set(['name', 'version']).issubset(set(package_json.keys())):
                    msg = _("""The package.json file of archive at %(path)s does not contain 'name'
                               and 'version' attributes which are required.""")
                    msg = msg % {'path': archive_path}
                    raise AttributeError(msg)
                # Read package.json values into Package metadata dictionary
                cls.metadata = package_json
                # So name and version don't get saved twice, once in unit_key and once in metadata
                cls.attrs['name'] = cls.metadata.pop('name', None)
                cls.attrs['version'] = cls.metadata.pop('version', None)
                # Because apparently, some versions have typos / old version schema
                cls.attrs['version'] = cls._sanitize_version(cls.attrs['version'])

            except ValueError:
                msg = _('The package.json file of archive at %(path)s isn\'t a valid JSON file.')
                msg = msg % {'path': archive_path}
                raise ValueError(msg)

            if '_id' in cls.metadata:
                cls.metadata['id'] = cls.metadata.pop('_id', None)
            if '_from' not in cls.metadata:
                cls.metadata['_from'] = '.'
            cls.metadata['_shasum'] = checksum
            cls.metadata['dist'] = {'shasum': checksum}
            cls.metadata['dist']['tarball'] = filename
            cls.attrs['_filename'] = filename
            # TODO Figure out dist -> tarball (Need distributor base URL)
            package = cls()
            return package
        finally:
            if 'package_archive' in locals():
                package_archive.close()

    def init_unit(self, conduit):
        """
        Use the given conduit's init_unit() method to initialize this Unit and store the underlying
        Pulp unit as self._unit.

        :param conduit: A conduit with a suitable init_unit() to create a Pulp Unit.
        :type  conduit: pulp.plugins.conduits.mixins.AddUnitMixin
        """

        relative_path = self._filename
        unit_key = {'name': self.name, 'version': self.version}

        # Removes forbidden characters from keys before inserton to MongoDB
        self._encode_metadata(self.metadata)
        self._unit = conduit.init_unit(self.TYPE, unit_key, self.metadata, relative_path)

    def save_unit(self, conduit):
        """
        Use the given conduit's save_unit() method to save self._unit.

        :param conduit: A conduit with a suitable save_unit() to save self._unit.
        :type  conduit: pulp.plugins.conduits.mixins.AddUnitMixin
        """
        conduit.save_unit(self._unit)

    @property
    def storage_path(self):
        """
        Return the storage path for self._unit.

        :return: The Unit storage path.
        :rtype:  basestring
        """
        return self._unit.storage_path

    @staticmethod
    def checksum(path, algorithm=DEFAULT_CHECKSUM_TYPE):
        """
        Return the checksum of the given path using the given algorithm.

        :param path:      A path to a file
        :type  path:      basestring
        :param algorithm: The hashlib algorithm you wish to use
        :type  algorithm: basestring
        :return:          The file's checksum
        :rtype:           basestring
        """
        chunk_size = 32 * 1024 * 1024
        hasher = getattr(hashlib, algorithm)()
        with open(path) as file_handle:
            bits = file_handle.read(chunk_size)
            while bits:
                hasher.update(bits)
                bits = file_handle.read(chunk_size)
        return hasher.hexdigest()

    @staticmethod
    def _sanitize_version(version):
        word_pos = re.search('[a-zA-Z]', version)
        if word_pos:
            start_pos = word_pos.start()
            if version[start_pos - 1] != '-':
                return version[:start_pos] + '-' + version[start_pos:]
        return version

    @staticmethod
    def _encode_metadata(dictionary):
        keys_with_dot = []
        for key in dictionary:
            if asciidot.search(key):
                keys_with_dot.append(key)
            if type(dictionary[key]) == dict:
                Package._encode_metadata(dictionary[key])
        for key in keys_with_dot:
            dictionary[asciidot.sub(u'\uff0e', key)] = dictionary.pop(key)

    @staticmethod
    def decode_metadata(dictionary):
        keys_with_unidot = []
        for key in dictionary:
            if unidot.search(key):
                keys_with_unidot.append(key)
            if type(dictionary[key]) == dict:
                Package.decode_metadata(dictionary[key])
        for key in keys_with_unidot:
            dictionary[unidot.sub('.', key)] = dictionary.pop(key)

    def __init__(self):
        """
        Initialize self with the given parameters as its attributes.

        """
        for attr in self.attrs:
            setattr(self, attr, self.attrs[attr])

        self._unit = None

    def __repr__(self):
        """
        Return a string representation of self.

        :return: A string representing self.
        :rtype:  basestring
        """
        return 'Npm Package: %(name)s@%(version)s' % {'name': self.name, 'version': self.version}
