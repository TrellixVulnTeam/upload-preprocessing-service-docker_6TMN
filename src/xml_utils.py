"""
Utilities functions for creating XML files for dbGaP submission
"""
import codecs
import os
import sys
import tarfile
from lxml import etree
from subprocess import call
from src.utilities import silent_remove, write_to_logs

ALIGNMENT_SOFTWARE = {
    2: 'BWA v0.6.2',
    3: 'BWA-mem v0.7.12',
    4: 'STAR'
}

DESIGN_DESC = {
    2: 'The exome capture utilizes the NimbleGen liquid capture on HGSC VCRome 2.1 that targets approximately 34 Mbp of genomic DNA including all coding exons of currently known disease genes (OMIM, HGMD, and GeneTests). To enhance the coverage of clinically relevant disease genes, the spike-in probe set (Exome 3 - PKV2) is used in 1:1.25 equimolar ratio with the VCRome exome capture design',
    3: 'DNA was sonicated to a specific fragment size and prepared as a paired-end library with ligation of Illumina-flowcell specific adapter sequences and a unique barcode. Prepared library was then quality checked for adequate yield through fluorescent methods and quantitative PCR, as well as accurate library size and profile using bioanalysis.',
    4: 'RNA-Seq consists of isolating RNA, converting it to complementary DNA (cDNA), enriching for polyadenylated transcripts or ribo-depletion to remove ribosomal RNAs, preparing the sequencing library and sequencing on an NGS platform.'
}

SEQUENCING_TYPE = {
    2: 'WXS',
    3: 'WGS',
    4: 'RNA-Seq'
}

XML_ACTIONS = [
    {'source': 'experiment.xml', 'schema': 'experiment'},
    {'source': 'run.xml', 'schema': 'run'}
]

XML_CONTACTS = [
    {'name': 'Cecilia Esteves', 'email': 'cecilia_esteves@hms.harvard.edu'},
    {'name': 'John Carmichael', 'email': 'john_carmichael@hms.harvard.edu'},
]


def create_xml_library(
        dna_source, fileservice_uuid, instrument_model, md5_checksum, read_lengths, sample_id, sequence_type,
        upload_file_name):
    """
    Create the library object used for creating the XML files
    """
    try:
        library = {}
        library['attributes'] = [['alignment_software', ALIGNMENT_SOFTWARE[sequence_type]]]
        library['center'] = 'HMS-CC'
        library['design_description'] = DESIGN_DESC[sequence_type]
        library['filename'] = fileservice_uuid
        library['instrument_model'] = instrument_model
        library['library_layout'] = 'PAIRED'
        library['md5_checksum'] = md5_checksum
        library['phs_accession'] = 'phs001232'
        library['platform'] = 'ILLUMINA'
        library['read_lengths'] = make_read_length_list(read_lengths)
        library['reference'] = 'GRCh37/hg19'
        library['sample_id'] = sample_id
        library['selection'] = 'RANDOM'
        library['source'] = 'GENOMIC'
        library['strategy'] = SEQUENCING_TYPE[sequence_type]
        library['title'] = get_title_prefix(sequence_type, dna_source) + sample_id
        library['upload_file_name'] = upload_file_name
        library["latf_load"] = False

        return library
    except Exception as exc:
        error_message = "[ERROR] Step 2 - Processing File: Failed to create XML library object files for {} with error {}".format(
            upload_file_name, exc)
        write_to_logs(error_message)
        raise Exception(error_message)


def xml_indent(elem, level=0):
    """
    Sets proper indent on xml
    """
    try:
        i = "\n" + level*"  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                xml_indent(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i
    except Exception as exc:
        error_message = "[ERROR] Step 2 - Processing File: Failed to indent XML with error {}".format(exc)
        write_to_logs(error_message)
        raise Exception(error_message)


def xml_to_string(xml):
    """
    Properly formats XML as String
    """
    elem = xml.getroot()
    xml_indent(elem)
    return etree.tostring(elem, encoding="utf-8")


def get_title_prefix(sequence_type, dna_source):
    """
    Returns the appropriate title prefix for the BAM xml given
    the sequence type and dnasource of the ExportFile
    """
    title_prefix = {
        2: 'exome sequencing of homo sapiens: whole blood: Sample ',
        3: 'genome sequencing of homo sapiens: whole blood: Sample ',
        4: 'RNA sequencing of homo sapiens: {dna_source}: Sample '.format(dna_source=dna_source)
    }

    return title_prefix[sequence_type] if sequence_type in title_prefix else ''


def make_read_length_list(read_lengths):
    """
    Returns an array of the readlengths stored in the exportfile
    """
    if read_lengths:
        return [int(length) for length in read_lengths.rstrip(' ').rstrip(',').split(',')]

    return []


def format_experiment_xml(library):
    """
    Converts libraries into "experiment_set" ElementTree object
    """
    try:
        xml_exp_set = etree.Element("EXPERIMENT_SET")
        xml_exp = etree.SubElement(xml_exp_set, "EXPERIMENT")
        xml_e_identifiers = etree.SubElement(xml_exp, "IDENTIFIERS")
        xml_e_submitter_id = etree.SubElement(xml_e_identifiers, "SUBMITTER_ID")
        xml_e_submitter_id.set("namespace", library['center'])
        xml_e_submitter_id.text = library["sample_id"]
        xml_title = etree.SubElement(xml_exp, "TITLE")
        xml_title.text = library["title"]
        xml_study_ref = etree.SubElement(xml_exp, "STUDY_REF")
        xml_study_ref.set("accession", library["phs_accession"])
        xml_design = etree.SubElement(xml_exp, "DESIGN")
        xml_des_desc = etree.SubElement(xml_design, "DESIGN_DESCRIPTION")
        xml_des_desc.text = library["design_description"]
        xml_smp_desc = etree.SubElement(xml_design, "SAMPLE_DESCRIPTOR")
        xml_smp_desc.set("refname", library["sample_id"])
        xml_smp_desc.set("refcenter", library["phs_accession"])
        xml_lib_desc = etree.SubElement(xml_design, "LIBRARY_DESCRIPTOR")
        xml_lib_name = etree.SubElement(xml_lib_desc, "LIBRARY_NAME")
        xml_lib_name.text = library["sample_id"]
        xml_lib_strat = etree.SubElement(xml_lib_desc, "LIBRARY_STRATEGY")
        xml_lib_strat.text = library["strategy"]
        xml_lib_src = etree.SubElement(xml_lib_desc, "LIBRARY_SOURCE")
        xml_lib_src.text = library["source"]
        xml_lib_sel = etree.SubElement(xml_lib_desc, "LIBRARY_SELECTION")
        xml_lib_sel.text = library["selection"]
        xml_lib_layout = etree.SubElement(xml_lib_desc, "LIBRARY_LAYOUT")
        etree.SubElement(xml_lib_layout, library["library_layout"])

        if library["read_lengths"]:
            xml_spot_desc = etree.SubElement(xml_design, "SPOT_DESCRIPTOR")
            xml_decode_spec = etree.SubElement(xml_spot_desc, "SPOT_DECODE_SPEC")

            if sum(library["read_lengths"]) > 0:
                xml_spot_len = etree.SubElement(xml_decode_spec, "SPOT_LENGTH")
                xml_spot_len.text = str(sum(library["read_lengths"]))

            for i in range(0, len(library["read_lengths"])):
                xml_read_spec = etree.SubElement(xml_decode_spec, "READ_SPEC")
                xml_read_index = etree.SubElement(xml_read_spec, "READ_INDEX")
                xml_read_index.text = str(i)
                xml_read_class = etree.SubElement(xml_read_spec, "READ_CLASS")
                xml_read_class.text = "Application Read"

                if i == 0:
                    xml_read_type = etree.SubElement(xml_read_spec, "READ_TYPE")
                    xml_read_type.text = "Forward"
                    xml_base_coord = etree.SubElement(xml_read_spec, "BASE_COORD")
                    xml_base_coord.text = "1"
                elif i == 1:
                    xml_read_type = etree.SubElement(xml_read_spec, "READ_TYPE")
                    xml_read_type.text = "Reverse"
                    xml_base_coord = etree.SubElement(xml_read_spec, "BASE_COORD")
                    xml_base_coord.text = str(library["read_lengths"][i - 1] + 1)
                else:
                    sys.exit(5)

        xml_platform = etree.SubElement(xml_exp, "PLATFORM")
        xml_mftr = etree.SubElement(xml_platform, library["platform"])
        xml_model = etree.SubElement(xml_mftr, "INSTRUMENT_MODEL")
        xml_model.text = library["instrument_model"]

        if library["attributes"]:
            xml_e_attributes = etree.SubElement(xml_exp, "EXPERIMENT_ATTRIBUTES")

            for attribute in library["attributes"]:
                xml_e_attribute = etree.SubElement(
                    xml_e_attributes, "EXPERIMENT_ATTRIBUTE")
                xml_tag = etree.SubElement(xml_e_attribute, "TAG")
                xml_tag.text = attribute[0]
                xml_value = etree.SubElement(xml_e_attribute, "VALUE")
                xml_value.text = attribute[1]

        return etree.ElementTree(xml_exp_set)
    except Exception as exc:
        error_message = "[ERROR] Step 2 - Processing File: Failed to format experiment XML with error {}".format(exc)
        write_to_logs(error_message)
        raise Exception(error_message)


def format_run_xml(library):
    """
    Converts libraries into "run_set" ElementTree object
    """
    try:
        xml_run_set = etree.Element("RUN_SET")
        xml_run = etree.SubElement(xml_run_set, "RUN")
        xml_r_identifiers = etree.SubElement(xml_run, "IDENTIFIERS")
        xml_r_submitter_id = etree.SubElement(xml_r_identifiers, "SUBMITTER_ID")
        xml_r_submitter_id.set("namespace", library['center'])
        xml_r_submitter_id.text = library["filename"]
        xml_experiment_ref = etree.SubElement(xml_run, "EXPERIMENT_REF")
        xml_e_identifiers = etree.SubElement(xml_experiment_ref, "IDENTIFIERS")
        xml_e_submitter_id = etree.SubElement(xml_e_identifiers, "SUBMITTER_ID")
        xml_e_submitter_id.set("namespace", library['center'])
        xml_e_submitter_id.text = library["sample_id"]
        xml_data_block = etree.SubElement(xml_run, "DATA_BLOCK")
        xml_files = etree.SubElement(xml_data_block, "FILES")
        xml_file = etree.SubElement(xml_files, "FILE")

        xml_file.set("checksum", library['md5_checksum'])
        xml_file.set("checksum_method", "MD5")
        xml_file.set("filename", library['upload_file_name'])
        xml_file.set("filetype", 'bam')

        if library["reference"] is not None or library["latf_load"]:
            xml_r_attributes = etree.SubElement(xml_run, "RUN_ATTRIBUTES")

            if library["reference"] is not None:
                xml_r_attribute = etree.SubElement(xml_r_attributes, "RUN_ATTRIBUTE")
                xml_tag = etree.SubElement(xml_r_attribute, "TAG")
                xml_tag.text = "assembly"
                xml_value = etree.SubElement(xml_r_attribute, "VALUE")
                xml_value.text = library["reference"]

            if library["latf_load"]:
                xml_r_attribute = etree.SubElement(xml_r_attributes, "RUN_ATTRIBUTE")
                xml_tag = etree.SubElement(xml_r_attribute, "TAG")
                xml_tag.text = "loader"
                xml_value = etree.SubElement(xml_r_attribute, "VALUE")
                xml_value.text = "latf-load"

        return etree.ElementTree(xml_run_set)
    except Exception as exc:
        error_message = "[ERROR] Step 2 - Processing File: Failed to format run XML with error {}".format(exc)
        write_to_logs(error_message)
        raise Exception(error_message)


def format_submission_xml(library):
    """
    Converts a library into a "submission" ElementTree object
    """
    try:
        xml_submission = etree.Element("SUBMISSION")
        xml_submission.set('alias', library['phs_accession'] + '.v2')
        xml_submission.set('center_name', library['center'])
        xml_submission.set(
            'xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
        xml_submission.set(
            'xsi:noNamespaceSchemaLocation',
            'http://www.ncbi.nlm.nih.gov/viewvc/v1/trunk/sra/doc/SRA/SRA.submission.xsd?view=co')

        xml_contacts = etree.SubElement(xml_submission, "CONTACTS")

        for contact in XML_CONTACTS:
            xml_contact = etree.SubElement(xml_contacts, "CONTACT")
            xml_contact.set('name', contact['name'])
            xml_contact.set('inform_on_error', contact['email'])
            xml_contact.set('inform_on_status', contact['email'])

        xml_actions = etree.SubElement(xml_submission, 'ACTIONS')

        for action in XML_ACTIONS:
            xml_action = etree.SubElement(xml_actions, 'ACTION')
            xml_action_add = etree.SubElement(xml_action, 'ADD')
            xml_action_add.set('source', action['source'])
            xml_action_add.set('schema', action['schema'])

        return etree.ElementTree(xml_submission)
    except Exception as exc:
        error_message = "[ERROR] Step 2 - Processing File: Failed to format submission XML with error {}".format(exc)
        write_to_logs(error_message)
        raise Exception(error_message)


def create_and_tar_xml(dna_source, fileservice_uuid, instrument_model, md5_checksum, read_lengths, sample_id, sequence_type, upload_file_name, logger):
    """
    Creates the XML files for the BAM file and
    """
    write_to_logs("Step 2 - Processing File: Creating XML for {}".format(upload_file_name))

    temp_experiment_file = '/scratch/experiment.xml'
    temp_run_file = "/scratch/run.xml"
    temp_submission_file = '/scratch/submission.xml'

    try:
        library = create_xml_library(
            dna_source, fileservice_uuid, instrument_model, md5_checksum, read_lengths, sample_id,
            sequence_type, upload_file_name)

        experiment_xml = xml_to_string(format_experiment_xml(library))
        run_xml = xml_to_string(format_run_xml(library))
        submission_xml = xml_to_string(format_submission_xml(library))

        experiment_file_handle = codecs.open(temp_experiment_file, "w", "utf-8")
        experiment_file_handle.write(codecs.decode(experiment_xml, "utf-8"))
        experiment_file_handle.close()

        run_file_handle = codecs.open(temp_run_file, "w", "utf-8")
        run_file_handle.write(codecs.decode(run_xml, "utf-8"))
        run_file_handle.close()

        submission_file_handle = codecs.open(temp_submission_file, "w", "utf-8")
        submission_file_handle.write(codecs.decode(submission_xml, "utf-8"))
        submission_file_handle.close()
    except Exception as exc:
        error_message = "[ERROR] Step 2 - Processing File: Failed creation of XML files for {} with error {}".format(
            upload_file_name, exc)
        write_to_logs(error_message, logger)
        raise Exception(error_message)

    write_to_logs("Step 2 - Processing File: Validating XML for {}".format(upload_file_name))

    exp_result = call(
        'xmllint --schema http://www.ncbi.nlm.nih.gov/viewvc/v1/trunk/sra/doc/SRA/SRA.experiment.xsd?view=co /scratch/experiment.xml > /dev/null', shell=True)
    run_result = call(
        'xmllint --schema http://www.ncbi.nlm.nih.gov/viewvc/v1/trunk/sra/doc/SRA/SRA.run.xsd?view=co /scratch/run.xml > /dev/null', shell=True)
    sub_result = call(
        'xmllint --schema http://www.ncbi.nlm.nih.gov/viewvc/v1/trunk/sra/doc/SRA/SRA.submission.xsd?view=co /scratch/submission.xml > /dev/null', shell=True)

    if exp_result == 0 and run_result == 0 and sub_result == 0:
        print("Step 2 - Processing File: Successful validation of XML files for {}".format(upload_file_name), flush=True)
    else:
        error_message = "[ERROR] Step 2 - Processing File: Failed validation of XML files for {} - exp_result ==> {}; run_result ==> {}; sub_result ==> {} ".format(
            upload_file_name, exp_result, run_result, sub_result)
        write_to_logs(error_message, logger)
        raise Exception(error_message)

    tar_file_name = os.path.join('/scratch', '{}.tar'.format(upload_file_name))
    tar = tarfile.open(tar_file_name, "w")

    for name in ['/scratch/experiment.xml', '/scratch/run.xml', '/scratch/submission.xml']:
        write_to_logs("Step 2 - Processing File: Adding {} to tar file".format(name))
        try:
            tar.add(name)
        except:
            error_message = "Step 2 - Processing File: Error adding {} to tar file".format(name)
            write_to_logs(error_message, logger)
            raise Exception(error_message)

    tar.close()

    silent_remove(temp_run_file)
    silent_remove(temp_submission_file)
    silent_remove(temp_experiment_file)

    return tar_file_name
