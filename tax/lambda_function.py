"""
This is a proof of concept to demonstrate how Alexa might be used to support the bids team.
"""

#from __future__ import print_function
import parseTable
from bs4 import BeautifulSoup
import requests
import boto3
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
import json
import hashlib

response = requests.get('https://aws.amazon.com/tax-help/european-union/').text


def getTaxList():
    hp = parseTable.HTMLTableParser()
    soup = BeautifulSoup(response, 'html.parser')
    table = soup.find_all('table')
    tax_table = hp.parse_html_table(table[0])
    df = tax_table.set_index([0])
    #print('Table: %s' % df)
    return df
# Grab the first table
#    table = soup.find_all('table')[0]
#    taxList = []
#    new_table = pd.DataFrame(columns=range(0, 2), index=[0])
#    row_marker = 0
#    for row in table.find_all('tr'):
#        column_marker = 0
#        columns = row.find_all('td')
#        for column in columns:
#            new_table.iat[row_marker, column_marker] = column.get_text()
#            column_marker += 1
#            row_marker += 1

#    for taxCountry in soup.find_all(class_='table-wrapper section'):
#        serviceUrl = service.a['href']
#        serviceName = service.a.contents[0].strip()
#        serviceList.append({'Country': serviceName,
#                            'Rate': taxRate})
#    return tax_table


def getServiceDescription(serviceUrl):
    response = requests.get(serviceUrl).text
    soup = BeautifulSoup(response, 'html.parser')
    return soup.find('div', {'id': 'aws-page-content'})


def createPdf(serviceUrl):
    outputFilename = '/tmp/service_description.pdf'
    with open(outputFilename, 'w+b') as resultFile:
        pisa.CreatePDF(getServiceDescription(serviceUrl).encode('utf-8'),
                       resultFile)


def findService(serviceName):
    confidenceList = []
    serviceList = getServiceList()
    for service in serviceList:
        service.update({'ratio': fuzz.ratio(service, serviceName)})
        confidenceList.append(service)
    sortedConfidenceList = sorted(confidenceList,
                                  key=itemgetter('ratio'), reverse=True)
    return sortedConfidenceList[0]


def verifyEmail(email):
    client = boto3.client('ses')
    response = client.list_verified_email_addresses()
    if email in response['VerifiedEmailAddresses']:
        return None
    else:
        response = client.verify_email_address(
            EmailAddress=email,
        )
        return True


def getAllParagraphs(url):
    soup = BeautifulSoup(url, 'html.parser')
    paragraphs = []
    content = soup.find(role='main')
    for paragraph in content.find_all('p'):
        if paragraph is not None:
            paragraphs.append(paragraph.text.strip())
    return paragraphs


def getUrlDigest(url):
    m = hashlib.md5()
    m.update(url.content)
    digest = m.hexdigest()
    return digest


def sendEmail(emailAddress, taxCountry, taxRate):
    client = boto3.client('ses')
    if verifyEmail(emailAddress) is None:
        msg = MIMEMultipart()
        msg['Subject'] = 'Here is the VAT rate for ' + taxCountry
        msg['From'] = emailAddress
        msg['To'] = emailAddress

        part = MIMEText('VAT Rate for %s: %s' %
                        (taxCountry, taxRate))
        msg.attach(part)

        result = client.send_raw_email(RawMessage={
            'Data': msg.as_string()
            },
            Source=msg['From'])
        print(result)
        return 'I am emailing you the VAT rate for ' + taxCountry
    else:
        return 'Please go to your mail and verify your email address so we can email you the service description'


def get_user_info(access_token):
    amazonProfileURL = 'https://api.amazon.com/user/profile?access_token='
    r = requests.get(url=amazonProfileURL+access_token)
    if r.status_code == 200:
        return r.json()
    else:
        return False

# --------------- Main handler ------------------


taxRates = {'UK': '20%', 'Germany': '19%', 'France': '20%'}


def lambda_handler(event, context):
    print(event)
    alexa_event = json.loads(event['Records'][0]['Sns']['Message'])
    print(alexa_event)
    #intent = alexa_event['request']['intent']
    slot = alexa_event['request']['intent']['slots']
    tax_dict = getTaxList().to_dict()[1]
    if 'country' in slot.keys():
        taxCountry = slot['country']['value']
        print('We have the country: %s' % taxCountry)
        print('VAT Rate for %s = %s' % (taxCountry, tax_dict[taxCountry]))
    #service_name = intent['slots']['service']['value']
    #emailProfile = get_user_info(alexa_event['session']['user']['accessToken'])['email']
    emailProfile = 'cmking@gmail.com'
    #service = findService(service_name)
    #html = requests.get(service['serviceUrl']).text
    #createPdf(service['serviceUrl'])
    resultResponse = sendEmail(emailProfile, taxCountry, tax_dict[taxCountry])