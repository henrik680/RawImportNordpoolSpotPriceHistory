from __future__ import absolute_import
import argparse
import logging
import re
import apache_beam as beam
from google.cloud import storage
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.options.pipeline_options import SetupOptions
from RenewalyticsDataflowMetadataLib import *


project_name = 'RawImportNordpoolSpotPriceHistory'

g_schema = {
    'fields': [{
        'name': 'Date', 'type': 'STRING', 'mode': 'REQUIRED'
    }, {
        'name': 'SYS', 'type': 'DECIMAL', 'mode': 'REQUIRED'
    }, {
        'name': 'SE1', 'type': 'DECIMAL', 'mode': 'REQUIRED'
    }, {
        'name': 'SE2', 'type': 'DECIMAL', 'mode': 'REQUIRED'
    }, {
        'name': 'SE3', 'type': 'DECIMAL', 'mode': 'REQUIRED'
    }, {
        'name': 'SE4', 'type': 'DECIMAL', 'mode': 'REQUIRED'
    }, {
        'name': 'FI', 'type': 'DECIMAL', 'mode': 'REQUIRED'
    }, {
        'name': 'DK1', 'type': 'DECIMAL', 'mode': 'REQUIRED'
    }, {
        'name': 'DK2', 'type': 'DECIMAL', 'mode': 'REQUIRED'
    }, {
        'name': 'Oslo', 'type': 'DECIMAL', 'mode': 'REQUIRED'
    }, {
        'name': 'Kr_sand', 'type': 'DECIMAL', 'mode': 'NULLABLE'
    }, {
        'name': 'Bergen', 'type': 'DECIMAL', 'mode': 'NULLABLE'
    }, {
        'name': 'Molde', 'type': 'DECIMAL', 'mode': 'NULLABLE'
    }, {
        'name': 'Tr_heim', 'type': 'DECIMAL', 'mode': 'NULLABLE'
    }, {
        'name': 'Tromso', 'type': 'DECIMAL', 'mode': 'NULLABLE'
    }, {
        'name': 'EE', 'type': 'DECIMAL', 'mode': 'NULLABLE'
    }, {
        'name': 'LV', 'type': 'DECIMAL', 'mode': 'NULLABLE'
    }, {
        'name': 'LT', 'type': 'DECIMAL', 'mode': 'NULLABLE'
    }]
}

g_schema_pre2013 = {
    'fields': [{
        'name': 'Date', 'type': 'STRING', 'mode': 'REQUIRED'
    }, {
        'name': 'SYS', 'type': 'DECIMAL', 'mode': 'REQUIRED'
    }, {
        'name': 'SE', 'type': 'DECIMAL', 'mode': 'NULLABLE'
    }, {
        'name': 'FI', 'type': 'DECIMAL', 'mode': 'NULLABLE'
    }, {
        'name': 'DK1', 'type': 'DECIMAL', 'mode': 'NULLABLE'
    }, {
        'name': 'DK2', 'type': 'DECIMAL', 'mode': 'NULLABLE'
    }, {
        'name': 'Oslo', 'type': 'DECIMAL', 'mode': 'NULLABLE'
    }, {
        'name': 'Kr_sand', 'type': 'DECIMAL', 'mode': 'NULLABLE'
    }, {
        'name': 'Bergen', 'type': 'DECIMAL', 'mode': 'NULLABLE'
    }, {
        'name': 'Molde', 'type': 'DECIMAL', 'mode': 'NULLABLE'
    }, {
        'name': 'Tr_heim', 'type': 'DECIMAL', 'mode': 'NULLABLE'
    }, {
        'name': 'Tromso', 'type': 'DECIMAL', 'mode': 'NULLABLE'
    }]
}


class DataIngestion:
    """A helper class which contains the logic to translate the file into
    a format BigQuery will accept."""

    def __init__(self,year):
        self._year = year

    def parse_method(self, string_input):
        """This method translates a single line of comma separated values to a
        dictionary which can be loaded into BigQuery.
        Args:
            string_input: A comma separated list of values in the form of
                state_abbreviation,gender,year,name,count_of_babies,dataset_created_date
                Example string_input: KS,F,1923,Dorothy,654,11/28/2016
        Returns:
            A dict mapping BigQuery column names as keys to the corresponding value
            parsed from string_input. In this example, the data is not transformed, and
            remains in the same format as the CSV.
         """
        logging.debug("DataIngestion.parse_method(...) started")

        if self._year < 2013:
            data_schema = g_schema_pre2013
        else:
            data_schema = g_schema

        # Strip out carriage return, newline and quote characters.
        values = re.split(";",
                          re.sub('\r\n', '',
                                 re.sub('"', '',
                                        re.sub(',', '.',
                                                         string_input))))
        cols = []
        scehma_fields = data_schema['fields']
        for x in scehma_fields: cols.append(x['name'])
        row = dict(
            zip(cols,
                values))
        logging.debug("DataIngestion.parse_method(...): {}".format(row))
        return row


def run(argv=None, save_main_session=True):
    logging.info("Starting RawImportNordpoolSpotPriceHistory")
    logging.info('argv={}'.format(argv))
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--input',
        dest='input',
        default='gs://dataflow-sample',
        help='Input file to process.')
    parser.add_argument(
        '--output',
        dest='output',
        required=True,
        help='Output file to write results to.')
    known_args, pipeline_args = parser.parse_known_args(argv)
    logging.info('known_args: {}'.format(known_args))
    logging.info('pipeline_args: {}'.format(pipeline_args))

    # We use the save_main_session option because one or more DoFn's in this
    # workflow rely on global context (e.g., a module imported at module level).
    pipeline_options = PipelineOptions(pipeline_args)
    pipeline_options.view_as(SetupOptions).save_main_session = save_main_session

    for year in range(2000, 2022):
        bucket = known_args.input.split('/')[2]  # 'prod-bucket.renewalytics.io'
        blob = known_args.input[-len(known_args.input) + len('gs://') + len(bucket) + 1:] + str(year)
        metadata = {**{'code_module': project_name, 'input': known_args.input,
                       'output': known_args.output, 'updated': datetime.now()},
                    **convert_storage_metadata_to_catalog(get_storage_metadata(storage.Client(), bucket, blob))}
        data_ingestion = DataIngestion(year)
        p = beam.Pipeline(options=PipelineOptions(pipeline_args))
        if year < 2013:
            schema = g_schema_pre2013
            output = known_args.output.split('.')[0] + '.NordpoolPricePre2013SEK'
        else:
            schema = g_schema
            output = known_args.output
        (p

         | 'Read from a File' >> beam.io.ReadFromText(known_args.input + str(year), skip_header_lines=1)
         | 'String To BigQuery Row' >> beam.Map(lambda s: data_ingestion.parse_method(s))
         | 'Write to BigQuery' >> beam.io.Write(
                    # beam.io.BigQuerySink(
                    beam.io.WriteToBigQuery(
                        output,
                        schema=schema,
                        create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED,
                        # Deletes all data in the BigQuery table before writing.
                        write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND)))
        p.run().wait_until_finish()
        write_metadata(dc=datacatalog_v1.DataCatalogClient(), metadata=metadata, table_id=known_args.output.split('.')[-1])


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    run()
