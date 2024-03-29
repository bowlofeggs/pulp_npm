"""
This module contains tests for the pulp_npm.plugins.distributors.steps module.
"""
from gettext import gettext as _
import os
import unittest
from xml.etree import cElementTree as ElementTree

import mock
from pulp.plugins.model import Unit

from pulp_npm.common import constants
from pulp_npm.plugins.distributors import steps


_GET_UNITS_RETURN = [
    Unit(constants.PACKAGE_TYPE_ID, {'name': 'nectar', 'version': '1.2.0'},
         {'_filename': 'nectar-1.2.0.tar.gz', '_checksum': 'abcde', '_checksum_type': 'made_up'},
         '/path/to/nectar-1.2.0.tar.gz'),
    Unit(constants.PACKAGE_TYPE_ID, {'name': 'nectar', 'version': '1.3.1'},
         {'_filename': 'nectar-1.3.1.tar.gz', '_checksum': 'fghij', '_checksum_type': 'made_up'},
         '/path/to/nectar-1.3.1.tar.gz'),
    Unit(constants.PACKAGE_TYPE_ID, {'name': 'pulp_npm_plugins', 'version': '0.0.0'},
         {'_filename': 'pulp_npm_plugins-0.0.0.tar.gz', '_checksum': 'klmno',
          '_checksum_type': 'made_up'},
         '/path/to/pulp_npm_plugins-0.0.0.tar.gz'),
]


class TestPublishContentStep(unittest.TestCase):
    """
    This class contains tests for the PublishContentStep class.
    """
    @mock.patch('pulp_npm.plugins.distributors.steps.PluginStep.__init__')
    def test___init__(self, super___init__):
        """
        Assert correct behavior from the __init__() method.
        """
        step = steps.PublishContentStep()

        super___init__.assert_called_once_with(constants.PUBLISH_STEP_CONTENT)
        self.assertEqual(step.context, None)
        self.assertEqual(step.redirect_context, None)
        self.assertEqual(step.description, _('Publishing Npm Content.'))

    @mock.patch('pulp_npm.plugins.distributors.steps.os.makedirs')
    @mock.patch('pulp_npm.plugins.distributors.steps.os.path.exists')
    @mock.patch('pulp_npm.plugins.distributors.steps.os.symlink')
    def test_process_main(self, symlink, exists, makedirs):
        """
        Assert correct operation from the process_main() method with our _GET_UNITS_RETURN data.
        """
        _seen_paths = []

        def mock_exists(path):
            """
            This mocks the return value of exists to return False the first time a path is given to
            it, and True every time thereafter for that same path.
            """
            if path not in _seen_paths:
                _seen_paths.append(path)
                return False
            return True

        exists.side_effect = mock_exists

        step = steps.PublishContentStep()
        conduit = mock.MagicMock()
        conduit.get_units.return_value = _GET_UNITS_RETURN
        step.get_conduit = mock.MagicMock(return_value=conduit)
        step.parent = mock.MagicMock()
        step.parent.web_working_dir = '/some/path/'

        step.process_main()

        step.get_conduit.assert_called_once_with()
        conduit.get_units.assert_called_once_with()
        # os.path.exists should have been called once for each Unit. It also gets called for a lot
        # of locale stuff, so we'll need to filter those out.
        pulp_exists_calls = [c for c in exists.mock_calls if 'locale' not in c[1][0]]
        self.assertEqual(len(pulp_exists_calls), 3)
        expected_symlink_args = [
            (u.storage_path, steps._get_package_path(u.unit_key['name'], u.metadata['_filename']))
            for u in _GET_UNITS_RETURN]
        expected_symlink_args = [(a[0], os.path.join(step.parent.web_working_dir, a[1]))
                                 for a in expected_symlink_args]
        expected_exists_call_args = [(os.path.dirname(a[1]),) for a in expected_symlink_args]
        actual_exists_call_args = [c[1] for c in pulp_exists_calls]
        self.assertEqual(set(actual_exists_call_args), set(expected_exists_call_args))
        # os.makedirs should only have been called twice, since there are two versions of Nectar and
        # they share a directory. This is also going to be the same set as the exists set.
        self.assertEqual(makedirs.call_count, 2)
        makedirs_call_args = [c[1] for c in makedirs.mock_calls]
        self.assertEqual(set(makedirs_call_args), set(expected_exists_call_args))
        # Lastly, three calls to symlink should have been made, one for each Unit.
        self.assertEqual(symlink.call_count, 3)
        actual_mock_call_args = [c[1] for c in symlink.mock_calls]
        self.assertEqual(set(actual_mock_call_args), set(expected_symlink_args))


class TestPublishMetadataStep(unittest.TestCase):
    """
    Test the PublishMetadataStep class.
    """
    @mock.patch('pulp_npm.plugins.distributors.steps.PluginStep.__init__')
    def test___init__(self, super___init__):
        """
        Assert correct behavior from the __init__() method.
        """
        step = steps.PublishMetadataStep()

        super___init__.assert_called_once_with(constants.PUBLISH_STEP_METADATA)
        self.assertEqual(step.context, None)
        self.assertEqual(step.redirect_context, None)
        self.assertEqual(step.description, _('Publishing Npm Metadata.'))

    @mock.patch('__builtin__.open', autospec=True)
    @mock.patch('pulp_npm.plugins.distributors.steps.os.makedirs')
    @mock.patch('pulp_npm.plugins.distributors.steps.PublishMetadataStep._create_package_index')
    def test_process_main(self, _create_package_index, makedirs, mock_open):
        """
        Assert all the correct calls from process_main().
        """
        step = steps.PublishMetadataStep()
        conduit = mock.MagicMock()
        conduit.get_units.return_value = _GET_UNITS_RETURN
        step.get_conduit = mock.MagicMock(return_value=conduit)
        step.parent = mock.MagicMock()
        step.parent.web_working_dir = '/some/path/'

        step.process_main()

        # Assert correct usage of various mocked items
        step.get_conduit.assert_called_once_with()
        conduit.get_units.assert_called_once_with()
        makedirs.assert_called_once_with(os.path.join(step.parent.web_working_dir, 'simple'))
        mock_open.assert_called_once_with(
            os.path.join(step.parent.web_working_dir, 'simple', 'index.html'), 'w')

        # Assert that the two calls to _create_package_index for each package name are correct
        self.assertEqual(_create_package_index.call_count, 2)
        expected_packages_by_name = steps._get_packages(conduit)
        for call in _create_package_index.mock_calls:
            expected_packages = expected_packages_by_name[call[1][0]]
            self.assertEqual(call[1][1], os.path.join(step.parent.web_working_dir, 'simple'))
            self.assertEqual(call[1][2], expected_packages)
            del expected_packages_by_name[call[1][0]]
        self.assertEqual(expected_packages_by_name, {})

        # Assert that the resulting HTML index is correct
        write = mock_open.return_value.__enter__.return_value
        index_html = write.mock_calls[0][1][0]
        html = ElementTree.fromstring(index_html)
        head = html.find('head')
        title = head.find('title')
        self.assertEqual(title.text, 'Simple Index')
        meta = head.find('meta')
        self.assertEqual(meta.get('name'), 'api-version')
        self.assertEqual(meta.get('value'), '2')
        body = html.find('body')
        # There should be four subelements, two anchors and two breaks
        self.assertEqual(len(body.findall('br')), 2)
        self.assertEqual(len(body.findall('a')), 2)
        anchors = body.findall('a')
        self.assertEqual(set([a.get('href') for a in anchors]),
                         set(['nectar', 'pulp_npm_plugins']))
        self.assertEqual(set([a.text for a in anchors]), set(['nectar', 'pulp_npm_plugins']))

    @mock.patch('__builtin__.open', autospec=True)
    @mock.patch('pulp_npm.plugins.distributors.steps.os.makedirs')
    def test__create_package_index(self, makedirs, mock_open):
        """
        Assert all the correct calls from _create_package_index().
        """
        step = steps.PublishMetadataStep()
        name = 'test_package'
        simple_path = os.path.join('/', 'path', 'to', 'simple')
        packages = [
            {'version': '2.4.3', 'filename': 'test_package-2.4.3.tar.gz', 'checksum': 'sum',
             'checksum_type': 'barlow'},
            {'version': '2.5.0', 'filename': 'test_package-2.5.0.tar.gz', 'checksum': 'different',
             'checksum_type': 'barlow'},
        ]

        step._create_package_index(name, simple_path, packages)

        # Assert the right files and directories are made
        makedirs.assert_called_once_with(os.path.join(simple_path, name))
        mock_open.assert_called_once_with(
            os.path.join(simple_path, name, 'index.html'), 'w')

        # Assert that the resulting HTML index is correct
        write = mock_open.return_value.__enter__.return_value
        index_html = write.mock_calls[0][1][0]
        html = ElementTree.fromstring(index_html)
        head = html.find('head')
        title = head.find('title')
        self.assertEqual(title.text, 'Links for %s' % name)
        meta = head.find('meta')
        self.assertEqual(meta.get('name'), 'api-version')
        self.assertEqual(meta.get('value'), '2')
        body = html.find('body')
        # There should be four subelements, two anchors and two breaks
        self.assertEqual(len(body.findall('br')), 2)
        self.assertEqual(len(body.findall('a')), 2)
        anchors = body.findall('a')
        hrefs = [
            os.path.join('..', '..', steps._get_package_path(name, p['filename'])) +
            '#%s=%s' % (p['checksum_type'], p['checksum']) for p in packages]
        self.assertEqual(set([a.get('href') for a in anchors]), set(hrefs))
        self.assertEqual(set([a.text for a in anchors]), set([p['filename'] for p in packages]))


class TestNpmPublisher(unittest.TestCase):
    """
    This class contains tests for the NpmPublisher object.
    """
    @mock.patch('pulp_npm.plugins.distributors.steps.AtomicDirectoryPublishStep')
    @mock.patch('pulp_npm.plugins.distributors.steps.configuration.get_master_publish_dir')
    @mock.patch('pulp_npm.plugins.distributors.steps.configuration.get_web_publish_dir')
    @mock.patch('pulp_npm.plugins.distributors.steps.os.makedirs')
    @mock.patch('pulp_npm.plugins.distributors.steps.PluginStep.__init__',
                side_effect=steps.PluginStep.__init__, autospec=True)
    @mock.patch('pulp_npm.plugins.distributors.steps.PluginStep.get_working_dir', autospec=True)
    @mock.patch('pulp_npm.plugins.distributors.steps.PublishContentStep')
    @mock.patch('pulp_npm.plugins.distributors.steps.PublishMetadataStep')
    def test___init___working_dir_does_not_exist(
            self, PublishMetadataStep, PublishContentStep, get_working_dir,
            super___init__, makedirs, get_web_publish_dir, get_master_publish_dir,
            AtomicDirectoryPublishStep):
        """
        Assert correct operation from the __init__() method when the working_dir does not exist.
        """
        repo = mock.MagicMock()
        publish_conduit = mock.MagicMock()
        config = mock.MagicMock()
        working_dir = os.path.join('/', 'some', 'working', 'dir')
        get_working_dir.return_value = working_dir
        publish_dir = os.path.join('/', 'some', 'web', 'publish', 'dir')
        get_web_publish_dir.return_value = publish_dir
        master_publish_dir = os.path.join('/', 'some', 'master', 'publish', 'dir')
        get_master_publish_dir.return_value = master_publish_dir

        p = steps.NpmPublisher(repo, publish_conduit, config)

        super___init__.assert_called_once_with(p, constants.PUBLISH_STEP_PUBLISHER, repo,
                                               publish_conduit, config)
        get_web_publish_dir.assert_called_once_with(repo, config)
        makedirs.assert_called_once_with(working_dir)
        AtomicDirectoryPublishStep.assert_called_once_with(
            working_dir, [(repo.id, publish_dir)], master_publish_dir,
            step_type=constants.PUBLISH_STEP_OVER_HTTP)
        self.assertEqual(AtomicDirectoryPublishStep.return_value.description,
                         _('Making files available via web.'))
        self.assertEqual(len(p.children), 3)
        self.assertEqual(
            set(p.children),
            set([AtomicDirectoryPublishStep.return_value, PublishContentStep.return_value,
                 PublishMetadataStep.return_value]))

    @mock.patch('pulp_npm.plugins.distributors.steps.AtomicDirectoryPublishStep')
    @mock.patch('pulp_npm.plugins.distributors.steps.configuration.get_master_publish_dir')
    @mock.patch('pulp_npm.plugins.distributors.steps.configuration.get_web_publish_dir')
    @mock.patch('pulp_npm.plugins.distributors.steps.os.makedirs')
    @mock.patch('pulp_npm.plugins.distributors.steps.os.path.exists', return_value=True)
    @mock.patch('pulp_npm.plugins.distributors.steps.PluginStep.__init__',
                side_effect=steps.PluginStep.__init__, autospec=True)
    @mock.patch('pulp_npm.plugins.distributors.steps.PluginStep.get_working_dir', autospec=True)
    @mock.patch('pulp_npm.plugins.distributors.steps.PublishContentStep')
    @mock.patch('pulp_npm.plugins.distributors.steps.PublishMetadataStep')
    def test___init___working_dir_exists(
            self, PublishMetadataStep, PublishContentStep, get_working_dir,
            super___init__, exists, makedirs, get_web_publish_dir, get_master_publish_dir,
            AtomicDirectoryPublishStep):
        """
        Assert correct operation from the __init__() method when the working_dir does exist.
        """
        repo = mock.MagicMock()
        publish_conduit = mock.MagicMock()
        config = mock.MagicMock()
        working_dir = os.path.join('/', 'some', 'working', 'dir')
        get_working_dir.return_value = working_dir
        publish_dir = os.path.join('/', 'some', 'web', 'publish', 'dir')
        get_web_publish_dir.return_value = publish_dir
        master_publish_dir = os.path.join('/', 'some', 'master', 'publish', 'dir')
        get_master_publish_dir.return_value = master_publish_dir

        p = steps.NpmPublisher(repo, publish_conduit, config)

        super___init__.assert_called_once_with(p, constants.PUBLISH_STEP_PUBLISHER, repo,
                                               publish_conduit, config)
        get_web_publish_dir.assert_called_once_with(repo, config)
        # os.path.exists should have been called once for working_dir. It also gets called for a lot
        # of locale stuff, so we'll need to filter those out.
        pulp_exists_calls = [c for c in exists.mock_calls if 'locale' not in c[1][0]]
        self.assertEqual(len(pulp_exists_calls), 1)
        self.assertEqual(pulp_exists_calls[0][1], (working_dir,))
        self.assertEqual(makedirs.call_count, 0)
        AtomicDirectoryPublishStep.assert_called_once_with(
            working_dir, [(repo.id, publish_dir)], master_publish_dir,
            step_type=constants.PUBLISH_STEP_OVER_HTTP)
        self.assertEqual(AtomicDirectoryPublishStep.return_value.description,
                         _('Making files available via web.'))
        self.assertEqual(len(p.children), 3)
        self.assertEqual(
            set(p.children),
            set([AtomicDirectoryPublishStep.return_value, PublishContentStep.return_value,
                 PublishMetadataStep.return_value]))


class TestGetPackages(unittest.TestCase):
    """
    This class contains tests for the _get_packages() function.
    """
    def test__get_packages(self):
        """
        Assert the correct return value from _get_packages() with the _GET_UNITS_RETURN data set.
        """
        conduit = mock.MagicMock()
        conduit.get_units.return_value = _GET_UNITS_RETURN

        packages = steps._get_packages(conduit)

        expected_packages = {
            'pulp_npm_plugins': [
                {'checksum': 'klmno', 'checksum_type': 'made_up', 'version': '0.0.0',
                 'storage_path': '/path/to/pulp_npm_plugins-0.0.0.tar.gz',
                 'filename': 'pulp_npm_plugins-0.0.0.tar.gz'}],
            'nectar': [
                {'checksum': 'abcde', 'checksum_type': 'made_up', 'version': '1.2.0',
                 'storage_path': '/path/to/nectar-1.2.0.tar.gz', 'filename': 'nectar-1.2.0.tar.gz'},
                {'checksum': 'fghij', 'checksum_type': 'made_up', 'version': '1.3.1',
                 'storage_path': '/path/to/nectar-1.3.1.tar.gz',
                 'filename': 'nectar-1.3.1.tar.gz'}]}
        self.assertEqual(packages, expected_packages)
