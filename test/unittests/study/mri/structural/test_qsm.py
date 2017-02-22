import logging  # @IgnorePep8
from nipype import config
config.enable_debug_mode()
from nianalysis.dataset import Dataset  # @IgnorePep8
from nianalysis.testing import PipelineTeseCase as TestCase  # @IgnorePep8 @Reimport

from nianalysis.data_formats import zip_format  # @IgnorePep8
from nianalysis.study.mri.structural.t2star_kspace import T2StarKSpaceStudy  # @IgnorePep8

logger = logging.getLogger('NiAnalysis')


class TestQSM(TestCase):

    def test_qsm_pipeline(self):
        study = self.create_study(
            T2StarKSpaceStudy, 'qsm', input_datasets={
                't2starkspace': Dataset('swi_coils', zip_format)})
        study.qsm_pipeline().run(work_dir=self.work_dir)
        self.assertDatasetCreated('qsm.nii.gz')