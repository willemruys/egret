# egret.py: Command line interface for EGRET
#
# Copyright (C) 2016-2018  Eric Larson and Anna Kirk
# elarson@seattleu.edu
#
# This file is part of EGRET.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import threading
import signal
import json
import re
import string
from string import printable
import sys
import time
from xml.etree.ElementInclude import include
import egret_ext
from optparse import OptionParser
import numpy as np
import os
import errno
from functools import wraps

class TimeOutException(Exception):
    def __init__(self, message, errors):
        super(TimeOutException, self).__init__(message)
        self.errors = errors

# Precondition: regexStr successfully compiles and all strings in testStrings
# match the regular expression


def printProgressBar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█', printEnd="\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optifonal  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 *
                                                     (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=printEnd)
    # Print New Line on Complete
    if iteration == total:
        print()


def handle_timout(fn_name):
    print(fn_name)
    raise TimeOutException('Time is up! Moving to next regex.', Exception())


def get_group_info(regexStr, testStrings, namedOnly):
    # check for empty list
    if len(testStrings) == 0:
        return {}

    # compile regex
    regex = re.compile(regexStr)

    # determine if there are named groups, numbered groups, or no groups
    match = regex.fullmatch(testStrings[0])
    if len(match.groupdict()) != 0:
        useNames = True
        names = list(match.groupdict().keys())
        nameList = []
        for name in names:
            r = r"\?P<" + name
            start = re.search(r, regexStr).start()
            nameList.append((start, name))
        nameList = sorted(nameList)
        groupHdr = [name for (start, name) in nameList]
    elif len(match.groups()) != 0:
        if namedOnly:
            return None
        useNames = False
    else:
        return None

    # get groups for each string
    groupDict = {}
    for testStr in testStrings:
        match = regex.match(testStr)
        if useNames:
            g = match.groupdict()
            groupList = []
            for i in groupHdr:
                groupList.append({i: g[i]})
            groupDict[testStr] = groupList
        else:
            groupDict[testStr] = match.groups()

    return groupDict

class TimeoutError(Exception):
    pass
def timeout(seconds, error_message=os.strerror(errno.ETIME)):
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.setitimer(signal.ITIMER_REAL,seconds) #used timer instead of alarm
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result
        return wraps(func)(wrapper)
    return decorator

parser = OptionParser()
parser.add_option("-f", "--file", dest="fileName",
                  help="file containing regex")
parser.add_option("-r", "--regex", dest="regex", help="regular expression")
parser.add_option("-b", "--base_substring", dest="baseSubstring",
                  default="evil", help="base substring for regex strings")
parser.add_option("-o", "--output_file", dest="outputFile",
                  help="output file name")
parser.add_option("-d", "--debug", action="store_true", dest="debugMode",
                  default=False, help="display debug info")
parser.add_option("-s", "--stat", action="store_true", dest="statMode",
                  default=False, help="display stats")
parser.add_option("-g", "--groups", action="store_true", dest="showGroups",
                  default=False, help="show groups")
parser.add_option("-n", "--named_groups", action="store_true", dest="showNamedGroups",
                  default=False, help="only show named groups")
opts, args = parser.parse_args()

# check for valid command lines
if opts.fileName != None and opts.regex != None:
    print("Cannot specify both a regular expression and input file")
    sys.exit(-1)

logFile = open("./tmp/logs.tx", 'w')
# get the regular expression
output = []
descStr = []
regexStrings = []
hasError = False
if opts.fileName != None:
    inFile = open(opts.fileName)

    fileAsJson = json.load(inFile)
    for regexObject in fileAsJson:
        # regexes from stackoverflow and regexlib are stored in array called patterns
        if 'patterns' in regexObject:
            for pattern in regexObject['patterns']:
                regexStrings.append(pattern)
        else:
            regexStrings.append(regexObject['pattern'])
            try:
                descStr.append(regexObject['pattern'])
            except:
                continue
        inFile.close()

# compile the regular expression
l = len(regexStrings)
printProgressBar(0, l, prefix='Progress:', suffix='Complete', length=50)

@timeout(10)
def compile_regex(regexStr):
    output = egret_ext.run(regexStr, opts.baseSubstring,
                  False, False, False, False)
    return output
    
@timeout(10)
def perform_search(inputStr):
    return regex.search(inputStr)

for i, regexStr in enumerate(regexStrings):
    if isinstance(regexStr, str) and len(regexStr) > 0 and len(regexStr) < 501:
        compileRegex = True
        exception = ''
        hasError = False
        try:
            regex = re.compile(regexStr)
            inputStrs = [10]
            inputStrs = compile_regex(regexStr)
            status = inputStrs[0]
            hasError = (status[0:5] == "ERROR")
            # in this case, an error is thrown by EGRET
            if status and status[0:5] == "ERROR":
                output.append({'regex': regexStr, 'exceptionStackTrace': {
                    'exceptionThrownBy': 'EGRET',
                    'exception': status
                },
                    'matches': [], 'nonMatches': []})
                hasError = False
                continue

        # here we catch errors thrown by the re library
        except re.error as e:
            # if e.msg.find('escape') != -1 or e.msg.find('unterminated subpattern') != -1 or e.msg.find('unsupported character') != -1 or e.msg.find('unknown extension') != -1:
            #     exception = e.msg
            #     hasError = True
            #     output.append({'regex': regexStr, 'exception': exception,
            #                   'matches': [], 'exceptionThrownBy': 'Python'})
            #     continue
            output.append({'regex': regexStr, 'exceptionStackTrace': {
                'exceptionThrownBy': 'Python',
                'exception':  e.msg
            },

                'matches': [], })
            hasError = False
            continue
        except TimeoutError:
            print('Timeout!')
            continue
        except Exception as e:
            if len(e.args) > 0:
                output.append({'regex': regexStr, 'exceptionStackTrace': {
                    'exceptionThrownBy': 'EGRET',
                    'exception': e.args[0]
                },
                    'matches': []})
            hasError = False
            continue

        if hasError:
            alerts = [status]
        else:
            idx = 0
            line = inputStrs[idx]
            while line != "BEGIN":
                idx += 1
                line = inputStrs[idx]
            if idx == 0:
                alerts = []
                inputStrs = inputStrs[1:]
            else:
                alerts = inputStrs[:idx]
                inputStrs = inputStrs[idx+1:]
        printProgressBar(i + 1, l, prefix='Progress:',
                         suffix='Complete', length=50)
    matches = []
    nonMatches = []
    try:
        for inputStr in inputStrs:
            search = perform_search(inputStr)
            if search:
                matches.append(inputStr)
            else:
                nonMatches.append(inputStr)
        output.append(
            {'regex': regexStr, 'exceptionStackTrace': None, 'matches': matches, 'nonMatches': nonMatches})
    except:
        # do nothing
        continue

amount_of_splits = 10

splitted = np.array_split(output, amount_of_splits)

for i, split in enumerate(splitted):

    outFile = open(
        "./data/output/stackoverflow/stackoverflow_egret_" + str(i) + ".json", 'w')
    json.dump(list(split), outFile)

if opts.outputFile:
    outFile.close()

sys.exit(0)
