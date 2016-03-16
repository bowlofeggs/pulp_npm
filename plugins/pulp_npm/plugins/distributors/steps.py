from gettext import gettext as _
import json
import os

from pulp.plugins.util.publish_step import AtomicDirectoryPublishStep, PluginStep

from pulp_npm.common import constants
from pulp_npm.plugins.distributors import configuration
from pulp_npm.plugins.models import Package


class PublishContentStep(PluginStep):
    """
    Publish Content
    """

    def __init__(self):
        """
        Initialize the PublishContentStep.
        """
        super(PublishContentStep, self).__init__(constants.PUBLISH_STEP_CONTENT)
        self.context = None
        self.redirect_context = None
        self.description = _('Publishing Npm Content.')

    def process_main(self):
        """
        Publish all the Npm files themselves by creating the symlinks to the storage paths.
        """
        conduit = self.get_conduit()
        packages = conduit.get_units()
        for p in packages:
            relative_path = os.path.join(p.unit_key['name'], '-', p.metadata['dist']['tarball'])
            symlink_path = os.path.join(self.parent.web_working_dir, relative_path)
            if not os.path.exists(os.path.dirname(symlink_path)):
                os.makedirs(os.path.dirname(symlink_path))
            os.symlink(p.storage_path, symlink_path)


class PublishMetadataStep(PluginStep):
    """
    Publish Metadata (refs, branch heads, etc)
    """

    def __init__(self):
        """
        Initialize the PublishMetadataStep.
        """
        super(PublishMetadataStep, self).__init__(constants.PUBLISH_STEP_METADATA)
        self.context = None
        self.redirect_context = None
        self.description = _('Publishing Npm Metadata.')

    def process_main(self):
        """
        Publish all the Npm metadata.
        """

        os.makedirs(self.parent.web_working_dir)

        conduit = self.get_conduit()
        packages = conduit.get_units()
        metadata = self._construct_metadata(packages, self.parent.publish_domain,
                                            self.parent.repo_name)

        for package_name in metadata:
            meta_path = os.path.join(self.parent.web_working_dir, package_name + '.json')
            with open(meta_path, 'w') as meta_file:
                json.dump(metadata[package_name], meta_file)

    @staticmethod
    def _construct_metadata(packages, publish_domain, repo_name):
        """
        Method that reconstructs all the packages metadata into the format required by npm
        """
        # TODO The metadata isn't complete, add as neccessary
        metadata = {}
        # First pass which aggregates the packages by name, inserts simply deducable metadata
        for p in packages:
            if p.unit_key['name'] not in metadata:
                metadata[p.unit_key['name']] = {'versions': {}}

            package_meta = metadata[p.unit_key['name']]
            package_meta['versions'][p.unit_key['version']] = p.metadata.copy()

            version_meta = package_meta['versions'][p.unit_key['version']]
            Package.decode_metadata(version_meta)
            # Because _id is a reserved key in MongoDB
            if 'id' in version_meta:
                version_meta['_id'] = version_meta.pop('id', None)
            else:
                version_meta['_id'] = p.unit_key['name'] + '@' + p.unit_key['version']

            version_meta['version'] = p.unit_key['version']
            version_meta['name'] = p.unit_key['name']
            # TODO add HTTPS
            # The tarball must contain the whole link not just the name of the file
            version_meta['dist']['tarball'] = 'http://' + publish_domain + '/pulp/npm/web/' + \
                                              repo_name + '/' + p.unit_key['name'] + '/-/' + \
                                              version_meta['dist']['tarball']
        # Second pass which inserts metadata for which we need to know all the versions
        # of a given package before we can correctly insert them
        explicit_meta = ['author', 'bugs', 'contributors', 'description', 'homepage', 'keywords',
                         'license', 'maintainers', 'readme', 'readmeFilename', 'repository']

        for package_name in metadata:
            package_meta = metadata[package_name]
            package_meta['name'] = package_name
            package_meta['_id'] = package_name
            package_meta['_attachments'] = {}
            latest = _get_latest_version(package_meta['versions'].keys())
            package_meta['dist-tags'] = {'latest': latest}
            for meta in explicit_meta:
                if meta in package_meta['versions'][latest]:
                    package_meta[meta] = package_meta['versions'][latest][meta]
        return metadata


class NpmPublisher(PluginStep):
    """
    Publisher class that is responsible for the actual publishing
    of a repository via a web server.
    """

    def __init__(self, repo, publish_conduit, config):
        """
        :param repo:            Pulp managed Npm repository
        :type  repo:            pulp.plugins.model.Repository
        :param publish_conduit: Conduit providing access to relative Pulp functionality
        :type  publish_conduit: pulp.plugins.conduits.repo_publish.RepoPublishConduit
        :param config:          Pulp configuration for the distributor
        :type  config:          pulp.plugins.config.PluginCallConfiguration
        """
        super(NpmPublisher, self).__init__(constants.PUBLISH_STEP_PUBLISHER,
                                           repo, publish_conduit, config)

        self.repo_name = repo.id
        publish_dir = configuration.get_web_publish_dir(repo, config)
        self.publish_domain = configuration.get_web_publish_domain(config)
        if not os.path.exists(self.get_working_dir()):
            os.makedirs(self.get_working_dir())
        self.web_working_dir = os.path.join(self.get_working_dir(), repo.id)
        master_publish_dir = configuration.get_master_publish_dir(repo, config)
        atomic_publish_step = AtomicDirectoryPublishStep(self.get_working_dir(),
                                                         [(repo.id, publish_dir)],
                                                         master_publish_dir,
                                                         step_type=constants.PUBLISH_STEP_OVER_HTTP)
        atomic_publish_step.description = _('Making files available via web.')

        self.add_child(PublishMetadataStep())
        self.add_child(PublishContentStep())
        self.add_child(atomic_publish_step)


def _get_latest_version(versions):
    # Removes pre-release versions
    without_pre = [ver for ver in versions if len(ver.split('.')) <= 3]
    if len(without_pre) > 0:
        return sorted(without_pre, cmp=_version_cmp)[-1]
    else:
        return sorted(versions, cmp=_version_cmp)[-1]


def _version_cmp(v1, v2):
    # This function assumes that two exactly same versions will never be compared
    # If this predicate gets broken, the function will fail
    ver1 = v1.split('-')[0].split('.')
    ver2 = v2.split('-')[0].split('.')
    for i in xrange(3):
        if int(ver1[i]) < int(ver2[i]):
            return -1
        elif int(ver1[i]) > int(ver2[i]):
            return 1
    # If function arrives here, the X.X.X of the versions match,
    # therefore a remainder must exist in at least one of them

    # Ensures if a "worded" version is compared with a normal version
    # The normal version is always bigger
    if len(v1.split('-')) > len(v2.split('-')):
        return -1
    elif len(v1.split('-')) < len(v2.split('-')):
        return 1

    rem1 = v1.split('-')[1].split('.')[0]
    rem2 = v2.split('-')[1].split('.')[0]
    if rem1 < rem2:
        return -1
    elif rem1 > rem2:
        return 1
    # If function arrives here, the X.X.X-word of the versions match,
    # therefore a pre-release must be specified in at least one of them

    # Ensures if a pre release version is compared with a released version
    # The pre release is always lower
    if len(v1.split('.')) > len(v2.split('.')):
        return -1
    elif len(v1.split('.')) < len(v2.split('.')):
        return 1

    pre1 = v1.split('.')[-1]
    pre2 = v2.split('.')[-1]
    if int(pre1) < int(pre2):
        return -1
    elif int(pre1) > int(pre2):
        return 1
