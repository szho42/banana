from arcana.data import FilesetSpec, InputFilesets
from banana.file_format import (
    dicom_format, nifti_format, text_format, directory_format,
    zip_format)
from arcana.study.base import Study, StudyMetaClass
from arcana.utils.testing import BaseTestCase
from nipype.interfaces.utility import IdentityInterface


class ConversionStudy(Study, metaclass=StudyMetaClass):

    add_data_specs = [
        FilesetSpec('mrtrix', text_format),
        FilesetSpec('nifti_gz', text_format),
        FilesetSpec('dicom', dicom_format),
        FilesetSpec('directory', directory_format),
        FilesetSpec('zip', zip_format),
        FilesetSpec('nifti_gz_from_dicom', text_format, 'conv_pipeline'),
        FilesetSpec('mrtrix_from_nifti_gz', text_format, 'conv_pipeline'),
        FilesetSpec('nifti_from_mrtrix', nifti_format, 'conv_pipeline'),
        FilesetSpec('directory_from_zip', directory_format, 'conv_pipeline'),
        FilesetSpec('zip_from_directory', zip_format, 'conv_pipeline')]

    def conv_pipeline(self):
        pipeline = self.new_pipeline(
            name='conv_pipeline',
            inputs=[FilesetSpec('mrtrix', text_format),
                    FilesetSpec('nifti_gz', text_format),
                    FilesetSpec('dicom', text_format),
                    FilesetSpec('directory', directory_format),
                    FilesetSpec('zip', directory_format)],
            outputs=[FilesetSpec('nifti_gz_from_dicom', text_format),
                     FilesetSpec('mrtrix_from_nifti_gz', text_format),
                     FilesetSpec('nifti_from_mrtrix', text_format),
                     FilesetSpec('directory_from_zip', directory_format),
                     FilesetSpec('zip_from_directory', directory_format)],
            desc=("A pipeline that tests out various data format "
                         "conversions"),
            citations=[],)
        # Convert from DICOM to NIfTI.gz format on input
        nifti_gz_from_dicom = pipeline.add(
            IdentityInterface(
                "nifti_gz_from_dicom",
                fields=['file']))
        pipeline.connect_input('dicom', nifti_gz_from_dicom,
                               'file')
        pipeline.connect_output('nifti_gz_from_dicom', nifti_gz_from_dicom,
                                'file')
        # Convert from NIfTI.gz to MRtrix format on output
        mrtrix_from_nifti_gz = pipeline.add(
            'mrtrix_from_nifti_gz',
            IdentityInterface(fields=['file']))
        pipeline.connect_input('nifti_gz', mrtrix_from_nifti_gz,
                               'file')
        pipeline.connect_output('mrtrix_from_nifti_gz', mrtrix_from_nifti_gz,
                                'file')
        # Convert from MRtrix to NIfTI format on output
        nifti_from_mrtrix = pipeline.add(
            'nifti_from_mrtrix',
            IdentityInterface(fields=['file']))
        pipeline.connect_input('mrtrix', nifti_from_mrtrix,
                               'file')
        pipeline.connect_output('nifti_from_mrtrix', nifti_from_mrtrix,
                                'file')
        # Convert from zip file to directory format on input
        directory_from_zip = pipeline.add(
            'directory_from_zip',
            IdentityInterface(fields=['file']),)
        pipeline.connect_input('zip', directory_from_zip,
                               'file')
        pipeline.connect_output('directory_from_zip', directory_from_zip,
                                'file')
        # Convert from NIfTI.gz to MRtrix format on output
        zip_from_directory = pipeline.add(
            'zip_from_directory',
            IdentityInterface(fields=['file']))
        pipeline.connect_input('directory', zip_from_directory,
                               'file')
        pipeline.connect_output('zip_from_directory', zip_from_directory,
                                'file')
        return pipeline


class TestFormatConversions(BaseTestCase):

    def test_pipeline_prerequisites(self):
        study = self.create_study(
            ConversionStudy, 'conversion', [
                InputFilesets('mrtrix', 'mrtrix', text_format),
                InputFilesets('nifti_gz', text_format,
                             'nifti_gz'),
                InputFilesets('dicom', dicom_format,
                             't1_mprage_sag_p2_iso_1_ADNI'),
                InputFilesets('directory', directory_format,
                             't1_mprage_sag_p2_iso_1_ADNI'),
                InputFilesets('zip', 'zip', zip_format)])
        study.data('nifti_gz_from_dicom')
        study.data('mrtrix_from_nifti_gz')
        study.data('nifti_from_mrtrix')
        study.data('directory_from_zip')
        study.data('zip_from_directory')
        self.assertFilesetCreated('nifti_gz_from_dicom.nii.gz',
                                  study.name)
        self.assertFilesetCreated('mrtrix_from_nifti_gz.mif',
                                  study.name)
        self.assertFilesetCreated('nifti_from_mrtrix.nii', study.name)
        self.assertFilesetCreated('directory_from_zip', study.name)
        self.assertFilesetCreated('zip_from_directory.zip', study.name)
