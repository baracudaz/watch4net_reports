import operator
import ssl
import urllib
import base64
import http.cookiejar as cookielib
import json
import logging
import zipfile
import os
import re
from lxml import html, etree

ssl._create_default_https_context = ssl._create_unverified_context


class Client:

    def __init__(self, hostname, username, password, reports_path=''):
        self.logged_in = False
        self.username = username
        self.password = password
        self.APG_URL = "http://" + hostname + ":58080/APG/"
        self.WSGW_URL = "https://" + hostname + ":48443/"
        self.soap_headers = {
            "Content-Type": "text/xml;charset=UTF-8",
            "Authorization": f"Basic {base64.b64encode(f'{username}:{password}'.encode()).decode()}"
        }
        self.reports_path = reports_path
        self.cookiejar = cookielib.CookieJar()
        # Use the HTTPCookieProcessor and CookieJar to store the cookies
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookiejar))
        urllib.request.install_opener(opener)

    def _login(self, username, password):
        if not self.logged_in:
            # Connect to server to create session
            try:
                response = urllib.request.urlopen(self.APG_URL + 'empty.html')
            except (urllib.request.HTTPError, urllib.request.URLError) as e:
                logging.error(f"Connection failed due to: {e.reason}")
                self.logged_in = False
                return

            loginParams = {
                'j_username': username,
                'j_password': password
            }

            data = urllib.parse.urlencode(loginParams)

            # Send credentials
            try:
                response = urllib.request.urlopen(
                    self.APG_URL + 'j_security_check', data.encode())
            except (urllib.request.HTTPError, urllib.request.URLError) as e:
                logging.error(f"Connection failed due to: {e.reason}")
                self.logged_in = False
                return

            try:
                json_response = json.loads(response.read())
            except:
                logging.debug('Authorization OK')
                json_response = []

            if ('error' in json_response):
                logging.error('Authorization failed: %s',
                              json_response['error'])
                self.logged_in = False
                return

            self.logged_in = True

    def _checkLogin(self):
        if not self.logged_in:
            self._login(self.username, self.password)

    def listPinnedReportPacks(self):
        self._checkLogin()

        # Get a list of available report pack as HTML
        try:
            response = urllib.request.urlopen(self.APG_URL + 'admin/reports/')
        except (urllib.request.HTTPError, urllib.request.URLError) as e:
            logging.error(f"Connection failed due to: {e.reason}")
            self.logged_in = False
            return

        tree = html.parse(response)
        logging.debug('Parsed HTML table headers:   %s:', tree.xpath(
            '//table[@class="content-table"]/thead/tr/th/text()'))
        logging.debug('Parsed HTML table structure: %s:', tree.xpath(
            '//table[@class="content-table"]/tbody/tr/td/text()'))

        reportpacks = list()
        for row in tree.xpath('//table[@class="content-table"]/tbody/tr'):
            # Populate data for each ReportPack
            reportpack = dict()
            # Look up the reportpack id
            reportpack['id'] = row.get('data-id')
            reportpack['name'] = row.xpath('./td/text()')[0]
            logging.debug('ReportPack: %s', reportpack)
            reportpacks.append(reportpack)

        logging.debug('Complete list of Pinned ReportPacks: %s', reportpacks)

        sorted_reportpacks = sorted(reportpacks, key=lambda k: int(k['id']))

        return sorted_reportpacks

    def getReportPack(self, report_id, report_name):
        soap_data = b"""
            <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
                <soapenv:Header/>
                <soapenv:Body>
                    <getReportPack xmlns="http://www.watch4net.com/APG/Management/MasterAccessorService">
                        <report-pack id="%s" name="%s"/>
                    </getReportPack>
                </soapenv:Body>
            </soapenv:Envelope>
            """ % (report_id, report_name)

        soap_url = self.WSGW_URL + 'Tools/Administration-Tool/Default?disableSSLValidation=true'

        request_object = urllib.request.Request(
            soap_url, soap_data, self.soap_headers)

        # Send the SOAP request
        try:
            response = urllib.request.urlopen(request_object)
        except (urllib.request.HTTPError, urllib.request.URLError) as e:
            logging.error(f"Connection failed due to: {e.reason}")
            self.logged_in = False
            return

        xml = response.read()
        #logging.debug('XML Response: %s', xml)

        tree = etree.fromstring(xml)
        #logging.debug('SOAP Response: \n%s', etree.tostring(tree, pretty_print=True))

        try:
            result = tree.find(
                './/{http://www.watch4net.com/APG/Management/MasterAccessorService}file')
        except:
            logging.error('ReportPack file not downloaded!')
            return None

        decoded_result = base64.b64decode(result.text)
        report_file = self.reports_path + report_name + '.arp'

        logging.info(
            "Downloading the ReportPack '%s' to the file '%s'", report_name, report_file)
        with open(report_file, 'w') as file:
            file.write(decoded_result)

        return report_file

    def unzipReportPack(self, report_file):

        unzip_path = os.path.splitext(report_file)[0]

        if zipfile.is_zipfile(report_file):
            logging.info("Unzipping ReportPack file '%s' to '%s'",
                         report_file, unzip_path)
            unzip = zipfile.ZipFile(report_file)
            unzip.extractall(unzip_path)
            unzip.close()

        # Convert the XML files to pretty
        for root, dirs, files in os.walk(unzip_path):
            for filename in files:
                # Match only the XML files
                if re.search('^.*\.xml$', filename):
                    xml_file = root + '/' + filename
                    logging.debug("Extracting pretty XML file '%s'", xml_file)
                    self.prettyPrintXML(xml_file)

    def prettyPrintXML(self, xml_file):
        assert xml_file is not None
        parser = etree.XMLParser(resolve_entities=False, strip_cdata=False)
        document = etree.parse(xml_file, parser)
        document.write(xml_file, pretty_print=True, encoding='utf-8')

    def zipReportPack(self, report_name):

        zip_path = self.reports_path + report_name
        zip_file = zip_path + '.arp'

        if not os.path.exists(zip_path):
            return None

        logging.info("Creating ReportPack from '%s' to file '%s'",
                     zip_path, zip_file)

        zip = zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED)

        file_list = list()

        for root, dirs, files in sorted(os.walk(zip_path)):
            for filename in files:
                logging.debug(
                    "root '%s', dirs: '%s', Files: '%s'", root, dirs, files)
                file_list.append(os.path.join(root, filename))

        # Find the files in 'META-INF' path
        meta_subs = 'META-INF'
        meta_files = [i for i in file_list if meta_subs in i]

        # Ensure these files are at the begining of the zip
        for meta_file in meta_files:
            file_list.remove(meta_file)
            file_list.insert(0, meta_file)

        for full_path in file_list:
            rel_path = os.path.relpath(full_path, zip_path)
            zip.write(full_path, rel_path)
            logging.debug(
                "Adding file '%s' with full path '%s' to zip file", rel_path, full_path)

        zip.close()

        return zip_file

    def putReportPack(self, report_file):
        # Encode the file
        with open(report_file, "rb") as file:
            encoded_report_file = base64.b64encode(file.read())

        soap_data = b"""
            <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
                <soapenv:Header/>
                <soapenv:Body>
                    <createReportPack xmlns="http://www.watch4net.com/APG/Management/MasterAccessorService">
                        <report-pack>
                            <file>%s</file>
                        </report-pack>
                    </createReportPack>
                </soapenv:Body>
            </soapenv:Envelope>
            """ % (encoded_report_file)

        soap_url = self.WSGW_URL + 'Tools/Administration-Tool/Default?disableSSLValidation=true'

        request_object = urllib.request.Request(
            soap_url, soap_data, self.soap_headers)

        # Send credentials
        try:
            response = urllib.urlopen(request_object)
        except (urllib.HTTPError, urllib.URLError) as e:
            logging.error('Connection failed due to: %s', e.reason)
            self.logged_in = False
            return None

        xml = response.read()
        logging.debug('XML Response: %s', xml)

        tree = etree.fromstring(xml)
        logging.debug('SOAP Response: \n%s',
                      etree.tostring(tree, pretty_print=True))

        try:
            result = tree.find(
                './/{http://www.watch4net.com/APG/Management/MasterAccessorService}createReportPackResponse')
        except:
            logging.error('ReportPack file not uploaded!')
            return None

        return result[0].attrib

    def listReportPacks(self):
        soap_data = b"""
            <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
                <soapenv:Header/>
                <soapenv:Body>
                    <listReportPack xmlns="http://www.watch4net.com/APG/Management/MasterAccessorService">
                    </listReportPack>
                </soapenv:Body>
            </soapenv:Envelope>
            """

        soap_url = self.WSGW_URL + 'Tools/Administration-Tool/Default?disableSSLValidation=true'

        request_object = urllib.request.Request(
            soap_url, soap_data, self.soap_headers)

        # Send credentials
        try:
            response = urllib.request.urlopen(request_object)
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            logging.error('Connection failed due to: %s', e.reason)
            self.logged_in = False
            return None

        xml = response.read()
        logging.debug('XML Response: %s', xml)

        tree = etree.fromstring(xml)
        logging.debug('SOAP Response: \n%s',
                      etree.tostring(tree, pretty_print=True))

        try:
            result = tree.find(
                './/{http://www.watch4net.com/APG/Management/MasterAccessorService}listReportPackResponse')
        except:
            logging.error('ReportPacks not found!')
            return None

        reportpacks = list()
        for row in result:
            # Populate data for each ReportPack
            reportpack = dict()
            # Look up the reportpack id
            reportpack['id'] = row.attrib['id']
            reportpack['name'] = row.attrib['name']
            reportpacks.append(reportpack)
            logging.debug('ReportPack: %s', reportpack)

        sorted_reportpacks = sorted(reportpacks, key=lambda k: int(k['id']))

        return sorted_reportpacks

    def deleteReportPack(self, report_id, report_name):
        soap_data = b"""
            <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
                <soapenv:Header/>
                <soapenv:Body>
                    <deleteReportPack xmlns="http://www.watch4net.com/APG/Management/MasterAccessorService">
                        <report-pack id="%s" name="%s"/>
                    </deleteReportPack>
                </soapenv:Body>
            </soapenv:Envelope>
            """ % (report_id, report_name)

        soap_url = self.WSGW_URL + 'Tools/Administration-Tool/Default?disableSSLValidation=true'

        request_object = urllib.request.Request(
            soap_url, soap_data, self.soap_headers)

        # Send the SOAP request
        try:
            response = urllib.urlopen(request_object)
        except urllib.HTTPError or urllib.URLError as e:
            logging.error('Connection failed due to: %s', e.reason)
            self.logged_in = False
            return

        xml = response.read()
        logging.debug('XML Response: %s', xml)

        tree = etree.fromstring(xml)
        logging.debug('SOAP Response: \n%s',
                      etree.tostring(tree, pretty_print=True))

        try:
            tree.find(
                './/{http://www.watch4net.com/APG/Management/MasterAccessorService}deleteReportPackResponse')
        except:
            logging.error('ReportPack cannot be not deteled!')
            return None

        return report_id
