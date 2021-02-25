from __future__ import absolute_import
import argparse
import logging
import re
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.options.pipeline_options import SetupOptions

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


class DataIngestion:
    """A helper class which contains the logic to translate the file into
    a format BigQuery will accept."""

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
        data_schema = {
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
            'name': 'Kr_sand', 'type': 'DECIMAL', 'mode': 'REQUIRED'
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
    parser.add_argument(
        '--year',
        dest='year',
        required=True,
        help='Year used to find correct storage blob.')
    known_args, pipeline_args = parser.parse_known_args(argv)
    logging.info('known_args: {}'.format(known_args))
    logging.info('pipeline_args: {}'.format(pipeline_args))

    # We use the save_main_session option because one or more DoFn's in this
    # workflow rely on global context (e.g., a module imported at module level).
    pipeline_options = PipelineOptions(pipeline_args)
    pipeline_options.view_as(SetupOptions).save_main_session = save_main_session

    data_ingestion = DataIngestion()

    p = beam.Pipeline(options=PipelineOptions(pipeline_args))

    (p

     | 'Read from a File' >> beam.io.ReadFromText(known_args.input+known_args.year, skip_header_lines=1)
     | 'String To BigQuery Row' >> beam.Map(lambda s: data_ingestion.parse_method(s))
     | 'Write to BigQuery' >> beam.io.Write(
                # beam.io.BigQuerySink(
                beam.io.WriteToBigQuery(
                    known_args.output,
                    schema=g_schema,
                    create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED,
                    # Deletes all data in the BigQuery table before writing.
                    write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND)))
    p.run().wait_until_finish()


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    run()
