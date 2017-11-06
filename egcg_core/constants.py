
ELEMENT_RUN_ELEMENT_ID = 'run_element_id'
ELEMENT_RUN_NAME = 'run_id'
ELEMENT_LANE_ID = 'lane_id'
ELEMENT_LANE = 'lane'
ELEMENT_LANE_NUMBER = 'lane_number'
ELEMENT_NUMBER_LANE = 'number_of_lanes'
ELEMENT_BARCODE = 'barcode'
ELEMENT_PROJECT = 'project'
ELEMENT_PROJECT_ID = 'project_id'
ELEMENT_LIBRARY_INTERNAL_ID = 'library_id'
ELEMENT_SAMPLE_INTERNAL_ID = 'sample_id'
ELEMENT_SAMPLES = 'samples'
ELEMENT_NB_READS_SEQUENCED = 'total_reads'
ELEMENT_NB_READS_PASS_FILTER = 'passing_filter_reads'
ELEMENT_PC_READ_IN_LANE = 'pc_reads_in_lane'
ELEMENT_NB_BASE_R1 = 'bases_r1'
ELEMENT_NB_BASE_R2 = 'bases_r2'
ELEMENT_NB_Q30_R1 = 'q30_bases_r1'
ELEMENT_NB_Q30_R2 = 'q30_bases_r2'
ELEMENT_NB_READS_CLEANED = 'clean_reads'  # this implies that the filter has been passed
ELEMENT_NB_BASE_R1_CLEANED = 'clean_bases_r1'
ELEMENT_NB_BASE_R2_CLEANED = 'clean_bases_r2'
ELEMENT_NB_Q30_R1_CLEANED = 'clean_q30_bases_r1'
ELEMENT_NB_Q30_R2_CLEANED = 'clean_q30_bases_r2'
ELEMENT_LANE_PC_OPT_DUP = 'lane_pc_optical_dups'
ELEMENT_FASTQC_REPORT_R1 = 'fastqc_report_r1'
ELEMENT_FASTQC_REPORT_R2 = 'fastqc_report_r2'
ELEMENT_ADAPTER_TRIM_R1 = 'adaptor_bases_removed_r1'
ELEMENT_ADAPTER_TRIM_R2 = 'adaptor_bases_removed_r2'
ELEMENT_TILES_FILTERED = 'tiles_filtered'
ELEMENT_TRIM_R1_LENGTH = 'trim_r1'
ELEMENT_TRIM_R2_LENGTH = 'trim_r2'

ELEMENT_SAMPLE_EXTERNAL_ID = 'user_sample_id'
ELEMENT_SAMPLE_SPECIES = 'species_name'
ELEMENT_SAMPLE_PLATE = 'plate_name'
ELEMENT_SAMPLE_REQUIRED_COVERAGE = 'required_coverage'
ELEMENT_SAMPLE_REQUIRED_YIELD = 'required_yield'
ELEMENT_SAMPLE_REQUIRED_YIELD_Q30 = 'required_yield_q30'
ELEMENT_SAMPLE_GENOME_SIZE = 'genome_size'
ELEMENT_MAPPING_STATISTICS = 'mapping_metrics'
ELEMENT_NB_READS_IN_BAM = 'bam_file_reads'
ELEMENT_NB_MAPPED_READS = 'mapped_reads'
ELEMENT_NB_SEC_MAPPED_READS = 'Nb secondary alignments'
ELEMENT_NB_DUPLICATE_READS = 'duplicate_reads'
ELEMENT_NB_PROPERLY_MAPPED = 'properly_mapped_reads'
ELEMENT_MEDIAN_INSERT_SIZE = 'median_insert_size'
ELEMENT_MEDIAN_ABS_DEV_INSERT_SIZE = 'median_abs_dev_insert_size'
ELEMENT_MEAN_INSERT_SIZE = 'mean_insert_size'
ELEMENT_STD_DEV_INSERT_SIZE = 'std_dev_insert_size'
ELEMENT_MEDIAN_COVERAGE = 'median_coverage'
ELEMENT_SAMTOOLS_MEDIAN_COVERAGE = 'samtools_median_coverage'
ELEMENT_PC_BASES_CALLABLE = 'pc_callable'
ELEMENT_RUN_ELEMENTS = 'run_elements'
ELEMENT_GENDER_VALIDATION = 'gender_validation'
ELEMENT_GENDER_HETX = 'hetX'
ELEMENT_GENDER_COVY = 'covY'
ELEMENT_CALLED_GENDER = 'called_gender'
ELEMENT_PROVIDED_GENDER = 'provided_gender'
ELEMENT_GENOTYPE_VALIDATION = 'genotype_validation'
ELEMENT_NO_CALL_CHIP = 'no_call_chip'
ELEMENT_NO_CALL_SEQ = 'no_call_seq'
ELEMENT_MATCHING = 'matching_snps'
ELEMENT_MISMATCHING = 'mismatching_snps'
ELEMENT_SPECIES_CONTAMINATION = 'species_contamination'
ELEMENT_SAMPLE_CONTAMINATION = 'sample_contamination'
ELEMENT_FREEMIX = 'freemix'
ELEMENT_SNPS_TI_TV = 'ti_tv_ratio'
ELEMENT_SNPS_HET_HOM = 'het_hom_ratio'
ELEMENT_TOTAL_READS_MAPPED = 'total_reads_mapped'
ELEMENT_CONTAMINANT_UNIQUE_MAP = 'contaminant_unique_mapped'
ELEMENT_PCNT_UNMAPPED_FOCAL = 'percent_unmapped_focal'
ELEMENT_PCNT_UNMAPPED = 'percent_unmapped'
ELEMENT_NB_PICARD_DUP_READS = 'picard_dup_reads'
ELEMENT_NB_PICARD_OPT_DUP_READS = 'picard_opt_dup_reads'
ELEMENT_PICARD_EST_LIB_SIZE = 'picard_est_lib_size'
ELEMENT_COVERAGE_STATISTICS = 'coverage'
ELEMENT_MEAN_COVERAGE = 'mean'
ELEMENT_MEDIAN_COVERAGE_SAMTOOLS = 'median'
ELEMENT_COVERAGE_PERCENTILES = 'coverage_percentiles'
ELEMENT_BASES_AT_COVERAGE = 'bases_at_coverage'
ELEMENT_PERCENTILE_5 = 'percentile_5'
ELEMENT_PERCENTILE_25 = 'percentile_25'
ELEMENT_PERCENTILE_50 = 'percentile_50'
ELEMENT_PERCENTILE_75 = 'percentile_75'
ELEMENT_PERCENTILE_95 = 'percentile_95'
ELEMENT_BASES_AT_5X = 'bases_at_5X'
ELEMENT_BASES_AT_15X = 'bases_at_15X'
ELEMENT_BASES_AT_30X = 'bases_at_30X'
ELEMENT_COVERAGE_SD = 'std_dev'
ELEMENT_COVERAGE_EVENNESS = 'evenness'
ELEMENT_REVIEWED = 'reviewed'
ELEMENT_REVIEW_COMMENTS = 'review_comments'
ELEMENT_REVIEW_DATE = 'review_date'
ELEMENT_USEABLE = 'useable'
ELEMENT_USEABLE_COMMENTS = 'useable_comments'
ELEMENT_USEABLE_DATE = 'useable_date'
ELEMENT_DELIVERED = 'delivered'
ELEMENT_DELIVERY_DATE = 'delivery_date'

ELEMENT_FASTQS_DELETED = 'input_fastqs_deleted'

ELEMENT_PROCS = 'analysis_driver_procs'
ELEMENT_PROC_ID = 'proc_id'
ELEMENT_STATUS = 'status'

DATASET_NEW = 'new'
DATASET_READY = 'ready'
DATASET_FORCE_READY = 'force_ready'
DATASET_RESUME = 'resume'
DATASET_PROCESSING = 'processing'
DATASET_PROCESSED_SUCCESS = 'finished'
DATASET_PROCESSED_FAIL = 'failed'
DATASET_ABORTED = 'aborted'
DATASET_REPROCESS = 'reprocess'
DATASET_DELETED = 'deleted'
