'''This takes care of uploading to S3 in a multiprocess environment'''
import os
import re
from multiprocessing import get_context

from markov.s3_client import SageS3Client
from markov.log_handler.exception_handler import log_and_exit
from markov.log_handler.constants import (SIMAPP_SIMULATION_WORKER_EXCEPTION,
                                          SIMAPP_EVENT_ERROR_CODE_500)
from markov.metrics.constants import MULTIPROCESS_S3WRITER_POOL

class S3Writer(object):
    '''This takes care of uploading to S3 in a multiprocess environment'''
    def __init__(self, job_info, s3_endpoint_url=None):
        '''s3_dict - Dictionary containing the required s3 info with keys
                     specified by MetricsS3Keys
        '''
        self.job_info = job_info
        self.upload_num = 0
        self.agent_pattern = r'.*agent/|.*agent_\d+/'
        self.s3_endpoint_url=s3_endpoint_url

    def _multiprocess_upload_s3(self, s3_bucket, s3_prefix, aws_region, local_file):
        if os.path.exists(local_file):
            s3_client = SageS3Client(bucket=s3_bucket, s3_prefix=s3_prefix, aws_region=aws_region, s3_endpoint_url=self.s3_endpoint_url)
            s3_keys = "{}/{}/{}-{}".format(s3_prefix, os.path.dirname(re.sub(self.agent_pattern, '', local_file)),
                                           self.upload_num, os.path.basename(local_file))
            print("Uploading {}".format(s3_keys))
            s3_client.upload_file(s3_keys, local_file)
            print("Uploaded {}".format(s3_keys))

    def upload_to_s3(self):
        ''' This will upload all the files provided parallely using multiprocess
        '''
        # Continue uploading other files if one of the file does not exists
        try:
            print("Uploading files to S3:" , self.job_info)
            with get_context("spawn").Pool(MULTIPROCESS_S3WRITER_POOL) as multiprocess_pool:
                multiprocess_pool.starmap(self._multiprocess_upload_s3,
                                      [(job.s3_bucket, job.s3_prefix, job.aws_region, job.local_file)
                                       for job in self.job_info])
                multiprocess_pool.close()
                multiprocess_pool.join()
            
            _ = [os.remove(job.local_file) for job in self.job_info]
            self.upload_num += 1
        except Exception as ex:
            log_and_exit('S3 writer exception: {}'
                             .format(ex), 
                         SIMAPP_SIMULATION_WORKER_EXCEPTION,
                         SIMAPP_EVENT_ERROR_CODE_500)
