import boto3
import numpy as np

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import io

class Plot:

    def __init__(self, s3_profile, s3_bucket, objects, stats, title, y_label, filename):
        self.s3_profile = s3_profile
        self.s3_bucket = s3_bucket
        self.objects = objects
        self.stats = stats
        self.title = title
        self.y_label = y_label
        self.filename = filename
        self.make_plot()


    def make_plot(self):
        y_pos = np.arange(len(self.objects))

        plt.bar(y_pos, self.stats, width=0.35, align='center', alpha=0.5)
        plt.xticks(y_pos, self.objects)
        plt.title(self.title)
        plt.ylabel(self.y_label)

        img_data = io.BytesIO()
        plt.savefig(img_data, format='png')
        img_data.seek(0)
        plt.clf()

        session = boto3.Session(profile_name = self.s3_profile)
        resource = session.resource('s3')
        bucket = resource.Bucket(self.s3_bucket)
        bucket.put_object(
            ACL='public-read',
            Body=img_data,
            ContentType='image/png',
            Key=self.filename,
            StorageClass='REDUCED_REDUNDANCY',
        )
