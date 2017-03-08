from nianalysis.requirements import fsl5_req, matlab_req
from nianalysis.citations import (
    fsl_cite, matlab_cite, sti_cites)
from nianalysis.data_formats import directory_format, nifti_gz_format
from nianalysis.study.base import set_dataset_specs
from nianalysis.dataset import DatasetSpec
from nianalysis.interfaces.qsm import STI, Prepare
from ..base import MRIStudy
from nipype.interfaces import fsl


class T2StarStudy(MRIStudy):

    def qsm_pipeline(self, **options):  # @UnusedVariable @IgnorePep8
        """
        Segments grey matter, white matter and CSF from T1 images using
        SPM "NewSegment" function.

        NB: Default values come from the STI-Suite
        """
        pipeline = self.create_pipeline(
            name='qsmrecon',
            inputs=[DatasetSpec('kspace', directory_format)],
            # TODO should this be primary?
            outputs=[DatasetSpec('qsm', nifti_gz_format),
                     DatasetSpec('tissue_phase', nifti_gz_format),
                     DatasetSpec('tissue_mask', nifti_gz_format),
                     DatasetSpec('qsm_mask', nifti_gz_format)],
            description="Resolve QSM from t2star kspace",
            default_options={},
            requirements=[fsl5_req, matlab_req],
            citations=[sti_cites, fsl_cite, matlab_cite],
            approx_runtime=100,
            version=1,
            options=options)

        # Prepare and reformat SWI_COILS
        prepare = pipeline.create_node(interface=Prepare(), name='prepare')

        # Brain Mask
        mask = pipeline.create_node(interface=fsl.BET(), name='bet')
        mask.inputs.reduce_bias = True
        mask.inputs.frac = 0.3
        mask.inputs.mask = True

        # Phase and QSM for single echo
        qsmrecon = pipeline.create_node(interface=STI(), name='qsmrecon')

        # Connect inputs/outputs
        pipeline.connect_input('kspace', prepare, 'in_dir')
        pipeline.connect_output('qsm_mask', mask, 'mask_file')
        pipeline.connect_output('qsm', qsmrecon, 'qsm')
        pipeline.connect_output('tissue_phase', qsmrecon, 'tissue_phase')
        pipeline.connect_output('tissue_mask', qsmrecon, 'tissue_mask')

        pipeline.connect(prepare, 'out_file', mask, 'in_file')
        pipeline.connect(mask, 'mask_file', qsmrecon, 'mask_file')
        pipeline.connect(prepare, 'out_dir', qsmrecon, 'in_dir')

        pipeline.assert_connected()
        return pipeline

    _dataset_specs = set_dataset_specs(
        DatasetSpec('kspace', directory_format,
                    description=("Raw reconstructed k-space from T2* image for"
                                 " each coil")),
        DatasetSpec('qsm', nifti_gz_format, qsm_pipeline,
                    description=("Quantitative susceptibility image resolved "
                                 "from T2* coil images")),
        DatasetSpec('tissue_phase', nifti_gz_format, qsm_pipeline,
                    description=("Phase map for each coil following unwrapping"
                                 " and background field removal")),
        DatasetSpec('tissue_mask', nifti_gz_format, qsm_pipeline,
                    description=("Mask for each coil corresponding to areas of"
                                 " high magnitude")),
        DatasetSpec('qsm_mask', nifti_gz_format, qsm_pipeline,
                    description=("Brain mask generated from T2* image")))