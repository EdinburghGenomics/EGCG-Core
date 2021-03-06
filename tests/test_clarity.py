import os
from unittest.mock import patch, Mock
from egcg_core import clarity
from egcg_core.clarity import lims_samples_info
from tests import TestEGCG


def patched(path, **kwargs):
    return patch('egcg_core.clarity.' + path, **kwargs)


def patched_lims(method, return_value=None, side_effect=None):
    return patched('_lims.' + method, return_value=return_value, side_effect=side_effect)


def patched_clarity(func, return_value=None, side_effect=None):
    return patched(func, return_value=return_value, side_effect=side_effect)


class FakeEntity(Mock):
    def __init__(self, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name


class FakeContainer:
    @staticmethod
    def get_placements():
        return {
            'this': Mock(samples=[FakeEntity('a name')]),
            'that': Mock(samples=[FakeEntity('another name')])
        }


class FakeProcess(Mock):
    date_run = 'a_date'
    udf = {}

    @staticmethod
    def all_inputs():
        return [Mock(samples=[FakeEntity('this'), FakeEntity('that')])]

    @staticmethod
    def input_per_sample(sample_name):
        return [Mock(id=sample_name, location=('container', '1:this'), udf={})]

    @staticmethod
    def outputs_per_input(artifact_id, **kwargs):
        return [Mock(container=artifact_id)]


fake_samples = [
    Mock(project=FakeEntity('this'), udf={'Species': 'a_species'}),
    Mock(project=FakeEntity('this'), udf={'Species': 'a_species'}),
    Mock(project=FakeEntity('that'), udf={'Species': 'a_species'})
]


class TestClarity(TestEGCG):
    def setUp(self):
        clarity._lims = Mock()
        clarity.app_logger = Mock()
        clarity._lims_samples_info.clear()

    def test_connection(self):
        clarity._lims = None
        # create connection from config
        lims = clarity.connection()
        assert lims.baseuri == 'a_baseuri/'

        # Check caching
        assert lims is clarity.connection()

        # override caching
        assert lims != clarity.connection(new=True)

        # create connection from config and param
        lims = clarity.connection(new=True, baseuri='second_uri')
        assert lims.baseuri == 'second_uri/'

    @patch('egcg_core.rest_communication.get_document', return_value={'sample_id': 'a_sample'})
    def test_lims_samples_info(self, mock_get_doc):
        assert lims_samples_info('a_sample') == {'sample_id': 'a_sample'}
        assert len(clarity._lims_samples_info) == 1
        assert clarity._lims_samples_info.get('a_sample') == {'sample_id': 'a_sample'}
        mock_get_doc.assert_called_once_with('lims/sample_info', match={'sample_id': 'a_sample'})

    def test_get_valid_lanes(self):
        fake_flowcell = Mock(
            placements={
                '1:this': Mock(udf={'Lane Failed?': False}),
                '2:that': Mock(udf={'Lane Failed?': False}),
                '3:other': Mock(udf={'Lane Failed?': True})
            }
        )
        with patched_lims('get_containers', [fake_flowcell]) as mocked_lims:
            valid_lanes = clarity.get_valid_lanes('a_flowcell_name')
            mocked_lims.assert_called_with(type='Patterned Flowcell', name='a_flowcell_name')
            assert valid_lanes == [1, 2]

    def test_find_project_from_sample(self):
        with patched_clarity('get_samples', fake_samples) as mocked_get_samples:
            project_name = clarity.find_project_name_from_sample('a_sample')
            mocked_get_samples.assert_called_with('a_sample')
            assert project_name is None
            clarity.app_logger.error.assert_called_with('%s projects found for sample %s', 2, 'a_sample')

        with patched_clarity('get_samples', fake_samples[0:1]):
            assert clarity.find_project_name_from_sample('a_sample') == 'this'

    @patched_lims('get_artifacts', [Mock(parent_process=FakeProcess)])
    @patched_clarity('get_sample', FakeEntity('a_sample'))
    def test_find_run_elements_from_sample(self, mocked_get_sample, mocked_get_artifacts):
        assert list(clarity.find_run_elements_from_sample('a_sample')) == [(None, '1')]
        mocked_get_sample.assert_called_with('a_sample')
        mocked_get_artifacts.assert_called_with(sample_name='a_sample', process_type='AUTOMATED - Sequence')

    @patched_clarity('get_species_name', 'Genus species')
    @patched_clarity('get_samples', fake_samples)
    def test_get_species_from_sample(self, mocked_get_samples, mocked_ncbi):
        clarity._lims_samples_info['a_sample_name'] = {'Species': 'genus species'}
        assert clarity.get_species_from_sample('a_sample_name') == 'Genus species'
        mocked_ncbi.assert_called_with('genus species')
        clarity._lims_samples_info['a_sample_name'] = {}

        assert clarity.get_species_from_sample('a_sample_name') == 'Genus species'
        mocked_get_samples.assert_called_with('a_sample_name')
        mocked_ncbi.assert_called_with('a_species')

    def test_get_genome_version(self):
        clarity._lims_samples_info['a_sample_name'] = {'Genome Version': 'hh45'}
        assert clarity.get_genome_version('a_sample_name', species='Homo habilis') == 'hh45'
        clarity._lims_samples_info['a_sample_name'] = {}

        with patched_clarity('get_sample', Mock(udf={'Genome Version': 'hh44'})):
            assert clarity.get_genome_version('a_sample_name', species='Homo habilis') == 'hh44'

        with patched_clarity('get_sample', Mock(udf={})), \
             patch('egcg_core.rest_communication.get_document', return_value={'default_version': 'hh43'}):
            assert clarity.get_genome_version('a_sample_name', species='Homo habilis') == 'hh43'

    def test_sanitize_user_id(self):
        assert clarity.sanitize_user_id('this?that$other another:more') == 'this_that_other_another_more'
        assert clarity.sanitize_user_id('this.that$other another:more') == 'this_that_other_another_more'

    def test_get_list_of_samples(self):
        exp_lims_sample_ids = ['this', 'that:01', 'other _L:01']
        calling_sample_ids = ['this', 'that_01', 'other__L_01']
        fake_list_samples = [[FakeEntity(n)] for n in exp_lims_sample_ids]
        psamples = patched_lims('get_samples', side_effect=fake_list_samples)

        with patched_lims('get_batch'), psamples as mocked_get_samples:
            samples = clarity.get_list_of_samples(calling_sample_ids)
            assert [s.name for s in samples] == exp_lims_sample_ids
            mocked_get_samples.assert_any_call(name=['this', 'that_01', 'other__L_01'])
            mocked_get_samples.assert_any_call(name=['other__L:01', 'that:01'])
            mocked_get_samples.assert_any_call(name=['other _L:01'])

    def test_get_list_of_samples_broken(self):
        exp_lims_sample_ids = ['this', 'that:01', 'other _L:01']
        calling_sample_ids = ['this', 'that_01', 'other__L_01']
        fake_list_samples = [[FakeEntity(n)] for n in exp_lims_sample_ids]
        psamples = patched_lims('get_samples', side_effect=fake_list_samples)
        pwarn = patched('app_logger.warning')

        with patched_lims('get_batch'), psamples as mocked_get_samples, pwarn as mocked_warn:
            samples = clarity.get_list_of_samples(calling_sample_ids + ['sample_not_in_lims'])
            assert [s.name for s in samples] == exp_lims_sample_ids
            mocked_get_samples.assert_any_call(name=['this', 'that_01', 'other__L_01', 'sample_not_in_lims'])
            mocked_get_samples.assert_any_call(name=['other__L:01', 'sample_not_in_lims', 'that:01'])
            mocked_get_samples.assert_any_call(name=['other _L:01', 'sample_not_in_lims'])
            mocked_warn.assert_called_with("Could not find %s in Lims", ['sample_not_in_lims'])

    @patched_lims('get_samples', side_effect=[[], [], [None]])
    def test_get_samples(self, mocked_lims):
        assert clarity.get_samples('a_sample_name__L_01') == [None]
        mocked_lims.assert_any_call(name='a_sample_name__L_01')
        mocked_lims.assert_any_call(name='a_sample_name__L:01')
        mocked_lims.assert_any_call(name='a_sample_name _L:01')

    @patched_clarity('get_samples', return_value=['a sample'])
    def test_get_sample(self, mocked_lims):
        assert clarity.get_sample('a_sample_id') == 'a sample'
        mocked_lims.assert_called_with('a_sample_id')

    @patched_clarity('get_sample', return_value=Mock(udf={'User Sample Name': 'a:user:sample:id'}))
    def test_get_user_sample_name(self, mocked_lims):
        clarity._lims_samples_info['a_sample_id'] = {'User Sample Name': 'uid_sample1'}
        assert clarity.get_user_sample_name('a_sample_id') == 'uid_sample1'
        clarity._lims_samples_info['a_sample_id'] = {}

        assert clarity.get_user_sample_name('a_sample_id') == 'a_user_sample_id'
        mocked_lims.assert_called_with('a_sample_id')

    @patched_clarity('get_sample', return_value=Mock(udf={'Sex': 'unknown'}))
    def test_get_sample_sex(self, mocked_lims):
        clarity._lims_samples_info['a_sample_id'] = {'Sex': 'Male'}
        assert clarity.get_sample_sex('a_sample_id') == 'Male'
        clarity._lims_samples_info['a_sample_id'] = {}

        assert clarity.get_sample_sex('a_sample_id') == 'unknown'
        mocked_lims.assert_called_with('a_sample_id')

    @patched_lims('get_file_contents', 'some test content')
    @patched_clarity('get_sample', Mock(udf={'Genotyping results file id': 1337}))
    def test_get_genotype_information_from_lims(self, mocked_get_sample, mocked_file_contents):
        genotype_vcf = os.path.join(TestEGCG.assets_path, 'a_genotype.vcf')
        assert clarity.get_sample_genotype('a_sample_name', genotype_vcf) == genotype_vcf
        mocked_get_sample.assert_called_with('a_sample_name')
        mocked_file_contents.assert_called_with(id=1337)
        assert open(genotype_vcf).read() == 'some test content'
        os.remove(genotype_vcf)

    @patched_lims('get_processes', ['a_run'])
    def test_get_run(self, mocked_lims):
        assert clarity.get_run('a_run_id') == 'a_run'
        mocked_lims.assert_called_with(type='AUTOMATED - Sequence', udf={'RunID': 'a_run_id'})

    @patched_lims('route_artifacts')
    @patched_clarity('get_list_of_samples', return_value=[Mock(artifact='this'), Mock(artifact='that')])
    @patched_lims('get_workflows', return_value=[Mock(uri='workflow_uri', stages=[Mock(uri='stage_uri')])])
    def test_route_samples_to_delivery_workflow_no_name(self, mocked_get_workflow, mocked_get_list_of_sample, mocked_route):
        clarity.route_samples_to_delivery_workflow(['a_sample_id', 'another_sample_id'])
        mocked_get_workflow.assert_called_with(name='Data Release 1.0')
        mocked_get_list_of_sample.assert_called_with(['a_sample_id', 'another_sample_id'])
        mocked_route.assert_called_with(['this', 'that'], stage_uri='stage_uri')

    @patched_lims('route_artifacts')
    @patched_clarity('get_list_of_samples', return_value=[Mock(artifact='this'), Mock(artifact='that')])
    @patched_lims('get_workflows', return_value=[Mock(uri='workflow_uri', stages=[Mock(uri='stage_uri')])])
    def test_route_samples_to_delivery_workflow_with_name(self, mocked_get_workflow, mocked_get_list_of_sample, mocked_route):
        clarity.route_samples_to_delivery_workflow(['a_sample_id', 'another_sample_id'], workflow_name='Much better workflow')
        mocked_get_workflow.assert_called_with(name='Much better workflow')
        mocked_get_list_of_sample.assert_called_with(['a_sample_id', 'another_sample_id'])
        mocked_route.assert_called_with(['this', 'that'], stage_uri='stage_uri')

    @patched_clarity('get_samples', [Mock(artifact=Mock(location=(FakeEntity('a_plate'), 'a_well')))])
    def test_get_plate_id_and_well_from_lims(self, mocked_lims):
        assert clarity.get_plate_id_and_well('a_sample_id') == ('a_plate', 'a_well')
        mocked_lims.assert_called_with('a_sample_id')

    @patched_lims('get_containers', [FakeContainer])
    def test_get_sample_names_from_plate_from_lims(self, mocked_lims):
        obs = clarity.get_sample_names_from_plate('a_plate_id')
        assert sorted(obs) == ['a_name', 'another_name']
        mocked_lims.assert_called_with(type='96 well plate', name='a_plate_id')

    @patched_lims('get_samples', [FakeEntity('this'), FakeEntity('that')])
    def test_get_sample_names_from_project_from_lims(self, mocked_lims):
        assert clarity.get_sample_names_from_project('a_project') == ['this', 'that']
        mocked_lims.assert_called_with(projectname='a_project')

    @patched_lims('get_processes', [FakeProcess])
    @patched_lims('get_artifacts', [Mock(id='this'), Mock(id='that')])
    @patched_clarity('get_sample', FakeEntity('a_sample_name'))
    def test_get_output_containers_from_sample_and_step_name(self, mocked_get_sample, mocked_get_arts, mocked_get_prcs):
        obs = clarity.get_output_containers_from_sample_and_step_name('a_sample_id', 'a_step_name')
        assert obs == {'a_sample_name'}
        mocked_get_sample.assert_called_with('a_sample_id')
        mocked_get_arts.assert_called_with(sample_name='a_sample_name')
        mocked_get_prcs.assert_called_with(type='a_step_name', inputartifactlimsid=['this', 'that'])

    @patched_clarity('get_sample_names_from_plate', ['this', 'that', 'other'])
    @patched_clarity('get_sample', Mock(artifact=Mock(container=FakeEntity('a_container', type=FakeEntity('96 well plate')))))
    def test_get_samples_arrived_with(self, mocked_get_sample, mocked_names_from_plate):
        assert clarity.get_samples_arrived_with('a_sample_name') == ['this', 'that', 'other']
        mocked_get_sample.assert_called_with('a_sample_name')
        mocked_names_from_plate.assert_called_with('a_container')

    @patched_clarity('get_sample_names_from_plate', ['other'])
    @patched_clarity('get_output_containers_from_sample_and_step_name', [FakeEntity('this'), FakeEntity('that')])
    @patched_clarity('get_sample', FakeEntity('a_sample_name'))
    def test_get_samples_genotyped_with(self, mocked_get_sample, mocked_containers, mocked_names_from_plate):
        assert clarity.get_samples_genotyped_with('a_sample_name') == {'other'}
        mocked_get_sample.assert_called_with('a_sample_name')
        mocked_containers.assert_called_with('a_sample_name', 'Genotyping Plate Preparation EG 1.0')
        mocked_names_from_plate.assert_any_call('this')
        mocked_names_from_plate.assert_any_call('that')

    @patched_clarity('get_sample_names_from_plate', ['other'])
    @patched_clarity('get_output_containers_from_sample_and_step_name', [FakeEntity('this'), FakeEntity('that')])
    @patched_clarity('get_sample', FakeEntity('a_sample_name'))
    def test_get_samples_sequenced_with(self, mocked_get_sample, mocked_containers, mocked_names_from_plate):
        assert clarity.get_samples_sequenced_with('a_sample_name') == {'other'}
        mocked_get_sample.assert_called_with('a_sample_name')
        mocked_containers.assert_called_with('a_sample_name', 'Sequencing Plate Preparation EG 1.0')
        mocked_names_from_plate.assert_any_call('this')
        mocked_names_from_plate.assert_any_call('that')

    @patched_clarity('get_sample', Mock(artifact=Mock(id='an_artifact_id')))
    @patched_lims('get_processes', side_effect=[[FakeProcess], [], [FakeProcess, FakeProcess(date_run='another_date')],
                                                [], [], []])
    def test_get_sample_release_date(self, mocked_get_procs, mocked_get_sample):
        assert clarity.get_sample_release_date('a_sample_name') == 'a_date'
        mocked_get_procs.assert_any_call(type='Data Release EG 1.0', inputartifactlimsid='an_artifact_id')
        mocked_get_procs.assert_any_call(type='Data Release EG 2.0', inputartifactlimsid='an_artifact_id')
        assert mocked_get_procs.call_count == 2
        mocked_get_sample.assert_called_with('a_sample_name')
        mocked_get_procs.reset_mock()
        mocked_get_sample.reset_mock()

        assert clarity.get_sample_release_date('a_sample_name2') == 'another_date'
        clarity.app_logger.warning.assert_called_with(
            '%s Processes found for sample %s: returning latest one', 2, 'a_sample_name2'
        )
        mocked_get_procs.reset_mock()
        mocked_get_sample.reset_mock()

        # get_processes return empty lists
        assert clarity.get_sample_release_date('a_sample_name2') is None

        # Sample does not exist
        mocked_get_sample.return_value = None
        mocked_get_procs.reset_mock()
        mocked_get_sample.reset_mock()
        assert clarity.get_sample_release_date('a_sample_name2') is None

