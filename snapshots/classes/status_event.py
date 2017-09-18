import json
import pprint
pp = pprint.PrettyPrinter(indent=4)
import hashlib

class StatusEvent():

    def __init__(
        self,
        m_profile_name,
        m_server,
        m_desc = None,
        m_not_before_date = None,
        m_not_after_date = None,
    ):
        self.profile_name = m_profile_name
        self.server = m_server
        self.desc = m_desc
        self.not_before_date = m_not_before_date
        self.not_after_date = m_not_after_date
        self.digest = self.get_digest()
        self.customer_notified = True

    def get_html(self):
        m_html = ''
        m_html += "<h4>Status Event</h4>\n"
        m_html += "<p>Instance: " + self.instance_id + "<br />\n"
        m_html += 'Email to: ' + self.owner + "<br />" + "\n"
        m_html += "Description: " + self.get_status_desc(m_status_event) + "<br />" + "\n"
        m_html += "Deadline: " + self.get_not_before_date_str() + " -> " + self.get_not_after_date_str() + "<br />" + "\n\n"
        return m_html

    def dump(self):
        pp.pprint(self.__dict__)

    def get_digest(self):
        return hashlib.sha224(self.server.get_instance_id().encode('utf-8') + self.server.get_owner().encode('utf-8') + self.desc.encode('utf-8')).hexdigest()

    def is_complete(self):
        if "Completed" in self.desc: self.completed = True
        else: self.completed = False
        return self.completed

    def get_not_before_date_str(self):
        return self.not_before_date.strftime("%Y-%m-%d %H:%M")

    def get_not_after_date_str(self):
        return self.not_after_date.strftime("%Y-%m-%d %H:%M")

    def set_customer_notified(self, m_flag):
        self.customer_notified = m_flag

    def get_customer_notified(self):
        return self.customer_notified

    def set_complete(self, m_flag=True):
        self.customer_notified = m_flag
