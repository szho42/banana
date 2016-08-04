import os.path
import shutil
from unittest import TestCase
from nipype.pipeline import engine as pe
from nipype.interfaces.utility import IdentityInterface
from nianalysis.archive.local import (
    LocalArchive, LocalSource, LocalSink, LocalSubjectSink, LocalProjectSink)
from nianalysis.formats import nifti_gz_format
from nianalysis.base import Scan
import logging

logger = logging.getLogger('NiAnalysis')


class TestLocalArchive(TestCase):

    PROJECT_ID = 'DUMMYPROJECTID'
    SUBJECT_ID = 'DUMMYSUBJECTID'
    SESSION_ID = 'DUMMYSESSIONID'
    TEST_IMAGE = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '..', '_data', 'test_image.nii.gz'))
    TEST_DIR = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '..', '_data', 'local'))
    BASE_DIR = os.path.abspath(os.path.join(TEST_DIR, 'base_dir'))
    WORKFLOW_DIR = os.path.abspath(os.path.join(TEST_DIR, 'workflow_dir'))

    def setUp(self):
        # Create test data on DaRIS
        self._study_id = None
        # Make cache and working dirs
        shutil.rmtree(self.TEST_DIR, ignore_errors=True)
        os.makedirs(self.WORKFLOW_DIR)
        session_path = os.path.join(
            self.BASE_DIR, self.PROJECT_ID, self.SUBJECT_ID, self.SESSION_ID)
        os.makedirs(session_path)
        for i in xrange(1, 5):
            shutil.copy(self.TEST_IMAGE,
                        os.path.join(session_path,
                                     'source{}.nii.gz'.format(i)))

    def tearDown(self):
        # Clean up working dirs
        shutil.rmtree(self.TEST_DIR, ignore_errors=True)

    def test_archive_roundtrip(self):
        # Create working dirs
        # Create LocalSource node
        archive = LocalArchive(base_dir=self.BASE_DIR)
        # TODO: Should test out other file formats as well.
        source_files = [Scan('source1', nifti_gz_format),
                        Scan('source2', nifti_gz_format),
                        Scan('source3', nifti_gz_format),
                        Scan('source4', nifti_gz_format)]
        sink_files = [Scan('sink1', nifti_gz_format),
                      Scan('sink3', nifti_gz_format),
                      Scan('sink4', nifti_gz_format)]
        inputnode = pe.Node(IdentityInterface(['session']), 'inputnode')
        inputnode.inputs.session = (self.SUBJECT_ID, self.SESSION_ID)
        source = archive.source(self.PROJECT_ID, source_files)
        sink = archive.sink(self.PROJECT_ID, sink_files)
        sink.inputs.name = 'archive_sink'
        sink.inputs.description = (
            "A test study created by archive roundtrip unittest")
        # Create workflow connecting them together
        workflow = pe.Workflow('source_sink_unit_test',
                               base_dir=self.WORKFLOW_DIR)
        workflow.add_nodes((source, sink))
        workflow.connect(inputnode, 'session', source, 'session')
        workflow.connect(inputnode, 'session', sink, 'session')
        for source_file in source_files:
            if not source_file.name.endswith('2'):
                source_name = source_file.name
                sink_name = source_name.replace('source', 'sink')
                workflow.connect(
                    source, source_name + LocalSource.OUTPUT_SUFFIX,
                    sink, sink_name + LocalSink.INPUT_SUFFIX)
        workflow.run()
        # Check cache was created properly
        session_dir = os.path.join(
            self.BASE_DIR, str(self.PROJECT_ID), str(self.SUBJECT_ID),
            str(self.SESSION_ID))
        self.assertEqual(sorted(os.listdir(session_dir)),
                         ['sink1.nii.gz', 'sink3.nii.gz', 'sink4.nii.gz',
                          'source1.nii.gz', 'source2.nii.gz',
                          'source3.nii.gz', 'source4.nii.gz'])

    def test_summary(self):
        # Create working dirs
        # Create LocalSource node
        archive = LocalArchive(base_dir=self.BASE_DIR)
        # TODO: Should test out other file formats as well.
        source_files = [Scan('source1', nifti_gz_format),
                        Scan('source2', nifti_gz_format)]
        inputnode = pe.Node(IdentityInterface(['session']), 'inputnode')
        inputnode.inputs.session = (self.SUBJECT_ID, self.SESSION_ID)
        source = archive.source(self.PROJECT_ID, source_files)
        subject_sink = archive.sink(self.PROJECT_ID,
                                    [Scan('sink1', nifti_gz_format,
                                          multiplicity='per_subject')],
                                    multiplicity='per_subject')
        subject_sink.inputs.name = 'subject_summary'
        subject_sink.inputs.description = (
            "Tests the sinking of subject-wide scans")
        project_sink = archive.sink(self.PROJECT_ID,
                                    [Scan('sink2', nifti_gz_format,
                                          multiplicity='per_project')],
                                    multiplicity='per_project')
        project_sink.inputs.name = 'project_summary'
        project_sink.inputs.description = (
            "Tests the sinking of project-wide scans")
        # Create workflow connecting them together
        workflow = pe.Workflow('summary_unittest',
                               base_dir=self.WORKFLOW_DIR)
        workflow.add_nodes((source, subject_sink, project_sink))
        workflow.connect(inputnode, 'session', source, 'session')
        workflow.connect(inputnode, 'session', project_sink, 'session')
        workflow.connect(
            source, 'source1' + LocalSource.OUTPUT_SUFFIX,
            subject_sink, 'sink1' + LocalSink.INPUT_SUFFIX)
        workflow.connect(
            source, 'source1' + LocalSource.OUTPUT_SUFFIX,
            project_sink, 'sink1' + LocalSink.INPUT_SUFFIX)
        workflow.run()
        # Check cache was created properly
        subject_dir = os.path.join(
            self.BASE_DIR, str(self.PROJECT_ID), str(self.SUBJECT_ID),
            LocalSubjectSink.DIRNAME)
        self.assertEqual(sorted(os.listdir(subject_dir)),
                         ['sink1.nii.gz'])
        project_dir = os.path.join(
            self.BASE_DIR, str(self.PROJECT_ID), LocalProjectSink.DIRNAME)
        self.assertEqual(sorted(os.listdir(project_dir)),
                         ['sink2.nii.gz'])
