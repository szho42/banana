from itertools import chain
from nipype.pipeline import engine as pe
from nipype.interfaces.spm.preprocess import Coregister
from nianalysis.dataset.base import _create_component_dict
from nianalysis.interfaces.mrtrix import MRConvert
from nianalysis.base import Scan
from nianalysis.formats import nifti_format
from nianalysis.requirements import spm12_req
from nianalysis.citations import spm_cite
from .t1 import T1Dataset
from .t2 import T2Dataset


class T1AndT2Dataset(T1Dataset, T2Dataset):

    def __init__(self, *args, **kwargs):
        T1Dataset.__init__(self, *args, **kwargs)
        T2Dataset.__init__(self, *args, **kwargs)

    def coregistration_pipeline(self):
        pipeline = self._create_pipeline(
            name='coregistration',
            inputs=['t1', 't2'],
            outputs=['t2_coreg'],
            description="Preprocess dMRI datasets using distortion correction",
            options={},
            requirements=[spm12_req],
            citations=[spm_cite],
            approx_runtime=30)
        coreg = pe.Node(Coregister(), name='coreg')
        coreg.inputs.jobtype = 'estwrite'
        coreg.inputs.cost_function = 'nmi'
        coreg.inputs.separation = [4, 2]
        coreg.inputs.tolerance = [
            0.02, 0.02, 0.02, 0.001, 0.001, 0.001, 0.01, 0.01, 0.01, 0.001,
            0.001, 0.001]
        coreg.inputs.fwhm = [7, 7]
        coreg.inputs.write_interp = 4
        coreg.inputs.write_wrap = [0, 0, 0]
        coreg.inputs.write_mask = False
        coreg.inputs.out_prefix = 'r'
        # Connect inputs
        pipeline.connect_input('t1', coreg, 'target')
        pipeline.connect_input('t2', coreg, 'source')
        # Connect outputs
        pipeline.connect_output('t2_coreg', coreg, 'coregistered_source')
        pipeline.assert_connected()
        return pipeline

    _components = _create_component_dict(
        Scan('t1', nifti_format),
        Scan('t2', nifti_format),
        Scan('t2_coreg', nifti_format, coregistration_pipeline),
        inherit_from=chain(T1Dataset.generated_components(),
                           T2Dataset.generated_components()))
