from copy import copy
from nipype.interfaces.freesurfer.preprocess import ReconAll
# from arcana.interfaces.utils import DummyReconAll as ReconAll
from nianalysis.requirement import freesurfer_req, ants19_req, fsl5_req
from nianalysis.citation import freesurfer_cites, fsl_cite
from nipype.interfaces import fsl, ants
from arcana.interfaces import utils
from nianalysis.file_format import (
    freesurfer_recon_all_format, nifti_gz_format, text_matrix_format,
    STD_IMAGE_FORMATS)
from arcana.data import FilesetSpec, AcquiredFilesetSpec
from arcana.interfaces.utils import JoinPath
from ..base import MRIStudy
from arcana.study.base import StudyMetaClass
from arcana.parameter import ParameterSpec, SwitchSpec
from nianalysis.atlas import LocalAtlas


class T1Study(MRIStudy, metaclass=StudyMetaClass):

    add_data_specs = [
        FilesetSpec('fs_recon_all', freesurfer_recon_all_format,
                    'freesurfer_pipeline'),
        FilesetSpec('brain', nifti_gz_format, 'brain_extraction_pipeline'),
        # Templates
        AcquiredFilesetSpec('suit_mask', STD_IMAGE_FORMATS,
                            frequency='per_study',
                            default=LocalAtlas('SUIT'))]

    add_parameter_specs = [
        SwitchSpec('bet_method', 'optibet',
                   choices=MRIStudy.parameter_spec('bet_method').choices),
        ParameterSpec('bet_robust', True),
        ParameterSpec('bet_f_threshold', 0.57),
        ParameterSpec('bet_g_threshold', -0.1)]

    def freesurfer_pipeline(self, **mods):
        """
        Segments grey matter, white matter and CSF from T1 images using
        SPM "NewSegment" function.

        NB: Default values come from the W2MHS toolbox
        """
        pipeline = self.pipeline(
            name='segmentation',
            modifications=mods,
            desc="Segment white/grey matter and csf",
            references=copy(freesurfer_cites))

        # FS ReconAll node
        recon_all = pipeline.add(
            'recon_all',
            interface=ReconAll(
                directive='all',
                openmp=self.processor.num_processes),
            inputs={
                'T1_files': ('magnitude', nifti_gz_format)},
            requirements=[freesurfer_req], wall_time=2000)

        # Wrapper around os.path.join
        pipeline.add(
            'join',
            JoinPath(),
            connections={
                'dirname': (recon_all, 'subjects_dir'),
                'filename': (recon_all, 'subject_id')},
            outputs={
                'path': ('fs_recon_all', freesurfer_recon_all_format)})

        return pipeline

    def segmentation_pipeline(self, **mods):
        pipeline = super(T1Study, self).segmentation_pipeline(img_type=1,
                                                              **mods)
        return pipeline

    def bet_T1(self, **mods):

        pipeline = self.pipeline(
            name='BET_T1',
            modifications=mods,
            desc=("python implementation of BET"),
            references=[fsl_cite])

        bias = pipeline.add(
            'n4_bias_correction',
            ants.N4BiasFieldCorrection(),
            inputs={
                'input_image': ('t1', nifti_gz_format)},
            requirements=[ants19_req],
            wall_time=60, memory=12000)

        pipeline.add(
            'bet',
            fsl.BET(frac=0.15, reduce_bias=True),
            connections={
                'in_file': (bias, 'output_image')},
            outputs={
                'out_file': ('betted_T1', nifti_gz_format),
                'mask_file': ('betted_T1_mask', nifti_gz_format)},
            requirements=[fsl5_req], memory=8000, wall_time=45)

        return pipeline

    def cet_T1(self, **mods):
        pipeline = self.pipeline(
            name='CET_T1',
            modifications=mods,
            desc=("Construct cerebellum mask using SUIT template"),
            references=[fsl_cite])

        # FIXME: Should convert to inputs
        nl = self._lookup_nl_tfm_inv_name('MNI')
        linear = self._lookup_l_tfm_to_name('MNI')

        # Initially use MNI space to warp SUIT into T1 and threshold to mask
        merge_trans = pipeline.add(
            'merge_transforms',
            utils.Merge(2),
            inputs={
                'in2': (nl, nifti_gz_format),
                'in1': (linear, nifti_gz_format)})

        apply_trans = pipeline.add(
            'ApplyTransform',
            ants.resampling.ApplyTransforms(
                interpolation='NearestNeighbor',
                input_image_type=3,
                invert_transform_flags=[True, False]),
            inputs={
                'reference_image': ('betted_T1', nifti_gz_format),
                'input_image': ('suit_mask', nifti_gz_format)},
            connections={
                'transforms': (merge_trans, 'out')},
            requirements=[ants19_req], memory=16000, wall_time=120)

        pipeline.add(
            'maths2',
            fsl.utils.ImageMaths(
                suffix='_optiBET_cerebellum',
                op_string='-mas'),
            inputs={
                'in_file': ('betted_T1', nifti_gz_format)},
            connections={
                'in_file2': (apply_trans, 'output_image')},
            outputs={
                'out_file': ('cetted_T1', nifti_gz_format),
                'output_image': ('cetted_T1_mask', nifti_gz_format)},
            requirements=[fsl5_req], memory=16000, wall_time=5)

        return pipeline
