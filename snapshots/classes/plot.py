import boto3
import numpy as np

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import io

class Plot:

    def __init__(self, m_s3_profile, m_s3_bucket, m_objects, m_stats, m_title, m_y_label, m_filename):
        self.s3_profile = m_s3_profile
        self.s3_bucket = m_s3_bucket
        self.objects = m_objects
        self.stats = m_stats
        self.title = m_title
        self.m_y_label = m_y_label
        self.filename = m_filename
        self.make_plot()


    def make_plot(self):
        y_pos = np.arange(len(self.objects))

        plt.bar(y_pos, self.stats, width=0.35, align='center', alpha=0.5)
        plt.xticks(y_pos, self.objects)
        plt.title(self.title)
        plt.ylabel(self.m_y_label)

        img_data = io.BytesIO()
        plt.savefig(img_data, format='png')
        img_data.seek(0)
        plt.clf()

        m_session = boto3.Session(profile_name = self.s3_profile)
        m_resource = m_session.resource('s3')
        m_bucket = m_resource.Bucket(self.s3_bucket)
        m_bucket.put_object(
            ACL='public-read',
            Body=img_data,
            ContentType='image/png',
            Key=self.filename,
            StorageClass='REDUCED_REDUNDANCY',
        )
