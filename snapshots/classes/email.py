import boto3

class Email:

    debug = False

    def __init__(self, m_ses_profile, m_subject, m_html, m_text, m_email_from, m_email_to):
        self.ses_profile = m_ses_profile
        self.subject = m_subject
        self.body = {}
        if m_html:
            self.body.update({'Html': { 'Charset': 'UTF-8', 'Data': m_html, }})
        if m_text:
            self.body.update({'Text': { 'Charset': 'UTF-8', 'Data': m_text, }})
        self.text = m_text
        self.email_to = m_email_to
        self.email_from = m_email_from
        self.send_email()

    def send_email(self):
        m_session = boto3.Session(profile_name = self.ses_profile)
        m_client = m_session.client('ses')

        m_response = m_client.send_email(
            Source=self.email_from,
            Destination={ 'ToAddresses': self.email_to },
            Message={
                'Subject': { 'Data': self.subject, },
                'Body': self.body,
            }
        )
