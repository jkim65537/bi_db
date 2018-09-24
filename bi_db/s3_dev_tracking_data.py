import boto3
import pandas as pd
import gzip
import json
from biz_intel_creds import CredsList
dev_s3_creds = CredsList().dev_s3

class S3DevTrackingData():
    def __init__(self):
        self.s3login = boto3.client('s3',
                                    aws_access_key_id=dev_s3_creds['key_id'],
                                    aws_secret_access_key=dev_s3_creds['key'])

    def retrieve_newsletterview_file(self, file_date, download_directory):
        self.s3login.download_file(dev_s3_creds['bucket'],
                                'event_source=NEWSLETTER_VIEW/event_date={0}/'\
                                'newsletter-view-app6.pitchbook.com-{0}.gz'.\
                                    format(file_date), download_directory)

    def retrieve_newsletterlink_file(self, file_date, download_directory):
        self.s3login.download_file(dev_s3_creds['bucket'],
                                'event_source=NEWSLETTER_LINK/event_date={0}/'\
                                'newsletter-link-app6.pitchbook.com-{0}.gz'.\
                                    format(file_date), download_directory)

    def retrieve_platform_usage_file(self, file_date, download_directory):
                            self.s3login.download_file(dev_s3_creds['bucket'],
                            'event_source=PLATFORM/event_date={0}/'\
                            'platform-user-event-app6.pitchbook.com-{0}.gz'.\
                                format(file_date), download_directory)

    def retrieve_mobile_usage_file(self, file_date, download_directory):
        self.s3login.download_file(dev_s3_creds['bucket'],
                                'event_source=MOBILE/event_date={0}/'\
                                'mobile-user-event-app6.pitchbook.com-{0}.gz'.\
                                    format(file_date), download_directory)

    def retrieve_chrome_usage_file(self, file_date, download_directory):
        self.s3login.download_file(dev_s3_creds['bucket'],
                        'event_source=CHROME_PLUGIN/event_date={0}/'\
                        'chrome-plugin-user-event-app6.pitchbook.com-{0}.gz'.\
                            format(file_date), download_directory)

    def gzip_to_dataframe(self, file_location):
        file_name = gzip.open(file_location)
        file_content = file_name.read()
        formatted_file = file_content.split("\n")
        del formatted_file[-1] #Deleting the empty value on the end
        list_of_newsletterviews = []
        for i in formatted_file:
            try:
                list_of_newsletterviews.append(json.loads(i))
            except:
                ValueError("Unable to parse gzip JSON.")
        newsletterviews_dataframe = pd.DataFrame(list_of_newsletterviews)
        file_name.close()
        return newsletterviews_dataframe
