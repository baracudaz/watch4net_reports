#!/usr/local/bin/python

from lib import watch4net
from lib import tabulate
from lib import utils

import logging
import ConfigParser
import argparse

def listPinnedReportPacks(args):
    # Retrieve a list of pinned RPs
    reportpacks = w4n.listPinnedReportPacks()
    print tabulate.tabulate(reportpacks, headers='keys')

def listReportPacks(args):
    # Retrieve a list of all RPs
    reportpacks = w4n.listReportPacks()
    print tabulate.tabulate(reportpacks, headers='keys')

def getReportPack(args):
    # Downloads the specified RP
    reportpacks = w4n.listReportPacks()

    # Resolve the report name from the id
    report_id = args.id
    report_name = ''

    try:
        report_name = utils.search('id', args.id, reportpacks)[0]['name']
    except:
        logging.error('ReportPack ID \'%s\' not found!', report_id)
        exit(1)

    # Download a ReportPack
    report_file = w4n.getReportPack(report_id, report_name)

    if args.x:
        w4n.unzipReportPack(report_file)

def createReportPack(args):
    if args.file:
        result = w4n.createReportPack(args.file)
    elif args.name:
        report_file = w4n.zipReportPack(args.name)
        if report_file:
            result = w4n.createReportPack(report_file)
        else:
            logging.error('ReportPack \'%s\' cannot be created!', args.name)
            exit(1)

    logging.info('ReportPack \'%s\' ID \'%s\' succesfully uploaded', result['name'], result['id'])

def deleteReportPack(args):
    # Downloads the specified RP
    reportpacks = w4n.listReportPacks()

    # Resolve the report name from the id
    report_id = args.id
    report_name = ''

    try:
        report_name = utils.search('id', args.id, reportpacks)[0]['name']
    except:
        logging.error('ReportPack ID \'%s\' not found!', report_id)
        exit(1)

    # Delete ReportPack
    result = w4n.deleteReportPack(report_id, report_name)
    logging.info('ReportPack \'%s\' ID \'%s\' deleted', report_name, report_id)

def parse_args():
    # Command line parsing / Top-level parser
    parser = argparse.ArgumentParser(description='Watch4net ReportPack Management Utility')
    parser.add_argument('-d', '--debug', help='Debugging level (default is info)', required=False, default='info')

    group1 = parser.add_argument_group(title='Credentials stored in config file')
    group1.add_argument('-c', '--conf', help='Config file with credentials (default is config.ini)', required=False, default='config.ini')

    # TODO Implement reading credentials
    #group2 = parser.add_argument_group(title='Credentials set via commnad line')
    #group2.add_argument('-H', '--host', help='Watch4net hostname or IP address', required=False, default='localhost') 
    #group2.add_argument('-u', '--user', help='Watch4net username', required=False, default='admin')
    #group2.add_argument('-p', '--pass', help='Watch4net password', required=False)

    subparsers = parser.add_subparsers()

    # Create parser for 'list' command
    subparser0 = subparsers.add_parser('list', help='Show all ReportPacks')
    subparser0.set_defaults(func=listReportPacks)

    # Create parser for 'listPinnedReportPacks' command
    subparser1 = subparsers.add_parser('pinned', help='Show the currently pinned ReportPacks')
    subparser1.set_defaults(func=listPinnedReportPacks)

    # Create parser for 'get' command
    subparser2 = subparsers.add_parser('get', help='Download the specified ReportPack')
    subparser2.set_defaults(func=getReportPack)
    subparser2.add_argument('-id', help='ReportPack ID', required=True)
    subparser2.add_argument('-x', help='Unzip the ReportPack after download', action='store_true', default=False)

    # Create parser for 'put' command
    subparser3 = subparsers.add_parser('put', help='Upload the specified ReportPack')
    subparser3.set_defaults(func=createReportPack)
    subgroup = subparser3.add_mutually_exclusive_group(required=True)
    subgroup.add_argument('-name', help='ReportPack Name')
    subgroup.add_argument('-file', help='ReportPack File Name')

    # Create parser for 'remove' command
    subparser4 = subparsers.add_parser('remove', help='Delete the specified ReportPack')
    subparser4.set_defaults(func=deleteReportPack)
    subparser4.add_argument('-id', help='ReportPack ID', required=True)

    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()

    if args.debug:
        # Configure logging
        loglevel = args.debug
        numlevel = getattr(logging, loglevel.upper(), None)
        logging.basicConfig(format='%(levelname)s: %(message)s', level=numlevel)

    if args.conf:
        # Read the config file
        config = ConfigParser.ConfigParser()
        config.read(args.conf)
        
        # Wath4net authentication
        hostname = config.get('credentials','hostname')
        username = config.get('credentials','username')
        password = config.get('credentials','password')
        logging.debug('Credentials configured via config file: %s', args.conf)
        logging.debug('Watch4net credentials: %s', config.items('credentials'))

    # Create session to Wath4net
    w4n = watch4net.Client(hostname, username, password)

    args.func(args)  # call the default function
    exit(0)